# 🎸 Thomann Cyber Deals tracker

Tracks **every** deal on [thomann.pl Cyber Deals](https://www.thomann.pl/special_cyber-deals.html) (all pages behind "Pokaż więcej") and reports what changed since the last check: new and removed deals, price drops and rises, discount changes, and stock changes. It runs for free on GitHub Actions and writes plain Markdown, so you can read it on any phone.

<!-- DASHBOARD:START -->
**Last check:** 2026-11-26 04:59 CET · **1847** deals tracked of 1846 advertised · checks every **3 h**

📋 [All deals](deals.md) · 👀 [Watchlist](watchlist.md) (0) · 🕘 [Change log](CHANGELOG.md) · ⚙️ [Settings](config.yml)

## Latest changes

🆕 5 new deals · 🔁 12 returned deals · ❌ 3 removed deals · ✅ 1 back in stock → [full report](changes/2026-11-26T0359Z.md)

### 🆕 New deals (5)

| Product | Price | Discount | 30-day best | Stock | Badge |
|---|--:|--:|--:|---|---|
| [Kala KA-S Satin Mahogany Soprano](https://www.thomann.pl/kala_ka_s_satin_mahogany_soprano.htm) | 215 zł | ‑58% | 515 zł | Dostępny w magazynie |  |
| [Blackstar Carry On Digital Flute, black](https://www.thomann.pl/blackstar_carry_on_digital_flute_black.htm) | 173 zł | ‑56% | 389 zł | Dostępny w magazynie |  |
| [One Control Blackberry Bass OD Overdrive](https://www.thomann.pl/one_control_blackberry_bass_od_overdrive.htm) | 435 zł | ‑56% | 999 zł | Dostępny w magazynie |  |
| [Aquarian 22" Super Kick Clear Bass Set](https://www.thomann.pl/aquarian_22_super_kick_clear_bass_set.htm) | 259 zł | ‑52% | 539 zł | Dostępny w magazynie |  |
| [Yamaha YDP-S36 WH Arius Set](https://www.thomann.pl/yamaha_ydp_s36_wh_arius_set.htm) | 3 999 zł |  |  | Dostępny w magazynie |  |

### 🔁 Returned deals (12)

| Product | Price | Price when removed | Discount | 30-day best | Stock | Removed |
|---|--:|--:|--:|--:|---|---|
| [Eurolite LED Z-20](https://www.thomann.pl/eurolite_led_z_20.htm) | **173 zł** | 173 zł | ‑52% | 363 zł | Dostępny w magazynie | 2026‑11‑21 16:59 |
| [Citadel Bus Driver](https://www.thomann.pl/citadel_bus_driver.htm) | **389 zł** | 389 zł | ‑44% | 689 zł | Dostępny w magazynie | 2026‑11‑18 19:17 |
| [Tone City Holy Aura - Distortion / Boost](https://www.thomann.pl/tone_city_holy_aura_distortion_boost.htm) | **259 zł** | 259 zł | ‑40% | 432 zł | Dostępny w magazynie | 2026‑11‑25 01:57 |
| [Cort X-700 Triality OP VB](https://www.thomann.pl/cort_x_700_triality_op_vb.htm) | **3 499 zł** | 3 490 zł | ‑38% | 5 599 zł | Dostępny w magazynie | 2026‑11‑17 13:59 |
| [Hils Next HN4 Summer Sand](https://www.thomann.pl/hils_next_hn4_summer_sand.htm) | **1 599 zł** | 1 599 zł | ‑35% | 2 444 zł | Dostępny w magazynie | 2026‑11‑20 01:46 |
| [Recording King RM-995E-BN](https://www.thomann.pl/recording_king_rm_995e_bn.htm) | **2 899 zł** | 2 899 zł | ‑25% | 3 890 zł | Dostępny w magazynie | 2026‑11‑17 19:59 |
| [Strandberg Boden Standard N2.6T Fuchsia](https://www.thomann.pl/strandberg_boden_standard_n26t_fuchsia.htm) | **7 099 zł** | 6 999 zł | ‑18% | 8 699 zł | Dostępny w magazynie | 2026‑11‑23 23:00 |
| [Zoom LiveTrak L-6](https://www.thomann.pl/zoom_livetrak_l_6.htm) | **869 zł** | 869 zł |  |  | Dostępny w magazynie | 2026‑11‑25 19:59 |
| [Takamine EF341SC w/Softcase](https://www.thomann.pl/takamine_ef341sc_w_softcase.htm) | **5 699 zł** | 4 799 zł |  |  | dostępny w magazynie | 2026‑11‑24 13:59 |
| [Walrus Audio Canvas Rehearsal](https://www.thomann.pl/walrus_audio_canvas_rehearsal.htm) | **744 zł** | 744 zł |  |  | Dostępny w magazynie | 2026‑11‑23 01:59 |

…and 2 more in the full report.

### ❌ Removed deals (3)

| Product | Price | Discount | 30-day best | Stock | Badge |
|---|--:|--:|--:|---|---|
| [SOMA Warp](https://www.thomann.pl/soma_warp.htm) | 2 290 zł | ‑23% | 2 955 zł | Dostępny w magazynie |  |
| [Lauten Audio Clarion FC-357](https://www.thomann.pl/lauten_audio_clarion_fc_357.htm) | 4 222 zł | ‑19% | 5 199 zł | Dostępny w magazynie |  |
| [Erica Synths Steampipe](https://www.thomann.pl/erica_synths_steampipe.htm) | 3 999 zł | ‑18% | 4 899 zł | Dostępny w magazynie |  |

### ✅ Back in stock (1)

| Product | Price | Was | Now |
|---|--:|---|---|
| [NANO Modules ONA](https://www.thomann.pl/nano_modules_ona.htm) | 549 zł | Krótki czas oczekiwania (zazwyczaj 2-5 dni) | **dostępny w magazynie** |

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
