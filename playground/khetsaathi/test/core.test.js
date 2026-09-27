// Business-rule tests. Every edge case in docs/EDGE_CASES.md has a test here.
// Run: node --test test/
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const K = require('../public/core.js');

const HOUR = 3600e3;
// 1 Oct 2026, 10:00 IST
const T0 = Date.UTC(2026, 9, 1, 4, 30);

function world(opts) {
  const clock = { t: T0 };
  let seed = 42; // mulberry32: deterministic but well-mixed, so tokens never collide
  const randInt = (n) => {
    seed = (seed + 0x6d2b79f5) | 0;
    let x = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    x = (x + Math.imul(x ^ (x >>> 7), 61 | x)) ^ x;
    return ((x ^ (x >>> 14)) >>> 0) % n;
  };
  const app = K.createApp(Object.assign({ now: () => clock.t, randInt, onError: (e) => { throw e; } }, opts));
  const call = (method, path, body, token) => app.handle(method, path, body, token);
  const ok = (method, path, body, token) => {
    const r = call(method, path, body, token);
    assert.equal(r.status, 200, `${method} ${path} → ${JSON.stringify(r.body)}`);
    return r.body;
  };
  const err = (status, code, method, path, body, token) => {
    const r = call(method, path, body, token);
    assert.equal(r.status, status, `${method} ${path} expected ${status}, got ${r.status} ${JSON.stringify(r.body)}`);
    if (code) assert.equal(r.body.error.code, code);
    return r.body.error;
  };
  const login = (phone, name) => ok('POST', '/api/auth/demo', { phone, name }).token;
  const admin = login('9999999999', 'Ops');
  const provider = (phone, type, skills, villageId, extra) => {
    const tok = login(phone, 'P' + phone.slice(-3));
    const me = ok('POST', '/api/provider', Object.assign({ type, skills, villageId, vehicle: type === 'tractor' ? 'Mahindra 575' : '' }, extra), tok);
    ok('POST', `/api/admin/providers/${me.id}`, { verified: true }, admin);
    return { tok, id: me.id };
  };
  const customer = login('9876543210', 'Vinod');
  return { app, clock, call, ok, err, login, admin, provider, customer };
}

const D1 = '2026-10-02'; // tomorrow
const tractorBooking = (extra) => Object.assign({ service: 'tractor', task: 'plough', date: D1, slot: 'morning', quantity: 2, villageId: 'jungle' }, extra);

// ----------------------------------------------------------------- auth

test('phone numbers: accepts +91 / 0 prefixes and spaces, rejects landlines and short numbers', () => {
  assert.equal(K.normPhone('+91 98765 43210'), '9876543210');
  assert.equal(K.normPhone('09876543210'), '9876543210');
  assert.equal(K.normPhone('919876543210'), '9876543210');
  for (const bad of ['12345', '5876543210', '98765432101', 'abcdefghij', '', null]) {
    assert.throws(() => K.normPhone(bad), /valid 10-digit/);
  }
});

test('OTP: wrong code counts down, 5th wrong locks, expired OTP rejected, OTP single-use', () => {
  const w = world();
  const { devOtp } = w.ok('POST', '/api/auth/otp', { phone: '9123456789' });
  assert.match(devOtp, /^\d{6}$/);
  const e = w.err(400, 'OTP_WRONG', 'POST', '/api/auth/verify', { phone: '9123456789', code: '000000' });
  assert.match(e.message, /4 tries left/);
  for (let i = 0; i < 3; i++) w.err(400, 'OTP_WRONG', 'POST', '/api/auth/verify', { phone: '9123456789', code: '000000' });
  w.err(400, 'OTP_LOCKED', 'POST', '/api/auth/verify', { phone: '9123456789', code: '000000' });
  w.err(400, 'OTP_EXPIRED', 'POST', '/api/auth/verify', { phone: '9123456789', code: devOtp });

  const second = w.ok('POST', '/api/auth/otp', { phone: '9123456789' }).devOtp;
  const s = w.ok('POST', '/api/auth/verify', { phone: '9123456789', code: second, name: 'Asha' });
  assert.equal(s.user.name, 'Asha');
  w.err(400, 'OTP_EXPIRED', 'POST', '/api/auth/verify', { phone: '9123456789', code: second });

  const third = w.ok('POST', '/api/auth/otp', { phone: '9123456788' }).devOtp;
  w.clock.t += 6 * 60e3;
  w.err(400, 'OTP_EXPIRED', 'POST', '/api/auth/verify', { phone: '9123456788', code: third });
});

test('OTP: at most 3 requests per 10 minutes per phone', () => {
  const w = world();
  for (let i = 0; i < 3; i++) w.ok('POST', '/api/auth/otp', { phone: '9123456789' });
  w.err(429, 'OTP_RATE_LIMIT', 'POST', '/api/auth/otp', { phone: '9123456789' });
  w.clock.t += 11 * 60e3;
  w.ok('POST', '/api/auth/otp', { phone: '9123456789' });
});

