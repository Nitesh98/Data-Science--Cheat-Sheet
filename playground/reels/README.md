# Reels: motion-design videos for Instagram

Short vertical videos (1080×1920, 30 fps, H.264 + sound effects) about maths, science, tech,
analytics and product management. Each reel is a web page that draws every frame as a function of
time; a headless browser captures the frames and ffmpeg turns them into an MP4.

```bash
pip install imageio-ffmpeg                       # an ffmpeg that can write H.264
python3 build.py 01-simpsons-paradox --check     # quick contact sheet of key moments (seconds)
python3 build.py 01-simpsons-paradox             # full video + cover (takes several minutes)
```

Output lands in `<reel>/out/` (the MP4 is git-ignored). Needs node + Playwright + Chromium.

| Reel | Topic |
|---|---|
| `01-simpsons-paradox` | Data analytics: a trend that reverses when you split the groups |

Each reel folder holds `reel.html` + `reel.js` (the animation), `cover.html` (thumbnail) and
`caption.md` (caption, hashtags, alt text). `engine/` has the shared motion toolkit: easings and
springs, screen shake, glitch, aurora background with film grain, and a synthesized sound-effects
track. The data in the reels is synthetic and every number on screen is computed from it. Fonts are
Space Grotesk, Inter and JetBrains Mono (SIL Open Font License).
