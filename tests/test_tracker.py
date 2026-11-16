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
        # fixed test settings, not the live config.yml (which the owner edits freely)
        shutil.copy(REPO / "tests" / "config.yml", self.tmp / "config.yml")
        (self.tmp / "README.md").write_text(
            "# Test\n\n<!-- DASHBOARD:START -->\n<!-- DASHBOARD:END -->\n\n## Run locally\n", encoding="utf-8")
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
        from tracker import scrape as scr
        from tests.fake_site import FakeSession
        cat = make_catalog(1536)
        self.catalog.write_text(json.dumps(cat))
        cfg = yaml.safe_load((self.tmp / "config.yml").read_text())
        results = {}
        for workers in (1, 4):
            cfg["source"]["concurrency"] = workers
            sess = FakeSession(str(self.catalog), latency=0.02)
            results[workers] = (scr.scrape(cfg, session=sess), sess.max_in_flight)
        seq, par = results[1][0], results[4][0]
        self.assertEqual(len(seq.deals), 1537)  # 1536 + SM58 only in "featured"
        self.assertEqual(set(seq.deals), set(par.deals))
        self.assertEqual({k: v.price for k, v in seq.deals.items()}, {k: v.price for k, v in par.deals.items()})
        self.assertFalse(par.errors)
        self.assertEqual(results[1][1], 1)                 # one request at a time
        self.assertTrue(2 <= results[4][1] <= 4, results)  # really in parallel, never more than asked

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

    def test_short_wait_stock_label_is_recognised(self):
        from tracker.scrape import Parser
        p = Parser("https://www.thomann.pl/special_cyber-deals.html", "zł|zl|PLN")
        html = ('<html><body><h2>Przegląd wszystkich 1535 ofert</h2><div><a href="ableton_move.htm">Ableton Move</a>'
                '<div><span>1 699 zł</span></div><div>-21%</div><div>najlepsza cena z 30-dni: 2 155 zł</div>'
                '<div>Krótki czas oczekiwania (zazwyczaj 2-5 dni)</div></div></body></html>')
        d = p.parse(html)[0][0]
        self.assertEqual((d.price, d.ref_price, d.stock_state), (1699, 2155, "delayed"))
        self.assertEqual(d.stock, "Krótki czas oczekiwania (zazwyczaj 2-5 dni)")
        self.assertEqual(d.sections, ["Przegląd wszystkich ofert"])  # no deal count in the name
        self.assertFalse(hasattr(d, "old_price"))

    def test_sections_do_not_pile_up_between_checks(self):
        cat = make_catalog()
        self.run_at("2026-11-16T10:00:00+00:00", cat)
        before = self.snap()["product_001.htm"]["sections"]
        for i, when in enumerate(("13:05", "16:10", "19:15")):
            cat["advertised"] = 95 + i + 1  # the heading's count changes on every check
            self.run_at(f"2026-11-16T{when}:00+00:00", cat)
        after = self.snap()["product_001.htm"]["sections"]
        self.assertEqual(before, after)
        self.assertEqual(after, ["Przegląd wszystkich ofert", "Wyróżnione okazje"])
        self.assertNotIn("old_price", self.snap()["product_001.htm"])

    def test_removed_deal_that_comes_back_is_reported_as_returned(self):
        cat = make_catalog()
        self.run_at("2026-11-16T10:00:00+00:00", cat)
        gone = cat["deals"].pop(10)
        self.run_at("2026-11-16T13:05:00+00:00", cat)
        st = self.run_at("2026-11-16T16:10:00+00:00", cat)
        self.assertEqual(st["last_result"]["counts"], {"removed": 1})
        removed = json.loads((self.tmp / "data" / "removed.json").read_text())
        self.assertEqual(removed[gone["slug"]]["price"], gone["price"])
        cat["deals"].append(dict(gone, price=gone["price"] - 40))
        st = self.run_at("2026-11-16T19:15:00+00:00", cat)
        self.assertEqual(st["last_result"]["counts"], {"returned": 1})
        report = (self.tmp / "changes" / "2026-11-16T1915Z.md").read_text()
        self.assertIn("Returned deals (1)", report)
        self.assertIn("2026\u201111\u201116\u00a017:10", report)  # when it was removed, in Polish time
        self.assertEqual(json.loads((self.tmp / "data" / "removed.json").read_text()), {})
        self.assertIn(",returned,", (self.tmp / "data" / "price_history.csv").read_text())

    def test_manual_check_does_not_shift_the_schedule(self):
        cat = make_catalog()
        self.run_at("2026-11-16T10:00:00+00:00", cat)                      # scheduled
        st = self.run_at("2026-11-16T11:30:00+00:00", cat, force=True)     # manual extra
        self.assertEqual(st["runs"], 2)
        st = self.run_at("2026-11-16T12:59:00+00:00", cat)                 # 3 h after the scheduled one
        self.assertEqual(st["runs"], 3)
        st = self.run_at("2026-11-16T13:59:00+00:00", cat)                 # too early: skipped
        self.assertEqual(st["runs"], 3)
        st = self.run_at("2026-11-16T15:59:00+00:00", cat)
        self.assertEqual(st["runs"], 4)

    def test_small_price_moves_are_ignored_but_cannot_creep(self):
        cfg = yaml.safe_load((self.tmp / "config.yml").read_text())
        cfg["diff"]["min_price_change_pct"] = 1
        (self.tmp / "config.yml").write_text(yaml.safe_dump(cfg, allow_unicode=True))
        cat = make_catalog()
        cat["deals"][20]["price"] = 1000
        self.run_at("2026-11-16T10:00:00+00:00", cat)
        cat["deals"][20]["price"] = 1006                                   # +0.6 %: ignored
        st = self.run_at("2026-11-16T13:05:00+00:00", cat)
        self.assertEqual(st["last_result"]["counts"], {})
        self.assertEqual(self.snap()["product_020.htm"]["price"], 1006)    # deals.md still shows the real price
        cat["deals"][20]["price"] = 1012                                   # +0.6 % again, +1.2 % in total: reported
        st = self.run_at("2026-11-16T16:10:00+00:00", cat)
        self.assertEqual(st["last_result"]["counts"], {"price_up": 1})
        self.assertIn("1\u00a0000\u00a0zł | **1\u00a0012\u00a0zł**", (self.tmp / "changes" / "2026-11-16T1610Z.md").read_text())

    def test_live_config_is_usable(self):
        """Catches a typo made while editing config.yml on github.com."""
        from zoneinfo import ZoneInfo
        cfg = yaml.safe_load((REPO / "config.yml").read_text(encoding="utf-8"))
        self.assertTrue(cfg["source"]["url"].startswith("https://"))
        self.assertGreater(float(cfg["schedule"]["check_every_hours"]), 0)
        self.assertGreaterEqual(float(cfg["diff"]["min_price_change_pct"]), 0)
        self.assertGreaterEqual(int(cfg["diff"]["removal_grace_runs"]), 1)
        self.assertTrue(1 <= int(cfg["source"]["concurrency"]) <= 10)
        self.assertIn(cfg["report"]["deals_sort"], ["newest", "discount", "price", "name", "savings"])
        ZoneInfo(cfg["display_timezone"])
        for section in ("source", "schedule", "diff", "report", "watchlist", "alerts"):
            self.assertIsInstance(cfg[section], dict, section)
        for key in ("keywords", "ids"):
            self.assertIsInstance(cfg["watchlist"][key], list, key)

    def test_fewer_deals_than_advertised_counts_as_incomplete(self):
        cat = make_catalog()
        self.run_at("2026-11-16T10:00:00+00:00", cat)
        cat["advertised"] = 95
        del cat["deals"][85:]            # the shop says 95 but only 85 could be read
        st = self.run_at("2026-11-16T13:05:00+00:00", cat)
        self.assertTrue(st["last_result"]["partial"])
        st = self.run_at("2026-11-16T16:10:00+00:00", cat)
        self.assertNotIn("removed", st["last_result"]["counts"])
        self.assertIn("product_090.htm", self.snap())

    def test_unchanged_deals_are_not_rewritten(self):
        cat = make_catalog()
        self.run_at("2026-11-16T10:00:00+00:00", cat)
        self.run_at("2026-11-16T13:05:00+00:00", cat)
        first = (self.tmp / "data" / "snapshot.json").read_text()
        gone = cat["deals"].pop(10)["slug"]
        self.run_at("2026-11-16T16:10:00+00:00", cat)
        second = (self.tmp / "data" / "snapshot.json").read_text()
        changed = set(first.splitlines()) ^ set(second.splitlines())
        self.assertLess(len(changed), 6, changed)                     # only the missing deal's lines
        self.assertEqual(self.snap()[gone]["last_seen"], "2026-11-16T13:05Z")

    def test_throttled_single_requests_keep_slowing_down(self):
        from tracker import scrape as scr
        from tests.fake_site import FakeSession
        cat = make_catalog(200)
        cat["per_page"] = 20
        cat["throttle_pages"] = [3, 6]
        self.catalog.write_text(json.dumps(cat))
        cfg = yaml.safe_load((self.tmp / "config.yml").read_text())
        cfg["source"].update(concurrency=1, delay_seconds=0.01, throttled_delay_seconds=0.02)
        with self.assertLogs("tracker.scrape", level="WARNING") as logs:
            res = scr.scrape(cfg, session=FakeSession(str(self.catalog)))
        self.assertEqual(len(res.deals), 201)
        self.assertEqual(sum("slowing down" in l for l in logs.output), 2)

    def test_trigger_timing_gives_one_check_per_interval(self):
        """Replays triggers with realistic lateness through the schedule rule itself."""
        from datetime import datetime, timedelta, timezone
        cfg = yaml.safe_load((self.tmp / "config.yml").read_text())

        def replay(tick_hours, every, lateness_minutes, n=40):
            cfg["schedule"]["check_every_hours"] = every
            state, ran = {}, []
            t0 = datetime(2026, 11, 17, 0, 59, tzinfo=timezone.utc)
            for i in range(n):
                start = t0 + timedelta(hours=tick_hours * i, minutes=lateness_minutes[i % len(lateness_minutes)])
                ok, _ = self.m.should_run(cfg, state, start)
                if ok:  # what main() records when a scheduled check starts
                    state["last_scheduled_run"] = state["last_run"] = start.isoformat()
                    ran.append(start)
            return [round((b - a).total_seconds() / 3600, 1) for a, b in zip(ran, ran[1:])]

        # a trigger every 3 h, check every 3 h: every trigger checks, even when one starts
        # 20 or 40 minutes late and the next one is on time
        gaps = replay(3, 3, [0, 1, 0, 20, 0, 40, 0, 2])
        self.assertEqual(len(gaps), 39)
        self.assertTrue(all(2.3 <= g <= 3.7 for g in gaps), gaps)
        # a trigger every hour, check every 3 h: exactly every third trigger checks
        gaps = replay(1, 3, [0, 3, 1, 8, 0])
        self.assertTrue(all(2.8 <= g <= 3.2 for g in gaps), gaps)
        # a trigger every hour, check every hour
        gaps = replay(1, 1, [0, 3, 1, 8, 0])
        self.assertTrue(all(0.8 <= g <= 1.2 for g in gaps), gaps)

    def test_zero_deals_fails_and_saves_debug(self):
        cat = {"per_page": 40, "deals": [], "featured": []}
        self.catalog.write_text(json.dumps(cat))
        os.environ["FORCE"] = "1"
        self.assertEqual(self.m.main(), 1)
        self.assertTrue((self.tmp / "debug" / "page1.html").exists())


if __name__ == "__main__":
    unittest.main()