test('live mode never returns the OTP and has no demo login', () => {
  const w0 = K.createApp({ devMode: false });
  const r = w0.handle('POST', '/api/auth/otp', { phone: '9123456789' });
  assert.equal(r.status, 200);
  assert.equal(r.body.devOtp, undefined);
  assert.equal(w0.handle('POST', '/api/auth/demo', { phone: '9123456789' }).status, 404);
});

test('sessions: missing/unknown token is 401, logout kills the token, sessions expire after 30 days', () => {
  const w = world();
  w.err(401, 'UNAUTHORIZED', 'GET', '/api/me');
  w.err(401, 'UNAUTHORIZED', 'GET', '/api/me', null, 'nope');
  const tok = w.login('9123456789');
  w.ok('GET', '/api/me', null, tok);
  w.ok('POST', '/api/auth/logout', {}, tok);
  w.err(401, 'UNAUTHORIZED', 'GET', '/api/me', null, tok);
  const tok2 = w.login('9123456789');
  w.clock.t += 31 * 24 * HOUR;
  w.err(401, 'UNAUTHORIZED', 'GET', '/api/me', null, tok2);
});

test('names: blank gets a default, too long is rejected', () => {
  const w = world();
  const tok = w.login('9123456789');
  assert.equal(w.ok('GET', '/api/me', null, tok).name, 'Kisan 6789');
  w.err(400, 'BAD_NAME', 'PATCH', '/api/me', { name: 'x'.repeat(41) }, tok);
  assert.equal(w.ok('PATCH', '/api/me', { name: '  Ram   Lal ' }, tok).name, 'Ram Lal');
});

test('router: unknown route 404, wrong method 405, garbage body tolerated', () => {
  const w = world();
  w.err(404, 'NOT_FOUND', 'GET', '/api/nothing');
  w.err(405, 'METHOD_NOT_ALLOWED', 'DELETE', '/api/catalog');
  w.err(400, 'BAD_PHONE', 'POST', '/api/auth/otp', 'not-an-object');
});

// ----------------------------------------------------------------- pricing

test('pricing: per acre, half-day workers, travel beyond 5 km, platform fee floor and cap', () => {
  const p1 = K.computePrice('tractor', 'plough', 2, 'morning', 12, 0);
  assert.equal(p1.base, 2400);
  assert.equal(p1.travel, Math.round(7 * 15));
  assert.equal(p1.platformFee, 99); // 5% of 2400 = 120 → capped at 99
  assert.equal(p1.total, 2400 + 105 + 99);
  const p2 = K.computePrice('labour', 'weeding', 3, 'morning', 0, 0);
  assert.equal(p2.base, Math.round(450 * 3 * 0.6));
  assert.equal(p2.travel, 0);
  const p3 = K.computePrice('farmer', 'crop_advice', 1, 'morning', 30, 0);
  assert.equal(p3.travel, 0); // farmers are local; no travel charge
  assert.equal(p3.platformFee, 15);
  const p4 = K.computePrice('mechanic', 'pump_repair', 1, 'morning', 3, 50);
  assert.equal(p4.travel, 0); // within 5 km is free
  assert.equal(p4.platformFee, 13);
  assert.equal(p4.total, 250 + 13 + 50); // late-cancel dues carried
  assert.equal(K.computePrice('mechanic', 'pump_repair', 1, 'morning', 0, 0, 0).platformFee, 13);
  assert.equal(K.computePrice('labour', 'general', 1, 'morning', 0, 0).platformFee, 14);
});

test('quantity: acres must fit the slot, half-acre steps, worker count 1–20', () => {
  const w = world();
  assert.equal(K.maxQuantity(K.SERVICES.tractor.tasks.plough, 'morning'), 7.5);
  assert.equal(K.maxQuantity(K.SERVICES.tractor.tasks.plough, 'full'), 16.5);
  assert.equal(K.maxQuantity(K.SERVICES.tractor.tasks.trolley, 'afternoon'), 5);
  w.err(400, 'BAD_QUANTITY', 'POST', '/api/quote', tractorBooking({ quantity: 8 }), w.customer);
  w.ok('POST', '/api/quote', tractorBooking({ quantity: 8, slot: 'full' }), w.customer);
  w.err(400, 'BAD_QUANTITY', 'POST', '/api/quote', tractorBooking({ quantity: 1.3 }), w.customer);
  w.err(400, 'BAD_QUANTITY', 'POST', '/api/quote', tractorBooking({ quantity: 0 }), w.customer);
  w.err(400, 'BAD_QUANTITY', 'POST', '/api/quote', tractorBooking({ quantity: 'lots' }), w.customer);
  w.err(400, 'BAD_QUANTITY', 'POST', '/api/quote', { service: 'labour', task: 'weeding', date: D1, slot: 'full', quantity: 21, villageId: 'jungle' }, w.customer);
  const q = w.ok('POST', '/api/quote', { service: 'mechanic', task: 'pump_repair', date: D1, slot: 'full', villageId: 'jungle' }, w.customer);
  assert.equal(q.price.quantity, 1);
  assert.equal(q.billable, true);
});

