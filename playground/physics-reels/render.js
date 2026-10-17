/*
 * Render a reel spec to a vertical 1080x1920 video, frame by frame (deterministic, no dropped frames).
 *
 *   node render.js reels/day-001.json            -> one version per platform, each with its own handle:
 *        out/day-001-youtube.mp4    + day-001-youtube-cover-9x16.png + -cover-16x9.png + day-001-youtube-upload.txt
 *        out/day-001-instagram.mp4  + day-001-instagram-cover-9x16.png               + day-001-instagram-caption.txt
 *   node render.js reels/day-001.json --only instagram   -> just one platform
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

// The channel's handles. YouTube: @Insightloopin. Instagram: @insightloop_in. (A script may override with "handles".)
const PLATFORMS = {
  youtube: { handle: "@Insightloopin", covers: [["9x16", 1080, 1920], ["16x9", 1280, 720]] },
  instagram: { handle: "@insightloop_in", covers: [["9x16", 1080, 1920]] },
};

(async () => {
  const specPath = process.argv[2];
  if (!specPath) { console.error("usage: node render.js reels/day-NNN.json [--stills] [--covers] [--no-music] [--only youtube|instagram]"); process.exit(1); }
  const base = JSON.parse(fs.readFileSync(specPath, "utf8"));
  const name = path.basename(specPath, ".json"), outDir = path.join(__dirname, "out");
  fs.mkdirSync(outDir, { recursive: true });
  const only = process.argv.includes("--only") ? process.argv[process.argv.indexOf("--only") + 1] : null;
  const platforms = Object.keys(PLATFORMS).filter((p) => !only || p === only);
  const handles = { ...Object.fromEntries(Object.entries(PLATFORMS).map(([k, v]) => [k, v.handle])), ...(base.handles || {}) };
  const enc = pickEncoder();
  const withMusic = base.music !== false && !process.argv.includes("--no-music");
  const coversOnly = process.argv.includes("--covers");

  const launch = { args: ["--autoplay-policy=no-user-gesture-required"] };
  if (fs.existsSync("/opt/pw-browsers/chromium")) launch.executablePath = "/opt/pw-browsers/chromium";
  const browser = await chromium.launch(launch);
  const page = await browser.newPage({ viewport: { width: 400, height: 700 } });
  await page.goto("file://" + path.join(__dirname, "engine.html"));
  await page.evaluate(() => document.fonts.ready);
  const t0 = Date.now();

  // music is the same for every platform: compose it once
  let audioFile = null;
  if (withMusic && !coversOnly) {
    const { duration } = await page.evaluate((s) => window.reel.load(s), base);
    const m = typeof base.music === "object" ? base.music : {};
    process.stdout.write("  composing music (records in real time)…\n");
    const b64 = await page.evaluate(async ({ d, seed, volume }) => window.music.encode(await window.music.render(d, seed, { volume })),
      { d: duration + 0.5, seed: m.seed ?? base.day ?? 1, volume: m.volume ?? 1.0 });
    audioFile = path.join(outDir, `${name}-music.webm`);
    fs.writeFileSync(audioFile, Buffer.from(b64, "base64"));
  }

  for (const plat of platforms) {
    const spec = { ...base, handle: handles[plat] }, tag = `${name}-${plat}`;
    const { duration, fps } = await page.evaluate((s) => window.reel.load(s), spec);
    for (const [label, w, h] of PLATFORMS[plat].covers) {
      const png = await page.evaluate(({ s, w, h }) => window.reel.cover(s, w, h).split(",")[1], { s: spec, w, h });
      fs.writeFileSync(path.join(outDir, `${tag}-cover-${label}.png`), Buffer.from(png, "base64"));
    }
    writeTexts(spec, plat, path.join(outDir, tag));
    if (coversOnly) continue;

    const outFile = path.join(outDir, `${tag}.${enc.ext}`), videoFile = audioFile ? path.join(outDir, `${tag}.video-only.${enc.ext}`) : outFile;
    const n = Math.round(duration * fps);
    process.stdout.write(`  ${plat} (${spec.handle}):`);
    const ff = spawn(enc.bin, ["-y", "-hide_banner", "-loglevel", "error", "-f", "image2pipe", "-framerate", String(fps), "-c:v", "mjpeg", "-i", enc.input,
      "-r", String(fps), ...enc.args, videoFile], { stdio: ["pipe", "inherit", "inherit"] });
    const done = new Promise((res, rej) => ff.on("close", (c) => (c === 0 ? res() : rej(new Error("ffmpeg exited " + c)))));
    const stillsAt = process.argv.includes("--stills") && plat === platforms[0] ? (spec.stills || [0.6, 3, 9, 20, duration - 1]) : [];
    for (let i = 0; i < n; i++) {
      const t = i / fps;
      const b64 = await page.evaluate((t) => { window.reel.frame(t); return window.reel.canvas.toDataURL("image/jpeg", 0.93).split(",")[1]; }, t);
      const buf = Buffer.from(b64, "base64");
      if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once("drain", r));
      for (const s of stillsAt) if (i === Math.round(s * fps)) fs.writeFileSync(path.join(outDir, `${name}-still-${s.toFixed(1)}s.jpg`), buf);
      if (i % (fps * 5) === 0) process.stdout.write(` ${Math.round((100 * i) / n)}%`);
    }
    ff.stdin.end(); await done;
    if (audioFile) {
      const audioArgs = enc.ext === "mp4" ? ["-c:v", "copy", "-c:a", "aac", "-b:a", "192k"] : ["-c", "copy"];
      execFileSync(enc.bin, ["-y", "-hide_banner", "-loglevel", "error", "-i", videoFile, "-i", audioFile,
        "-map", "0:v:0", "-map", "1:a:0", ...audioArgs, "-shortest", outFile]);
      fs.unlinkSync(videoFile);
    }
    console.log(` -> ${outFile}`);
  }
  await browser.close();
  console.log(coversOnly ? "covers written" : `Done in ${((Date.now() - t0) / 1000).toFixed(0)} s`);
})().catch((e) => { console.error(e); process.exit(1); });

// Paste-ready text per platform: YouTube gets title/description/pinned comment; Instagram gets one caption.
function writeTexts(spec, plat, stem) {
  const up = spec.upload || {}, tags = (up.hashtags || []).join(" ");
  if (plat === "youtube") {
    fs.writeFileSync(`${stem}-upload.txt`,
      `TITLE\n${up.title || spec.title}\n\nDESCRIPTION\n${up.description || ""}\n\nFollow ${spec.handle} for a new physics fact every day.\n\n${tags}\n\nPINNED COMMENT\n${up.pinned_comment || ""}\n`);
  } else {
    const hook = spec.scenes?.[0]?.text || spec.title;
    const igTags = (up.hashtags || []).filter((h) => h.toLowerCase() !== "#shorts").concat(["#reels", "#physicsreels"]).slice(0, 6).join(" ");
    fs.writeFileSync(`${stem}-caption.txt`,
      `${hook}\n\n${up.description || ""}\n\n${up.pinned_comment || ""}\n\nFollow ${spec.handle} for a new physics fact every day.\n\n${igTags}\n`);
  }
}
