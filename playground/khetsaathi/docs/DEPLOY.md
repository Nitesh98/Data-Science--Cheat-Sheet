# Deploying KhetSaathi

There are three levels, from zero effort to a real pilot.

## Level 1: static demo (no server, free)

`dist/khetsaathi-demo.html` is the whole app in one file. It runs in "demo
mode", and data stays in that browser.

- Open it straight from disk, or
- drag it onto https://app.netlify.com/drop, or
- turn on GitHub Pages for the repo and open `playground/khetsaathi/dist/khetsaathi-demo.html`.

Rebuild after changing code: `npm run build:demo`.

## Level 2: real server (shared data, many phones)

The app is plain Node 18+ with **no npm dependencies**.

**Render** (simplest): New → Blueprint → pick this repo. `render.yaml` sets the
root folder, start command, health check and a persistent disk. (A persistent
disk needs a paid instance, about $7/month. On the free tier, data resets on
every deploy.)

**Railway / Fly.io / any VPS with Docker:**
```bash
cd playground/khetsaathi
docker build -t khetsaathi .
docker run -p 8080:8080 -v khet-data:/data khetsaathi
```

**Plain VM:**
```bash
PORT=8080 DATA_FILE=/var/lib/khetsaathi/db.json node server.js
```
Put Caddy or nginx in front for HTTPS. Phones need HTTPS for the
"Use my location" button and for installing the app.

| Env var | Default | Meaning |
|---|---|---|
| `PORT` | 8080 | HTTP port |
| `DATA_FILE` | `data/db.json` | Where data is saved |
| `DEMO_MODE` | `1` | `1`: OTP shown on screen, seed data, demo user switcher. `0`: live mode |
| `ADMIN_PHONES` | `9999999999` | Comma-separated admin mobile numbers |

## Level 3: pilot with real users (checklist)

1. **SMS OTP.** In `requestOtp()` in `public/core.js`, send the code through
   MSG91 or Twilio (a DLT-registered template is required in India). Then set
   `DEMO_MODE=0`.
2. **Set `ADMIN_PHONES`** to your team's numbers.
3. **Database.** The JSON file is fine for one pilot cluster (thousands of
   bookings). Move to Postgres before you run more than one server instance.
   All reads and writes go through `store`, so only that layer changes.
4. **Provider alerts.** Send an SMS or WhatsApp message when a job appears
   nearby. Push notifications need the Android app (next section).
5. **Backups.** Copy `db.json` every hour (for example with cron and `rclone`
   to cloud storage).
6. **Legal.** Privacy policy, terms of service (cash is paid directly to the
   provider; the platform is an intermediary), and grievance officer details.
   These are needed under the IT Rules 2021.

## The Android app

The web app is already an installable PWA (`manifest.webmanifest`, icon). Two
ways to get it on the Play Store:

- **Trusted Web Activity** (fastest): `npx @bubblewrap/cli init --manifest https://your-domain/manifest.webmanifest`,
  then `bubblewrap build` produces an `.aab` to upload. Same code, no rewrite.
- **Capacitor**: wrap `public/` for native push notifications (FCM) and
  offline caching. It's worth it once providers need instant job alerts.

Play Store account: one-time $25. Build and sign on a machine with the
Android SDK. This container can't reach the Play Console.

## Checks before every deploy

```bash
npm test                      # 32 business-rule and HTTP tests
npm run build:demo            # rebuild the single-file demo
node scripts/e2e.js           # optional: real-browser journey (needs Playwright)
```