test('dates: past slots, today-but-started, beyond 30 days, invalid calendar dates, unknown slot', () => {
  const w = world(); // now is 10:00 IST on 2026-10-01
  w.err(400, 'BAD_DATE', 'POST', '/api/quote', tractorBooking({ date: '2026-09-30' }), w.customer);
  w.err(400, 'BAD_DATE', 'POST', '/api/quote', tractorBooking({ date: '2026-10-01', slot: 'morning' }), w.customer);
  w.ok('POST', '/api/quote', tractorBooking({ date: '2026-10-01', slot: 'afternoon' }), w.customer);
  w.ok('POST', '/api/quote', tractorBooking({ date: '2026-10-31' }), w.customer);
  w.err(400, 'BAD_DATE', 'POST', '/api/quote', tractorBooking({ date: '2026-11-01' }), w.customer);
  w.err(400, 'BAD_DATE', 'POST', '/api/quote', tractorBooking({ date: '2026-02-30' }), w.customer);
  w.err(400, 'BAD_DATE', 'POST', '/api/quote', tractorBooking({ date: '02-10-2026' }), w.customer);
  w.err(400, 'BAD_SLOT', 'POST', '/api/quote', tractorBooking({ slot: 'night' }), w.customer);
  w.err(400, 'BAD_SERVICE', 'POST', '/api/quote', tractorBooking({ service: 'drone' }), w.customer);
  w.err(400, 'BAD_TASK', 'POST', '/api/quote', tractorBooking({ task: 'weeding' }), w.customer);
  w.err(400, 'BAD_VILLAGE', 'POST', '/api/quote', tractorBooking({ villageId: 'mumbai' }), w.customer);
});

test('IST day boundary: at 00:30 IST "today" is already the new date', () => {
  const t = Date.UTC(2026, 9, 1, 19, 0); // 2 Oct 00:30 IST
  assert.equal(K.todayIST(t), '2026-10-02');
});

test('quote uses nearest free provider for travel; with nobody nearby it warns and assumes 15 km', () => {
  const w = world();
  let q = w.ok('POST', '/api/quote', tractorBooking(), w.customer);
  assert.equal(q.availableProviders, 0);
  assert.equal(q.travelEstimated, true);
  assert.equal(q.price.travelKm, 15);
  assert.ok(q.warning);
  w.provider('9811100001', 'tractor', ['plough'], 'pipraich');
  q = w.ok('POST', '/api/quote', tractorBooking(), w.customer);
  assert.equal(q.availableProviders, 1);
  assert.ok(q.price.travelKm > 5 && q.price.travelKm < 10);
});

// ----------------------------------------------------------------- lifecycle

test('happy path: book → accept → start with PIN → complete with actual acres → rate', () => {
  const w = world();
  const r = w.provider('9811100001', 'tractor', ['plough'], 'pipraich');
  const b = w.ok('POST', '/api/bookings', tractorBooking({ landmark: 'Near tube well' }), w.customer);
  assert.equal(b.status, 'requested');
  assert.match(b.pin, /^\d{4}$/);
  const offer = w.ok('GET', '/api/provider/jobs', null, r.tok).offers[0];
  assert.equal(offer.id, b.id);
  assert.equal(offer.customer, undefined, 'customer phone hidden before accepting');
  assert.equal(offer.pin, undefined);
  const acc = w.ok('POST', `/api/bookings/${b.id}/accept`, {}, r.tok);
  assert.equal(acc.status, 'confirmed');
  assert.equal(acc.pin, undefined, 'provider never sees the PIN');
  assert.equal(acc.customer.phone, '9876543210', 'phone revealed after accepting');
  assert.equal(w.ok('GET', `/api/bookings/${b.id}`, null, w.customer).providers[0].phone, '9811100001');

  w.clock.t = Date.UTC(2026, 9, 1, 23, 30); // 05:00 IST on D1 (1h before)
  w.err(400, 'PIN_WRONG', 'POST', `/api/bookings/${b.id}/start`, { pin: '0000' }, r.tok);
  const s = w.ok('POST', `/api/bookings/${b.id}/start`, { pin: b.pin }, r.tok);
  assert.equal(s.status, 'in_progress');
  w.err(409, 'BAD_STATE', 'POST', `/api/bookings/${b.id}/rate`, { stars: 5 }, w.customer);
  const c = w.ok('POST', `/api/bookings/${b.id}/complete`, { quantity: 2.5 }, r.tok);
  assert.equal(c.status, 'completed');
  assert.equal(c.price.base, 3000);
  w.ok('POST', `/api/bookings/${b.id}/rate`, { stars: 4, comment: 'On time' }, w.customer);
  w.err(409, 'ALREADY_RATED', 'POST', `/api/bookings/${b.id}/rate`, { stars: 5 }, w.customer);
  const jobs = w.ok('GET', '/api/provider/jobs', null, r.tok);
  assert.equal(jobs.provider.rating, 4);
  assert.equal(jobs.provider.jobsDone, 1);
  assert.equal(jobs.earnings, c.price.providerPayout);
});

