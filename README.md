# 🎸 Thomann Cyber Deals tracker

Tracks **every** deal on [thomann.pl Cyber Deals](https://www.thomann.pl/special_cyber-deals.html) (all pages behind "Pokaż więcej") and reports what changed since the last check: new and removed deals, price drops and rises, discount changes, and stock changes. It runs for free on GitHub Actions and writes plain Markdown, so you can read it on any phone.

<!-- DASHBOARD:START -->
**Last check:** 2026-11-20 01:46 CET · **1808** deals tracked of 1808 advertised · checks every **3 h**

📋 [All deals](deals.md) · 👀 [Watchlist](watchlist.md) (0) · 🕘 [Change log](CHANGELOG.md) · ⚙️ [Settings](config.yml)

## Latest changes

🆕 1 new deals · ❌ 7 removed deals · ✅ 2 back in stock · 📦 5 stock changes → [full report](changes/2026-11-20T0046Z.md)

### 🆕 New deals (1)

| Product | Price | Discount | 30-day best | Stock | Badge |
|---|--:|--:|--:|---|---|
| [Hercules DJ Control Inpulse 500](https://www.thomann.pl/hercules_dj_control_inpulse_500.htm) | 869 zł | ‑19% | 1 079 zł | Dostępny w magazynie |  |

### ❌ Removed deals (7)

| Product | Price | Discount | 30-day best | Stock | Badge |
|---|--:|--:|--:|---|---|
| [One Control Hooker's Green Bass Machine 4K](https://www.thomann.pl/one_control_hookers_green_bass_machine_4k.htm) | 258 zł | ‑57% | 599 zł | Dostępny w magazynie |  |
| [Hils Next HN4 Summer Sand](https://www.thomann.pl/hils_next_hn4_summer_sand.htm) | 1 599 zł | ‑35% | 2 444 zł | Dostępny w magazynie |  |
| [Electro Harmonix LPB-3 Boost & EQ](https://www.thomann.pl/electro_harmonix_lpb_3_boost_eq.htm) | 444 zł | ‑33% | 658 zł | Dostępny w magazynie |  |
| [Fender Rumble 40 V3 Ivory](https://www.thomann.pl/fender_rumble_40_v3_ivory.htm) | 1 499 zł | ‑25% | 1 990 zł | Dostępny w magazynie |  |
| [Strandberg Boden Original N2.6 Sunset](https://www.thomann.pl/strandberg_boden_original_n26_sunset.htm) | 8 799 zł | ‑22% | 11 333 zł | Dostępny w magazynie |  |
| [Electro Harmonix Silencer](https://www.thomann.pl/electro_harmonix_silencer.htm) | 289 zł |  |  | Dostępny w magazynie |  |
| [Mackie Thump 215](https://www.thomann.pl/mackie_thump_215.htm) | 1 299 zł |  |  | Dostępny w magazynie | Deal |

### ✅ Back in stock (2)

| Product | Price | Was | Now |
|---|--:|---|---|
| [JBL BandBox TRIO Bag Bundle](https://www.thomann.pl/jbl_bandbox_trio_bag_bundle.htm) | 2 599 zł | Dostępny za 1–2 tygodnie | **dostępny w magazynie** |
| [LD Systems Maui 28 G3 White](https://www.thomann.pl/ld_systems_maui_28_g3_white.htm) | 5 890 zł | Dostępny za 1–2 tygodnie | **dostępny w magazynie** |

### 📦 Stock changes (5)

| Product | Price | Was | Now |
|---|--:|---|---|
| [PUR PTC-01 Travel Compact Cajon](https://www.thomann.pl/pur_ptc_01_travel_compact_cajon.htm) | 257 zł | dostępny w magazynie | **Krótki czas oczekiwania (zazwyczaj 2-5 dni)** |
| [Yamaha YDP-146 R Arius Set](https://www.thomann.pl/yamaha_ydp_146_r_arius_set.htm) | 3 890 zł | Dostępny w magazynie | **Krótki czas oczekiwania (zazwyczaj 2-5 dni)** |
| [Sequential Fourm](https://www.thomann.pl/sequential_fourm.htm) | 2 890 zł | dostępny w magazynie | **Krótki czas oczekiwania (zazwyczaj 2-5 dni)** |
| [Expert Sleepers Disting NT](https://www.thomann.pl/expert_sleepers_disting_nt.htm) | 2 399 zł | dostępny w magazynie | **Krótki czas oczekiwania (zazwyczaj 2-5 dni)** |
| [Heritage Musical Spoon Medium Blue](https://www.thomann.pl/heritage_musical_spoon_medium_blue.htm) | 126 zł | dostępny w magazynie | **Krótki czas oczekiwania (zazwyczaj 2-5 dni)** |

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
