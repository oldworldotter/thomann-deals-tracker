# 🎸 Thomann Cyber Deals tracker

Tracks **every** deal on [thomann.pl Cyber Deals](https://www.thomann.pl/special_cyber-deals.html) (all pages behind "Pokaż więcej") and reports what changed since the last check: new and removed deals, price drops and rises, discount changes, and stock changes. It runs for free on GitHub Actions and writes plain Markdown, so you can read it on any phone.

<!-- DASHBOARD:START -->
**Last check:** 2026-11-19 22:59 CET · **1809** deals tracked of 1810 advertised · checks every **3 h**

📋 [All deals](deals.md) · 👀 [Watchlist](watchlist.md) (0) · 🕘 [Change log](CHANGELOG.md) · ⚙️ [Settings](config.yml)

## Latest changes

❌ 2 removed deals · 📈 4 price increases · 🏷️ 1 discount changes · ✅ 3 back in stock · 📦 6 stock changes → [full report](changes/2026-11-19T2159Z.md)

### ❌ Removed deals (2)

| Product | Price | Discount | 30-day best | Stock | Badge |
|---|--:|--:|--:|---|---|
| [Zoom V6 SP](https://www.thomann.pl/zoom_v6_sp.htm) | 879 zł | ‑34% | 1 333 zł | Dostępny w magazynie |  |
| [Harley Benton Fusion-IV HH MN OTC](https://www.thomann.pl/harley_benton_fusion_iv_hh_mn_otc.htm) | 1 499 zł | ‑21% | 1 899 zł | Dostępny w magazynie |  |

### 📈 Price increases (4)

| Product | Was | Now | Change | Discount | 30-day best | Stock |
|---|--:|--:|--:|--:|--:|---|
| [Thomann FL-200 Flute](https://www.thomann.pl/thomann_fls_querfloete.htm) | 699 zł | **711 zł** | +1.7% |  |  | Dostępny w magazynie |
| [Yamaha YTR-4335 GII Bb- Trumpet](https://www.thomann.pl/yamaha_ytr_4335_gii.htm) | 3 444 zł | **3 490 zł** | +1.3% |  |  | Dostępny w magazynie |
| [Yamaha YAS-280 Alto Sax](https://www.thomann.pl/yamaha_yas_280_alto_sax.htm) | 4 333 zł | **4 390 zł** | +1.3% |  |  | Dostępny w magazynie |
| [Gravity MS TBA 01](https://www.thomann.pl/gravity_ms_tba_01.htm) | 255 zł | **258 zł** | +1.2% |  |  | Dostępny w magazynie |

### 🏷️ Discount changes (1)

| Product | Price | Discount was | Discount now |
|---|--:|--:|--:|
| [Slate Digital ML-2A](https://www.thomann.pl/slate_digital_ml_2a.htm) | 1 177 zł | -30% | **none** |

### ✅ Back in stock (3)

| Product | Price | Was | Now |
|---|--:|---|---|
| [Harley Benton SC-400 GT w/Soran Dual Lite](https://www.thomann.pl/harley_benton_sc_400_gt_w_soran_dual_lite.htm) | 869 zł | Krótki czas oczekiwania (zazwyczaj 2-5 dni) | **Dostępny w magazynie** |
| [Harley Benton SC-400GT w/Marshall MG15G](https://www.thomann.pl/harley_benton_sc_400gt_w_marshall_mg15g.htm) | 1 069 zł | Krótki czas oczekiwania (zazwyczaj 2-5 dni) | **Dostępny w magazynie** |
| [Harley Benton HBWY-25 BKS w/Soran Tiny Stomp](https://www.thomann.pl/harley_benton_hbwy_25_bks_w_soran_tiny_stomp.htm) | 649 zł | Krótki czas oczekiwania (zazwyczaj 2-5 dni) | **Dostępny w magazynie** |

### 📦 Stock changes (6)

| Product | Price | Was | Now |
|---|--:|---|---|
| [Marcus Miller M6 Headless 5 TS](https://www.thomann.pl/marcus_miller_m6_headless_5_ts.htm) | 3 055 zł | Dostępny w magazynie | **Krótki czas oczekiwania (zazwyczaj 2-5 dni)** |
| [Hils Next HN4 Black](https://www.thomann.pl/hils_next_hn4_black.htm) | 1 745 zł | Dostępny w magazynie | **Krótki czas oczekiwania (zazwyczaj 2-5 dni)** |
| [JBL BandBox TRIO Bag Bundle](https://www.thomann.pl/jbl_bandbox_trio_bag_bundle.htm) | 2 599 zł | Dostępny w magazynie | **Dostępny za 1–2 tygodnie** |
| [Hils Next HN3 Met. Emerald Green](https://www.thomann.pl/hils_next_hn3_met._emerald_green.htm) | 1 444 zł | Dostępny w magazynie | **Krótki czas oczekiwania (zazwyczaj 2-5 dni)** |
| [Harley Benton EX-84 Modern BK](https://www.thomann.pl/harley_benton_het_550_bk.htm) | 1 177 zł | Dostępny w magazynie | **Krótki czas oczekiwania (zazwyczaj 2-5 dni)** |
| [Harley Benton Blues Guitar Set 2](https://www.thomann.pl/harley_benton_blues_guitar_set_2.htm) | 369 zł | Dostępny w magazynie | **Krótki czas oczekiwania (zazwyczaj 2-5 dni)** |

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
