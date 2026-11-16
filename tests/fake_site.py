"""A simulated Thomann deals page, used by the offline tests.

The markup imitates what thomann.pl serves (tiles with an image link, a
name link split into manufacturer/model spans, badges, a price, the
"najlepsza cena z 30-dni" reference price and a stock line). Class names are
made up on purpose: the parser must not depend on them.
"""
import json
import time
from types import SimpleNamespace

NB = " "


def fmt(v):
    s = f"{v:,.0f}".replace(",", NB)
    return f"{s}{NB}zł"


def tile(d, variant):
    badge = f"-{d['discount']}%" if d.get("discount") else d.get("badge", "Deal")
    ref = f'<div class="p-ref">najlepsza cena z 30-dni: <span>{fmt(d["ref"])}</span></div>' if d.get("ref") else ""
    maker, _, model = d["name"].partition(" ")
    if variant == 0:
        return f"""
<article class="xT1">
  <a href="{d['slug']}"><img src="placeholder.svg" alt="{d['name']}"></a>
  <span class="xB">{badge}</span>
  <a href="{d['slug']}" class="xN"><span>{maker}</span> <span>{model}</span></a>
  <div class="xR"><span>★★★★★</span><span>{d.get('reviews', 751)}</span></div>
  <div class="xP"><span>{fmt(d['price']).replace(NB + 'zł', '')}</span><sup>zł</sup></div>
  {ref}
  <div class="product-availability">{d['stock']}</div>
</article>"""
    # variant 1: deeper nesting, absolute URLs, price before the name
    return f"""
<li><div class="c"><div class="c2">
  <div class="img"><a href="https://www.thomann.pl/{d['slug']}?offid=1"><img src="x.svg" alt=""></a></div>
  <div class="lbl">{badge}</div>
  <div class="pr">{fmt(d['price'])}</div>{ref}
  <div class="t"><a href="https://www.thomann.pl/{d['slug']}?offid=1">{d['name']}</a></div>
  <p>{d['stock']}</p>
</div></div></li>"""


def page_html(cat, pg):
    per = cat.get("per_page", 40)
    deals = cat["deals"]
    last = max(1, -(-len(deals) // per))
    pg = min(pg, last)  # like many shops: past the end you get the last page again
    chunk = deals[(pg - 1) * per : pg * per]
    featured = "".join(tile(d, 0) for d in cat.get("featured", []))
    grid = "".join(tile(d, i % 2) for i, d in enumerate(chunk))
    return f"""<!doctype html><html><body>
<nav><a href="/gitary_i_basy.html">Gitary</a> <a href="/special_cyber-deals.html">Cyber deals</a></nav>
<h1>Cyber Deals</h1><p>05.11 - 30.11 Zaoszczędź nawet 70%</p>
<section><h2>Wyróżnione okazje</h2><div class="g">{featured}</div></section>
<section><h2>Przegląd wszystkich {cat.get('advertised', len(deals))} ofert</h2><ul class="g">{grid}</ul>
<button>Pokaż więcej</button></section>
<footer><a href="/compinfo_terms.html">Regulamin</a></footer>
</body></html>"""


class FakeSession:
    def __init__(self, catalog_path, latency=0.0):
        self.catalog_path = catalog_path
        self.latency = latency  # simulated network round-trip, seconds
        self.headers = {}
        self.calls = []
        self.throttled = {}  # page -> 429 answers given so far
        self.in_flight = 0
        self.max_in_flight = 0
        import threading
        self._lock = threading.Lock()

    def get(self, url, params=None, timeout=None):
        with open(self.catalog_path, encoding="utf-8") as fh:
            cat = json.load(fh)
        pg = int((params or {}).get("pg", 1))
        self.calls.append(pg)
        if pg in cat.get("fail_pages", []):
            raise ConnectionError(f"simulated failure on page {pg}")
        with self._lock:
            self.in_flight += 1
            self.max_in_flight = max(self.max_in_flight, self.in_flight)
            busy = self.in_flight
            # like Thomann: too many parallel requests -> 429 for the first N tries of a page
            limit = cat.get("throttle_above", 99)
            n = self.throttled.get(pg, 0)
            throttle = (busy > limit or pg in cat.get("throttle_pages", [])) and n < cat.get("throttle_times", 1)
            if throttle:
                self.throttled[pg] = n + 1
        try:
            time.sleep(self.latency)  # request is "in flight" during this
            if throttle:
                resp = SimpleNamespace(status_code=429, text="", headers={"Retry-After": "0"})
                resp.raise_for_status = lambda: None
                return resp
            resp = SimpleNamespace(status_code=200, text=page_html(cat, pg), headers={})
            resp.raise_for_status = lambda: None
            return resp
        finally:
            with self._lock:
                self.in_flight -= 1
