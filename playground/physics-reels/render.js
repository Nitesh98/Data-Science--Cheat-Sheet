/*
 * Render a reel spec to a vertical 1080x1920 video, frame by frame (deterministic, no dropped frames).
 *
 *   node render.js reels/day-001.json            -> out/day-001.mp4 (or .webm), thumbnail + upload text
 *   node render.js reels/day-001.json --stills   -> also saves a few still frames for a quick look
 *   node render.js reels/day-001.json --no-music -> silent video (music is on by default; see music.js)
 *   node render.js reels/day-001.json --covers   -> only the cover images (fast; no video)
 *
 * Needs Node + Playwright (Chromium). Uses a system ffmpeg with libx264 when present (MP4, works
 * everywhere incl. Instagram); otherwise falls back to Playwright's bundled ffmpeg (WebM VP8,
 * which YouTube accepts).
 */
const fs = require("fs"), path = require("path"), { spawn, execFileSync } = require("child_process");
const { chromium } = require("playwright");

function pickEncoder() {
  const cands = [process.env.FFMPEG, "ffmpeg"].filter(Boolean);
  for (const bin of cands) {
    try { if (execFileSync(bin, ["-hide_banner", "-encoders"], { encoding: "utf8" }).includes("libx264")) return { bin, ext: "mp4",
      input: "pipe:0", args: ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart"] }; } catch {}
  }
  const root = process.env.PLAYWRIGHT_BROWSERS_PATH || "/opt/pw-browsers";
  const dir = fs.existsSync(root) && fs.readdirSync(root).find((d) => d.startsWith("ffmpeg"));
  if (!dir) throw new Error("No ffmpeg found: install ffmpeg (with libx264) or Playwright's ffmpeg");
  return { bin: path.join(root, dir, "ffmpeg-linux"), ext: "webm", input: "pipe:0", args: ["-c:v", "libvpx", "-b:v", "6M", "-crf", "10", "-qmin", "0", "-qmax", "30", "-deadline", "good", "-cpu-used", "2", "-auto-alt-ref", "1"] };
}

(async () => {
  const specPath = process.argv[2];
  if (!specPath) { console.error("usage: node render.js reels/day-NNN.json [--stills]"); process.exit(1); }
  const spec = JSON.parse(fs.readFileSync(specPath, "utf8"));
  const name = path.basename(specPath, ".json"), outDir = path.join(__dirname, "out");
  fs.mkdirSync(outDir, { recursive: true });
  const enc = pickEncoder(), outFile = path.join(outDir, `${name}.${enc.ext}`);
  const withMusic = spec.music !== false && !process.argv.includes("--no-music");
  const videoFile = withMusic ? path.join(outDir, `${name}.video-only.${enc.ext}`) : outFile;

  const launch = { args: ["--autoplay-policy=no-user-gesture-required"] };
  if (fs.existsSync("/opt/pw-browsers/chromium")) launch.executablePath = "/opt/pw-browsers/chromium";
  const browser = await chromium.launch(launch);
  const page = await browser.newPage({ viewport: { width: 400, height: 700 } });
  await page.goto("file://" + path.join(__dirname, "engine.html"));
  await page.evaluate(() => document.fonts.ready);
  const { duration, fps } = await page.evaluate((s) => window.reel.load(s), spec);
  if (process.argv.includes("--covers")) {
    for (const [label, w, h] of [["9x16", 1080, 1920], ["16x9", 1280, 720]]) {
      const png = await page.evaluate(({ s, w, h }) => window.reel.cover(s, w, h).split(",")[1], { s: spec, w, h });
      fs.writeFileSync(path.join(outDir, `${name}-cover-${label}.png`), Buffer.from(png, "base64"));
    }
    await browser.close(); console.log("covers written"); return;
  }
  const n = Math.round(duration * fps);

  const ff = spawn(enc.bin, ["-y", "-hide_banner", "-loglevel", "error", "-f", "image2pipe", "-framerate", String(fps), "-c:v", "mjpeg", "-i", enc.input,
    "-r", String(fps), ...enc.args, videoFile], { stdio: ["pipe", "inherit", "inherit"] });
  const done = new Promise((res, rej) => ff.on("close", (c) => (c === 0 ? res() : rej(new Error("ffmpeg exited " + c)))));
  const stillsAt = process.argv.includes("--stills") ? (spec.stills || [0.6, 3, 9, 20, duration - 1]) : [];
  const t0 = Date.now();
  for (let i = 0; i < n; i++) {
    const t = i / fps;
    const b64 = await page.evaluate((t) => { window.reel.frame(t); return window.reel.canvas.toDataURL("image/jpeg", 0.93).split(",")[1]; }, t);
    const buf = Buffer.from(b64, "base64");
    if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once("drain", r));
    if (i === Math.round((spec.thumbnail_at ?? 1.0) * fps)) fs.writeFileSync(path.join(outDir, `${name}-thumbnail.jpg`), buf);
    for (const s of stillsAt) if (i === Math.round(s * fps)) fs.writeFileSync(path.join(outDir, `${name}-still-${s.toFixed(1)}s.jpg`), buf);
    if (i % (fps * 5) === 0) process.stdout.write(`  ${Math.round((100 * i) / n)}%`);
  }
  ff.stdin.end(); await done;

  if (withMusic) {
    // original ambient track: seed = spec.music.seed or the day number, so each reel differs
    const m = typeof spec.music === "object" ? spec.music : {};
    process.stdout.write("\n  composing music (records in real time)…");
    const b64 = await page.evaluate(async ({ d, seed, volume }) => window.music.encode(await window.music.render(d, seed, { volume })),
      { d: duration + 0.5, seed: m.seed ?? spec.day ?? 1, volume: m.volume ?? 1.0 });
    const audioFile = path.join(outDir, `${name}-music.webm`);
    fs.writeFileSync(audioFile, Buffer.from(b64, "base64"));
    const audioArgs = enc.ext === "mp4" ? ["-c:v", "copy", "-c:a", "aac", "-b:a", "192k"] : ["-c", "copy"];
    execFileSync(enc.bin, ["-y", "-hide_banner", "-loglevel", "error", "-i", videoFile, "-i", audioFile,
      "-map", "0:v:0", "-map", "1:a:0", ...audioArgs, "-shortest", outFile]);
    fs.unlinkSync(videoFile);
  }
  // covers: 9:16 for Reels/Shorts (inside Instagram's 3:4 grid crop) and 16:9 for YouTube
  for (const [label, w, h] of [["9x16", 1080, 1920], ["16x9", 1280, 720]]) {
    const png = await page.evaluate(({ s, w, h }) => window.reel.cover(s, w, h).split(",")[1], { s: spec, w, h });
    fs.writeFileSync(path.join(outDir, `${name}-cover-${label}.png`), Buffer.from(png, "base64"));
  }
  await browser.close();

  const up = spec.upload || {};
  fs.writeFileSync(path.join(outDir, `${name}-upload.txt`),
    `TITLE\n${up.title || spec.title}\n\nDESCRIPTION\n${up.description || ""}\n\n${(up.hashtags || []).join(" ")}\n\nPINNED COMMENT\n${up.pinned_comment || ""}\n`);
  console.log(`\nRendered ${n} frames (${duration.toFixed(1)} s) in ${((Date.now() - t0) / 1000).toFixed(0)} s -> ${outFile}`);
})().catch((e) => { console.error(e); process.exit(1); });