test('start: too early, PIN lockout after 5 wrong tries, only assigned provider', () => {
  const w = world();
  const r = w.provider('9811100001', 'tractor', ['plough'], 'pipraich');
  const other = w.provider('9811100002', 'tractor', ['plough'], 'bhathat');
  const b = w.ok('POST', '/api/bookings', tractorBooking(), w.customer);
  w.ok('POST', `/api/bookings/${b.id}/accept`, {}, r.tok);
  w.err(409, 'TOO_EARLY', 'POST', `/api/bookings/${b.id}/start`, { pin: b.pin }, r.tok);
  w.clock.t = Date.UTC(2026, 9, 2, 0, 30); // 06:00 IST
  w.err(403, 'FORBIDDEN', 'POST', `/api/bookings/${b.id}/start`, { pin: b.pin }, other.tok);
  w.err(403, 'FORBIDDEN', 'POST', `/api/bookings/${b.id}/start`, { pin: b.pin }, w.customer);
  for (let i = 0; i < 5; i++) w.err(400, 'PIN_WRONG', 'POST', `/api/bookings/${b.id}/start`, { pin: '9999' }, r.tok);
  w.err(429, 'PIN_LOCKED', 'POST', `/api/bookings/${b.id}/start`, { pin: b.pin }, r.tok);
  w.clock.t += 16 * 60e3;
  w.ok('POST', `/api/bookings/${b.id}/start`, { pin: b.pin }, r.tok);
});

test('complete: actual acres capped at 2x booked; mechanic bill for parts; complete needs start', () => {
  const w = world();
  const r = w.provider('9811100001', 'tractor', ['plough'], 'pipraich');
  const m = w.provider('9811100021', 'mechanic', ['pump_repair'], 'gkp');
  const b = w.ok('POST', '/api/bookings', tractorBooking(), w.customer);
  w.ok('POST', `/api/bookings/${b.id}/accept`, {}, r.tok);
  w.err(409, 'BAD_STATE', 'POST', `/api/bookings/${b.id}/complete`, {}, r.tok);
  w.clock.t = Date.UTC(2026, 9, 2, 1, 0);
  w.ok('POST', `/api/bookings/${b.id}/start`, { pin: b.pin }, r.tok);
  w.err(400, 'BAD_QUANTITY', 'POST', `/api/bookings/${b.id}/complete`, { quantity: 5 }, r.tok);
  w.err(400, 'BAD_QUANTITY', 'POST', `/api/bookings/${b.id}/complete`, { quantity: 0 }, r.tok);

  const mb = w.ok('POST', '/api/bookings', { service: 'mechanic', task: 'pump_repair', date: D1, slot: 'afternoon', villageId: 'jungle' }, w.customer);
  w.ok('POST', `/api/bookings/${mb.id}/accept`, {}, m.tok);
  w.clock.t = Date.UTC(2026, 9, 2, 6, 30); // 12:00 IST
  w.ok('POST', `/api/bookings/${mb.id}/start`, { pin: mb.pin }, m.tok);
  w.err(400, 'BAD_EXTRA', 'POST', `/api/bookings/${mb.id}/complete`, { extra: -5 }, m.tok);
  w.err(400, 'BAD_EXTRA', 'POST', `/api/bookings/${mb.id}/complete`, { extra: 99999 }, m.tok);
  const done = w.ok('POST', `/api/bookings/${mb.id}/complete`, { extra: 850 }, m.tok);
  assert.equal(done.price.extra, 850);
  assert.equal(done.price.total, 250 + 850 + done.price.travel + done.price.platformFee);
});

// ----------------------------------------------------------------- matching & races

