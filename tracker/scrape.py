"""Fetch every page of a Thomann deals listing and parse the product tiles.

The parser is deliberately structure-agnostic: Thomann changes its CSS class
names often, so instead of relying on them we find every link to a product
page (``*.htm``) and climb up the DOM to the smallest element that contains
exactly one product and a price. That element is treated as the tile.
"""
from __future__ import annotations

import bisect
import json
import logging
import re
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup, Tag

log = logging.getLogger(__name__)

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
)

SPACES = "    "
NUM = r"\d{1,3}(?:[    .]\d{3})*(?:,\d{1,2})?|\d+(?:,\d{1,2})?"

REF_LABEL_RE = re.compile(
    r"najlepsza cena|najni[zż]sza cena|30[ -]?dni|niedrigster preis|lowest price|30[ -]?day",
    re.I,
)
DISCOUNT_RE = re.compile(r"-\s?(\d{1,2})\s?%")
BADGE_RE = re.compile(
    r"\b(GIVEAWAY|Top Deal|Hot Deal|Cyber Deal|Black Friday|Blowout|B-Stock|Deal)\b", re.I
)
STOCK_PATTERNS = [
    # (regex, normalised state)
    (r"dost[eę]pn\w*\s+w\s+magazynie|dost[eę]pn\w*\s+natychmiast|auf lager|in stock", "in_stock"),
    (r"pobierz licencj\w*|download|licencja", "download"),
    (r"dost[eę]pn\w*\s+za\s+[^\d]*\d+(?:\s*[–-]\s*\d+)?\s*\w+|lieferbar in|available in", "delayed"),
    (r"kr[oó]tki czas oczekiwania(?:\s*\([^)]{0,40}\))?|kurzfristig lieferbar|available shortly", "delayed"),
    (r"wkr[oó]tce|na zam[oó]wienie|zam[oó]wion\w*", "delayed"),
    (r"brak w magazynie|niedost[eę]pn\w*|nicht verf[uü]gbar|out of stock|wyprzedan\w*", "out"),
]
SEP = "\x1f"  # marks HTML element boundaries in tile text used for price parsing
STRIKE_CLASS_RE = re.compile(r"strike|crossed|old|was|before|rrp|uvp", re.I)


@dataclass
class Deal:
    id: str
    url: str
    name: str
    price: float | None = None
    ref_price: float | None = None  # "best price of the last 30 days"
    discount: int | None = None
    stock: str = ""
    stock_state: str = "unknown"
    badge: str = ""
    sections: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def parse_number(s: str) -> float | None:
    s = s.strip()
    for ch in SPACES:
        s = s.replace(ch, "")
    if re.search(r",\d{1,2}$", s):  # Polish/German decimal comma
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(".", "").replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


