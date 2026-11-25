# 🎸 Thomann Cyber Deals tracker

Tracks **every** deal on [thomann.pl Cyber Deals](https://www.thomann.pl/special_cyber-deals.html) (all pages behind "Pokaż więcej") and reports what changed since the last check: new and removed deals, price drops and rises, discount changes, and stock changes. It runs for free on GitHub Actions and writes plain Markdown, so you can read it on any phone.

<!-- DASHBOARD:START -->
**Last check:** 2026-11-25 01:57 CET · **1748** deals tracked of 1747 advertised · checks every **3 h**

📋 [All deals](deals.md) · 👀 [Watchlist](watchlist.md) (0) · 🕘 [Change log](CHANGELOG.md) · ⚙️ [Settings](config.yml)

## Latest changes

❌ 9 removed deals · ✅ 3 back in stock · 📦 6 stock changes → [full report](changes/2026-11-25T0057Z.md)

### ❌ Removed deals (9)

| Product | Price | Discount | 30-day best | Stock | Badge |
|---|--:|--:|--:|---|---|
| [Sonor 14"x5.75" MOM. Snare Maple REP](https://www.thomann.pl/sonor_14x575_mom_snare_maple_rep.htm) | 2 199 zł | ‑40% | 3 666 zł | Dostępny w magazynie |  |
| [Tone City Holy Aura - Distortion / Boost](https://www.thomann.pl/tone_city_holy_aura_distortion_boost.htm) | 259 zł | ‑40% | 432 zł | Dostępny w magazynie |  |
| [Gibson LP Junior 57 Singlecut TVY VOS](https://www.thomann.pl/gibson_lp_junior_57_singecut_tvy_vos.htm) | 12 690 zł | ‑19% | 15 690 zł | Dostępny w magazynie |  |
| [Epiphone 1963 Firebird I Silver Mist](https://www.thomann.pl/epiphone_1963_firebird_i_silver_mist.htm) | 3 899 zł | ‑14% | 4 555 zł | Dostępny w magazynie |  |
| [Gibson Les Paul Custom 70s Wine Red](https://www.thomann.pl/gibson_les_paul_custom_70s_wine_red.htm) | 13 333 zł | ‑13% | 15 290 zł | Dostępny w magazynie |  |
| [Elation SDC-6 Faderdesk V2 black](https://www.thomann.pl/elation_sdc_6_faderdesk_v2_black.htm) | 154 zł |  |  | Dostępny w magazynie |  |
| [Guild Starfire I DC Cherry](https://www.thomann.pl/guild_starfire_i_dc_cherry.htm) | 1 977 zł |  |  | Dostępny w magazynie |  |
| [Kala Ukadelic Soprano Uku BL](https://www.thomann.pl/kala_ukadelic_soprano_uku_bl.htm) | 88 zł |  |  | Krótki czas oczekiwania (zazwyczaj 2-5 dni) |  |
| [Varytec LED Pad7 7x10W 6in1 RGBAWUV BL](https://www.thomann.pl/varytec_led_pad7_7x10w_6in1_rgbwauv_bl.htm) | 374 zł |  |  | Dostępny w magazynie |  |

### ✅ Back in stock (3)

| Product | Price | Was | Now |
|---|--:|---|---|
| [Midas M32 Live](https://www.thomann.pl/midas_m_32_live.htm) | 11 790 zł | Dostępny za 10–13 tygodnie | **Dostępny w magazynie** |
| [ESP Eclipse Custom DB Black Satin](https://www.thomann.pl/esp_eclipse_custom_db_black_satin.htm) | 21 090 zł | Dostępny za 1–2 tygodnie | **dostępny w magazynie** |
| [Daddario XSE1052-3P](https://www.thomann.pl/daddario_xse1052_3p.htm) | 148 zł | Dostępny za 1–2 tygodnie | **dostępny w magazynie** |

### 📦 Stock changes (6)

| Product | Price | Was | Now |
|---|--:|---|---|
| [Stairville Tri Flat PAR Profile Bundle](https://www.thomann.pl/stairville_tri_flat_par_profile_bundle.htm) | 1 099 zł | Dostępny w magazynie | **Dostępny za 1–2 tygodnie** |
| [Fun Generation SePar Hex LED RGBAW UV Bundle](https://www.thomann.pl/fun_generation_separ_hex_led_rgbaw_uv_bundle.htm) | 1 019 zł | Dostępny w magazynie | **Dostępny za 1–2 tygodnie** |
| [Harley Benton SC-500 BK w/Soran Dual Stomp](https://www.thomann.pl/harley_benton_sc_500_bk_w_soran_dual_stomp.htm) | 999 zł | Dostępny w magazynie | **Krótki czas oczekiwania (zazwyczaj 2-5 dni)** |
| [Harley Benton SC-500BK w/Marshall MG15GFX](https://www.thomann.pl/harley_benton_sc_500bk_w_marshall_mg15gfx.htm) | 1 399 zł | Dostępny w magazynie | **Krótki czas oczekiwania (zazwyczaj 2-5 dni)** |
| [ESP LTD EC-1000 FT Black Fluence](https://www.thomann.pl/esp_ltd_ec_01_ft_black_fluence.htm) | 4 899 zł | Dostępny w magazynie | **Dostępny za 1–2 tygodnie** |
| [Harley Benton SC-Custom III Gold Top](https://www.thomann.pl/harley_benton_sc_custom_iii_gold_top.htm) | 1 090 zł | Dostępny w magazynie | **Krótki czas oczekiwania (zazwyczaj 2-5 dni)** |

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
