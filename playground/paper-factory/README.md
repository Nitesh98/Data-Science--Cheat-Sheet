# The Main Character Factory

A 20-second silent paper-cut animation, drawn entirely in code (HTML canvas, no images or assets).

Story: tiny workers roll glowing "main character energy" along a belt. A press stamps ordinary people with it, and a crane
lifts each finished main character onto a pedestal. A worker knocks over a jar of "plot armor", it explodes into the sky,
and everything goes cinematic: letterbox bars, spotlights, capes, a sword, slow-motion walks away from explosions.
The workers shrug and get back to work.

- `scene.html`: the whole film. `window.film.frame(t)` draws second `t` (deterministic). Open `scene.html?play` to watch it live.
- `render.js`: renders it to `out/main-character-factory.mp4` (1080x1920, 9:16, 30 fps, H.264).

```
node render.js            # the MP4 (needs Playwright + an ffmpeg with libx264; set FFMPEG=/path/to/ffmpeg)
node render.js --sheet    # out/sheet.jpg: contact sheet of key moments, for checking
node render.js --at 11.2  # out/frame-11.2s.jpg: one full-size frame
```
