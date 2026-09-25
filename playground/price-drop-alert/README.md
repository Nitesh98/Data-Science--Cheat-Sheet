# Price Drop Alert 🔔

A small Python app that watches product pages on shopping sites and **notifies you
when the price drops** (or falls to a target price you choose). Alerts can go
to your phone (ntfy or Telegram), your email, or a desktop pop-up.

Uses only the Python 3 standard library, so there's nothing to install.

## Quick start

```bash
cd playground/price-drop-alert

# 1. See it work offline with a fake shop whose price keeps falling
python3 price_tracker.py demo

# 2. Track a real product (alert on any drop)
python3 price_tracker.py add "https://www.example-shop.com/product/123"

#    ...or only alert when it's ₹1,999 or less
python3 price_tracker.py add "https://www.example-shop.com/product/123" --target 1999

# 3. See what you're tracking
python3 price_tracker.py list

# 4. Check prices: once, or keep checking every hour
python3 price_tracker.py check
python3 price_tracker.py watch --every 60
```

Other commands: `history <id>` shows a price chart in the terminal,
`remove <id>` stops tracking, and `test-notify` sends a test alert.

## When you get alerted

| You set                | You get a notification when…                                      |
|------------------------|-------------------------------------------------------------------|
| no `--target`          | the price is lower than the last time it was checked              |
| `--target 1999`        | the price first reaches ₹1,999 or less, and again if it drops further |

The same price never triggers a second alert.

## Getting alerts on your phone

Copy `config.env.example` to `config.env` and turn on the channels you want.
`config.env` is git-ignored, so your secrets are never committed.

- **ntfy (easiest):** install the free *ntfy* app, subscribe to a
  hard-to-guess topic name, and set `NTFY_TOPIC` to the same name.
- **Telegram:** create a bot with @BotFather and set `TELEGRAM_BOT_TOKEN` and
  `TELEGRAM_CHAT_ID`.
- **Email:** set the `SMTP_*` values. For Gmail, use an *App Password*.
- **Desktop pop-up:** on by default on Mac, Windows and Linux desktops.

Then run `python3 price_tracker.py test-notify` to confirm it works.

## Running it automatically

`watch` only runs while your terminal is open. To check in the background,
schedule `check` instead:

- **Mac / Linux (cron):** run `crontab -e` and add
  `0 * * * * cd /path/to/playground/price-drop-alert && /usr/bin/python3 price_tracker.py check >> tracker.log 2>&1`
- **Windows:** open Task Scheduler, create a basic task that runs hourly,
  program `python`, arguments `price_tracker.py check`, "Start in" = this folder.

## How it finds the price

It tries these in order and uses the first that works:

1. **JSON-LD product data** (`schema.org` `offers.price`). Most stores include
   this for Google Shopping, so it's the most reliable source.
2. **Meta tags**: `product:price:amount`, `og:price:amount`, `itemprop="price"`.
3. **Site-specific patterns** for Amazon, Myntra and Flipkart. These are best
   effort because stores change their HTML often.
4. **Your own pattern.** If nothing above works, open the page source, find the
   price, and pass a regex whose first group is the number:
   `add URL --pattern 'class="final-price">₹([\d,]+)'`

### Sites that block trackers

Some big stores (Amazon, Myntra, Flipkart) block automated requests, or load
the price with JavaScript after the page opens. When that happens, `check`
says *"couldn't find a price"* and saves the error, which `list` then shows.
A browser-automation version (for example with Playwright) could handle
these sites, but it needs third-party packages. Check the store's terms
before you scrape it, and keep checks infrequent. Once an hour is plenty.

## Files

| File | What it is |
|------|------------|
| `price_tracker.py` | The whole app (CLI, price extraction, notifications) |
| `config.env.example` | Template for notification settings |
| `watchlist.json` | Created automatically; your tracked items and price history (git-ignored) |
| `tests/` | Unit tests: `python3 -m unittest discover tests` |

## Ideas to extend it (good practice!)

- Put the price history in a CSV and plot it with matplotlib
- Add a `--percent 20` option: alert only on drops of 20% or more
- Build a tiny web page that lists the watchlist
