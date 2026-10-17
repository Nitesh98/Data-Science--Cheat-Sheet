# Physics Reels: a daily Short for @Insightloopin

Makes a **ready-to-upload, 9:16 physics Short every day**: animated physics visuals, big readable
captions (most viewers watch muted), your handle, a progress bar, an **original calm background
track**, and the title, description, hashtags and pinned comment to paste into YouTube.

## Background music

`music.js` composes an original ambient track for each reel in the browser's audio engine: soft pads,
a slow plucked arpeggio, deep bass, reverb, and a fade in and out. Nothing is sampled, so it is yours
and safe from Content ID claims. The day number picks the key, tempo (66–75 BPM) and chord
progression, so every reel sounds related but different. Set `"music": {"seed": 7, "volume": 0.9}` in
a script to choose a variation, `"music": false` (or `--no-music`) for silence.

A famous viral song can't be baked into the file: it would be claimed or muted. If you want one, add
it from YouTube's own sound library when you upload; it's licensed there. Keep the original track
quiet under it, or render with `--no-music`.

## How it's made (a small agent team)

| Step | Who | What |
|---|---|---|
| Plan | **Research subagent** | Studied what makes physics Shorts work and wrote the 30-day topic calendar (`calendar.json`) plus accuracy rules (misconceptions creators get called out for). |
| Write | **Writer** (the daily session) | Turns the day's topic into a scene-by-scene script, `reels/day-NNN.json`: hook in the first 2 s, one idea, about 35–45 s, an ending that loops back to the hook. |
| Check | **Fact-checker subagent** | Independently verifies every claim and number with sources, checks reading speed per scene and the hook. The reel is only rendered after it approves. |
| Render | `render.js` + `engine.html` | Draws every frame in headless Chromium (deterministic, no dropped frames) and encodes the video. |
| Post | **You** | Watch it, add music, upload. Nothing is posted automatically. |

## Make a reel yourself

```bash
cd playground/physics-reels
npm i -D playwright && npx playwright install chromium     # once
node render.js reels/day-001.json --stills                 # -> out/day-001.mp4 + thumbnail + upload text
```

With a normal `ffmpeg` (with libx264) installed you get an **MP4** (works on YouTube *and* Instagram).
Without one it falls back to Playwright's bundled ffmpeg and writes **WebM**, which YouTube accepts.
Preview a script live in a browser: open `engine.html?spec=reels/day-001.json` from a local web server.

## The visual library (`engine.html`)

`fall` (hammer/feather/ball, with or without air, stopwatch) · `projectile` (dropped vs fired) ·
`pendulum` · `wave` (travel, interference, Doppler, tunnelling) · `orbit` (star, Earth, black hole;
speed and gravity arrows) · `cannon` (Newton's cannonball) · `particles` (gas, hot vs cold, water to
ice lattice) · `rays` (refraction, prism, blue-sky scattering) · `spring` · `bars` (comparisons, log
scale) · `formula` (big equation reveal). New topics can add a visual here.

## Script format (`reels/day-NNN.json`)

Each scene has `dur` (seconds), `text` (the caption; words appear one by one), `highlight` (words
shown in amber), optional `big`, and a `visual` with a `type` from the library plus its settings.
`upload` holds the title, description, hashtags and pinned comment; `sources` holds the references
the fact-checker used.

## Every day

A scheduled cloud routine runs each morning (08:47 IST). It takes the next topic from the calendar,
writes the script, has the fact-checker subagent approve it, renders the video, and pushes it to the
`daily-reels` branch of this repo. Each day's folder holds `day-NNN.webm`, its thumbnail and
`upload.txt`. Download it from GitHub on your phone, add music in the YouTube app, and post.
Suggested posting slot: 7–8 PM IST; check your Studio retention data and adjust.

## Notes

- The channel itself couldn't be checked from here: the sandbox blocks youtube.com. Tell me your
  channel's style, language or audience and the scripts will match it.
- Facts follow the accuracy rules in `calendar.json`. If a commenter catches a mistake, add a rule
  so it never happens again.