class Parser:
    def __init__(self, base_url: str, currency_regex: str):
        self.base_url = base_url
        self.host = urlparse(base_url).netloc
        self.price_re = re.compile(rf"({NUM})\s*(?:{currency_regex})", re.I)
        # Same, for text where HTML element boundaries are marked with SEP: a number may
        # not continue across a boundary (so a review count "751" in the element before
        # "599 zł" can't merge into "751 599 zł"), but the currency may sit in its own element.
        self.price_sep_re = re.compile(rf"({NUM})\s*{SEP}?\s*(?:{currency_regex})", re.I)
        self.unknown_stock: list[str] = []  # a few samples of tiles whose stock text wasn't recognised
        self._ids_cache: dict[int, frozenset] = {}
        self._headings: list[tuple[tuple[int, int], str]] = []

    # ---------- helpers ----------
    def product_id(self, href: str) -> str | None:
        if not href:
            return None
        url = urljoin(self.base_url, href)
        p = urlparse(url)
        if p.netloc and p.netloc != self.host:
            return None
        path = p.path.rstrip("/")
        if not path.endswith(".htm"):
            return None  # categories/specials are .html, products are .htm
        if path.count("/") > 2:
            return None
        return path.rsplit("/", 1)[-1].lower()

    def _distinct_ids(self, el: Tag) -> frozenset:
        """Product ids linked inside `el`. Cached per page: every tile climbs through the same
        ancestors, and without the cache a 400-tile page costs seconds instead of milliseconds."""
        key = id(el)
        hit = self._ids_cache.get(key)
        if hit is None:
            ids = set()
            for a in el.find_all("a", href=True):
                pid = self.product_id(a["href"])
                if pid:
                    ids.add(pid)
            hit = self._ids_cache[key] = frozenset(ids)
        return hit

    def _find_tile(self, a: Tag, pid: str) -> Tag | None:
        best = None
        el: Tag | None = a
        for _ in range(10):
            el = el.parent if el is not None else None
            if el is None or el.name in ("body", "html", "[document]"):
                break
            ids = self._distinct_ids(el)
            if len(ids) > 1 or (ids and pid not in ids):
                break
            if self.price_re.search(el.get_text(" ", strip=True)):
                best = el
                # keep climbing while still a single product: bigger tile
                # may hold stock/badge info that sits outside the price box
        return best

    @staticmethod
    def _heading_text(h: Tag) -> str:
        """Section name without counts: "Przegląd wszystkich 1535 ofert" changes with every
        check, so the number is dropped to keep the name stable."""
        t = re.sub(r"\s+", " ", h.get_text(" ", strip=True))
        return re.sub(r"\s+", " ", re.sub(r"\d[\d .\u00a0\u202f\u2009]*", " ", t)).strip()[:80]

    def _index_headings(self, soup: BeautifulSoup):
        self._headings = []
        for h in soup.find_all(["h1", "h2", "h3"]):
            if h.sourceline is None:
                self._headings = []  # parser gave no positions: fall back to searching per tile
                return
            self._headings.append(((h.sourceline, h.sourcepos or 0), self._heading_text(h)))
        self._headings.sort(key=lambda x: x[0])

    def _section_of(self, tile: Tag) -> str:
        """The nearest heading before the tile (looked up by position in the page source)."""
        if self._headings and tile.sourceline is not None:
            i = bisect.bisect_left(self._headings, ((tile.sourceline, tile.sourcepos or 0), "")) - 1
            return self._headings[i][1] if i >= 0 else ""
        h = tile.find_previous(["h1", "h2", "h3"])
        return self._heading_text(h) if h else ""

    def _sep_text(self, el: Tag) -> str:
        return re.sub(r"[ \t\r\n]+", " ", el.get_text(SEP, strip=True))

    def _prices(self, tile: Tag, text: str):
        struck = []
        for el in tile.find_all(["s", "del", "strike"]):
            struck.append(self._sep_text(el))
        for el in tile.find_all(class_=STRIKE_CLASS_RE):
            if el.name in ("s", "del", "strike"):
                continue
            t = self._sep_text(el)
            if self.price_sep_re.search(t) and len(t) < 40:
                struck.append(t)
        # On thomann.pl this ends up matching the normal price element, so it isn't stored;
        # it is still used below exactly as before, to keep price selection unchanged.
        old_price = None
        for t in struck:
            m = self.price_sep_re.search(t)
            if m:
                old_price = parse_number(m.group(1))
                break

        ptext = self._sep_text(tile)
        matches = [(m.start(), parse_number(m.group(1))) for m in self.price_sep_re.finditer(ptext)]
        matches = [(pos, v) for pos, v in matches if v is not None]
        ref_price = None
        label = REF_LABEL_RE.search(ptext)
        if label and len(matches) >= 2:
            # the price closest to the "30-day best price" label is the reference price
            ref_idx = min(range(len(matches)), key=lambda i: abs(matches[i][0] - label.end()))
            ref_price = matches[ref_idx][1]
            matches = matches[:ref_idx] + matches[ref_idx + 1 :]
        remaining = [v for _, v in matches if v != old_price] or [v for _, v in matches]
        price = remaining[0] if remaining else None
        return price, ref_price

    @staticmethod
    def _stock(tile: Tag, text: str):
        raw = ""
        for el in tile.find_all(class_=re.compile(r"availab|delivery|stock|shipping", re.I)):
            t = re.sub(r"\s+", " ", el.get_text(" ", strip=True))
            if t and len(t) < 80:
                raw = t
                break
        hay = raw or text
        for pat, state in STOCK_PATTERNS:
            m = re.search(pat, hay, re.I)
            if m:
                return (raw or m.group(0)).strip(), state
        return raw, "unknown"

    @staticmethod
    def _name(tile: Tag, anchors: list[Tag]) -> str:
        texts = [re.sub(r"\s+", " ", a.get_text(" ", strip=True)) for a in anchors]
        texts = [t for t in texts if t and not re.fullmatch(r"[\d\s,.()%zł★-]+", t)]
        if texts:
            return max(texts, key=len)[:200]
        for a in anchors:
            if a.get("title"):
                return a["title"].strip()
        img = tile.find("img", alt=True)
        return img["alt"].strip() if img else ""

    # ---------- main ----------
    def parse(self, html: str) -> tuple[list[Deal], int | None]:
        soup = BeautifulSoup(html, "html.parser")
        self._ids_cache = {}
        self._index_headings(soup)
        expected = None
        m = re.search(r"wszystkich\s+([\d\s .]+)\s+ofert|all\s+([\d,.]+)\s+(?:deals|offers)",
                      soup.get_text(" "), re.I)
        if m:
            expected = int(re.sub(r"\D", "", m.group(1) or m.group(2)) or 0) or None

        deals: dict[str, Deal] = {}
        seen_tiles: set[int] = set()
        for a in soup.find_all("a", href=True):
            pid = self.product_id(a["href"])
            if not pid:
                continue
            tile = self._find_tile(a, pid)
            if tile is None or id(tile) in seen_tiles:
                continue
            seen_tiles.add(id(tile))
            section = self._section_of(tile)
            if pid in deals:
                if section and section not in deals[pid].sections:
                    deals[pid].sections.append(section)
                continue
            text = re.sub(r"\s+", " ", tile.get_text(" ", strip=True))
            anchors = [x for x in tile.find_all("a", href=True) if self.product_id(x["href"]) == pid]
            price, ref_price = self._prices(tile, text)
            dm = DISCOUNT_RE.search(text)
            bm = BADGE_RE.search(text)
            stock, state = self._stock(tile, text)
            if state == "unknown" and len(self.unknown_stock) < 5:
                self.unknown_stock.append(f"{pid}: …{text[-140:]}")
            deals[pid] = Deal(
                id=pid,
                url=urljoin(self.base_url, urlparse(urljoin(self.base_url, a["href"])).path),
                name=self._name(tile, anchors),
                price=price,
                ref_price=ref_price,
                discount=int(dm.group(1)) if dm else None,
                stock=stock,
                stock_state=state,
                badge=bm.group(1) if bm else "",
                sections=[section] if section else [],
            )
        if not deals:
            deals = {d.id: d for d in self._parse_jsonld(soup)}
        return list(deals.values()), expected

    def _parse_jsonld(self, soup: BeautifulSoup) -> list[Deal]:
        """Fallback: structured data, if the page ships any."""
        out = []
        for s in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(s.string or "")
            except Exception:
                continue
            stack = data if isinstance(data, list) else [data]
            while stack:
                node = stack.pop()
                if isinstance(node, list):
                    stack.extend(node)
                    continue
                if not isinstance(node, dict):
                    continue
                for k in ("itemListElement", "item", "@graph"):
                    if k in node:
                        stack.append(node[k])
                if node.get("@type") == "Product" and node.get("url"):
                    pid = self.product_id(node["url"])
                    if not pid:
                        continue
                    offers = node.get("offers") or {}
                    if isinstance(offers, list):
                        offers = offers[0] if offers else {}
                    price = offers.get("price")
                    avail = str(offers.get("availability", ""))
                    out.append(Deal(
                        id=pid, url=urljoin(self.base_url, node["url"]), name=node.get("name", ""),
                        price=float(price) if price not in (None, "") else None,
                        stock=avail.rsplit("/", 1)[-1],
                        stock_state="in_stock" if "InStock" in avail else ("out" if "OutOfStock" in avail else "unknown"),
                    ))
        return out


