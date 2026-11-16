import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent

STOCKS = ["Dostępny w magazynie", "Dostępny za 1–2 tygodnie", "Pobierz licencję"]


def make_catalog(n=95):
    deals = []
    for i in range(n):
        d = {
            "slug": f"product_{i:03d}.htm",
            "name": f"Brand{i % 7} Model {i} Pro",
            "price": 100 + i * 37,
            "stock": STOCKS[i % 3],
        }
        if i % 4 == 0:
            d["discount"] = 10 + i % 50
            d["ref"] = d["price"] + 50
        else:
            d["badge"] = "GIVEAWAY" if i % 5 == 0 else "Deal"
        deals.append(d)
    featured = [dict(deals[1], name="Brand1 Model 1 Pro"), {"slug": "shure_sm58.htm", "name": "Shure SM58 LC", "price": 499, "stock": STOCKS[0], "badge": "GIVEAWAY"}]
    return {"per_page": 40, "advertised": n, "deals": deals, "featured": featured}


class TrackerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        cfg = yaml.safe_load((REPO / "config.yml").read_text(encoding="utf-8"))
        cfg["source"]["delay_seconds"] = 0
        cfg["source"]["concurrency"] = 4
        cfg["source"]["retry_wait_seconds"] = 0.01
        cfg["schedule"]["active_from"] = "2026-11-01"
        cfg["watchlist"]["keywords"] = ["Model 4 ", "Shure"]
        (self.tmp / "config.yml").write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
        shutil.copy(REPO / "README.md", self.tmp / "README.md")
        self.catalog = self.tmp / "catalog.json"
        os.environ["TRACKER_FAKE_SITE"] = str(self.catalog)
        os.environ.pop("FORCE", None)
        import tracker.main as m
        m.ROOT = self.tmp
        self.m = m

    def tearDown(self):
        shutil.rmtree(self.tmp)
        for k in ("TRACKER_FAKE_SITE", "TRACKER_NOW", "FORCE"):
            os.environ.pop(k, None)

    def run_at(self, when, cat, force=False):
        self.catalog.write_text(json.dumps(cat), encoding="utf-8")
        os.environ["TRACKER_NOW"] = when
        if force:
            os.environ["FORCE"] = "1"
        else:
            os.environ.pop("FORCE", None)
        self.assertEqual(self.m.main(), 0)
        return json.loads((self.tmp / "data" / "state.json").read_text())

    def snap(self):
        return json.loads((self.tmp / "data" / "snapshot.json").read_text())

    def test_full_cycle(self):
        cat = make_catalog()
        st = self.run_at("2026-11-16T10:00:00+00:00", cat)
        r = st["last_result"]
        self.assertTrue(r["baseline"])
        self.assertEqual(r["deals"], 96)  # 95 + SM58 that is only in "featured"
        self.assertEqual(r["expected"], 95)
        snap = self.snap()
        d0 = snap["product_000.htm"]
        self.assertEqual(d0["name"], "Brand0 Model 0 Pro")
        self.assertEqual(d0["price"], 100)
        self.assertEqual(d0["ref_price"], 150)
        self.assertEqual(d0["discount"], 10)
        self.assertEqual(d0["stock_state"], "in_stock")
        p1 = snap["product_001.htm"]
        self.assertEqual(p1["stock_state"], "delayed")
        self.assertIsNone(p1["ref_price"])
        self.assertEqual(snap["product_002.htm"]["stock_state"], "download")
        self.assertEqual(snap["product_005.htm"]["badge"], "GIVEAWAY")
        self.assertEqual(snap["product_041.htm"]["price"], 100 + 41 * 37)  # variant-1 tile, absolute URL
        self.assertEqual(snap["shure_sm58.htm"]["price"], 499)
        self.assertTrue(any("Wyróżnione" in s for s in snap["product_001.htm"]["sections"]))
        self.assertTrue(any("Przegląd" in s for s in snap["product_001.htm"]["sections"]))
        for d in snap.values():
            self.assertIsNotNone(d["price"], d)
            self.assertTrue(d["name"], d)

        # too early for the next check (every 3 h) -> skip, nothing changes
        st2 = self.run_at("2026-11-16T11:00:00+00:00", cat)
        self.assertEqual(st2["runs"], 1)

        # 3 h later with changes
        cat2 = json.loads(json.dumps(cat))
        deals = cat2["deals"]
        deals[3]["price"] -= 50          # price drop
        deals[7]["price"] += 20          # price rise
        deals[8]["discount"] = 33        # discount change (was 18)
        deals[4]["stock"] = STOCKS[0]    # delayed -> in stock (product_004)
        removed = [deals.pop(90)["slug"], deals.pop(60)["slug"]]
        deals += [{"slug": f"new_{i}.htm", "name": f"Newbrand X{i}", "price": 999 + i, "stock": STOCKS[0], "discount": 25, "ref": 1400} for i in range(3)]
        st3 = self.run_at("2026-11-16T13:05:00+00:00", cat2)
        c = st3["last_result"]["counts"]
        self.assertEqual(c.get("added"), 3)
        self.assertEqual(c.get("price_down"), 1)
        self.assertEqual(c.get("price_up"), 1)
        self.assertEqual(c.get("discount"), 1)
        self.assertEqual(c.get("back_in_stock"), 1)
        self.assertNotIn("removed", c)  # grace: missing only once so far
        self.assertEqual(self.snap()[removed[0]]["missing_runs"], 1)

        # next check: still missing -> removed
        st4 = self.run_at("2026-11-16T16:05:00+00:00", cat2)
        self.assertEqual(st4["last_result"]["counts"], {"removed": 2})
        self.assertNotIn(removed[0], self.snap())

        # partial scrape (page 2 fails) -> no removals, flagged
        cat3 = json.loads(json.dumps(cat2))
        cat3["fail_pages"] = [2]
        st5 = self.run_at("2026-11-16T19:05:00+00:00", cat3)
        self.assertTrue(st5["last_result"]["partial"])
        self.assertNotIn("removed", st5["last_result"]["counts"])

        # files exist and look right
        readme = (self.tmp / "README.md").read_text()
        self.assertIn("Last check:", readme)
        self.assertIn("Run locally", readme)  # static part kept
        log = (self.tmp / "CHANGELOG.md").read_text()
        self.assertEqual(log.count("\n- **"), 2)
        deals_md = (self.tmp / "deals.md").read_text()
        self.assertIn("Newbrand X0", deals_md)
        wl = (self.tmp / "watchlist.md").read_text()
        self.assertIn("Shure SM58 LC", wl)
        changes = sorted((self.tmp / "changes").glob("*.md"))
        self.assertEqual(len(changes), 2)
        first = changes[0].read_text()
        self.assertIn("Price drops", first)
        self.assertIn("Back in stock", first)
        print("\n----- sample changes report -----\n" + first[:1800])

    def test_parallel_matches_sequential_on_full_size_sale(self):
        import time
        from tracker import scrape as scr
        from tests.fake_site import FakeSession
        cat = make_catalog(1536)
        self.catalog.write_text(json.dumps(cat))
        cfg = yaml.safe_load((self.tmp / "config.yml").read_text())
        results = {}
        for workers in (1, 4):
            cfg["source"]["concurrency"] = workers
            sess = FakeSession(str(self.catalog), latency=0.3)
            t = time.time()
            res = scr.scrape(cfg, session=sess)
            results[workers] = (res, time.time() - t)
        seq, par = results[1][0], results[4][0]
        self.assertEqual(len(seq.deals), 1537)  # 1536 + SM58 only in "featured"
        self.assertEqual(set(seq.deals), set(par.deals))
        self.assertEqual({k: v.price for k, v in seq.deals.items()}, {k: v.price for k, v in par.deals.items()})
        self.assertFalse(par.errors)
        print(f"\\n1536 deals / {seq.pages_fetched} pages: sequential {results[1][1]:.1f}s, 4 parallel {results[4][1]:.1f}s")
        self.assertLess(results[4][1], results[1][1] / 2)

    def test_parallel_page_failure_marks_partial(self):
        from tracker import scrape as scr
        from tests.fake_site import FakeSession
        cat = make_catalog(300)
        cat["fail_pages"] = [3]
        self.catalog.write_text(json.dumps(cat))
        cfg = yaml.safe_load((self.tmp / "config.yml").read_text())
        res = scr.scrape(cfg, session=FakeSession(str(self.catalog)))
        self.assertTrue(res.errors)  # page 3 never loads -> run flagged incomplete
        self.assertEqual(len(res.deals), 301 - 40)  # every other page still scraped

    def test_discord_message_for_new_deals(self):
        from unittest import mock
        sent = []
        fake_post = lambda url, json=None, timeout=None, **kw: sent.append((url, json)) or mock.Mock(status_code=204, text="")
        os.environ.update(DISCORD_WEBHOOK_URL="https://discord.example/webhook", GITHUB_REPOSITORY="me/tracker")
        try:
            with mock.patch("tracker.alerts.requests.post", side_effect=fake_post):
                cat = make_catalog()
                self.run_at("2026-11-16T10:00:00+00:00", cat)
                self.assertEqual(sent, [])  # baseline: no message
                cat["deals"] += [{"slug": f"new_{i}.htm", "name": f"Newbrand X{i}", "price": 999 + i,
                                  "stock": STOCKS[0], "discount": 20 + i, "ref": 1400} for i in range(20)]
                cat["deals"][3]["price"] -= 50  # price drop: not in discord.on by default
                self.run_at("2026-11-16T13:05:00+00:00", cat)
        finally:
            os.environ.pop("DISCORD_WEBHOOK_URL", None)
            os.environ.pop("GITHUB_REPOSITORY", None)
        self.assertEqual(len(sent), 1)
        url, payload = sent[0]
        self.assertEqual(url, "https://discord.example/webhook")
        self.assertIn("20 new deals", payload["content"])
        desc = payload["embeds"][0]["description"]
        self.assertIn("https://github.com/me/tracker/blob/main/deals.md", desc)
        self.assertIn("changes/2026-11-16T1305Z.md", desc)
        self.assertIn("Newbrand X19", desc.splitlines()[0])  # biggest discount first
        self.assertIn("…and 5 more", desc)
        self.assertNotIn("Model 3 Pro", desc)
        print("\n----- discord payload -----\n" + payload["content"] + "\n" + desc)

    def test_throttling_429_loses_no_deals_and_slows_down(self):
        from tracker import scrape as scr
        from tests.fake_site import FakeSession
        cat = make_catalog(1536)
        cat["per_page"] = 20           # what Thomann really serves
        cat["throttle_above"] = 2      # >2 simultaneous requests -> 429
        cat["throttle_times"] = 2      # ...twice per page before it gives in
        self.catalog.write_text(json.dumps(cat))
        cfg = yaml.safe_load((self.tmp / "config.yml").read_text())
        cfg["source"]["concurrency"] = 4
        sess = FakeSession(str(self.catalog), latency=0.02)
        res = scr.scrape(cfg, session=sess)
        self.assertFalse(res.errors, res.errors)
        self.assertEqual(len(res.deals), 1537)
        self.assertTrue(sess.throttled, "test should have triggered 429s")

    def test_page_that_keeps_failing_gets_second_pass_and_rest_still_scraped(self):
        from tracker import scrape as scr
        from tests.fake_site import FakeSession
        cat = make_catalog(300)
        cat["per_page"] = 20
        cat["throttle_pages"] = [4]
        cat["throttle_times"] = 6      # page 4 fails all 5 attempts in the first pass
        self.catalog.write_text(json.dumps(cat))
        cfg = yaml.safe_load((self.tmp / "config.yml").read_text())
        res = scr.scrape(cfg, session=FakeSession(str(self.catalog)))
        self.assertFalse(res.errors, res.errors)       # rescued in the second pass
        self.assertEqual(len(res.deals), 301)          # nothing lost, pages after 4 too

    def test_review_count_before_price_is_not_merged(self):
        from tracker.scrape import Parser
        p = Parser("https://www.thomann.pl/special_cyber-deals.html", "zł|zl|PLN")
        html = ('<html><body><div><a href="adam_audio_t5v.htm">ADAM Audio T5V</a>'
                '<div><span>751</span></div><div><span>599</span><sup>zł</sup></div><div>-23%</div>'
                '<div>najlepsza cena z 30-dni: 775\u00a0zł</div></div></body></html>')
        d = p.parse(html)[0][0]
        self.assertEqual((d.price, d.ref_price, d.discount), (599, 775, 23))

    def test_parser_upgrade_corrects_prices_quietly(self):
        cat = make_catalog()
        self.run_at("2026-11-16T10:00:00+00:00", cat)
        # simulate a snapshot written by the old, buggy parser
        snap = self.snap()
        snap["product_003.htm"].update(price=751211.0, min_price=751211.0, max_price=751211.0)
        (self.tmp / "data" / "snapshot.json").write_text(json.dumps(snap))
        st = json.loads((self.tmp / "data" / "state.json").read_text())
        st.pop("parser_version")
        (self.tmp / "data" / "state.json").write_text(json.dumps(st))
        cat["deals"].append({"slug": "new_q.htm", "name": "Newbrand Q", "price": 500, "stock": STOCKS[0]})
        st = self.run_at("2026-11-16T13:05:00+00:00", cat)
        self.assertEqual(st["last_result"]["counts"], {"added": 1})  # no fake price drop
        self.assertEqual(self.snap()["product_003.htm"]["price"], 211)
        self.assertEqual(self.snap()["product_003.htm"]["min_price"], 211)
        self.assertEqual(st["parser_version"], 2)
        cat["deals"][3]["price"] = 180  # later real changes are reported again
        st = self.run_at("2026-11-16T16:10:00+00:00", cat)
        self.assertEqual(st["last_result"]["counts"], {"price_down": 1})

    def test_zero_deals_fails_and_saves_debug(self):
        cat = {"per_page": 40, "deals": [], "featured": []}
        self.catalog.write_text(json.dumps(cat))
        os.environ["FORCE"] = "1"
        self.assertEqual(self.m.main(), 1)
        self.assertTrue((self.tmp / "debug" / "page1.html").exists())


if __name__ == "__main__":
    unittest.main()
