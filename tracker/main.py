"""Entry point: gate on schedule -> scrape -> diff against snapshot -> write Markdown -> alert."""
from __future__ import annotations

import json
import logging
import os
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


def should_run(cfg: dict, state: dict, now: datetime) -> tuple[bool, str]:
    if os.environ.get("FORCE", "").lower() in ("1", "true", "yes"):
        return True, "forced"
    sch = cfg.get("schedule", {})
    if not sch.get("enabled", True):
        return False, "schedule.enabled is false"
    tz_now = now
    start, end = sch.get("active_from"), sch.get("active_until")
    if start and tz_now.date() < datetime.fromisoformat(str(start)).date():
        return False, f"before active_from {start}"
    if end and tz_now.date() > datetime.fromisoformat(str(end)).date():
        return False, f"after active_until {end}"
    last = state.get("last_run")
    if last:
        every = float(sch.get("check_every_hours", 3))
        # 10 min slack: GitHub cron often starts a few minutes late
        due = datetime.fromisoformat(last) + timedelta(hours=every) - timedelta(minutes=10)
        if now < due:
            return False, f"next check due at {due.isoformat()} (every {every}h)"
    return True, "due"


def pct(a, b):
    if not a or b is None:
        return None
    return round((b - a) / a * 100, 1)


def diff(prev: dict, cur: dict, partial: bool, cfg: dict, ts: str, quiet_prices: bool = False):
    """Returns (new_snapshot, changes). changes is a list of dicts with a 'type'."""
    grace = int(cfg.get("diff", {}).get("removal_grace_runs", 2))
    min_pct = float(cfg.get("diff", {}).get("min_price_change_pct", 0))
    changes = []
    snap = {}

    for pid, d in cur.items():
        d = d.to_dict()
        old = prev.get(pid)
        if old is None:
            d.update(first_seen=ts, last_seen=ts, last_change=ts, min_price=d["price"], max_price=d["price"], missing_runs=0)
            changes.append({"type": "added", "deal": d})
            snap[pid] = d
            continue
        rec = {**old, **{k: v for k, v in d.items() if k != "sections"}}
        rec["sections"] = sorted(set(old.get("sections", [])) | set(d["sections"]))
        rec["last_seen"] = ts
        if old.get("missing_runs", 0) >= 1:
            # was missing for a run but never reported removed: silently restored
            pass
        rec["missing_runs"] = 0
        changed = False
        op, np_ = old.get("price"), d["price"]
        if quiet_prices:
            # parser upgrade: take the newly read price/discount as correct, report nothing
            rec["min_price"] = rec["max_price"] = np_
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
        else:
            snap[pid] = {**old, "missing_runs": missing}
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
    prev = load_json(data_dir / "snapshot.json", {})

    if not res.deals:
        scr.save_debug(res.first_page_html, ROOT / "debug" / "page1.html")
        log.error("Parsed 0 deals. Raw page 1 saved to debug/page1.html. Errors: %s", res.errors)
        return 1

    prev_live = [d for d in prev.values() if d.get("missing_runs", 0) == 0]
    thr = float(cfg.get("diff", {}).get("partial_scrape_threshold", 0.8))
    partial = bool(res.errors) or (len(prev_live) > 20 and len(res.deals) < thr * len(prev_live))
    if partial:
        log.warning("Scrape looks incomplete (%s deals vs %s last time, errors=%s): removals suppressed",
                    len(res.deals), len(prev_live), res.errors)

    first_run = not prev
    quiet = bool(prev) and state.get("parser_version", 1) < PARSER_VERSION
    if quiet:
        log.warning("Parser upgraded to v%s: correcting stored prices without reporting them as changes",
                    PARSER_VERSION)
    snap, changes = diff(prev, res.deals, partial, cfg, ts, quiet_prices=quiet)
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
    state.update(last_run=now.isoformat(), last_result=run, parser_version=PARSER_VERSION)
    state.setdefault("runs", 0)
    state["runs"] += 1

    dump_json(data_dir / "snapshot.json", snap)
    dump_json(data_dir / "state.json", state)
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