test('matching: wrong service, missing skill, unverified, suspended, out of range, own booking cannot accept', () => {
  const w = world();
  const b = w.ok('POST', '/api/bookings', tractorBooking(), w.customer);
  const worker = w.provider('9811100011', 'labour', ['weeding'], 'jungle');
  w.err(409, 'CANNOT_TAKE', 'POST', `/api/bookings/${b.id}/accept`, {}, worker.tok);
  const noSkill = w.provider('9811100003', 'tractor', ['sowing'], 'pipraich');
  w.err(409, 'CANNOT_TAKE', 'POST', `/api/bookings/${b.id}/accept`, {}, noSkill.tok);
  const far = w.provider('9811100004', 'tractor', ['plough'], 'bansgaon', { radiusKm: 10 });
  const e = w.err(409, 'CANNOT_TAKE', 'POST', `/api/bookings/${b.id}/accept`, {}, far.tok);
  assert.match(e.message, /outside your travel distance/);
  const unverifiedTok = w.login('9811100005');
  w.ok('POST', '/api/provider', { type: 'tractor', skills: ['plough'], villageId: 'jungle', vehicle: 'Swaraj' }, unverifiedTok);
  assert.match(w.err(409, 'CANNOT_TAKE', 'POST', `/api/bookings/${b.id}/accept`, {}, unverifiedTok).message, /verification/);
  assert.equal(w.ok('GET', '/api/provider/jobs', null, unverifiedTok).offers.length, 0);
  // Customer registers as a provider too, and tries to take their own job.
  w.ok('POST', '/api/provider', { type: 'tractor', skills: ['plough'], villageId: 'jungle', vehicle: 'Own tractor' }, w.customer);
  const me = w.ok('GET', '/api/me', null, w.customer);
  w.ok('POST', `/api/admin/providers/${me.id}`, { verified: true }, w.admin);
  assert.match(w.err(409, 'CANNOT_TAKE', 'POST', `/api/bookings/${b.id}/accept`, {}, w.customer).message, /own booking/);
  w.err(403, 'FORBIDDEN', 'POST', `/api/bookings/${b.id}/accept`, {}, w.login('9811100006'));
});

test('race: second tractor to accept gets NOT_OPEN; a provider cannot be double-booked', () => {
  const w = world();
  const a = w.provider('9811100001', 'tractor', ['plough', 'sowing'], 'pipraich');
  const c = w.provider('9811100002', 'tractor', ['plough'], 'bhathat');
  const b = w.ok('POST', '/api/bookings', tractorBooking(), w.customer);
  w.ok('POST', `/api/bookings/${b.id}/accept`, {}, a.tok);
  w.err(409, 'NOT_OPEN', 'POST', `/api/bookings/${b.id}/accept`, {}, c.tok);
  w.err(409, 'ALREADY_ACCEPTED', 'POST', `/api/bookings/${b.id}/accept`, {}, a.tok);
  const other = w.login('9876500000');
  const b2 = w.ok('POST', '/api/bookings', tractorBooking({ task: 'sowing', slot: 'full' }), other);
  assert.match(w.err(409, 'CANNOT_TAKE', 'POST', `/api/bookings/${b2.id}/accept`, {}, a.tok).message, /already have a job/);
  const b3 = w.ok('POST', '/api/bookings', tractorBooking({ task: 'sowing', slot: 'afternoon', villageId: 'bhathat' }), other);
  w.ok('POST', `/api/bookings/${b3.id}/accept`, {}, a.tok); // morning + afternoon do not overlap
});

test('duplicate booking and the 10-open-bookings limit', () => {
  const w = world();
  w.ok('POST', '/api/bookings', tractorBooking(), w.customer);
  w.err(409, 'DUPLICATE_BOOKING', 'POST', '/api/bookings', tractorBooking({ slot: 'full', quantity: 1 }), w.customer);
  w.ok('POST', '/api/bookings', tractorBooking({ villageId: 'pipraich' }), w.customer); // a different field is fine
  for (let i = 2; i < 10; i++) w.ok('POST', '/api/bookings', tractorBooking({ date: `2026-10-${String(i + 2).padStart(2, '0')}` }), w.customer);
  w.err(409, 'TOO_MANY_BOOKINGS', 'POST', '/api/bookings', tractorBooking({ date: '2026-10-20' }), w.customer);
});

test('workers: booking needs N acceptances; partial crew can start and price follows headcount', () => {
  const w = world();
  const ws = ['9811100011', '9811100012', '9811100013'].map((p) => w.provider(p, 'labour', ['weeding'], 'jungle'));
  const b = w.ok('POST', '/api/bookings', { service: 'labour', task: 'weeding', date: D1, slot: 'full', quantity: 4, villageId: 'jungle' }, w.customer);
  assert.equal(b.needed, 4);
  for (const x of ws) w.ok('POST', `/api/bookings/${b.id}/accept`, {}, x.tok);
  let v = w.ok('GET', `/api/bookings/${b.id}`, null, w.customer);
  assert.equal(v.status, 'requested');
  assert.equal(v.filled, 3);
  assert.equal(v.providers.length, 3);
  w.clock.t = Date.UTC(2026, 9, 2, 1, 0); // 06:30 IST, 4th worker never came
  v = w.ok('POST', `/api/bookings/${b.id}/start`, { pin: b.pin }, ws[0].tok);
  assert.equal(v.status, 'in_progress');
  assert.equal(v.quantity, 3);
  assert.equal(v.price.base, 450 * 3);
  const done = w.ok('POST', `/api/bookings/${b.id}/complete`, {}, ws[1].tok);
  assert.equal(done.payoutShare, 450);
});

// ----------------------------------------------------------------- cancellations

