// KhetSaathi HTTP server: serves the web app from public/ and the JSON API from core.js.
// Zero dependencies. Run: node server.js  (PORT, DATA_FILE, DEMO_MODE, ADMIN_PHONES env vars)
'use strict';
const http = require('http');
const fs = require('fs');
const path = require('path');
const { createApp, createEmptyStore, seedDemo } = require('./public/core.js');

const PUBLIC_DIR = path.join(__dirname, 'public');
const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8', '.json': 'application/json', '.svg': 'image/svg+xml', '.png': 'image/png', '.ico': 'image/x-icon', '.webmanifest': 'application/manifest+json' };
const MAX_BODY = 64 * 1024;

function loadStore(file) {
  try { return JSON.parse(fs.readFileSync(file, 'utf8')); } catch (e) { return null; }
}

function saveStore(file, store) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const tmp = file + '.tmp';
  fs.writeFileSync(tmp, JSON.stringify(store));
  fs.renameSync(tmp, file); // atomic replace, so a crash never leaves half a file
}

function createServer(options) {
  const o = options || {};
  const dataFile = o.dataFile === undefined ? (process.env.DATA_FILE || path.join(__dirname, 'data', 'db.json')) : o.dataFile;
  const devMode = o.devMode !== undefined ? o.devMode : process.env.DEMO_MODE !== '0';
  const adminPhones = (o.adminPhones || process.env.ADMIN_PHONES || '9999999999').toString().split(',').map((s) => s.trim());
  const existing = dataFile ? loadStore(dataFile) : null;
  const app = createApp({
    store: existing || createEmptyStore(), devMode, adminPhones, now: o.now,
    onError: (e) => console.error('[error]', e),
  });
  if (!existing && devMode && o.seed !== false) seedDemo(app, (o.now || Date.now)());
  if (dataFile) saveStore(dataFile, app.store);

  const server = http.createServer((req, res) => {
    const url = req.url || '/';
    const security = {
      'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'same-origin', 'X-Frame-Options': 'DENY',
    };
    if (url.startsWith('/api/')) {
      let size = 0; const chunks = [];
      req.on('data', (c) => {
        size += c.length;
        if (size > MAX_BODY) { res.writeHead(413, { 'Content-Type': 'application/json' }); res.end('{"error":{"code":"TOO_LARGE","message":"Request too large."}}'); req.destroy(); }
        else chunks.push(c);
      });
      req.on('end', () => {
        if (res.writableEnded) return;
        let body = {};
        if (chunks.length) {
          try { body = JSON.parse(Buffer.concat(chunks).toString('utf8')); } catch (e) {
            res.writeHead(400, { 'Content-Type': 'application/json', ...security });
            return res.end('{"error":{"code":"BAD_JSON","message":"Body must be JSON."}}');
          }
        }
        const auth = req.headers.authorization || '';
        const token = auth.startsWith('Bearer ') ? auth.slice(7) : null;
        // Node is single-threaded and handle() is synchronous, so two providers
        // racing for the last slot are processed one after the other: no double booking.
        const out = app.handle(req.method, url, body, token);
        if (req.method !== 'GET' && out.status < 500 && dataFile) saveStore(dataFile, app.store);
        res.writeHead(out.status, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store', ...security });
        res.end(JSON.stringify(out.body));
      });
      return;
    }
    if (req.method !== 'GET' && req.method !== 'HEAD') { res.writeHead(405); return res.end(); }
    let rel = decodeURIComponent(url.split('?')[0]);
    if (rel === '/' || rel === '') rel = '/index.html';
    const file = path.normalize(path.join(PUBLIC_DIR, rel));
    if (!file.startsWith(PUBLIC_DIR + path.sep)) { res.writeHead(403); return res.end(); }
    fs.readFile(file, (err, data) => {
      if (err) { res.writeHead(404, { 'Content-Type': 'text/plain' }); return res.end('Not found'); }
      res.writeHead(200, { 'Content-Type': TYPES[path.extname(file)] || 'application/octet-stream', ...security });
      res.end(req.method === 'HEAD' ? undefined : data);
    });
  });
  return { server, app };
}

if (require.main === module) {
  const port = Number(process.env.PORT || 8080);
  const { server, app } = createServer();
  server.listen(port, () => {
    console.log(`KhetSaathi running on http://localhost:${port}  (${app.isDevMode() ? 'demo mode: OTPs shown on screen' : 'live mode'})`);
  });
}

module.exports = { createServer };
