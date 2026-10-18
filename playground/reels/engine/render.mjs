// Frame renderer: opens a reel page in headless Chromium, calls window.seek(t) and screenshots.
//
//   node render.mjs frames <reel.html> <outDir> [fps=30] [workers=4]   -> outDir/f00000.png ... + meta.json
//   node render.mjs stills <reel.html> <outDir> <t1,t2,...>            -> outDir/still_<t>.png  (for checking)
//   node render.mjs shot   <page.html> <out.png>                       -> one PNG of a static page (cover)
import { createRequire } from "node:module";
import { mkdirSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_PATH || "/opt/node22/lib/node_modules/playwright");

const [mode, page_, out, ...rest] = process.argv.slice(2);
const url = "file://" + resolve(page_);
const browser = await chromium.launch({
  executablePath: process.env.CHROMIUM_PATH || "/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
  args: ["--font-render-hinting=none", "--disable-lcd-text"],
});

async function open() {
  const ctx = await browser.newContext({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  page.on("pageerror", e => { console.error("PAGE ERROR:", e.message); process.exitCode = 1; });
  await page.goto(url);
  await page.waitForFunction(() => window.READY === true, null, { timeout: 30000 });
  return page;
}

if (mode === "shot") {
  const page = await open();
  await page.screenshot({ path: out, type: "png" });
} else if (mode === "stills") {
  mkdirSync(out, { recursive: true });
  const page = await open();
  for (const t of rest[0].split(",").map(Number)) {
    await page.evaluate(t => window.seek(t), t);
    await page.screenshot({ path: `${out}/still_${String(Math.round(t * 1000)).padStart(6, "0")}.png`, type: "png" });
  }
} else if (mode === "frames") {
  mkdirSync(out, { recursive: true });
  const fps = Number(rest[0] || 30), workers = Number(rest[1] || 4);
  const first = await open();
  const duration = await first.evaluate(() => window.DURATION);
  const cues = await first.evaluate(() => window.CUES);
  const total = Math.round(duration * fps);
  writeFileSync(`${out}/meta.json`, JSON.stringify({ duration, fps, total, cues }));
  const pages = [first];
  for (let i = 1; i < workers; i++) pages.push(await open());
  let done = 0;
  await Promise.all(pages.map(async (page, w) => {
    for (let f = w; f < total; f += workers) {
      await page.evaluate(t => window.seek(t), f / fps);
      await page.screenshot({ path: `${out}/f${String(f).padStart(5, "0")}.png`, type: "png" });
      if (++done % 60 === 0) process.stdout.write(`\r  rendered ${done}/${total} frames`);
    }
  }));
  console.log(`\r  rendered ${total}/${total} frames (${duration}s @ ${fps}fps)`);
}
await browser.close();