test('cancel: free before acceptance; free >12h ahead; ₹50/provider fee inside 12h, collected on next booking', () => {
  const w = world();
  const r = w.provider('9811100001', 'tractor', ['plough', 'sowing', 'rotavator'], 'pipraich');
  const b1 = w.ok('POST', '/api/bookings', tractorBooking(), w.customer);
  assert.equal(w.ok('POST', `/api/bookings/${b1.id}/cancel`, {}, w.customer).cancel.fee, 0);
  w.err(409, 'BAD_STATE', 'POST', `/api/bookings/${b1.id}/cancel`, {}, w.customer);

  const b2 = w.ok('POST', '/api/bookings', tractorBooking({ task: 'sowing' }), w.customer);
  w.ok('POST', `/api/bookings/${b2.id}/accept`, {}, r.tok);
  assert.equal(w.ok('POST', `/api/bookings/${b2.id}/cancel`, {}, w.customer).cancel.fee, 0); // 20h ahead

  const b3 = w.ok('POST', '/api/bookings', tractorBooking({ task: 'rotavator' }), w.customer);
  w.ok('POST', `/api/bookings/${b3.id}/accept`, {}, r.tok);
  w.clock.t = Date.UTC(2026, 9, 1, 16, 30); // 22:00 IST, 8h before
  const v = w.ok('GET', `/api/bookings/${b3.id}`, null, w.customer);
  assert.equal(v.lateCancelFee, 50);
  assert.equal(w.ok('POST', `/api/bookings/${b3.id}/cancel`, {}, w.customer).cancel.fee, 50);
  assert.equal(w.ok('GET', '/api/me', null, w.customer).dues, 50);
  const q = w.ok('POST', '/api/quote', tractorBooking({ date: '2026-10-05' }), w.customer);
  assert.equal(q.price.dues, 50);
  const b4 = w.ok('POST', '/api/bookings', tractorBooking({ date: '2026-10-05' }), w.customer);
  assert.equal(w.ok('GET', '/api/me', null, w.customer).dues, 0);
  // Cancelling that booking free gives the dues back instead of losing them.
  w.ok('POST', `/api/bookings/${b4.id}/cancel`, {}, w.customer);
  assert.equal(w.ok('GET', '/api/me', null, w.customer).dues, 50);
});

test('provider no-show: after 2h grace the customer cancels free and the provider gets a strike', () => {
  const w = world();
  const r = w.provider('9811100001', 'tractor', ['plough'], 'pipraich');
  const b = w.ok('POST', '/api/bookings', tractorBooking(), w.customer);
  w.ok('POST', `/api/bookings/${b.id}/accept`, {}, r.tok);
  w.clock.t = Date.UTC(2026, 9, 2, 3, 0); // 08:30 IST
  const v = w.ok('GET', `/api/bookings/${b.id}`, null, w.customer);
  assert.equal(v.noShow, true);
  assert.equal(v.lateCancelFee, 0);
  assert.equal(w.ok('POST', `/api/bookings/${b.id}/cancel`, {}, w.customer).cancel.fee, 0);
  assert.equal(w.ok('GET', '/api/provider/jobs', null, r.tok).provider.strikes, 1);
});

test('provider withdraws: job reopens; late withdrawals give strikes; 3 strikes suspend; cannot rejoin', () => {
  const w = world();
  const r = w.provider('9811100001', 'tractor', ['plough', 'sowing', 'rotavator', 'harvester'], 'pipraich');
  const backup = w.provider('9811100002', 'tractor', ['plough'], 'bhathat');
  const b = w.ok('POST', '/api/bookings', tractorBooking(), w.customer);
  w.ok('POST', `/api/bookings/${b.id}/accept`, {}, r.tok);
  const out = w.ok('POST', `/api/bookings/${b.id}/withdraw`, {}, r.tok);
  assert.equal(out.strikes, 0); // 20h ahead: no strike
  assert.equal(w.ok('GET', `/api/bookings/${b.id}`, null, w.customer).status, 'requested');
  w.err(409, 'WITHDREW', 'POST', `/api/bookings/${b.id}/accept`, {}, r.tok);
  w.ok('POST', `/api/bookings/${b.id}/accept`, {}, backup.tok);

  w.clock.t = Date.UTC(2026, 9, 1, 16, 30); // 8h before the D1 morning slot
  for (const task of ['sowing', 'rotavator', 'harvester']) {
    const x = w.ok('POST', '/api/bookings', tractorBooking({ task }), w.customer);
    w.ok('POST', `/api/bookings/${x.id}/accept`, {}, r.tok);
    const res = w.ok('POST', `/api/bookings/${x.id}/withdraw`, {}, r.tok);
    if (task === 'harvester') assert.equal(res.suspended, true);
  }
  const x = w.ok('POST', '/api/bookings', tractorBooking({ task: 'plough', date: '2026-10-06' }), w.customer);
  assert.match(w.err(409, 'CANNOT_TAKE', 'POST', `/api/bookings/${x.id}/accept`, {}, r.tok).message, /suspended/);
  w.ok('POST', `/api/admin/providers/${r.id}`, { suspended: false }, w.admin);
  w.ok('POST', `/api/bookings/${x.id}/accept`, {}, r.tok);
});

