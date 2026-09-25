#!/usr/bin/env python3
"""Price-drop alert: watch product pages and get notified when a price falls.

Standard library only. Typical use:

    python3 price_tracker.py add "https://example.com/product" --target 1999
    python3 price_tracker.py check            # check every item once
    python3 price_tracker.py watch --every 60 # keep checking every 60 minutes
    python3 price_tracker.py demo             # offline end-to-end demo

Notifications always print to the console. Phone / desktop / email alerts are
switched on by setting environment variables (or a `config.env` file next to
this script) - see README.md.
"""

import argparse
import gzip
import html
import json
import os
import re
import shutil
import smtplib
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
import zlib
from datetime import datetime, timezone
from email.message import EmailMessage
from http.server import BaseHTTPRequestHandler, HTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_WATCHLIST = os.path.join(HERE, "watchlist.json")
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)


# --------------------------------------------------------------------------
# Price extraction
# --------------------------------------------------------------------------

def parse_price(text):
    """Turn '₹1,299.00', 'Rs. 1299', '$19.99' or 1299 into a float (or None)."""
    if text is None:
        return None
    if isinstance(text, (int, float)):
        return float(text) if text > 0 else None
    match = re.search(r"\d[\d,]*(?:\.\d+)?", html.unescape(str(text)))
    if not match:
        return None
    value = float(match.group(0).replace(",", ""))
    return value if value > 0 else None


def _prices_in_jsonld(node):
    """Yield offer prices found anywhere inside a schema.org JSON-LD object."""
    if isinstance(node, list):
        for item in node:
            yield from _prices_in_jsonld(item)
    elif isinstance(node, dict):
        offers = node.get("offers")
        if offers is not None:
            for offer in offers if isinstance(offers, list) else [offers]:
                if isinstance(offer, dict):
                    for key in ("price", "lowPrice"):
                        price = parse_price(offer.get(key))
                        if price:
                            yield price
        for value in node.values():
            if isinstance(value, (dict, list)):
                yield from _prices_in_jsonld(value)


META_PATTERNS = [
    r'<meta[^>]+(?:property|name)=["\'](?:product:price:amount|og:price:amount|twitter:data1)["\'][^>]*content=["\']([^"\']+)',
    r'<meta[^>]+content=["\']([^"\']+)["\'][^>]*(?:property|name)=["\'](?:product:price:amount|og:price:amount)["\']',
    r'itemprop=["\']price["\'][^>]*content=["\']([^"\']+)',
    r'content=["\']([^"\']+)["\'][^>]*itemprop=["\']price["\']',
]

# Best-effort, site-specific fallbacks. Shops change their markup often, so if
# one of these stops working, pass your own --pattern when adding the item.
SITE_PATTERNS = [
    r'<span class="a-price-whole">([\d,]+)',              # Amazon
    r'"discounted"\s*:\s*(\d+(?:\.\d+)?)',                 # Myntra (inline page data)
    r'"finalPrice"\s*:\s*\{[^}]*"value"\s*:\s*(\d+)',      # Flipkart (inline page data)
    r'"sellingPrice"\s*:\s*(\d+(?:\.\d+)?)',               # several Indian shops
]


def extract_price(page, pattern=None):
    """Return (price, method) from a page's HTML, or (None, None)."""
    if pattern:
        match = re.search(pattern, page, re.S)
        if match:
            price = parse_price(match.group(1) if match.groups() else match.group(0))
            if price:
                return price, "custom pattern"
        return None, None

    for block in re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', page, re.S | re.I
    ):
        try:
            data = json.loads(block.strip())
        except ValueError:
            continue
        prices = list(_prices_in_jsonld(data))
        if prices:
            return min(prices), "json-ld"

    for regex in META_PATTERNS:
        match = re.search(regex, page, re.I)
        if match and parse_price(match.group(1)):
            return parse_price(match.group(1)), "meta tag"

    for regex in SITE_PATTERNS:
        match = re.search(regex, page)
        if match and parse_price(match.group(1)):
            return parse_price(match.group(1)), "site pattern"

    return None, None


def extract_title(page):
    match = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]*content=["\']([^"\']+)', page, re.I) \
        or re.search(r"<title[^>]*>(.*?)</title>", page, re.S | re.I)
    return html.unescape(match.group(1)).strip()[:80] if match else None


