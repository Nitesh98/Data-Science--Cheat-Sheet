// Browser end-to-end check (optional; needs Playwright: `npm i -g playwright`).
// Drives the full journey on a phone-sized screen against both the static demo
// build and the real server, and saves screenshots to dist/shots/.
//   node scripts/build-demo.js && node scripts/e2e.js
'use strict';
const path = require('path');
const fs = require('fs');
let chromium;
try { ({ chromium } = require('playwright')); } catch (e) {
  ({ chromium } = require(path.join(require('child_process').execSync('npm root -g').toString().trim(), 'playwright')));
}
const { createServer } = require('../server.js');

const root = path.join(__dirname, '..');
const shots = path.join(root, 'dist', 'shots');
fs.mkdirSync(shots, { recursive: true });
const assert = (c, m) => { if (!c) throw new Error('E2E: ' + m); };

async function journey(page, label) {
  const shot = (n) => page.screenshot({ path: path.join(shots, `${label}-${n}.png`), fullPage: true });
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));

  // 1. Log in with OTP (demo shows the OTP on screen).
  await page.waitForSelector('#phone');
  await shot('01-login');
  await page.fill('#phone', '98765 43210');
  await page.click('button[type=submit]');
  const otp = (await page.textContent('.note.info b')).trim();
  await page.fill('#otp', otp);
  await page.click('button[type=submit]');
  await page.waitForSelector('.services');
  await shot('02-home');

  // 2. Book a tractor for 3 acres of rotavator work.
  await page.click('a[href="#book-tractor"]');
  await page.check('input[name=task][value=rotavator]');
  await page.check('input[name=slot][value=afternoon]'); // Ramesh is busy tomorrow morning (seed)
  await page.waitForSelector('#quote .qline.total');
  await page.click('[data-act=qty][data-d="1"]');
  await page.click('[data-act=qty][data-d="1"]'); // acres go in 0.5 steps: 2 → 3
  await page.waitForFunction(() => /3/.test(document.querySelector('#qty-out').textContent));
  await page.fill('#landmark', 'North field, next to the mango orchard');
  await page.waitForTimeout(300);
  await shot('03-book');
  await page.click('#book-btn');
  await page.waitForSelector('.pin b');
  const pin = (await page.textContent('.pin b')).trim();
  assert(/^\d{4}$/.test(pin), 'PIN shown to customer');
  await shot('04-booked');
  const bookingId = (await page.evaluate(() => location.hash)).slice(3);

  // 3. Switch to the tractor owner, accept the job.
  await page.selectOption('#demo-user', '9811100001');
  await page.waitForSelector('#online');
  await shot('05-provider');
  await page.click(`a[href="#b-${bookingId}"]`);
  await page.click('[data-act=accept]');
  await page.waitForSelector('.phone');
  assert((await page.textContent('body')).includes('9876543210'), 'customer phone visible after accept');
  return { shot, pin, bookingId, errors };
}

(async () => {
  const browser = await chromium.launch();
  const ctx = { viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, locale: 'en-IN' };

  // --- A. static demo build (no server): full lifecycle using the demo clock.
  let page = await (await browser.newContext(ctx)).newPage();
  await page.goto('file://' + path.join(root, 'dist', 'khetsaathi-demo.html') + '#login');
  const a = await journey(page, 'demo');
  await page.click('[data-act=jump]');
  await page.waitForSelector('#pin');
  await page.fill('#pin', '0000');
  await page.click('form[data-form=start] button[type=submit]');
  await page.waitForSelector('.note.err');
  await page.fill('#pin', a.pin);
  await page.click('form[data-form=start] button[type=submit]');
  await page.waitForSelector('form[data-form=complete]');
  await a.shot('06-in-progress');
  await page.fill('#aqty', '3.5');
  await page.click('form[data-form=complete] button[type=submit]');
  await page.waitForSelector('.pill.st-completed');
  await a.shot('07-completed');
  // Customer rates the job.
  await page.selectOption('#demo-user', '9876543210');
  await page.waitForSelector('.services');
  await page.goto(page.url().split('#')[0] + '#b-' + a.bookingId);
  await page.click('.stars label:nth-child(5)');
  await page.click('form[data-form=rate] button[type=submit]');
  await page.waitForSelector('text=★ 5/5');
  // Admin sees it.
  await page.selectOption('#demo-user', '9999999999');
  await page.waitForSelector('.tiles');
  await page.click('[data-act=verify]');
  await page.waitForTimeout(200);
  await a.shot('08-admin');
  const gmv = await page.textContent('.tile .v');
  assert(gmv !== '₹0', 'GMV counted');
  // Hindi.
  await page.click('#lang-btn');
  await page.goto(page.url().split('#')[0] + '#home');
  await page.waitForSelector('.services');
  await a.shot('09-hindi');
  assert((await page.textContent('h1')).includes('खेत'), 'Hindi UI');
  assert(!a.errors.length, 'no page errors: ' + a.errors.join('; '));

  // --- B. real server: same journey over HTTP.
  const tmp = fs.mkdtempSync(path.join(require('os').tmpdir(), 'khet-e2e-'));
  const { server } = createServer({ dataFile: path.join(tmp, 'db.json') });
  await new Promise((r) => server.listen(0, r));
  page = await (await browser.newContext(ctx)).newPage();
  await page.goto(`http://127.0.0.1:${server.address().port}/#login`);
  const b = await journey(page, 'server');
  assert(!b.errors.length, 'no page errors (server): ' + b.errors.join('; '));

  // Dark mode renders.
  const dark = await (await browser.newContext(Object.assign({ colorScheme: 'dark' }, ctx))).newPage();
  await dark.goto('file://' + path.join(root, 'dist', 'khetsaathi-demo.html') + '#login');
  await dark.waitForSelector('#phone');
  await dark.screenshot({ path: path.join(shots, 'dark-login.png') });

  server.close();
  await browser.close();
  console.log('E2E passed: demo build + server. Screenshots in dist/shots/');
})().catch((e) => { console.error(e); process.exit(1); });