test('reschedule once (rain): keeps free providers, releases busy ones, second move refused', () => {
  const w = world();
  const a = w.provider('9811100001', 'tractor', ['plough'], 'pipraich');
  const b = w.ok('POST', '/api/bookings', tractorBooking(), w.customer);
  w.ok('POST', `/api/bookings/${b.id}/accept`, {}, a.tok);
  w.err(400, 'SAME_TIME', 'POST', `/api/bookings/${b.id}/reschedule`, { date: D1, slot: 'morning' }, w.customer);
  w.err(400, 'BAD_DATE', 'POST', `/api/bookings/${b.id}/reschedule`, { date: '2026-09-01', slot: 'morning' }, w.customer);
  let v = w.ok('POST', `/api/bookings/${b.id}/reschedule`, { date: '2026-10-03', slot: 'morning' }, w.customer);
  assert.equal(v.status, 'confirmed');
  w.err(409, 'RESCHEDULE_LIMIT', 'POST', `/api/bookings/${b.id}/reschedule`, { date: '2026-10-04', slot: 'morning' }, w.customer);

  const b2 = w.ok('POST', '/api/bookings', tractorBooking({ villageId: 'bhathat' }), w.customer);
  w.ok('POST', `/api/bookings/${b2.id}/accept`, {}, a.tok);
  v = w.ok('POST', `/api/bookings/${b2.id}/reschedule`, { date: '2026-10-03', slot: 'full' }, w.customer);
  assert.equal(v.status, 'requested', 'provider busy on the new day, so released');
  assert.equal(v.filled, 0);
  // 10 acres fits a full day but not a half-day slot.
  const b3 = w.ok('POST', '/api/bookings', tractorBooking({ villageId: 'khorabar', slot: 'full', quantity: 10 }), w.customer);
  w.err(400, 'BAD_QUANTITY', 'POST', `/api/bookings/${b3.id}/reschedule`, { date: '2026-10-04', slot: 'morning' }, w.customer);
});

// ----------------------------------------------------------------- expiry

test('expiry: unaccepted job expires 2h after start; partial crew expires at slot end; dues come back', () => {
  const w = world();
  w.app.store.users[Object.values(w.app.store.users).find((u) => u.phone === '9876543210').id].dues = 50;
  const b = w.ok('POST', '/api/bookings', tractorBooking(), w.customer);
  const worker = w.provider('9811100011', 'labour', ['weeding'], 'jungle');
  const l = w.ok('POST', '/api/bookings', { service: 'labour', task: 'weeding', date: D1, slot: 'morning', quantity: 2, villageId: 'jungle' }, w.customer);
  w.ok('POST', `/api/bookings/${l.id}/accept`, {}, worker.tok);
  w.clock.t = Date.UTC(2026, 9, 2, 2, 31); // 08:01 IST
  assert.equal(w.ok('GET', `/api/bookings/${b.id}`, null, w.customer).status, 'expired');
  assert.equal(w.ok('GET', '/api/me', null, w.customer).dues, 50);
  assert.equal(w.ok('GET', `/api/bookings/${l.id}`, null, w.customer).status, 'requested');
  w.clock.t = Date.UTC(2026, 9, 2, 5, 31); // 11:01 IST
  assert.equal(w.ok('GET', `/api/bookings/${l.id}`, null, w.customer).status, 'expired');
});

// ----------------------------------------------------------------- privacy, disputes, admin

test('privacy: strangers cannot read a booking; eligible provider sees an offer without phone or PIN', () => {
  const w = world();
  const b = w.ok('POST', '/api/bookings', tractorBooking(), w.customer);
  w.err(403, 'FORBIDDEN', 'GET', `/api/bookings/${b.id}`, null, w.login('9000000001'));
  const r = w.provider('9811100001', 'tractor', ['plough'], 'pipraich');
  const o = w.ok('GET', `/api/bookings/${b.id}`, null, r.tok);
  assert.equal(o.offer, true);
  assert.equal(o.pin, undefined);
  assert.equal(o.customer, undefined);
  assert.equal(JSON.stringify(o).includes('9876543210'), false);
  w.err(404, 'NOT_FOUND', 'GET', '/api/bookings/B999999', null, w.customer);
});

