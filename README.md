# 🎸 Thomann Cyber Deals tracker

Tracks **every** deal on [thomann.pl Cyber Deals](https://www.thomann.pl/special_cyber-deals.html) (all pages behind "Pokaż więcej") and reports what changed since the last check: new and removed deals, price drops and rises, discount changes, and stock changes. It runs for free on GitHub Actions and writes plain Markdown, so you can read it on any phone.

<!-- DASHBOARD:START -->
**Last check:** 2026-11-17 04:59 CET · **1553** deals tracked of 1553 advertised · checks every **3 h**

📋 [All deals](deals.md) · 👀 [Watchlist](watchlist.md) (0) · 🕘 [Change log](CHANGELOG.md) · ⚙️ [Settings](config.yml)

## Latest changes

🆕 20 new deals · ❌ 1 removed deals · 📦 1 stock changes → [full report](changes/2026-11-17T0359Z.md)

### 🆕 New deals (20)

| Product | Price | Discount | 30-day best | Stock | Badge |
|---|--:|--:|--:|---|---|
| [Eurolite LED Z-20](https://www.thomann.pl/eurolite_led_z_20.htm) | 172 zł | ‑53% | 363 zł | Dostępny w magazynie |  |
| [Sela SE 241 Kalimba Black 10](https://www.thomann.pl/sela_se_241_kalimba_black_10.htm) | 39 zł | ‑52% | 82 zł | Dostępny w magazynie |  |
| [Bulldog Phoenix Zebrano](https://www.thomann.pl/bulldog_phoenix_zebrano.htm) | 299 zł | ‑45% | 539 zł | Dostępny w magazynie |  |
| [Cort CM15-R Dark Blue](https://www.thomann.pl/cort_cm15_r_dark_blue.htm) | 299 zł | ‑42% | 515 zł | Dostępny w magazynie |  |
| [Hils HNB5 Sunburst](https://www.thomann.pl/hils_hnb5_sunburst.htm) | 1 739 zł | ‑42% | 2 990 zł | Dostępny w magazynie |  |
| [PRS SE Santana SY 2025](https://www.thomann.pl/prs_se_santana_sy_2025.htm) | 2 599 zł | ‑40% | 4 333 zł | Dostępny w magazynie | GIVEAWAY |
| [Mooer GTRS Guitars Standard 801 SP](https://www.thomann.pl/mooer_gtrs_guitars_standard_801_sp.htm) | 899 zł | ‑38% | 1 444 zł | Dostępny w magazynie |  |
| [Cort X-700 Triality OP VB](https://www.thomann.pl/cort_x_700_triality_op_vb.htm) | 3 490 zł | ‑38% | 5 599 zł | Dostępny w magazynie |  |
| [Martin Guitar D Jr E StreetMaster New](https://www.thomann.pl/martin_guitar_d_jr_e_streetmaster.htm) | 2 999 zł | ‑36% | 4 699 zł | Dostępny w magazynie |  |
| [Sela Seed Shaker Mixed](https://www.thomann.pl/sela_seed_shaker_mixed.htm) | 83 zł | ‑34% | 125 zł | Dostępny w magazynie |  |

…and 10 more in the full report.

### ❌ Removed deals (1)

| Product | Price | Discount | 30-day best | Stock | Badge |
|---|--:|--:|--:|---|---|
| [Suzuki Omnichord OM-108](https://www.thomann.pl/suzuki_omnichord_om_108.htm) | 2 999 zł | ‑13% | 3 444 zł | Dostępny w magazynie |  |

### 📦 Stock changes (1)

| Product | Price | Was | Now |
|---|--:|---|---|
| [Midas DL32](https://www.thomann.pl/midas_dl32.htm) | 4 499 zł | Dostępny w magazynie | **Dostępny za 4–5 tygodnie** |

<!-- DASHBOARD:END -->

---

## How it works

1. Something starts the workflow (see [What starts a check](#what-starts-a-check)). If `check_every_hours` in [config.yml](config.yml) says a check is due, it fetches `?pg=1`, `?pg=2`, … one page at a time until no new deals appear.
2. It compares the result with the last snapshot (`data/snapshot.json`) and writes:
   - **README.md**: this dashboard with the latest changes
   - **[deals.md](deals.md)**: every current deal in one table, with price, discount, 30-day best price, lowest price seen and stock
   - **[watchlist.md](watchlist.md)**: current deals matching your keywords
   - **[CHANGELOG.md](CHANGELOG.md)** + `changes/<time>.md`: the full history of changes (new, returned and removed deals, price, discount and stock changes)
   - `data/price_history.csv`: every price event, for spreadsheets
3. Optional alerts: a GitHub issue (GitHub emails it and sends it to the GitHub app) and/or an [ntfy](https://ntfy.sh) phone push.

Safety nets: a deal must be missing **2 checks in a row** before it counts as removed. If a check looks incomplete (a page never loaded, far fewer deals than last time, or fewer than Thomann itself advertises), removals are skipped for that run.

All times are shown in the zone set by `display_timezone`, and each check uses one time everywhere: the moment it started.

## What starts a check

The workflow can be started three ways. The title of each run in the **Actions** tab says which one it was:

| Run title | Started by |
|---|---|
| **Scheduled check (GitHub cron)** | GitHub's own timer (`cron` in `.github/workflows/track.yml`), every hour at :30 |
| **Scheduled check (started by Claude)** | An outside trigger that runs `gh workflow run track.yml --ref main -f force=false` |
| **Manual check** | You: **Actions → Track deals → Run workflow**, or `gh workflow run track.yml` |

A scheduled start only does a full check when `check_every_hours` have passed since the last scheduled check *started*; otherwise it ends after a few seconds. A manual check always runs and doesn't shift that rhythm.

GitHub does not guarantee its timer, and on this repo it has not fired at all, so an outside trigger does the job. Any scheduler that can run the command above works (a cron job on your own machine, cron-job.org with a token, a Claude scheduled task).

## Settings

Everything is in **[config.yml](config.yml)**. You can edit it on github.com or in the GitHub app:

| Setting | What it does |
|---|---|
| `schedule.check_every_hours` | Hours between scheduled checks (whatever starts the workflow must fire at least this often) |
| `schedule.active_from` / `active_until` | Only check during the sale |
| `report.show.*` | Which change types to report |
| `diff.min_price_change_pct` | Ignore price moves smaller than this (default 1 %) |
| `display_timezone` | Time zone for all times shown |
| `report.filters` | Minimum discount, price range, include/exclude keywords, section, stock |
| `report.deals_sort` | Sorting of deals.md (default: newest first, then biggest discount) |
| `watchlist` | Your keywords/products → watchlist.md + alerts |
| `alerts` | GitHub issue and/or ntfy push, which events, minimum drop % |
| `alerts.discord` | Discord message on new deals (or other change types) |
| `source.concurrency`, `source.delay_seconds` | How fast pages are fetched (default: one page every ~3 s, which Thomann doesn't throttle) |
| `source.cumulative_pages` | Shortcut: page 20 repeats pages 1–19, so those are skipped (checked on every run; 0 turns it off) |
| `source.url` | Track a different Thomann shop or deals page |

## Discord alerts

After each check that finds new deals, one message goes to a Discord channel listing them, with links to `deals.md` and the full report.

1. In Discord, open the channel's **Edit Channel → Integrations → Webhooks → New Webhook**, then **Copy Webhook URL**. You need the *Manage Webhooks* permission on that server.
2. Save it as a repo secret, never in config.yml:
   ```bash
   gh secret set DISCORD_WEBHOOK_URL
   ```
   (paste the URL when asked)
3. Adjust `alerts.discord` in config.yml: which change types (`on`), filters, and how many deals to list.

If the repo is private, people in the channel need access to the repo to open the `deals.md` link. The product links work for everyone.

## Share or set up your own copy

Anyone can **read** this repo if it's public. To get your own tracker with your own settings:

1. **Fork** this repo (or *Use this template*).
2. In your fork, open **Actions** and click **Enable workflows**.
3. Run **Track deals → Run workflow** once to save a baseline. If GitHub's timer fires for your fork, it runs by itself from then on; if not, see [What starts a check](#what-starts-a-check).
4. Edit `config.yml` to your taste.

Public repos get GitHub Actions for free with no limits. A private repo's free allowance (2,000 min/month) also covers hourly checks.

## Run locally

```bash
pip install -r requirements.txt
FORCE=1 python -m tracker.main
python -m unittest discover tests   # offline tests with a simulated shop (about 15 s)
```

The tests also run on GitHub whenever the code or `config.yml` changes (the **Tests** workflow), so a typo in the settings shows up as a failed run.

If a check parses 0 deals (Thomann changed its HTML), the workflow fails, GitHub emails you, and the raw page is attached to the failed run as `debug-html`.
