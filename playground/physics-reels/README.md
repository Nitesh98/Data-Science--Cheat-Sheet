# Physics Reels: a daily Short and Reel for Insightloop

Makes a **ready-to-upload, 9:16 physics Short every day**: animated physics visuals, big readable
captions (most viewers watch muted), your handle, a progress bar, an **original calm background
track**, and the title, description, hashtags and pinned comment to paste into YouTube.

## Cover images

Every render also writes two covers built from the script's `cover` block (big headline, one word in
amber, a question, a tag pill, the topic's visual and a giant "?"):

- `day-NNN-cover-9x16.png` (1080×1920): the Instagram Reel cover and the YouTube Shorts thumbnail.
  Everything important sits inside the centre 3:4 area, so Instagram's profile grid doesn't crop it.
- `day-NNN-cover-16x9.png` (1280×720): a YouTube thumbnail.

```json
"cover": { "headline": ["HAMMER", "vs FEATHER"], "highlight": "FEATHER", "question": "Which lands first?",
           "tag": "ON THE MOON", "visual": { "type": "fall", "air": false, "delay": 99, "scale": 1.5, "noLabel": true } }
```

`node render.js reels/day-NNN.json --covers` makes only the covers, in a few seconds.

## Background music

`music.js` composes an original ambient track for each reel in the browser's audio engine: soft pads,
a slow plucked arpeggio, deep bass, reverb, and a fade in and out. Nothing is sampled, so it is yours
and safe from Content ID claims. The day number picks the key, tempo (66–75 BPM) and chord
progression, so every reel sounds related but different. Set `"music": {"seed": 7, "volume": 0.9}` in
a script to choose a variation, `"music": false` (or `--no-music`) for silence.

A famous viral song can't be baked into the file: it would be claimed or muted. If you want one, add
it from YouTube's own sound library when you upload; it's licensed there. Keep the original track
quiet under it, or render with `--no-music`.

## Handles (remembered)

| Platform | Handle | What you get |
|---|---|---|
| YouTube | **@Insightloopin** | `day-NNN-youtube.mp4`, `-youtube-cover-9x16.png`, `-youtube-cover-16x9.png`, `-youtube-upload.txt` (title, description, hashtags, pinned comment) |
| Instagram | **@insightloop_in** | `day-NNN-instagram.mp4`, `-instagram-cover-9x16.png`, `-instagram-caption.txt` (one caption, ready to paste) |

Each platform's video and cover show only its own handle. Mentioning another platform on screen can hurt
how much Instagram shows a reel. The handles live in `render.js` (`PLATFORMS`), and a script can override
them with `"handles"`. `--only youtube` or `--only instagram` renders just one.

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

With a normal `ffmpeg` (with libx264) installed you get an **MP4** with H.264 and AAC, which works on
YouTube, Instagram and iPhone. Without one it falls back to Playwright's bundled ffmpeg and writes
**WebM**, which YouTube accepts. No ffmpeg and no admin rights? npm ships one:

```bash
npm install @ffmpeg-installer/linux-x64          # or the -darwin-arm64 / -win32-x64 package
export FFMPEG=$PWD/node_modules/@ffmpeg-installer/linux-x64/ffmpeg
```
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
routine's own branch of this repo: `day-NNN.mp4` (with music), its thumbnail and `upload.txt`.
You get a phone notification and an email with the link. Download it from GitHub on your phone, add music in the YouTube app, and post.
Suggested posting slot: 7–8 PM IST; check your Studio retention data and adjust.

## Notes

- The channel itself couldn't be checked from here: the sandbox blocks youtube.com. Tell me your
  channel's style, language or audience and the scripts will match it.
- Facts follow the accuracy rules in `calendar.json`. If a commenter catches a mistake, add a rule
  so it never happens again.