@dataclass
class ScrapeResult:
    deals: dict[str, Deal]
    expected_total: int | None
    pages_fetched: int
    errors: list[str]
    first_page_html: str = ""


class _Throttle:
    """Shared state: set when the shop answers 429 so the crawler slows down."""
    def __init__(self):
        self.hit = False


def _fetch(s, src, page, extra, page_param, throttle=None):
    """Fetch one listing page with retries and backoff.

    Returns html ("" for 404) or None if it still failed after all attempts.
    A 429 (Too Many Requests) honours the shop's Retry-After header.
    """
    params = dict(extra)
    if page > 1:
        params[page_param] = page
    attempts = int(src.get("retry_attempts", 5))
    base = float(src.get("retry_wait_seconds", 5))
    for attempt in range(attempts):
        wait = base * (2 ** attempt)  # 5, 10, 20, 40 s ...
        try:
            r = s.get(src["url"], params=params, timeout=30)
            if r.status_code == 404:
                return ""
            if r.status_code == 429:
                if throttle is not None:
                    throttle.hit = True
                ra = (getattr(r, "headers", None) or {}).get("Retry-After")
                if ra and str(ra).strip().isdigit():
                    wait = max(wait, min(float(ra), 120))
                raise RuntimeError("429 Too Many Requests")
            r.raise_for_status()
            return r.text
        except Exception as e:  # network hiccup / 5xx / 429
            if attempt == attempts - 1:
                log.warning("page %s failed after %s attempts: %s", page, attempts, e)
                break
            log.warning("page %s attempt %s failed: %s (retry in %.0fs)", page, attempt + 1, e, wait)
            time.sleep(wait)
    return None


