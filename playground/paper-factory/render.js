/*
 * Render scene.html to a 1080x1920 (9:16) MP4, frame by frame (deterministic, no dropped frames).
 *
 *   node render.js            -> out/main-character-factory.mp4 (silent, story reads without sound)
 *   node render.js --sheet    -> out/sheet.jpg only: a contact sheet of key moments, for checking
 *   node render.js --at 11.2  -> out/frame-11.2s.jpg only: one full-size frame
 *
 * Needs Node + Playwright (Chromium) and an ffmpeg with libx264 (set FFMPEG=/path/to/ffmpeg if not on PATH).
 */
const fs = require("fs"), path = require("path"), { spawn } = require("child_process");
const { chromium } = require("playwright");

(async () => {
  const outDir = path.join(__dirname, "out"), arg = (f) => process.argv.includes(f);
  fs.mkdirSync(outDir, { recursive: true });
  const launch = {};
  if (fs.existsSync("/opt/pw-browsers/chromium")) launch.executablePath = "/opt/pw-browsers/chromium";
  const browser = await chromium.launch(launch);
  const page = await browser.newPage({ viewport: { width: 400, height: 700 } });
  await page.goto("file://" + path.join(__dirname, "scene.html"));
  await page.evaluate(() => document.fonts.ready);

  if (arg("--sheet")) {
    const times = [0.5, 2.8, 4.0, 6.5, 8.6, 9.9, 10.8, 11.3, 12.0, 13.0, 14.5, 16.0, 17.6, 18.2, 19.0, 19.8];
    const b64 = await page.evaluate((ts) => window.film.sheet(ts).split(",")[1], times);
    fs.writeFileSync(path.join(outDir, "sheet.jpg"), Buffer.from(b64, "base64"));
    console.log("-> out/sheet.jpg"); return browser.close();
  }
  if (arg("--at")) {
    for (const t of process.argv.slice(process.argv.indexOf("--at") + 1).map(Number).filter((x) => !isNaN(x))) {
      const b64 = await page.evaluate((t) => { window.film.frame(t); return window.film.canvas.toDataURL("image/jpeg", 0.9).split(",")[1]; }, t);
      fs.writeFileSync(path.join(outDir, `frame-${t}s.jpg`), Buffer.from(b64, "base64"));
    }
    console.log("frames written"); return browser.close();
  }

  const { duration, fps } = await page.evaluate(() => ({ duration: window.film.duration, fps: window.film.fps }));
  const outFile = path.join(outDir, "main-character-factory.mp4"), n = Math.round(duration * fps);
  const ff = spawn(process.env.FFMPEG || "ffmpeg", ["-y", "-hide_banner", "-loglevel", "error", "-f", "image2pipe", "-framerate", String(fps),
    "-c:v", "mjpeg", "-i", "pipe:0", "-r", String(fps), "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
    "-movflags", "+faststart", outFile], { stdio: ["pipe", "inherit", "inherit"] });
  const done = new Promise((res, rej) => ff.on("close", (c) => (c === 0 ? res() : rej(new Error("ffmpeg exited " + c)))));
  process.stdout.write("rendering:");
  for (let i = 0; i < n; i++) {
    const b64 = await page.evaluate((t) => { window.film.frame(t); return window.film.canvas.toDataURL("image/jpeg", 0.94).split(",")[1]; }, i / fps);
    if (!ff.stdin.write(Buffer.from(b64, "base64"))) await new Promise((r) => ff.stdin.once("drain", r));
    if (i % (fps * 2) === 0) process.stdout.write(` ${Math.round((100 * i) / n)}%`);
  }
  ff.stdin.end(); await done; await browser.close();
  console.log(` -> ${outFile}`);
})().catch((e) => { console.error(e); process.exit(1); });
