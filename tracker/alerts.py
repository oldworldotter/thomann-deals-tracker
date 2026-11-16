"""Optional alerts: a GitHub issue, an ntfy.sh push, and/or a Discord channel message (webhook)."""
from __future__ import annotations

import logging
import os

import requests

from .report import ICONS, money, watch_match, matches

log = logging.getLogger(__name__)


def select(cfg, changes, a=None):
    """Pick the changes an alert channel cares about. `a` is that channel's settings."""
    if a is None:
        a = cfg.get("alerts", {})
        if not (a.get("github_issue") or a.get("ntfy_topic")):
            return []
    types = set(a.get("on") or ["added", "price_down", "back_in_stock"])
    w = cfg.get("watchlist", {})
    out = []
    for c in changes:
        if c["type"] not in types:
            continue
        d = c["deal"]
        if a.get("only_watchlist", True) and not watch_match(d, w):
            continue
        if not matches(d, a.get("filters") or {}):
            continue
        if c["type"] == "price_down" and (c.get("pct") or 0) > -float(a.get("min_drop_pct", 0)):
            continue
        out.append(c)
    return out


def _line(c, cfg):
    d = c["deal"]
    icon = ICONS[c["type"]][0]
    if c["type"] in ("price_down", "price_up"):
        what = f"{money(c['old'], cfg)} → {money(c['new'], cfg)} ({c['pct']:+.1f}%)"
    elif c["type"] in ("stock", "back_in_stock"):
        what = f"{c['old']} → {c['new']}"
    else:
        what = money(d.get("price"), cfg) + (f" (-{d['discount']}%)" if d.get("discount") else "")
    return icon, d.get("name") or d["id"], what, d["url"]


def send(cfg, hits, run):
    a = cfg.get("alerts", {})
    title = f"{len(hits)} deal alert(s) at {run['ts'].replace('T', ' ').replace('Z', ' UTC')}"
    if a.get("github_issue"):
        _github_issue(cfg, hits, title)
    if a.get("ntfy_topic"):
        _ntfy(cfg, hits, title, a["ntfy_topic"], a.get("ntfy_server", "https://ntfy.sh"))


def _github_issue(cfg, hits, title):
    token, repo = os.environ.get("GITHUB_TOKEN"), os.environ.get("GITHUB_REPOSITORY")
    if not (token and repo):
        log.info("GitHub issue alert skipped (not running in GitHub Actions)")
        return
    body = "\n".join(f"- {i} [{n}]({u}): {w}" for i, n, w, u in (_line(c, cfg) for c in hits))
    body += "\n\n_Close this issue whenever you like; a new one is opened on the next alert._"
    r = requests.post(
        f"https://api.github.com/repos/{repo}/issues",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
        json={"title": title, "body": body, "labels": ["deal-alert"]},
        timeout=30,
    )
    if r.status_code >= 300:
        log.warning("GitHub issue failed: %s %s", r.status_code, r.text[:300])


def _ntfy(cfg, hits, title, topic, server):
    lines = [f"{i} {n}: {w}" for i, n, w, _ in (_line(c, cfg) for c in hits)]
    msg = "\n".join(lines[:15]) + (f"\n…and {len(lines) - 15} more" if len(lines) > 15 else "")
    repo = os.environ.get("GITHUB_REPOSITORY")
    headers = {"Title": title, "Tags": "moneybag"}
    if repo:
        headers["Click"] = f"https://github.com/{repo}"
    try:
        requests.post(f"{server.rstrip('/')}/{topic}", data=msg.encode("utf-8"), headers=headers, timeout=30)
    except Exception as e:
        log.warning("ntfy failed: %s", e)


# ---------- Discord ----------
def discord(cfg, changes, run):
    """Post one message per check to a Discord channel via its webhook.

    The webhook URL is a secret: it comes from the DISCORD_WEBHOOK_URL environment
    variable (a GitHub Actions secret), never from config.yml.
    """
    dc = (cfg.get("alerts", {}) or {}).get("discord") or {}
    url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    if not dc.get("enabled") or not url:
        if dc.get("enabled"):
            log.info("Discord alert skipped: DISCORD_WEBHOOK_URL secret is not set")
        return
    settings = {"on": dc.get("on") or ["added"], "only_watchlist": dc.get("only_watchlist", False),
                "filters": dc.get("filters") or {}, "min_drop_pct": dc.get("min_drop_pct", 0)}
    hits = select(cfg, changes, settings)
    if not hits:
        return
    repo = os.environ.get("GITHUB_REPOSITORY")
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    base = f"{server}/{repo}/blob/main" if repo else None
    report_file = f"changes/{run['ts'].replace(':', '')}.md"

    counts = {}
    for c in hits:
        counts[c["type"]] = counts.get(c["type"], 0) + 1
    summary = " · ".join(f"{ICONS[t][0]} {n} {ICONS[t][1].lower()}" for t, n in counts.items())

    max_items = int(dc.get("max_items", 15))
    order = {"added": 0, "price_down": 1, "back_in_stock": 2}
    hits = sorted(hits, key=lambda c: (order.get(c["type"], 9), -(c["deal"].get("discount") or 0)))
    lines = []
    for c in hits[:max_items]:
        icon, name, what, link = _line(c, cfg)
        name = name.replace("[", "(").replace("]", ")")
        lines.append(f"{icon} [{name}]({link}): {what}")
    if len(hits) > max_items:
        lines.append(f"…and {len(hits) - max_items} more")
    desc = ""
    for ln in lines:  # embed description limit is 4096 chars
        if len(desc) + len(ln) + 1 > 3800:
            desc += "…"
            break
        desc += ln + "\n"
    links = []
    if base:
        links.append(f"[📋 All deals (deals.md)]({base}/deals.md)")
        links.append(f"[🔍 Full report]({base}/{report_file})")
    if links:
        desc += "\n" + " · ".join(links)

    payload = {
        "username": dc.get("username", "Thomann deals"),
        "content": f"**{summary}** at {run['ts'].replace('T', ' ').replace('Z', ' UTC')}",
        "embeds": [{
            "title": cfg.get("title", "Thomann deals"),
            "url": f"{base}/deals.md" if base else cfg["source"]["url"],
            "description": desc,
            "color": 0x2B7DE9,
        }],
        "allowed_mentions": {"parse": []},
    }
    try:
        r = requests.post(url, json=payload, timeout=30)
        if r.status_code >= 300:
            log.warning("Discord webhook failed: %s %s", r.status_code, r.text[:300])
        else:
            log.info("Discord: posted %s alert(s)", len(hits))
    except Exception as e:
        log.warning("Discord webhook failed: %s", e)