def fetch(url, timeout=20):
    request = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        "Accept-Language": "en-IN,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
    })
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read()
        encoding = response.headers.get("Content-Encoding", "")
        charset = response.headers.get_content_charset() or "utf-8"
    if encoding == "gzip":
        body = gzip.decompress(body)
    elif encoding == "deflate":
        body = zlib.decompress(body)
    return body.decode(charset, errors="replace")


# --------------------------------------------------------------------------
# Watchlist storage
# --------------------------------------------------------------------------

def load_watchlist(path):
    if not os.path.exists(path):
        return {"items": []}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_watchlist(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def money(value):
    return f"₹{value:,.2f}".replace(".00", "")


# --------------------------------------------------------------------------
# Notifications
# --------------------------------------------------------------------------

def load_config_env():
    """Read KEY=VALUE lines from config.env (if present) into os.environ."""
    path = os.path.join(HERE, "config.env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _post(url, data, headers=None):
    request = urllib.request.Request(url, data=data, headers=headers or {}, method="POST")
    with urllib.request.urlopen(request, timeout=15) as response:
        return response.status


def notify_ntfy(title, message, url):
    topic = os.environ.get("NTFY_TOPIC")
    if not topic:
        return None
    server = os.environ.get("NTFY_SERVER", "https://ntfy.sh").rstrip("/")
    payload = {"topic": topic, "title": title, "message": message, "tags": ["moneybag"], "priority": 4}
    if url:
        payload["click"] = url
    _post(server, json.dumps(payload).encode("utf-8"), {"Content-Type": "application/json"})
    return "ntfy"


def notify_telegram(title, message, url):
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not (token and chat):
        return None
    text = f"{title}\n{message}" + (f"\n{url}" if url else "")
    data = urllib.parse.urlencode({"chat_id": chat, "text": text}).encode()
    _post(f"https://api.telegram.org/bot{token}/sendMessage", data)
    return "telegram"


def notify_email(title, message, url):
    host, to = os.environ.get("SMTP_HOST"), os.environ.get("ALERT_EMAIL_TO")
    if not (host and to):
        return None
    user = os.environ.get("SMTP_USER", "")
    msg = EmailMessage()
    msg["Subject"] = title
    msg["From"] = os.environ.get("ALERT_EMAIL_FROM", user or to)
    msg["To"] = to
    msg.set_content(message + (f"\n\n{url}" if url else ""))
    with smtplib.SMTP(host, int(os.environ.get("SMTP_PORT", "587")), timeout=20) as server:
        server.starttls()
        if user:
            server.login(user, os.environ.get("SMTP_PASSWORD", ""))
        server.send_message(msg)
    return "email"


def notify_desktop(title, message, url):
    if os.environ.get("DESKTOP_NOTIFY", "1") == "0":
        return None
    if sys.platform == "darwin" and shutil.which("osascript"):
        script = f'display notification {json.dumps(message)} with title {json.dumps(title)} sound name "Glass"'
        subprocess.run(["osascript", "-e", script], check=False)
        return "desktop"
    if sys.platform.startswith("linux") and shutil.which("notify-send") and os.environ.get("DISPLAY"):
        subprocess.run(["notify-send", "-u", "critical", title, message], check=False)
        return "desktop"
    if sys.platform == "win32":
        ps = (
            "[reflection.assembly]::loadwithpartialname('System.Windows.Forms') | Out-Null;"
            "$n = New-Object System.Windows.Forms.NotifyIcon;"
            "$n.Icon = [System.Drawing.SystemIcons]::Information; $n.Visible = $true;"
            f"$n.ShowBalloonTip(10000, {json.dumps(title)}, {json.dumps(message)}, 'Info'); Start-Sleep 11"
        )
        subprocess.Popen(["powershell", "-NoProfile", "-Command", ps])
        return "desktop"
    return None


NOTIFIERS = [notify_desktop, notify_ntfy, notify_telegram, notify_email]


def notify(title, message, url=None):
    print(f"\n🔔 {title}\n   {message}" + (f"\n   {url}" if url else ""))
    sent = []
    for notifier in NOTIFIERS:
        try:
            channel = notifier(title, message, url)
            if channel:
                sent.append(channel)
        except Exception as exc:  # one broken channel must not stop the others
            print(f"   ⚠️  {notifier.__name__} failed: {exc}")
    if sent:
        print(f"   sent via: {', '.join(sent)}")
    return sent


# --------------------------------------------------------------------------
# Core check logic
# --------------------------------------------------------------------------

def decide_alert(item, price):
    """Return an alert reason string, or None if this price isn't worth a ping."""
    last = item.get("last_price")
    target = item.get("target_price")
    if target is not None:
        # Only ping when crossing to/below target, or dropping further below it.
        if price <= target and (last is None or last > target or price < last):
            return f"at/below your target of {money(target)}"
        return None
    if last is not None and price < last:
        return "price dropped"
    return None


def check_item(item, fetcher=fetch):
    """Fetch one item, update it in place and return an alert dict (or None)."""
    page = fetcher(item["url"])
    price, method = extract_price(page, item.get("pattern"))
    item["last_checked"] = now_iso()
    if price is None:
        item["last_error"] = "price not found on page"
        print(f"  ✗ {item['name']}: couldn't find a price (the site may block bots or load prices "
              f"with JavaScript - try --pattern, see README)")
        return None
    item.pop("last_error", None)

    last = item.get("last_price")
    reason = decide_alert(item, price)
    change = "" if last is None else f" (was {money(last)})"
    print(f"  ✓ {item['name']}: {money(price)}{change} via {method}")

    history = item.setdefault("history", [])
    if not history or history[-1]["price"] != price:
        history.append({"at": item["last_checked"], "price": price})
    item["lowest_price"] = min(price, item.get("lowest_price") or price)
    item["last_price"] = price

    if not reason:
        return None
    alert = {"item": item, "price": price, "previous": last, "reason": reason}
    title = f"Price drop: {item['name'][:60]}"
    msg = f"Now {money(price)}" + (f" (was {money(last)}, -{money(last - price)})" if last and price < last else "")
    msg += f" — {reason}."
    alert["sent_via"] = notify(title, msg, item["url"])
    return alert


def check_all(path, fetcher=fetch):
    data = load_watchlist(path)
    if not data["items"]:
        print("Watchlist is empty. Add something with:  python3 price_tracker.py add <url>")
        return []
    print(f"[{datetime.now():%Y-%m-%d %H:%M}] Checking {len(data['items'])} item(s)...")
    alerts = []
    for item in data["items"]:
        try:
            alert = check_item(item, fetcher)
            if alert:
                alerts.append(alert)
        except Exception as exc:
            item["last_error"] = str(exc)
            item["last_checked"] = now_iso()
            print(f"  ✗ {item['name']}: {exc}")
    save_watchlist(path, data)
    return alerts


# --------------------------------------------------------------------------
# CLI commands
# --------------------------------------------------------------------------

def cmd_add(args):
    data = load_watchlist(args.watchlist)
    if any(i["url"] == args.url for i in data["items"]):
        sys.exit("That URL is already on your watchlist.")
    name = args.name
    price = None
    try:
        page = fetch(args.url)
        price, method = extract_price(page, args.pattern)
        name = name or extract_title(page)
    except Exception as exc:
        print(f"Warning: couldn't fetch the page right now ({exc}). Saving it anyway.")
    item = {
        "id": max((i["id"] for i in data["items"]), default=0) + 1,
        "name": name or args.url,
        "url": args.url,
        "target_price": args.target,
        "pattern": args.pattern,
        "added": now_iso(),
        "last_price": price,
        "lowest_price": price,
        "history": [{"at": now_iso(), "price": price}] if price else [],
    }
    data["items"].append(item)
    save_watchlist(args.watchlist, data)
    print(f"Added #{item['id']}: {item['name']}")
    if price:
        print(f"Current price: {money(price)} (found via {method})")
        if args.target and price <= args.target:
            notify(f"Already at target: {item['name'][:60]}",
                   f"Now {money(price)} — at/below your target of {money(args.target)}.", args.url)
    else:
        print("Couldn't read a price yet. If this keeps happening, see 'Sites that block trackers' in README.md.")


def cmd_list(args):
    data = load_watchlist(args.watchlist)
    if not data["items"]:
        print("Watchlist is empty.")
        return
    for i in data["items"]:
        now = money(i["last_price"]) if i.get("last_price") else "—"
        low = money(i["lowest_price"]) if i.get("lowest_price") else "—"
        target = money(i["target_price"]) if i.get("target_price") else "any drop"
        print(f"#{i['id']:<3} {i['name'][:50]:<50}  now {now:>10}  lowest {low:>10}  alert: {target}")
        if i.get("last_error"):
            print(f"      ⚠️  last check: {i['last_error']}")


def cmd_remove(args):
    data = load_watchlist(args.watchlist)
    before = len(data["items"])
    data["items"] = [i for i in data["items"] if i["id"] != args.id]
    if len(data["items"]) == before:
        sys.exit(f"No item with id {args.id}.")
    save_watchlist(args.watchlist, data)
    print(f"Removed #{args.id}.")


def cmd_history(args):
    item = next((i for i in load_watchlist(args.watchlist)["items"] if i["id"] == args.id), None)
    if not item:
        sys.exit(f"No item with id {args.id}.")
    print(item["name"])
    prices = [h["price"] for h in item["history"]] or [0]
    top = max(prices)
    for h in item["history"]:
        bar = "█" * max(1, round(30 * h["price"] / top))
        print(f"  {h['at'][:16].replace('T', ' ')}  {money(h['price']):>10}  {bar}")


def cmd_check(args):
    check_all(args.watchlist)


def cmd_watch(args):
    print(f"Watching every {args.every} minute(s). Press Ctrl+C to stop.")
    try:
        while True:
            check_all(args.watchlist)
            time.sleep(args.every * 60)
    except KeyboardInterrupt:
        print("\nStopped.")


def cmd_test_notify(args):
    sent = notify("Price alert test", "If you can read this, notifications are working. 🎉",
                  "https://ntfy.sh")
    if not sent:
        print("\nOnly the console is set up. See README.md to enable phone/desktop/email alerts.")


def cmd_demo(args):
    """Serve a fake shop on localhost whose price falls, and track it."""
    prices = iter([2499, 2499, 1999, 1799, 1499])
    state = {"price": 2499}

    class Shop(BaseHTTPRequestHandler):
        def do_GET(self):
            state["price"] = next(prices, state["price"])
            body = (
                "<html><head><title>Demo Sneakers</title>"
                '<script type="application/ld+json">'
                + json.dumps({"@type": "Product", "name": "Demo Sneakers",
                              "offers": {"@type": "Offer", "price": str(state["price"]), "priceCurrency": "INR"}})
                + "</script></head><body>Demo shop</body></html>"
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    server = HTTPServer(("127.0.0.1", 0), Shop)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_port}/sneakers"
    path = os.path.join(HERE, "demo_watchlist.json")
    if os.path.exists(path):
        os.remove(path)
    ns = argparse.Namespace(watchlist=path, url=url, name=None, target=1600, pattern=None)
    print("== Adding a product from a fake local shop (alert when ≤ ₹1,600 or it's on target) ==")
    cmd_add(ns)
    for round_no in range(1, 5):
        print(f"\n== Check #{round_no} ==")
        check_all(path)
        time.sleep(0.3)
    print("\n== Price history ==")
    cmd_history(argparse.Namespace(watchlist=path, id=1))
    server.shutdown()
    os.remove(path)


def build_parser():
    p = argparse.ArgumentParser(description="Get alerted when e-commerce prices drop.")
    p.add_argument("--watchlist", default=DEFAULT_WATCHLIST, help="path to the watchlist JSON file")
    sub = p.add_subparsers(dest="command", required=True)

    a = sub.add_parser("add", help="start tracking a product URL")
    a.add_argument("url")
    a.add_argument("--name", help="friendly name (default: page title)")
    a.add_argument("--target", type=float, help="only alert at or below this price")
    a.add_argument("--pattern", help="custom regex whose first group is the price")
    a.set_defaults(func=cmd_add)

    sub.add_parser("list", help="show tracked products").set_defaults(func=cmd_list)

    r = sub.add_parser("remove", help="stop tracking a product")
    r.add_argument("id", type=int)
    r.set_defaults(func=cmd_remove)

    h = sub.add_parser("history", help="show price history for a product")
    h.add_argument("id", type=int)
    h.set_defaults(func=cmd_history)

    sub.add_parser("check", help="check all prices once (good for cron / schedulers)").set_defaults(func=cmd_check)

    w = sub.add_parser("watch", help="keep checking on a timer")
    w.add_argument("--every", type=float, default=60, help="minutes between checks (default 60)")
    w.set_defaults(func=cmd_watch)

    sub.add_parser("test-notify", help="send a test notification").set_defaults(func=cmd_test_notify)
    sub.add_parser("demo", help="offline demo with a fake shop whose price drops").set_defaults(func=cmd_demo)
    return p


def main(argv=None):
    load_config_env()
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
