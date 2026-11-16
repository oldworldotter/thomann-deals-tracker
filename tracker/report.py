"""Markdown output: README dashboard, deals.md, watchlist.md, changes/<run>.md, CHANGELOG.md."""
from __future__ import annotations

import csv
import re
from collections import Counter
from pathlib import Path

ICONS = {
    "added": ("🆕", "New deals"),
    "returned": ("🔁", "Returned deals"),
    "removed": ("❌", "Removed deals"),
    "price_down": ("💸", "Price drops"),
    "price_up": ("📈", "Price increases"),
    "discount": ("🏷️", "Discount changes"),
    "back_in_stock": ("✅", "Back in stock"),
    "stock": ("📦", "Stock changes"),
}
ORDER = list(ICONS)
DASH_START, DASH_END = "<!-- DASHBOARD:START -->", "<!-- DASHBOARD:END -->"


def count_types(changes):
    return dict(Counter(c["type"] for c in changes))


# ---------- formatting ----------
NBSP, NBHY = "\u00a0", "\u2011"  # non-breaking space / hyphen: keep table cells on one line


def nowrap(s: str) -> str:
    """GitHub tables can't be given column widths, but cells without break points stay on one line."""
    return (s or "").replace(" ", NBSP).replace("-", NBHY)


def money(v, cfg):
    if v is None:
        return "–"
    cur = cfg.get("source", {}).get("currency_label", "zł")
    s = f"{v:,.0f}" if float(v).is_integer() else f"{v:,.2f}"
    return f"{s.replace(',', NBSP)}{NBSP}{cur}"


def esc(s: str) -> str:
    return (s or "").replace("|", "\\|").replace("\n", " ")


def link(d):
    return f"[{esc(d.get('name') or d['id'])}]({d['url']})"


def disc(d):
    return nowrap(f"-{d['discount']}%") if d.get("discount") else ""


DISPLAY_TZ = "Europe/Warsaw"  # overridden by config.yml → display_timezone


def set_display_tz(cfg):
    global DISPLAY_TZ
    DISPLAY_TZ = cfg.get("display_timezone") or DISPLAY_TZ


