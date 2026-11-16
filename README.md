# 🎸 Thomann Cyber Deals tracker

Tracks **every** deal on [thomann.pl Cyber Deals](https://www.thomann.pl/special_cyber-deals.html) (all pages behind "Pokaż więcej") and reports what changed since the last check: new and removed deals, price drops and rises, discount changes, and stock changes. It runs for free on GitHub Actions and writes plain Markdown, so you can read it on any phone.

<!-- DASHBOARD:START -->
**Last check:** 2026-11-16 15:32 UTC · **1541** deals tracked of 1543 advertised · checks every **3 h**

📋 [All deals](deals.md) · 👀 [Watchlist](watchlist.md) (0) · 🕘 [Change log](CHANGELOG.md) · ⚙️ [Settings](config.yml)

## Latest changes

🆕 13 new deals → [full report](changes/2026-11-16T1532Z.md)

### 🆕 New deals (13)

| Product | Price | Discount | 30-day best | Stock | Badge |
|---|--:|--:|--:|---|---|
| [Sonor 13"x07" Kompressor Snare Beech](https://www.thomann.pl/sonor_13_x07_kompressor_snare_beech.htm) | 1 322 zł | -57% | 3 059 zł | Dostępny w magazynie |  |
| [Blackstar Carry On Digital Flute, white](https://www.thomann.pl/blackstar_carry_on_digital_flute_white.htm) | 172 zł | -56% | 389 zł | Dostępny w magazynie |  |
| [One Control Honey Bee OD - Overdrive](https://www.thomann.pl/one_control_honey_bee_od_overdrive_624367.htm) | 433 zł | -56% | 990 zł | Dostępny w magazynie |  |
| [Cort MR500E Open Pore Brown](https://www.thomann.pl/cort_mr500e_open_pore_brown.htm) | 869 zł | -47% | 1 639 zł | Dostępny w magazynie |  |
| [One Control Jubilee Red AIAB](https://www.thomann.pl/one_control_jubilee_red_aiab.htm) | 258 zł | -33% | 385 zł | Dostępny w magazynie |  |
| [Harley Benton TE-20HH SBK w/Soran Dual Stomp](https://www.thomann.pl/harley_benton_te_20hh_sbk_w_soran_dual_stomp.htm) | 698 zł | -29% | 990 zł | Dostępny w magazynie |  |
| [Warm Audio Foxy Tone Box Werewolf Fuzz](https://www.thomann.pl/warm_audio_foxy_tone_box_werewolf_fuzz.htm) | 433 zł | -22% | 555 zł | Dostępny w magazynie |  |
| [Walrus Audio Slö Multi Texture Reverb](https://www.thomann.pl/walrus_audio_sloe_multi_texture_reverb.htm) | 777 zł | -14% | 899 zł | Dostępny w magazynie |  |
| [Yamaha B3 SC3 PEC](https://www.thomann.pl/yamaha_b3_sc3_pec.htm) | 31 490 zł | -12% | 35 590 zł | Dostępny w magazynie |  |
| [Yamaha CG102 NT](https://www.thomann.pl/yamaha_cg102_nt.htm) | 898 zł |  |  | Dostępny w magazynie |  |

…and 3 more in the full report.

<!-- DASHBOARD:END -->

---

## How it works

1. Every hour GitHub wakes the workflow. If `check_every_hours` in [config.yml](config.yml) says a check is due, it fetches `?pg=1`, `?pg=2`, … until no new deals appear.
2. It compares the result with the last snapshot (`data/snapshot.json`) and writes:
   - **README.md**: this dashboard with the latest changes
   - **[deals.md](deals.md)**: every current deal in one table, with price, discount, 30-day best price, lowest price seen and stock
   - **[watchlist.md](watchlist.md)**: current deals matching your keywords
   - **[CHANGELOG.md](CHANGELOG.md)** + `changes/<time>.md`: the full history of changes
   - `data/price_history.csv`: every price event, for spreadsheets
3. Optional alerts: a GitHub issue (GitHub emails it and sends it to the GitHub app) and/or an [ntfy](https://ntfy.sh) phone push.

Safety nets: a deal must be missing **2 checks in a row** before it counts as removed, and if a check finds far fewer deals than last time (a blocked or half-loaded page), removals are skipped for that run.

## Settings

Everything is in **[config.yml](config.yml)**. You can edit it on github.com or in the GitHub app:

| Setting | What it does |
|---|---|
| `schedule.check_every_hours` | Check frequency (1 h minimum) |
| `schedule.active_from` / `active_until` | Only check during the sale |
| `report.show.*` | Which change types to report |
| `report.filters` | Minimum discount, price range, include/exclude keywords, section, stock |
| `report.deals_sort` | Sorting of deals.md (default: newest first, then biggest discount) |
| `watchlist` | Your keywords/products → watchlist.md + alerts |
| `alerts` | GitHub issue and/or ntfy push, which events, minimum drop % |
| `alerts.discord` | Discord message on new deals (or other change types) |
| `source.concurrency` | Pages fetched in parallel (default 4) |
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
3. Run **Track deals → Run workflow** once to save a baseline. From then on it runs by itself.
4. Edit `config.yml` to your taste.

Public repos get GitHub Actions for free with no limits. A private repo's free allowance (2,000 min/month) also covers hourly checks.

## Run locally

```bash
pip install -r requirements.txt
FORCE=1 python -m tracker.main
python -m unittest discover tests   # offline tests with a simulated shop
```

If a check parses 0 deals (Thomann changed its HTML), the workflow fails, GitHub emails you, and the raw page is attached to the failed run as `debug-html`.