def scrape(cfg: dict, session: requests.Session | None = None) -> ScrapeResult:
    """Fetch pages in batches of parallel requests, then process them in order.

    Polite by design: if the shop answers 429 (Too Many Requests), the batch size is
    halved (down to 1) and the pause between batches doubled (up to 30 s) for the rest of the run.
    Pages that still fail are retried one by one at the end, so a throttled run
    doesn't lose deals. Stops when `stop_after_empty_pages` consecutive pages bring
    no new deals, or at `max_pages`.
    """
    from concurrent.futures import ThreadPoolExecutor

    src = cfg["source"]
    parser = Parser(src["url"], src.get("currency_regex", "zł|zl|PLN|€|EUR"))
    s = session or requests.Session()
    s.headers.update({"User-Agent": UA, "Accept-Language": src.get("accept_language", "pl-PL,pl;q=0.9,en;q=0.5")})

    all_deals: dict[str, Deal] = {}
    expected = None
    errors: list[str] = []
    first_html = ""
    page_param = src.get("page_param", "pg")
    extra = dict(src.get("extra_params") or {})
    max_pages = int(src.get("max_pages", 150))
    delay = float(src.get("delay_seconds", 1.0))
    workers = max(1, min(int(src.get("concurrency", 4)), 10))
    stop_after = int(src.get("stop_after_empty_pages", 2))
    throttle = _Throttle()
    state = {"expected": None, "empty_streak": 0, "last_page": 0}
    failed: list[int] = []

    def absorb(page, html):
        nonlocal first_html
        if page == 1:
            first_html = html
        deals, exp = parser.parse(html)
        state["expected"] = state["expected"] or exp
        new = 0
        for d in deals:
            if d.id in all_deals:
                for sec in d.sections:
                    if sec not in all_deals[d.id].sections:
                        all_deals[d.id].sections.append(sec)
            else:
                all_deals[d.id] = d
                new += 1
        state["last_page"] = max(state["last_page"], page)
        log.info("page %s: %s tiles, %s new (total %s)", page, len(deals), new, len(all_deals))
        return new

    next_page = 1
    stop = False
    with ThreadPoolExecutor(max_workers=workers) as pool:
        while not stop and next_page <= max_pages:
            batch = list(range(next_page, min(next_page + workers, max_pages + 1)))
            next_page = batch[-1] + 1
            throttle.hit = False
            results = list(pool.map(lambda pg: _fetch(s, src, pg, extra, page_param, throttle), batch))
            for page, html in zip(batch, results):
                if html is None:
                    failed.append(page)  # retried at the end; doesn't count as "empty"
                    continue
                new = absorb(page, html)
                state["empty_streak"] = state["empty_streak"] + 1 if new == 0 else 0
                if state["empty_streak"] >= stop_after:
                    stop = True
                    break
                exp = state["expected"]
                if exp and len(all_deals) >= exp + int(src.get("extra_tiles_allowance", 80)):
                    stop = True
                    break
            if throttle.hit:
                # also when already down to one request at a time: keep lengthening the pause
                workers = max(1, workers // 2)
                delay = min(max(delay * 2, float(src.get("throttled_delay_seconds", 2.0))), 30.0)
                log.warning("shop is throttling: slowing down to %s parallel request(s), %.0fs pause", workers, delay)
            if len(failed) >= 10:
                errors.append(f"too many failed pages ({len(failed)}), giving up early")
                stop = True
            if not stop:
                time.sleep(delay)

    # second chance for pages that failed, one at a time and slower
    for page in sorted(failed):
        if page > state["last_page"] and state["empty_streak"] >= stop_after:
            continue  # past the end of the list anyway
        time.sleep(max(delay, float(src.get("second_pass_delay_seconds", 3.0))))
        html = _fetch(s, src, page, extra, page_param, throttle)
        if html is None:
            errors.append(f"page {page}: failed after retries")
        else:
            absorb(page, html)

    log.info("fetched %s pages; %s parallel request(s) at the end; %s page(s) needed a second pass",
             state["last_page"], workers, len(failed))
    unknown = sum(1 for d in all_deals.values() if d.stock_state == "unknown")
    if unknown:
        log.warning("%s deal(s) with an unrecognised stock label, e.g. %s", unknown, " | ".join(parser.unknown_stock))
    return ScrapeResult(all_deals, state["expected"], state["last_page"], errors, first_html)


def save_debug(html: str, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
