"""Entry point: gate on schedule -> scrape -> diff against snapshot -> write Markdown -> alert."""
from __future__ import annotations

import csv
import json
import logging
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from . import scrape as scr
from . import report
from . import alerts

ROOT = Path(os.environ.get("TRACKER_ROOT", Path(__file__).resolve().parent.parent))
# Bump when a parser fix changes how prices are read. The first check after an upgrade
# then corrects stored prices quietly instead of reporting them as price changes.
PARSER_VERSION = 2
log = logging.getLogger("tracker")


def load_json(p: Path, default):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def dump_json(p: Path, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")


def now_utc() -> datetime:
    override = os.environ.get("TRACKER_NOW")  # used by tests
    if override:
        return datetime.fromisoformat(override)
    return datetime.now(timezone.utc).replace(microsecond=0)


def is_forced() -> bool:
    return os.environ.get("FORCE", "").lower() in ("1", "true", "yes")


def should_run(cfg: dict, state: dict, now: datetime) -> tuple[bool, str]:
    if is_forced():
        return True, "forced"
    sch = cfg.get("schedule", {})
    if not sch.get("enabled", True):
        return False, "schedule.enabled is false"
    start, end = sch.get("active_from"), sch.get("active_until")
    if start and now.date() < datetime.fromisoformat(str(start)).date():
        return False, f"before active_from {start}"
    if end and now.date() > datetime.fromisoformat(str(end)).date():
        return False, f"after active_until {end}"
    # Counted from when the last *scheduled* check STARTED (not when it finished), so a check
    # that takes 5 minutes doesn't make the next trigger arrive "too early". A manual
    # ("forced") check in between is an extra and doesn't push the next scheduled one back.
    last = state.get("last_scheduled_run") or state.get("last_run")
    if last:
        every = float(sch.get("check_every_hours", 3))
        # Triggers never arrive exactly on time, and one check may start a few minutes late
        # while the next starts on time. Allow a quarter of the interval (45 min at most), or
        # a trigger that fires exactly every `check_every_hours` would skip every other time.
        slack = min(timedelta(minutes=45), timedelta(hours=every) / 4)
        due = datetime.fromisoformat(last) + timedelta(hours=every) - slack
        if now < due:
            return False, f"next check due at {due.isoformat()} (every {every}h)"
    return True, "due"


def pct(a, b):
    if not a or b is None:
        return None
    return round((b - a) / a * 100, 1)


def clean_record(rec: dict) -> dict:
    """Tidy records written by earlier versions: drop the unused old_price field and the
    deal counts inside section names ("Przegląd wszystkich 1535 ofert")."""
    rec.pop("old_price", None)
    secs = {re.sub(r"\s+", " ", re.sub(r"\d[\d .\u00a0\u202f\u2009]*", " ", x)).strip() for x in rec.get("sections", [])}
    rec["sections"] = sorted(x for x in secs if x)
    return rec


def load_removed(data_dir: Path) -> dict:
    """Deals that were removed earlier: {id: {"removed_at": ts, "price": last price}}.
    Lets a deal that comes back be reported as "returned" instead of "new"."""
    p = data_dir / "removed.json"
    if p.exists():
        return load_json(p, {})
    out = {}  # first use: rebuild from the price history
    try:
        with (data_dir / "price_history.csv").open(encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if r["event"] == "removed":
                    out[r["id"]] = {"removed_at": r["ts"], "price": float(r["price"]) if r["price"] else None}
                elif r["event"] in ("added", "returned"):
                    out.pop(r["id"], None)
    except FileNotFoundError:
        pass
    return out


def diff(prev: dict, cur: dict, partial: bool, cfg: dict, ts: str, quiet_prices: bool = False,
         removed: dict | None = None, prev_ts: str | None = None):
    """Returns (new_snapshot, changes). changes is a list of dicts with a 'type'.

    `removed` (see load_removed) is updated in place. `prev_ts` is the previous check's time.
    A deal's record only changes when the deal does, so each check's commit stays small.
    """
    removed = {} if removed is None else removed
    grace = int(cfg.get("diff", {}).get("removal_grace_runs", 2))
    min_pct = float(cfg.get("diff", {}).get("min_price_change_pct", 0))
    changes = []
    snap = {}

    for pid, d in cur.items():
        d = d.to_dict()
        old = prev.get(pid)
        d["sections"] = sorted(set(d["sections"]))
        if old is None:
            d.update(first_seen=ts, last_change=ts, min_price=d["price"], max_price=d["price"],
                     reported_price=d["price"], missing_runs=0)
            gone = removed.pop(pid, None)
            if gone:  # it was on the list before, got removed, and is back
                changes.append({"type": "returned", "deal": d, "old": gone.get("price"), "removed_at": gone.get("removed_at")})
            else:
                changes.append({"type": "added", "deal": d})
            snap[pid] = d
            continue
        # sections are replaced each check (they used to pile up); a deal that was missing
        # for one check and is back simply carries on
        rec = {**old, **d}
        rec.pop("last_seen", None)  # only kept while a deal is missing
        rec["missing_runs"] = 0
        changed = False
        # Price moves are measured from the last price that was *reported*, so a string of
        # moves each below min_price_change_pct can't add up unnoticed.
        op, np_ = old.get("reported_price", old.get("price")), d["price"]
        rec["reported_price"] = op
        if quiet_prices:
            # parser upgrade: take the newly read price/discount as correct, report nothing
            rec["min_price"] = rec["max_price"] = rec["reported_price"] = np_
            rec["missing_runs"] = 0
            snap[pid] = rec
            os_, ns = old.get("stock_state"), d["stock_state"]
            if os_ != ns and "unknown" not in (os_, ns):
                kind = "back_in_stock" if ns == "in_stock" else "stock"
                changes.append({"type": kind, "deal": rec, "old": old.get("stock") or os_, "new": d["stock"] or ns})
            continue
        if op is not None and np_ is not None and op != np_:
            p = pct(op, np_)
            if p is None or abs(p) >= min_pct:
                changes.append({"type": "price_down" if np_ < op else "price_up", "deal": rec, "old": op, "new": np_, "pct": p})
                rec["reported_price"] = np_
                changed = True
        if (old.get("discount") or 0) != (d["discount"] or 0):
            changes.append({"type": "discount", "deal": rec, "old": old.get("discount"), "new": d["discount"]})
            changed = True
        os_, ns = old.get("stock_state"), d["stock_state"]
        if os_ != ns and "unknown" not in (os_, ns):
            kind = "back_in_stock" if ns == "in_stock" else "stock"
            changes.append({"type": kind, "deal": rec, "old": old.get("stock") or os_, "new": d["stock"] or ns})
            changed = True
        if np_ is not None:
            rec["min_price"] = min(x for x in (old.get("min_price"), np_) if x is not None)
            rec["max_price"] = max(x for x in (old.get("max_price"), np_) if x is not None)
        if changed:
            rec["last_change"] = ts
        snap[pid] = rec

    for pid, old in prev.items():
        if pid in cur:
            continue
        if partial:
            snap[pid] = old  # scrape looked incomplete: don't count it as missing
            continue
        missing = old.get("missing_runs", 0) + 1
        if missing >= grace:
            changes.append({"type": "removed", "deal": old})
            removed[pid] = {"removed_at": ts, "price": old.get("price")}
        else:
            snap[pid] = {**old, "missing_runs": missing, "last_seen": old.get("last_seen") or prev_ts}
    return snap, changes


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    cfg = yaml.safe_load((ROOT / "config.yml").read_text(encoding="utf-8"))
    data_dir = ROOT / "data"
    state = load_json(data_dir / "state.json", {})
    now = now_utc()
    ts = now.strftime("%Y-%m-%dT%H:%MZ")

    ok, why = should_run(cfg, state, now)
    if not ok:
        log.info("Skipping: %s", why)
        return 0
    log.info("Running (%s)", why)

    res = scr.scrape(cfg, session=_test_session())
    prev = {k: clean_record(v) for k, v in load_json(data_dir / "snapshot.json", {}).items()}
    removed = load_removed(data_dir)

    if not res.deals:
        scr.save_debug(res.first_page_html, ROOT / "debug" / "page1.html")
        log.error("Parsed 0 deals. Raw page 1 saved to debug/page1.html. Errors: %s", res.errors)
        return 1

    prev_live = [d for d in prev.values() if d.get("missing_runs", 0) == 0]
    thr = float(cfg.get("diff", {}).get("partial_scrape_threshold", 0.8))
    # Three signs of an incomplete read: a page that never loaded, far fewer deals than last
    # time, or fewer deals than the shop itself advertises ("Przegląd wszystkich 1535 ofert").
    short = bool(res.expected_total) and len(res.deals) < 0.98 * res.expected_total
    partial = bool(res.errors) or short or (len(prev_live) > 20 and len(res.deals) < thr * len(prev_live))
    if partial:
        log.warning("Scrape looks incomplete (%s deals; %s advertised; %s last time; errors=%s): removals suppressed",
                    len(res.deals), res.expected_total, len(prev_live), res.errors)

    first_run = not prev
    quiet = bool(prev) and state.get("parser_version", 1) < PARSER_VERSION
    if quiet:
        log.warning("Parser upgraded to v%s: correcting stored prices without reporting them as changes",
                    PARSER_VERSION)
    snap, changes = diff(prev, res.deals, partial, cfg, ts, quiet_prices=quiet, removed=removed,
                         prev_ts=(state.get("last_result") or {}).get("ts"))
    if first_run:
        changes = []  # first snapshot is a baseline, not 1500 "new" deals

    run = {
        "ts": ts,
        "deals": len([d for d in snap.values() if d.get("missing_runs", 0) == 0]),
        "expected": res.expected_total,
        "pages": res.pages_fetched,
        "partial": partial,
        "baseline": first_run,
        "counts": report.count_types(changes),
    }
    if is_forced():
        # keep the scheduled rhythm where it was (see should_run)
        state.setdefault("last_scheduled_run", state.get("last_run") or now.isoformat())
    else:
        state["last_scheduled_run"] = now.isoformat()
    state.update(last_run=now.isoformat(), last_result=run, parser_version=PARSER_VERSION)
    state.setdefault("runs", 0)
    state["runs"] += 1

    dump_json(data_dir / "snapshot.json", snap)
    dump_json(data_dir / "state.json", state)
    dump_json(data_dir / "removed.json", removed)
    report.append_price_history(data_dir / "price_history.csv", ts, changes, snap if first_run else None)
    report.write_all(ROOT, cfg, snap, changes, run)

    hits = alerts.select(cfg, changes)
    if hits:
        alerts.send(cfg, hits, run)
    if not first_run:
        alerts.discord(cfg, changes, run)
    log.info("Done: %s deals, %s changes, %s alert hits", run["deals"], len(changes), len(hits))
    return 0


def _test_session():
    """Tests inject a fake HTTP session through this hook."""
    hook = os.environ.get("TRACKER_FAKE_SITE")
    if not hook:
        return None
    from tests.fake_site import FakeSession  # noqa
    return FakeSession(hook)


if __name__ == "__main__":
    sys.exit(main())
