// HTTP-level tests: real server on a random port, real JSON file on disk.
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { createServer } = require('../server.js');

async function boot(dataFile, opts) {
  const { server } = createServer(Object.assign({ dataFile }, opts));
  await new Promise((r) => server.listen(0, r));
  const base = `http://127.0.0.1:${server.address().port}`;
  const req = async (method, p, body, token, raw) => {
    const res = await fetch(base + p, {
      method,
      headers: Object.assign({ 'Content-Type': 'application/json' }, token ? { Authorization: 'Bearer ' + token } : {}),
      body: raw !== undefined ? raw : body ? JSON.stringify(body) : undefined,
    });
    const text = await res.text();
    let json = null; try { json = JSON.parse(text); } catch (e) { /* static file */ }
    return { status: res.status, json, text, headers: res.headers };
  };
  return { server, req, close: () => new Promise((r) => server.close(r)) };
}

const tmpFile = () => path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'khet-')), 'db.json');

test('serves the app, core.js and health; blocks path traversal', async () => {
  const s = await boot(tmpFile());
  try {
    const home = await s.req('GET', '/');
    assert.equal(home.status, 200);
    assert.match(home.text, /KhetSaathi/);
    assert.equal(home.headers.get('x-content-type-options'), 'nosniff');
    assert.equal((await s.req('GET', '/core.js')).status, 200);
    assert.equal((await s.req('GET', '/api/health')).json.mode, 'demo');
    const trav = await s.req('GET', '/..%2f..%2fserver.js');
    assert.ok([403, 404].includes(trav.status));
    assert.equal((await s.req('GET', '/nope.html')).status, 404);
  } finally { await s.close(); }
});

test('bad JSON is 400, oversized body is 413, unknown route is 404', async () => {
  const s = await boot(tmpFile());
  try {
    assert.equal((await s.req('POST', '/api/auth/otp', null, null, '{bad')).status, 400);
    const big = JSON.stringify({ phone: '9'.repeat(70000) });
    const r = await s.req('POST', '/api/auth/otp', null, null, big).catch(() => ({ status: 413 }));
    assert.equal(r.status, 413);
    assert.equal((await s.req('GET', '/api/unknown')).status, 404);
  } finally { await s.close(); }
});

test('OTP login and a booking survive a server restart (persisted to disk)', async () => {
  const file = tmpFile();
  let s = await boot(file);
  let token, id;
  try {
    const otp = await s.req('POST', '/api/auth/otp', { phone: '9123456789' });
    assert.match(otp.json.devOtp, /^\d{6}$/);
    const v = await s.req('POST', '/api/auth/verify', { phone: '9123456789', code: otp.json.devOtp, name: 'Asha' });
    token = v.json.token;
    const cat = (await s.req('GET', '/api/catalog')).json;
    const date = new Date(Date.parse(cat.today) + 2 * 864e5).toISOString().slice(0, 10);
    const b = await s.req('POST', '/api/bookings', { service: 'labour', task: 'weeding', date, slot: 'full', quantity: 2, villageId: 'jungle' }, token);
    assert.equal(b.status, 200, JSON.stringify(b.json));
    id = b.json.id;
  } finally { await s.close(); }
  s = await boot(file);
  try {
    const me = await s.req('GET', '/api/me', null, token);
    assert.equal(me.json.name, 'Asha');
    const b = await s.req('GET', `/api/bookings/${id}`, null, token);
    assert.equal(b.json.status, 'requested');
    assert.ok(JSON.parse(fs.readFileSync(file, 'utf8')).bookings[id]);
  } finally { await s.close(); }
});

test('live mode: no OTP in the response, no demo seed', async () => {
  const s = await boot(tmpFile(), { devMode: false });
  try {
    const otp = await s.req('POST', '/api/auth/otp', { phone: '9123456789' });
    assert.equal(otp.status, 200);
    assert.equal(otp.json.devOtp, undefined);
    assert.equal((await s.req('GET', '/api/health')).json.mode, 'live');
  } finally { await s.close(); }
});
