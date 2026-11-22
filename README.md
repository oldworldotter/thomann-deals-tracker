# 🎸 Thomann Cyber Deals tracker

Tracks **every** deal on [thomann.pl Cyber Deals](https://www.thomann.pl/special_cyber-deals.html) (all pages behind "Pokaż więcej") and reports what changed since the last check: new and removed deals, price drops and rises, discount changes, and stock changes. It runs for free on GitHub Actions and writes plain Markdown, so you can read it on any phone.

<!-- DASHBOARD:START -->
**Last check:** 2026-11-22 22:59 CET · **1772** deals tracked of 1773 advertised · checks every **3 h**

📋 [All deals](deals.md) · 👀 [Watchlist](watchlist.md) (0) · 🕘 [Change log](CHANGELOG.md) · ⚙️ [Settings](config.yml)

## Latest changes

❌ 5 removed deals · 📈 1 price increases · 🏷️ 12 discount changes · 📦 3 stock changes → [full report](changes/2026-11-22T2159Z.md)

### ❌ Removed deals (5)

| Product | Price | Discount | 30-day best | Stock | Badge |
|---|--:|--:|--:|---|---|
| [Music Man Sabre Blackdraft](https://www.thomann.pl/music_man_sabre_blackdraft.htm) | 12 990 zł | ‑21% | 16 390 zł | Dostępny w magazynie |  |
| [Alesis Vortex Wireless 2](https://www.thomann.pl/alesis_vortex_wireless_2.htm) | 898 zł |  |  | Dostępny w magazynie |  |
| [DW 5100 Drummer Throne](https://www.thomann.pl/dw_5100_drummer_throne.htm) | 535 zł |  |  | Dostępny w magazynie |  |
| [Sela Seed Chime Kenari XL](https://www.thomann.pl/sela_seed_chime_kenari_xl.htm) | 259 zł |  |  | Dostępny w magazynie |  |
| [Sonor Vintage Three20 Rosewood WM](https://www.thomann.pl/sonor_vintage_three20_rosewood_wm.htm) | 11 990 zł |  |  | Dostępny w magazynie |  |

### 📈 Price increases (1)

| Product | Was | Now | Change | Discount | 30-day best | Stock |
|---|--:|--:|--:|--:|--:|---|
| [Shure SLXD24+E/Beta58 G65](https://www.thomann.pl/shure_slxd24e_beta58_g65.htm) | 4 099 zł | **4 190 zł** | +2.2% |  |  | Dostępny w magazynie |

### 🏷️ Discount changes (12)

| Product | Price | Discount was | Discount now |
|---|--:|--:|--:|
| [Thomann Phoenix S F-Tuba](https://www.thomann.pl/thomann_phoenix_s_f_tuba.htm) | 17 790 zł | -10% | **-11%** |
| [JH Audio Universal JH5 Clear](https://www.thomann.pl/jh_audio_universal_jh5_clear.htm) | 1 499 zł | -19% | **none** |
| [Stairville LED BossFx-1 Pro Bundle Bundle](https://www.thomann.pl/stairville_led_bossfx_1_pro_bundle_bundle.htm) | 1 499 zł | -8% | **-9%** |
| [Yamaha YDS-122 Digital Saxophone](https://www.thomann.pl/yamaha_yds_122_digital_saxophone.htm) | 1 699 zł | -13% | **-14%** |
| [Gibson SG ´61 Standard Pelham Blue](https://www.thomann.pl/gibson_sg_61_standard_pelham_blue.htm) | 7 799 zł | -5% | **-6%** |
| [Boss VG-800 V-Guitar Processor](https://www.thomann.pl/boss_vg_800_v_guitar_processor.htm) | 2 290 zł | -15% | **-16%** |
| [Stairville RevueLED 150 Prof. 26° Bundle](https://www.thomann.pl/stairville_revueled_150_prof_26_bundle.htm) | 4 333 zł | -10% | **none** |
| [Focusrite Scarlett 18i20 4th Gen](https://www.thomann.pl/focusrite_scarlett_18i20_4th_gen.htm) | 2 190 zł | -19% | **-21%** |
| [Focusrite Scarlett Solo 4th Gen](https://www.thomann.pl/focusrite_scarlett_solo_4th_gen.htm) | 475 zł | -17% | **-18%** |
| [Yamaha PSS-E30](https://www.thomann.pl/yamaha_pss_e30.htm) | 222 zł | -9% | **-10%** |

…and 2 more in the full report.

### 📦 Stock changes (3)

| Product | Price | Was | Now |
|---|--:|---|---|
| [Wild Dog Bunyip](https://www.thomann.pl/wild_dog_bunyip.htm) | 1 438 zł | Dostępny w magazynie | **Krótki czas oczekiwania (zazwyczaj 2-5 dni)** |
| [OXI Instruments One MKII Black Edition](https://www.thomann.pl/oxi_instruments_one_mkii_black_edition.htm) | 3 099 zł | Dostępny w magazynie | **Dostępny za 1–2 tygodnie** |
| [Terre Djembe Carved Dragon 50cm](https://www.thomann.pl/terre_djembe_carved_dragon_50cm.htm) | 255 zł | Dostępny w magazynie | **Krótki czas oczekiwania (zazwyczaj 2-5 dni)** |

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