test('disputes: within 48h only, reason required, admin resolves with a bounded refund', () => {
  const w = world();
  const r = w.provider('9811100001', 'tractor', ['plough', 'sowing'], 'pipraich');
  const run = (task) => {
    const b = w.ok('POST', '/api/bookings', tractorBooking({ task, slot: task === 'plough' ? 'morning' : 'afternoon' }), w.customer);
    w.ok('POST', `/api/bookings/${b.id}/accept`, {}, r.tok);
    return b;
  };
  const b = run('plough');
  const b2 = run('sowing'); // same provider, afternoon of D1
  w.err(409, 'BAD_STATE', 'POST', `/api/bookings/${b.id}/dispute`, { reason: 'bad work' }, w.customer);
  w.clock.t = Date.UTC(2026, 9, 2, 1, 0);
  w.ok('POST', `/api/bookings/${b.id}/start`, { pin: b.pin }, r.tok);
  const done = w.ok('POST', `/api/bookings/${b.id}/complete`, {}, r.tok);
  w.err(400, 'BAD_REASON', 'POST', `/api/bookings/${b.id}/dispute`, { reason: 'no' }, w.customer);
  w.err(403, 'FORBIDDEN', 'POST', `/api/bookings/${b.id}/dispute`, { reason: 'bad work' }, r.tok);
  w.ok('POST', `/api/bookings/${b.id}/dispute`, { reason: 'Only half the field was ploughed' }, w.customer);
  const ov = w.ok('GET', '/api/admin/overview', null, w.admin);
  assert.equal(ov.disputes.length, 1);
  w.err(403, 'FORBIDDEN', 'GET', '/api/admin/overview', null, w.customer);
  w.err(400, 'BAD_REFUND', 'POST', `/api/admin/bookings/${b.id}/resolve`, { refund: done.price.total + 1 }, w.admin);
  const res = w.ok('POST', `/api/admin/bookings/${b.id}/resolve`, { refund: 600, note: 'Half done' }, w.admin);
  assert.equal(res.status, 'completed');
  assert.equal(res.dispute.resolution.refund, 600);
  w.err(409, 'BAD_STATE', 'POST', `/api/admin/bookings/${b.id}/resolve`, { refund: 0 }, w.admin);

  w.clock.t = Date.UTC(2026, 9, 2, 6, 30); // 12:00 IST
  w.ok('POST', `/api/bookings/${b2.id}/start`, { pin: b2.pin }, r.tok);
  w.ok('POST', `/api/bookings/${b2.id}/complete`, {}, r.tok);
  w.clock.t += 49 * HOUR;
  w.err(409, 'DISPUTE_WINDOW', 'POST', `/api/bookings/${b2.id}/dispute`, { reason: 'too late complaint' }, w.customer);
});

test('provider registration: validation, tractor needs vehicle, type is locked, radius bounded', () => {
  const w = world();
  const tok = w.login('9811100001');
  w.err(400, 'BAD_SERVICE', 'POST', '/api/provider', { type: 'drone', skills: ['x'], villageId: 'jungle' }, tok);
  w.err(400, 'BAD_SKILLS', 'POST', '/api/provider', { type: 'tractor', skills: [], villageId: 'jungle', vehicle: 'x' }, tok);
  w.err(400, 'BAD_SKILLS', 'POST', '/api/provider', { type: 'tractor', skills: ['weeding'], villageId: 'jungle', vehicle: 'x' }, tok);
  w.err(400, 'BAD_VEHICLE', 'POST', '/api/provider', { type: 'tractor', skills: ['plough'], villageId: 'jungle' }, tok);
  w.err(400, 'BAD_RADIUS', 'POST', '/api/provider', { type: 'tractor', skills: ['plough'], villageId: 'jungle', vehicle: 'x', radiusKm: 100 }, tok);
  const me = w.ok('POST', '/api/provider', { type: 'tractor', skills: ['plough', 'plough'], villageId: 'jungle', vehicle: 'x' }, tok);
  assert.deepEqual(me.provider.skills, ['plough']);
  assert.equal(me.provider.verified, false);
  w.err(409, 'TYPE_LOCKED', 'POST', '/api/provider', { type: 'mechanic', skills: ['pump_repair'], villageId: 'jungle' }, tok);
  const upd = w.ok('POST', '/api/provider', { skills: ['plough', 'sowing'], villageId: 'pipraich', vehicle: 'x', radiusKm: 12 }, tok);
  assert.equal(upd.provider.radiusKm, 12);
  // Going offline hides offers.
  w.ok('POST', `/api/admin/providers/${me.id}`, { verified: true }, w.admin);
  w.ok('POST', '/api/bookings', tractorBooking(), w.customer);
  assert.equal(w.ok('GET', '/api/provider/jobs', null, tok).offers.length, 1);
  w.ok('POST', '/api/provider/online', { online: false }, tok);
  assert.equal(w.ok('GET', '/api/provider/jobs', null, tok).offers.length, 0);
  w.err(403, 'FORBIDDEN', 'GET', '/api/provider/jobs', null, w.customer);
});

test('nearest village lookup and the demo seed run end to end', () => {
  const w = world();
  const n = w.ok('GET', '/api/villages/nearest?lat=26.83&lng=83.52', null);
  assert.equal(n.village.id, 'pipraich');
  const app = K.createApp({ now: () => T0 });
  const seeded = K.seedDemo(app, T0);
  const tok = app.handle('POST', '/api/auth/demo', { phone: seeded.adminPhone }).body.token;
  const ov = app.handle('GET', '/api/admin/overview', null, tok).body;
  assert.equal(ov.totals.providers, 13);
  assert.equal(ov.pendingProviders.length, 1);
  assert.equal(ov.totals.bookings, 4);
});