def human_ts(ts: str, label: bool = True) -> str:
    """Stored times are UTC ("2026-11-16T15:32Z"); show them in the display time zone.

    Every time shown for a run comes from the same stored value (taken when the
    check started), so "Last check", "First seen", change reports and the commit
    message always agree.
    """
    if not ts:
        return ""
    try:
        from datetime import datetime, timezone
        from zoneinfo import ZoneInfo
        dt = datetime.strptime(ts, "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)
        dt = dt.astimezone(ZoneInfo(DISPLAY_TZ))
    except Exception:
        return ts.replace("T", " ").replace("Z", " UTC")
    out = dt.strftime("%Y-%m-%d %H:%M")
    return f"{out} {dt.strftime('%Z')}" if label else out


# ---------- filtering ----------
def matches(d: dict, f: dict) -> bool:
    if not f:
        return True
    name = (d.get("name") or d["id"]).lower()
    price = d.get("price")
    if f.get("min_discount") and (d.get("discount") or 0) < f["min_discount"]:
        return False
    if f.get("max_price") is not None and price is not None and price > f["max_price"]:
        return False
    if f.get("min_price") is not None and price is not None and price < f["min_price"]:
        return False
    inc = [k.lower() for k in f.get("include_keywords") or []]
    if inc and not any(k in name for k in inc):
        return False
    exc = [k.lower() for k in f.get("exclude_keywords") or []]
    if any(k in name for k in exc):
        return False
    secs = [s.lower() for s in f.get("sections") or []]
    if secs and not any(any(s in x.lower() for s in secs) for x in d.get("sections", [])):
        return False
    stock = f.get("stock_states") or []
    if stock and d.get("stock_state") not in stock:
        return False
    return True


def watch_match(d: dict, w: dict) -> bool:
    if not w:
        return False
    kws = [k.lower() for k in w.get("keywords") or []]
    ids = [i.lower() for i in w.get("ids") or []]
    name = (d.get("name") or "").lower()
    hit = any(k in name for k in kws) or d["id"].lower() in ids
    if not hit:
        return False
    return matches(d, {"max_price": w.get("max_price"), "min_discount": w.get("min_discount")})


def visible_changes(cfg, changes):
    rep = cfg.get("report", {})
    show = rep.get("show", {})
    f = rep.get("filters", {})
    return [c for c in changes if show.get(c["type"], True) and matches(c["deal"], f)]


# ---------- tables ----------
def change_rows(t, items, cfg):
    if t in ("price_down", "price_up"):
        lines = ["| Product | Was | Now | Change | Discount | 30-day best | Stock |", "|---|--:|--:|--:|--:|--:|---|"]
        items = sorted(items, key=lambda c: c.get("pct") or 0, reverse=(t == "price_up"))
        for c in items:
            d = c["deal"]
            p = f"{c['pct']:+.1f}%" if c.get("pct") is not None else ""
            lines.append(f"| {link(d)} | {money(c['old'], cfg)} | **{money(c['new'], cfg)}** | {p} | {disc(d)} | {money(d.get('ref_price'), cfg) if d.get('ref_price') else ''} | {esc(d.get('stock'))} |")
    elif t == "discount":
        lines = ["| Product | Price | Discount was | Discount now |", "|---|--:|--:|--:|"]
        for c in items:
            d = c["deal"]
            o = f"-{c['old']}%" if c.get("old") else "none"
            n = f"-{c['new']}%" if c.get("new") else "none"
            lines.append(f"| {link(d)} | {money(d.get('price'), cfg)} | {o} | **{n}** |")
    elif t in ("stock", "back_in_stock"):
        lines = ["| Product | Price | Was | Now |", "|---|--:|---|---|"]
        for c in items:
            d = c["deal"]
            lines.append(f"| {link(d)} | {money(d.get('price'), cfg)} | {esc(str(c['old']))} | **{esc(str(c['new']))}** |")
    elif t == "returned":
        lines = ["| Product | Price | Price when removed | Discount | 30-day best | Stock | Removed |", "|---|--:|--:|--:|--:|---|---|"]
        items = sorted(items, key=lambda c: -(c["deal"].get("discount") or 0))
        for c in items:
            d = c["deal"]
            lines.append(f"| {link(d)} | **{money(d.get('price'), cfg)}** | {money(c['old'], cfg) if c.get('old') else ''} | {disc(d)} | {money(d.get('ref_price'), cfg) if d.get('ref_price') else ''} | {esc(d.get('stock'))} | {nowrap(human_ts(c.get('removed_at') or '', label=False))} |")
    else:  # added / removed
        lines = ["| Product | Price | Discount | 30-day best | Stock | Badge |", "|---|--:|--:|--:|---|---|"]
        items = sorted(items, key=lambda c: -(c["deal"].get("discount") or 0))
        for c in items:
            d = c["deal"]
            lines.append(f"| {link(d)} | {money(d.get('price'), cfg)} | {disc(d)} | {money(d.get('ref_price'), cfg) if d.get('ref_price') else ''} | {esc(d.get('stock'))} | {esc(d.get('badge'))} |")
    return lines


def summary_line(counts: dict) -> str:
    parts = [f"{ICONS[t][0]} {counts[t]} {ICONS[t][1].lower()}" for t in ORDER if counts.get(t)]
    return " · ".join(parts) if parts else "No changes"


def changes_md(cfg, changes, run, limit=None):
    out = []
    by = {}
    for c in changes:
        by.setdefault(c["type"], []).append(c)
    for t in ORDER:
        items = by.get(t)
        if not items:
            continue
        icon, title = ICONS[t]
        out.append(f"### {icon} {title} ({len(items)})\n")
        rows = change_rows(t, items, cfg)
        if limit and len(rows) - 2 > limit:
            out += rows[: limit + 2] + [f"\n…and {len(items) - limit} more in the full report.\n"]
        else:
            out += rows + [""]
    return "\n".join(out)


def deals_table(cfg, deals):
    sort = cfg.get("report", {}).get("deals_sort", "newest")
    by_discount = lambda d: (-(d.get("discount") or 0), d.get("price") or 0)
    if sort == "newest":
        # newest "First seen" on top; within the same check, biggest discount first
        deals = sorted(deals, key=by_discount)
        deals = sorted(deals, key=lambda d: d.get("first_seen") or "", reverse=True)
    else:
        keyf = {
            "discount": by_discount,
            "price": lambda d: d.get("price") or 0,
            "name": lambda d: (d.get("name") or "").lower(),
            "savings": lambda d: -((d.get("ref_price") or d.get("price") or 0) - (d.get("price") or 0)),
        }.get(sort, by_discount)
        deals = sorted(deals, key=keyf)
    lines = ["| # | Product | Price | Discount | 30-day best | Lowest seen | Stock | Badge | First seen |",
             "|--:|---|--:|--:|--:|--:|---|---|---|"]
    for i, d in enumerate(deals, 1):
        low = d.get("min_price")
        low_s = money(low, cfg) if low is not None and low != d.get("price") else ""
        lines.append(
            f"| {i} | {link(d)} | {money(d.get('price'), cfg)} | {disc(d)} | "
            f"{money(d.get('ref_price'), cfg) if d.get('ref_price') else ''} | {low_s} | {esc(d.get('stock'))} | "
            f"{esc(d.get('badge'))} | {nowrap(human_ts(d.get('first_seen') or '', label=False))} |"
        )
    return "\n".join(lines)


# ---------- writers ----------
def write_all(root: Path, cfg, snap, changes, run):
    set_display_tz(cfg)
    live = [d for d in snap.values() if d.get("missing_runs", 0) == 0]
    f = cfg.get("report", {}).get("filters", {})
    shown = [d for d in live if matches(d, f)]
    vis = visible_changes(cfg, changes)
    vis_counts = count_types(vis)
    title = cfg.get("title", "Thomann deals tracker")

    # deals.md
    filt_note = "" if len(shown) == len(live) else f" ({len(shown)} shown after `report.filters` in config.yml)"
    (root / "deals.md").write_text(
        f"# All current deals\n\nSource: {cfg['source']['url']}  \nLast check: **{human_ts(run['ts'])}** · "
        f"**{len(live)}** deals{filt_note} · sorted by `{cfg.get('report', {}).get('deals_sort', 'newest')}`\n\n"
        + deals_table(cfg, shown) + "\n", encoding="utf-8")

    # watchlist.md
    w = cfg.get("watchlist", {})
    wl = [d for d in live if watch_match(d, w)]
    kw = ", ".join(f"`{k}`" for k in (w.get("keywords") or [])) or "_none set_"
    (root / "watchlist.md").write_text(
        f"# Watchlist\n\nKeywords: {kw}  \nLast check: **{human_ts(run['ts'])}** · **{len(wl)}** matching deals\n\n"
        + (deals_table(cfg, wl) if wl else "_No current deals match. Edit `watchlist` in config.yml._") + "\n",
        encoding="utf-8")

    # changes/<ts>.md + CHANGELOG.md
    changes_link = None
    if vis:
        fname = run["ts"].replace(":", "")
        p = root / "changes" / f"{fname}.md"
        p.parent.mkdir(exist_ok=True)
        note = "\n> ⚠️ This scrape looked incomplete, so removals were not reported.\n" if run["partial"] else ""
        p.write_text(f"# Changes at {human_ts(run['ts'])}\n\n{summary_line(vis_counts)}\n{note}\n"
                     + changes_md(cfg, vis, run) + "\n", encoding="utf-8")
        changes_link = f"changes/{fname}.md"
        cl = root / "CHANGELOG.md"
        head = "# Change log\n\nNewest first. One line per check that found changes.\n\n"
        body = cl.read_text(encoding="utf-8").split("\n\n", 2)[-1] if cl.exists() else ""
        line = f"- **{human_ts(run['ts'])}**: {summary_line(vis_counts)} → [details]({changes_link})\n"
        cl.write_text(head + line + body, encoding="utf-8")

    # README dashboard block
    cov = f" of {run['expected']} advertised" if run.get("expected") else ""
    every = cfg.get("schedule", {}).get("check_every_hours", 3)
    if run.get("baseline"):
        latest = "First check: baseline saved. Changes will appear from the next check on."
    elif vis:
        latest = f"{summary_line(vis_counts)} → [full report]({changes_link})\n\n" + changes_md(cfg, vis, run, limit=10)
    else:
        latest = "No changes since the previous check. See [CHANGELOG.md](CHANGELOG.md) for earlier ones."
    warn = "\n> ⚠️ Last scrape looked incomplete; removals were not reported this time.\n" if run["partial"] else ""
    dash = (
        f"{DASH_START}\n"
        f"**Last check:** {human_ts(run['ts'])} · **{run['deals']}** deals tracked{cov} · checks every **{every} h**\n\n"
        f"📋 [All deals](deals.md) · 👀 [Watchlist](watchlist.md) ({len(wl)}) · 🕘 [Change log](CHANGELOG.md) · ⚙️ [Settings](config.yml)\n"
        f"{warn}\n## Latest changes\n\n{latest}\n{DASH_END}"
    )
    readme = root / "README.md"
    txt = readme.read_text(encoding="utf-8") if readme.exists() else f"# {title}\n\n{DASH_START}\n{DASH_END}\n"
    if DASH_START in txt and DASH_END in txt:
        txt = re.sub(re.escape(DASH_START) + r".*?" + re.escape(DASH_END), lambda _: dash, txt, flags=re.S)
    else:
        txt = txt + "\n" + dash + "\n"
    readme.write_text(txt, encoding="utf-8")


def append_price_history(path: Path, ts, changes, baseline_snap=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(["ts", "id", "event", "price", "discount", "stock_state"])
        if baseline_snap:
            for d in baseline_snap.values():
                w.writerow([ts, d["id"], "baseline", d.get("price"), d.get("discount"), d.get("stock_state")])
        for c in changes:
            d = c["deal"]
            w.writerow([ts, d["id"], c["type"], d.get("price"), d.get("discount"), d.get("stock_state")])
