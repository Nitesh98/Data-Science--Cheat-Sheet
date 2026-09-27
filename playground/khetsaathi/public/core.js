/*
 * KhetSaathi core: every business rule of the marketplace lives here.
 *
 * The same file runs in two places:
 *   - Node (server.js), behind a real HTTP API, persisted to a JSON file.
 *   - The browser, in "demo mode", persisted to localStorage (used for the
 *     hosted demo, where there is no server).
 * Both call app.handle(method, path, body, token), so the rules are tested once.
 *
 * No dependencies. Money is whole rupees. Times are epoch ms; dates/slots are IST.
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.KhetCore = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  const MIN = 60e3;
  const HOUR = 60 * MIN;
  const DAY = 24 * HOUR;
  const IST_OFFSET = 5.5 * HOUR;

  // ---------------------------------------------------------------- catalogue

  const RULES = {
    platformFeePct: 0.05, platformFeeMin: 10, platformFeeMax: 99,
    freeTravelKm: 5, travelPerKm: 15, assumedTravelKm: 15,
    cancelFeePerProvider: 50, lateWindowHours: 12,
    noShowGraceHours: 2, maxStrikes: 3,
    bookingHorizonDays: 30, disputeWindowHours: 48,
    maxActiveBookings: 10, maxPinFailures: 5, pinLockMinutes: 15,
    earlyStartHours: 1,
  };

  const SLOTS = {
    morning: { start: 6, end: 11, factor: 0.6, en: 'Morning 6–11 AM', hi: 'सुबह 6–11 बजे' },
    afternoon: { start: 12, end: 17, factor: 0.6, en: 'Afternoon 12–5 PM', hi: 'दोपहर 12–5 बजे' },
    full: { start: 6, end: 17, factor: 1, en: 'Full day 6 AM–5 PM', hi: 'पूरा दिन 6–5 बजे' },
  };

  // perSlotHour caps quantity by what fits in the slot (a tractor ploughs ~1.5 acres/hour).
  const UNITS = {
    acre: { min: 0.5, max: 50, step: 0.5, perSlotHour: 1.5, slotPriced: false, adjustable: true, en: 'acres', hi: 'एकड़' },
    hour: { min: 1, max: 12, step: 1, perSlotHour: 1, slotPriced: false, adjustable: true, en: 'hours', hi: 'घंटे' },
    worker_day: { min: 1, max: 20, step: 1, slotPriced: true, adjustable: false, en: 'workers', hi: 'मज़दूर' },
    day: { min: 1, max: 1, step: 1, slotPriced: true, adjustable: false, en: 'day', hi: 'दिन' },
    visit: { min: 1, max: 1, step: 1, slotPriced: false, adjustable: false, en: 'visit', hi: 'विज़िट' },
  };

  const SERVICES = {
    tractor: {
      icon: '🚜', en: 'Tractor', hi: 'ट्रैक्टर', radiusKm: 25, travel: true,
      tagline: { en: 'With driver, for ploughing, sowing, harvest, transport', hi: 'ड्राइवर के साथ — जुताई, बुवाई, कटाई, ढुलाई' },
      tasks: {
        plough: { en: 'Ploughing (cultivator)', hi: 'जुताई (कल्टीवेटर)', unit: 'acre', rate: 1200 },
        rotavator: { en: 'Rotavator', hi: 'रोटावेटर', unit: 'acre', rate: 1400 },
        sowing: { en: 'Sowing (seed drill)', hi: 'बुवाई (सीड ड्रिल)', unit: 'acre', rate: 1000 },
        harvester: { en: 'Harvesting (combine)', hi: 'कटाई (कंबाइन)', unit: 'acre', rate: 2200 },
        trolley: { en: 'Trolley transport', hi: 'ट्रॉली ढुलाई', unit: 'hour', rate: 700 },
      },
    },
    labour: {
      icon: '👷', en: 'Farm workers', hi: 'खेत मज़दूर', radiusKm: 10, travel: false, multi: true,
      tagline: { en: 'Daily workers for weeding, watering, transplanting, cutting', hi: 'निराई, सिंचाई, रोपाई, कटाई के लिए दिहाड़ी मज़दूर' },
      tasks: {
        weeding: { en: 'Weeding', hi: 'निराई', unit: 'worker_day', rate: 450 },
        irrigation: { en: 'Watering / irrigation', hi: 'सिंचाई', unit: 'worker_day', rate: 450 },
        transplanting: { en: 'Paddy transplanting', hi: 'धान रोपाई', unit: 'worker_day', rate: 500 },
        harvesting: { en: 'Crop cutting', hi: 'फसल कटाई', unit: 'worker_day', rate: 500 },
        spraying: { en: 'Pesticide spraying', hi: 'दवा छिड़काव', unit: 'worker_day', rate: 500 },
        general: { en: 'General field work', hi: 'खेत का सामान्य काम', unit: 'worker_day', rate: 450 },
      },
    },
    mechanic: {
      icon: '🔧', en: 'Mechanic', hi: 'मिस्त्री', radiusKm: 25, travel: true,
      tagline: { en: 'Comes to your field. Visit fee now, parts billed on site', hi: 'खेत पर आएगा। विज़िट फीस अभी, पुर्ज़े मौके पर' },
      tasks: {
        tractor_repair: { en: 'Tractor repair', hi: 'ट्रैक्टर मरम्मत', unit: 'visit', rate: 300, billable: true },
        pump_repair: { en: 'Pump / motor repair', hi: 'पंप / मोटर मरम्मत', unit: 'visit', rate: 250, billable: true },
        equipment_repair: { en: 'Sprayer / equipment repair', hi: 'स्प्रेयर / उपकरण मरम्मत', unit: 'visit', rate: 250, billable: true },
      },
    },
    farmer: {
      icon: '👨‍🌾', en: 'Experienced farmer', hi: 'अनुभवी किसान', radiusKm: 15, travel: false,
      tagline: { en: 'Runs your field for the day, or advises on your crop', hi: 'दिनभर खेत संभाले, या फसल पर सलाह दे' },
      tasks: {
        field_manager: { en: 'Look after my field for the day', hi: 'दिनभर खेत की देखरेख', unit: 'day', rate: 700 },
        crop_advice: { en: 'Crop advice visit', hi: 'फसल सलाह विज़िट', unit: 'visit', rate: 300 },
      },
    },
  };

  // Pilot cluster: villages/blocks around Gorakhpur, UP (approximate coordinates).
  const VILLAGES = [
    { id: 'gkp', en: 'Gorakhpur (city)', hi: 'गोरखपुर (शहर)', lat: 26.7606, lng: 83.3732 },
    { id: 'pipraich', en: 'Pipraich', hi: 'पिपराइच', lat: 26.8276, lng: 83.5270 },
    { id: 'chauri', en: 'Chauri Chaura', hi: 'चौरी चौरा', lat: 26.6440, lng: 83.5820 },
    { id: 'sahjanwa', en: 'Sahjanwa', hi: 'सहजनवा', lat: 26.7530, lng: 83.2140 },
    { id: 'campierganj', en: 'Campierganj', hi: 'कैम्पियरगंज', lat: 26.9900, lng: 83.2600 },
    { id: 'bhathat', en: 'Bhathat', hi: 'भटहट', lat: 26.8700, lng: 83.4000 },
    { id: 'khorabar', en: 'Khorabar', hi: 'खोराबार', lat: 26.7100, lng: 83.4000 },
    { id: 'jungle', en: 'Jungle Kauria', hi: 'जंगल कौड़िया', lat: 26.8000, lng: 83.4700 },
    { id: 'bansgaon', en: 'Bansgaon', hi: 'बांसगांव', lat: 26.5530, lng: 83.3530 },
  ];

  const ACTIVE = new Set(['requested', 'confirmed', 'in_progress']);

  // ------------------------------------------------------------------ helpers

  class AppError extends Error {
    constructor(status, code, message) { super(message); this.status = status; this.code = code; }
  }
  const bad = (code, msg) => new AppError(400, code, msg);
  const forbidden = (msg) => new AppError(403, 'FORBIDDEN', msg || 'You are not allowed to do this.');
  const notFound = (what) => new AppError(404, 'NOT_FOUND', `${what} not found.`);
  const conflict = (code, msg) => new AppError(409, code, msg);

  const clamp = (x, lo, hi) => Math.min(hi, Math.max(lo, x));
  const round1 = (x) => Math.round(x * 10) / 10;

  function haversineKm(a, b) {
    const R = 6371, toRad = (d) => d * Math.PI / 180;
    const dLat = toRad(b.lat - a.lat), dLng = toRad(b.lng - a.lng);
    const h = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(a.lat)) * Math.cos(toRad(b.lat)) * Math.sin(dLng / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(h));
  }

  function normPhone(raw) {
    let p = String(raw == null ? '' : raw).replace(/[\s-]/g, '');
    if (p.startsWith('+91')) p = p.slice(3);
    else if (p.length === 12 && p.startsWith('91')) p = p.slice(2);
    else if (p.length === 11 && p.startsWith('0')) p = p.slice(1);
    if (!/^[6-9]\d{9}$/.test(p)) throw bad('BAD_PHONE', 'Enter a valid 10-digit Indian mobile number.');
    return p;
  }

  function todayIST(t) { return new Date(t + IST_OFFSET).toISOString().slice(0, 10); }
  function addDays(dateStr, n) {
    const d = new Date(dateStr + 'T00:00:00Z');
    d.setUTCDate(d.getUTCDate() + n);
    return d.toISOString().slice(0, 10);
  }
  function istTime(dateStr, hour) {
    const [y, m, d] = dateStr.split('-').map(Number);
    return Date.UTC(y, m - 1, d, hour) - IST_OFFSET;
  }
  function slotStart(b) { return istTime(b.date, SLOTS[b.slot].start); }
  function slotEnd(b) { return istTime(b.date, SLOTS[b.slot].end); }
  function slotsOverlap(a, b) { return a === 'full' || b === 'full' || a === b; }

  function validDate(s) {
    if (typeof s !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(s)) return false;
    const d = new Date(s + 'T00:00:00Z');
    return !isNaN(d) && d.toISOString().slice(0, 10) === s;
  }

  function getTask(serviceId, taskId) {
    const service = SERVICES[serviceId];
    if (!service) throw bad('BAD_SERVICE', 'Choose a service.');
    const task = service.tasks[taskId];
    if (!task) throw bad('BAD_TASK', 'Choose a type of work for this service.');
    return { service, task };
  }

  function getVillage(id) {
    const v = VILLAGES.find((x) => x.id === id);
    if (!v) throw bad('BAD_VILLAGE', 'Choose your village from the list.');
    return v;
  }

  function nearestVillage(lat, lng) {
    let best = null, bestD = Infinity;
    for (const v of VILLAGES) {
      const d = haversineKm({ lat, lng }, v);
      if (d < bestD) { best = v; bestD = d; }
    }
    return { village: best, distanceKm: round1(bestD) };
  }

  function maxQuantity(task, slotKey) {
    const unit = UNITS[task.unit];
    if (!unit.perSlotHour) return unit.max;
    const s = SLOTS[slotKey];
    const cap = Math.floor(((s.end - s.start) * unit.perSlotHour) / unit.step) * unit.step;
    return Math.min(unit.max, cap);
  }

  function validateQuantity(task, slotKey, raw) {
    const unit = UNITS[task.unit];
    const q = raw == null || raw === '' ? unit.min : Number(raw);
    if (!Number.isFinite(q)) throw bad('BAD_QUANTITY', `Enter the number of ${unit.en}.`);
    const max = maxQuantity(task, slotKey);
    if (q < unit.min) throw bad('BAD_QUANTITY', `Minimum is ${unit.min} ${unit.en}.`);
    if (q > max) {
      throw bad('BAD_QUANTITY', unit.perSlotHour
        ? `At most ${max} ${unit.en} fit in this time slot. Pick a full day or split it into two bookings.`
        : `At most ${max} ${unit.en} per booking.`);
    }
    if (Math.abs(q / unit.step - Math.round(q / unit.step)) > 1e-9) throw bad('BAD_QUANTITY', `Quantity must be in steps of ${unit.step}.`);
    return q;
  }

  function computePrice(serviceId, taskId, qty, slotKey, travelKm, dues, extra) {
    const { service, task } = getTask(serviceId, taskId);
    const unit = UNITS[task.unit];
    const slotFactor = unit.slotPriced ? SLOTS[slotKey].factor : 1;
    const base = Math.round(task.rate * qty * slotFactor);
    const km = service.travel ? travelKm : 0;
    const travel = service.travel ? Math.round(Math.max(0, km - RULES.freeTravelKm) * RULES.travelPerKm) : 0;
    const work = base + (extra || 0);
    const platformFee = clamp(Math.round(work * RULES.platformFeePct), RULES.platformFeeMin, RULES.platformFeeMax);
    return {
      rate: task.rate, unit: task.unit, quantity: qty, slotFactor, base, extra: extra || 0,
      travelKm: round1(km), travel, platformFee, dues: dues || 0,
      providerPayout: work + travel, total: work + travel + platformFee + (dues || 0),
    };
  }

  function createEmptyStore() {
    return { version: 1, seq: 1000, users: {}, providers: {}, bookings: {}, otps: {}, sessions: {} };
  }

  function defaultRandInt(n) {
    const c = typeof globalThis !== 'undefined' && globalThis.crypto;
    if (c && c.getRandomValues) return c.getRandomValues(new Uint32Array(1))[0] % n;
    return Math.floor(Math.random() * n);
  }

  // ---------------------------------------------------------------------- app

  function createApp(opts) {
    opts = opts || {};
    const now = opts.now || (() => Date.now());
    const store = opts.store || createEmptyStore();
    const devMode = opts.devMode !== false;
    const adminPhones = new Set(opts.adminPhones || ['9999999999']);
    const randInt = opts.randInt || defaultRandInt;

    const nextId = (prefix) => prefix + (++store.seq);
    const digits = (n) => { let s = String(1 + randInt(9)); while (s.length < n) s += randInt(10); return s; };
    const hex = (n) => { let s = ''; for (let i = 0; i < n; i++) s += '0123456789abcdef'[randInt(16)]; return s; };

    function log(b, status, note) {
      b.history.push({ at: now(), status, note: note || '' });
      b.status = status;
    }

    // ---- users & auth

    function findUserByPhone(phone) {
      return Object.values(store.users).find((u) => u.phone === phone) || null;
    }

    function cleanName(name, phone) {
      const n = String(name == null ? '' : name).trim().replace(/\s+/g, ' ');
      if (!n) return 'Kisan ' + phone.slice(-4);
      if (n.length < 2 || n.length > 40) throw bad('BAD_NAME', 'Name should be 2 to 40 characters.');
      return n;
    }

    function createUser(phone, name) {
      const u = { id: nextId('U'), phone, name: cleanName(name, phone), dues: 0, createdAt: now() };
      store.users[u.id] = u;
      return u;
    }

    function isAdmin(u) { return !!u && adminPhones.has(u.phone); }

    function issueSession(user) {
      const token = hex(32);
      store.sessions[token] = { userId: user.id, expiresAt: now() + 30 * DAY };
      return { token, user: userView(user) };
    }

    function authUser(token) {
      if (!token) return null;
      const s = store.sessions[token];
      if (!s) return null;
      if (now() > s.expiresAt) { delete store.sessions[token]; return null; }
      return store.users[s.userId] || null;
    }

    function requestOtp(body) {
      const phone = normPhone(body.phone);
      const t = now();
      const prev = store.otps[phone];
      const recent = ((prev && prev.sent) || []).filter((x) => t - x < 10 * MIN);
      if (recent.length >= 3) throw new AppError(429, 'OTP_RATE_LIMIT', 'Too many OTP requests. Try again in 10 minutes.');
      const code = digits(6);
      store.otps[phone] = { code, expiresAt: t + 5 * MIN, attempts: 0, sent: recent.concat(t) };
      // Production: send `code` via an SMS gateway (e.g. MSG91) here, never in the response.
      const res = { sent: true, isNewUser: !findUserByPhone(phone) };
      if (devMode) res.devOtp = code;
      return res;
    }

    function verifyOtp(body) {
      const phone = normPhone(body.phone);
      const rec = store.otps[phone];
      if (!rec || !rec.code || now() > rec.expiresAt) throw bad('OTP_EXPIRED', 'OTP expired or not requested. Ask for a new OTP.');
      if (String(body.code || '').trim() !== rec.code) {
        rec.attempts += 1;
        if (rec.attempts >= 5) { rec.code = null; throw bad('OTP_LOCKED', 'Too many wrong tries. Ask for a new OTP.'); }
        throw bad('OTP_WRONG', `Wrong OTP. ${5 - rec.attempts} tries left.`);
      }
      rec.code = null;
      const user = findUserByPhone(phone) || createUser(phone, body.name);
      return issueSession(user);
    }

    function demoLogin(body) {
      if (!devMode) throw notFound('Route');
      const phone = normPhone(body.phone);
      const user = findUserByPhone(phone) || createUser(phone, body.name);
      return issueSession(user);
    }

    function logout(token) { delete store.sessions[token]; return { ok: true }; }

    function updateMe(user, body) {
      if (body.name != null) user.name = cleanName(body.name, user.phone);
      return userView(user);
    }

    function ratingOf(p) { return p.ratingCount ? round1(p.ratingSum / p.ratingCount) : null; }

    function providerView(p) {
      if (!p) return null;
      const v = VILLAGES.find((x) => x.id === p.villageId);
      return {
        type: p.type, skills: p.skills.slice(), villageId: p.villageId, village: v ? { id: v.id, en: v.en, hi: v.hi } : null,
        radiusKm: p.radiusKm, vehicle: p.vehicle || '', verified: p.verified, suspended: p.suspended,
        online: p.online, strikes: p.strikes, rating: ratingOf(p), ratingCount: p.ratingCount, jobsDone: p.jobsDone,
      };
    }

    function userView(u) {
      return { id: u.id, phone: u.phone, name: u.name, dues: u.dues, isAdmin: isAdmin(u), provider: providerView(store.providers[u.id]) };
    }

    // ---- providers

    function registerProvider(user, body) {
      const existing = store.providers[user.id];
      const type = existing ? existing.type : body.type;
      const service = SERVICES[type];
      if (!service) throw bad('BAD_SERVICE', 'Choose what you offer: tractor, farm work, mechanic, or experienced farmer.');
      if (existing && body.type && body.type !== existing.type) {
        throw conflict('TYPE_LOCKED', 'Service type cannot be changed. Contact support to switch.');
      }
      const skills = Array.isArray(body.skills) ? Array.from(new Set(body.skills)) : [];
      if (!skills.length) throw bad('BAD_SKILLS', 'Pick at least one type of work you can do.');
      for (const s of skills) if (!service.tasks[s]) throw bad('BAD_SKILLS', `Unknown work type: ${s}.`);
      const village = getVillage(body.villageId);
      const radiusKm = body.radiusKm == null ? service.radiusKm : Number(body.radiusKm);
      if (!Number.isFinite(radiusKm) || radiusKm < 1 || radiusKm > service.radiusKm) {
        throw bad('BAD_RADIUS', `Travel distance must be between 1 and ${service.radiusKm} km.`);
      }
      const vehicle = String(body.vehicle || '').trim().slice(0, 60);
      if (type === 'tractor' && !vehicle) throw bad('BAD_VEHICLE', 'Enter your tractor model and number, e.g. "Mahindra 575, UP53 AB 1234".');
      if (body.name) user.name = cleanName(body.name, user.phone);
      const p = existing || {
        userId: user.id, type, verified: false, suspended: false, online: true,
        strikes: 0, ratingSum: 0, ratingCount: 0, jobsDone: 0, createdAt: now(),
      };
      Object.assign(p, { skills, villageId: village.id, lat: village.lat, lng: village.lng, radiusKm, vehicle });
      store.providers[user.id] = p;
      return userView(user);
    }

    function requireProvider(user) {
      const p = store.providers[user.id];
      if (!p) throw forbidden('Register as a service provider first.');
      return p;
    }

    function setOnline(user, body) {
      const p = requireProvider(user);
      p.online = !!body.online;
      return providerView(p);
    }

    function activeAssignments(b) { return b.assignments.filter((a) => a.status === 'active'); }
    function isAssigned(b, userId) { return activeAssignments(b).some((a) => a.providerId === userId); }

    function providerBusy(p, date, slot, exceptBookingId) {
      return Object.values(store.bookings).some((b) =>
        b.id !== exceptBookingId && ACTIVE.has(b.status) && b.date === date &&
        slotsOverlap(b.slot, slot) && isAssigned(b, p.userId));
    }

    // Returns null when the provider may take the booking, else a reason string.
    function whyCannotTake(p, b, opts2) {
      const o = opts2 || {};
      if (p.type !== b.service) return 'This job needs a different service.';
      if (!p.skills.includes(b.task)) return 'You have not listed this type of work.';
      if (!p.verified) return 'Your profile is waiting for verification.';
      if (p.suspended) return 'Your account is suspended. Contact support.';
      if (p.userId === b.customerId) return 'You cannot take your own booking.';
      const v = getVillage(b.villageId);
      const d = haversineKm(p, v);
      if (d > Math.min(p.radiusKm, SERVICES[b.service].radiusKm)) return 'This field is outside your travel distance.';
      if (!o.ignoreBusy && providerBusy(p, b.date, b.slot, b.id)) return 'You already have a job at this time.';
      return null;
    }

    function candidates(serviceId, taskId, villageId, date, slot, customerId) {
      const fake = { id: '__quote__', service: serviceId, task: taskId, villageId, date, slot, customerId };
      const v = getVillage(villageId);
      return Object.values(store.providers)
        .filter((p) => p.online && !whyCannotTake(p, fake))
        .map((p) => ({ p, km: haversineKm(p, v) }))
        .sort((a, b) => a.km - b.km);
    }

    // ---- booking

    function validateWhen(date, slot) {
      if (!SLOTS[slot]) throw bad('BAD_SLOT', 'Choose a time: morning, afternoon or full day.');
      if (!validDate(date)) throw bad('BAD_DATE', 'Choose a valid date.');
      const t = now();
      const last = addDays(todayIST(t), RULES.bookingHorizonDays);
      if (date > last) throw bad('BAD_DATE', `You can book up to ${RULES.bookingHorizonDays} days ahead.`);
      if (istTime(date, SLOTS[slot].start) <= t) throw bad('BAD_DATE', 'This time has already started or passed. Pick a later slot.');
    }

    function quote(user, body) {
      const { service, task } = getTask(body.service, body.task);
      validateWhen(body.date, body.slot);
      const qty = validateQuantity(task, body.slot, body.quantity);
      getVillage(body.villageId);
      const c = candidates(body.service, body.task, body.villageId, body.date, body.slot, user && user.id);
      const km = c.length ? c[0].km : RULES.assumedTravelKm;
      const price = computePrice(body.service, body.task, qty, body.slot, km, user ? user.dues : 0);
      const needed = service.multi ? qty : 1;
      return {
        price, availableProviders: c.length, needed,
        travelEstimated: !!service.travel && !c.length,
        warning: c.length === 0 ? 'No provider is free nearby right now. You can still book; we will alert providers as they come online.'
          : c.length < needed ? `Only ${c.length} of ${needed} workers are free nearby right now. The rest may join later.` : null,
        billable: !!task.billable,
      };
    }

    function createBooking(user, body) {
      const q = quote(user, body);
      const active = Object.values(store.bookings).filter((b) => b.customerId === user.id && ACTIVE.has(b.status));
      if (active.length >= RULES.maxActiveBookings) {
        throw conflict('TOO_MANY_BOOKINGS', `You already have ${RULES.maxActiveBookings} open bookings. Finish or cancel one first.`);
      }
      const dup = active.find((b) => b.service === body.service && b.task === body.task && b.date === body.date &&
        b.villageId === body.villageId && slotsOverlap(b.slot, body.slot));
      if (dup) throw conflict('DUPLICATE_BOOKING', `You already booked this work for this time (${dup.id}).`);
      const b = {
        id: nextId('B'), customerId: user.id, service: body.service, task: body.task,
        date: body.date, slot: body.slot, quantity: q.price.quantity, needed: q.needed,
        villageId: body.villageId, landmark: String(body.landmark || '').trim().slice(0, 120),
        notes: String(body.notes || '').trim().slice(0, 300),
        assignments: [], status: 'requested', pin: digits(4), pinFailures: 0, pinLockedUntil: 0,
        price: q.price, createdAt: now(), history: [], rescheduleCount: 0,
        rating: null, dispute: null, cancel: null, startedAt: null, completedAt: null,
      };
      // Dues from an earlier late cancellation are collected with this booking.
      user.dues = 0;
      log(b, 'requested', q.availableProviders ? `Sent to ${q.availableProviders} nearby provider${q.availableProviders > 1 ? 's' : ''}` : 'Waiting for providers');
      store.bookings[b.id] = b;
      return bookingView(b, user);
    }

    function getBooking(id) {
      const b = store.bookings[id];
      if (!b) throw notFound('Booking');
      return b;
    }

    function canSee(b, user) { return b.customerId === user.id || isAssigned(b, user.id) || isAdmin(user); }

    function viewBooking(user, id) {
      const b = getBooking(id);
      if (!canSee(b, user)) {
        const p = store.providers[user.id];
        if (p && b.status === 'requested' && !whyCannotTake(p, b)) return offerView(b, p);
        throw forbidden();
      }
      return bookingView(b, user);
    }

    function myBookings(user) {
      return Object.values(store.bookings).filter((b) => b.customerId === user.id)
        .sort((a, b) => b.createdAt - a.createdAt).map((b) => bookingView(b, user));
    }

    function restoreDues(b) {
      if (b.price.dues) store.users[b.customerId].dues += b.price.dues;
    }

    function strike(p, reason) {
      p.strikes += 1;
      if (p.strikes >= RULES.maxStrikes) p.suspended = true;
      return reason;
    }

    function cancelBooking(user, id, body) {
      const b = getBooking(id);
      if (b.customerId !== user.id && !isAdmin(user)) throw forbidden('Only the person who booked can cancel.');
      if (!['requested', 'confirmed'].includes(b.status)) throw conflict('BAD_STATE', `A ${b.status.replace('_', ' ')} booking cannot be cancelled.`);
      const t = now();
      const start = slotStart(b);
      const assigned = activeAssignments(b);
      let fee = 0, note;
      if (assigned.length && t > start + RULES.noShowGraceHours * HOUR) {
        for (const a of assigned) strike(store.providers[a.providerId], 'no_show');
        note = 'Provider did not arrive; cancelled free';
      } else if (assigned.length && start - t < RULES.lateWindowHours * HOUR && !isAdmin(user)) {
        fee = RULES.cancelFeePerProvider * assigned.length;
        note = `Late cancellation fee ₹${fee}, added to your next booking`;
      } else {
        note = 'Cancelled free';
      }
      restoreDues(b);
      store.users[b.customerId].dues += fee;
      b.cancel = { by: user.id, at: t, reason: String((body && body.reason) || '').slice(0, 200), fee };
      for (const a of assigned) a.status = 'released';
      log(b, 'cancelled', note);
      return bookingView(b, user);
    }

    function rescheduleBooking(user, id, body) {
      const b = getBooking(id);
      if (b.customerId !== user.id) throw forbidden('Only the person who booked can change the date.');
      if (!['requested', 'confirmed'].includes(b.status)) throw conflict('BAD_STATE', 'Only a booking that has not started can be moved.');
      if (b.rescheduleCount >= 1) throw conflict('RESCHEDULE_LIMIT', 'A booking can be moved only once. Cancel and book again instead.');
      validateWhen(body.date, body.slot);
      const { task } = getTask(b.service, b.task);
      validateQuantity(task, body.slot, b.quantity);
      if (body.date === b.date && body.slot === b.slot) throw bad('SAME_TIME', 'Pick a different date or time.');
      b.date = body.date; b.slot = body.slot; b.rescheduleCount += 1;
      const dues = b.price.dues;
      b.price = computePrice(b.service, b.task, b.quantity, b.slot, b.price.travelKm, dues);
      let released = 0;
      for (const a of activeAssignments(b)) {
        if (providerBusy(store.providers[a.providerId], b.date, b.slot, b.id)) { a.status = 'released'; released++; }
      }
      const filled = activeAssignments(b).length;
      log(b, filled >= b.needed ? 'confirmed' : 'requested',
        `Moved to ${b.date}, ${SLOTS[b.slot].en}` + (released ? `; ${released} provider(s) not free, finding replacements` : ''));
      return bookingView(b, user);
    }

    function acceptBooking(user, id) {
      const p = requireProvider(user);
      const b = getBooking(id);
      if (isAssigned(b, user.id)) throw conflict('ALREADY_ACCEPTED', 'You have already accepted this job.');
      if (b.status !== 'requested') throw conflict('NOT_OPEN', 'This job is no longer open. Another provider may have taken it.');
      const why = whyCannotTake(p, b);
      if (why) throw conflict('CANNOT_TAKE', why);
      const prior = b.assignments.find((a) => a.providerId === user.id);
      if (prior && prior.status === 'withdrawn') throw conflict('WITHDREW', 'You withdrew from this job earlier and cannot rejoin.');
      if (prior) prior.status = 'active'; else b.assignments.push({ providerId: user.id, status: 'active', at: now() });
      const filled = activeAssignments(b).length;
      if (filled >= b.needed) log(b, 'confirmed', `${user.name} accepted`);
      else b.history.push({ at: now(), status: 'requested', note: `${user.name} accepted (${filled}/${b.needed})` });
      return bookingView(b, user);
    }

    function withdrawBooking(user, id) {
      const p = requireProvider(user);
      const b = getBooking(id);
      const a = b.assignments.find((x) => x.providerId === user.id && x.status === 'active');
      if (!a || !['requested', 'confirmed'].includes(b.status)) throw conflict('BAD_STATE', 'You can only withdraw from a job you accepted that has not started.');
      a.status = 'withdrawn';
      const late = slotStart(b) - now() < RULES.lateWindowHours * HOUR;
      if (late) strike(p, 'late_withdraw');
      log(b, 'requested', `${user.name} withdrew${late ? ' (late: 1 strike)' : ''}; finding a replacement`);
      return { ok: true, strikes: p.strikes, suspended: p.suspended };
    }

    function startBooking(user, id, body) {
      const b = getBooking(id);
      if (!isAssigned(b, user.id)) throw forbidden('Only a provider on this job can start it.');
      const assigned = activeAssignments(b);
      const partial = b.status === 'requested' && assigned.length > 0 && SERVICES[b.service].multi;
      if (b.status !== 'confirmed' && !partial) throw conflict('BAD_STATE', 'This job cannot be started now.');
      const t = now();
      if (t < slotStart(b) - RULES.earlyStartHours * HOUR) throw conflict('TOO_EARLY', 'You can start the job from one hour before the booked time.');
      if (t < b.pinLockedUntil) throw new AppError(429, 'PIN_LOCKED', 'Too many wrong PINs. Try again in 15 minutes.');
      if (String((body && body.pin) || '').trim() !== b.pin) {
        b.pinFailures += 1;
        if (b.pinFailures >= RULES.maxPinFailures) { b.pinFailures = 0; b.pinLockedUntil = t + RULES.pinLockMinutes * MIN; }
        throw bad('PIN_WRONG', 'Wrong PIN. Ask the customer for the 4-digit start PIN.');
      }
      if (partial) {
        // Start with the workers who came; the price follows the actual headcount.
        b.quantity = assigned.length; b.needed = assigned.length;
        b.price = computePrice(b.service, b.task, b.quantity, b.slot, b.price.travelKm, b.price.dues);
      }
      b.startedAt = t;
      log(b, 'in_progress', partial ? `Started with ${assigned.length} worker(s)` : 'Work started');
      return bookingView(b, user);
    }

    function completeBooking(user, id, body) {
      body = body || {};
      const b = getBooking(id);
      if (!isAssigned(b, user.id)) throw forbidden('Only a provider on this job can complete it.');
      if (b.status !== 'in_progress') throw conflict('BAD_STATE', 'Start the job with the customer PIN first.');
      const { task } = getTask(b.service, b.task);
      const unit = UNITS[task.unit];
      let qty = b.quantity, extra = 0;
      if (unit.adjustable && body.quantity != null) {
        qty = Number(body.quantity);
        if (!Number.isFinite(qty) || qty < unit.step || qty > b.quantity * 2) {
          throw bad('BAD_QUANTITY', `Actual work must be between ${unit.step} and ${b.quantity * 2} ${unit.en}.`);
        }
        qty = Math.round(qty / unit.step) * unit.step;
      }
      if (task.billable && body.extra != null) {
        extra = Number(body.extra);
        if (!Number.isInteger(extra) || extra < 0 || extra > 50000) throw bad('BAD_EXTRA', 'Parts and labour must be a whole amount between ₹0 and ₹50,000.');
      }
      b.quantity = qty;
      b.price = computePrice(b.service, b.task, qty, b.slot, b.price.travelKm, b.price.dues, extra);
      b.completedAt = now();
      for (const a of activeAssignments(b)) store.providers[a.providerId].jobsDone += 1;
      log(b, 'completed', `Done. Collect ₹${b.price.total} in cash or UPI`);
      return bookingView(b, user);
    }

    function rateBooking(user, id, body) {
      const b = getBooking(id);
      if (b.customerId !== user.id) throw forbidden('Only the customer can rate.');
      if (b.status !== 'completed' && b.status !== 'disputed') throw conflict('BAD_STATE', 'You can rate after the work is completed.');
      if (b.rating) throw conflict('ALREADY_RATED', 'You have already rated this job.');
      const stars = Number(body && body.stars);
      if (!Number.isInteger(stars) || stars < 1 || stars > 5) throw bad('BAD_RATING', 'Give 1 to 5 stars.');
      b.rating = { stars, comment: String(body.comment || '').trim().slice(0, 300), at: now() };
      for (const a of activeAssignments(b)) {
        const p = store.providers[a.providerId];
        p.ratingSum += stars; p.ratingCount += 1;
      }
      return bookingView(b, user);
    }

    function disputeBooking(user, id, body) {
      const b = getBooking(id);
      if (b.customerId !== user.id) throw forbidden('Only the customer can raise a complaint.');
      if (b.status !== 'completed') throw conflict('BAD_STATE', 'You can raise a complaint only on completed work.');
      if (now() - b.completedAt > RULES.disputeWindowHours * HOUR) throw conflict('DISPUTE_WINDOW', 'Complaints must be raised within 48 hours of completion.');
      const reason = String((body && body.reason) || '').trim();
      if (reason.length < 5) throw bad('BAD_REASON', 'Tell us what went wrong (at least 5 characters).');
      b.dispute = { reason: reason.slice(0, 500), at: now(), resolution: null };
      log(b, 'disputed', 'Complaint raised');
      return bookingView(b, user);
    }

    // ---- provider views

    function payoutShare(b) { return Math.round(b.price.providerPayout / Math.max(1, b.needed)); }

    function providerJobs(user) {
      const p = requireProvider(user);
      const offers = p.online && p.verified && !p.suspended
        ? Object.values(store.bookings)
          .filter((b) => b.status === 'requested' && !b.assignments.some((a) => a.providerId === user.id) && !whyCannotTake(p, b))
          .sort((a, b) => slotStart(a) - slotStart(b)).map((b) => offerView(b, p))
        : [];
      const mine = Object.values(store.bookings).filter((b) => isAssigned(b, user.id))
        .sort((a, b) => slotStart(b) - slotStart(a)).map((b) => bookingView(b, user));
      const earnings = mine.filter((b) => b.status === 'completed' || b.status === 'disputed')
        .reduce((s, b) => s + b.payoutShare, 0);
      return { provider: providerView(p), offers, jobs: mine, earnings };
    }

    function offerView(b, p) {
      const v = getVillage(b.villageId);
      const c = store.users[b.customerId];
      return {
        id: b.id, offer: true, service: b.service, task: b.task, date: b.date, slot: b.slot, quantity: b.quantity,
        needed: b.needed, filled: activeAssignments(b).length, village: { id: v.id, en: v.en, hi: v.hi },
        landmark: b.landmark, notes: b.notes, distanceKm: round1(haversineKm(p, v)), payoutShare: payoutShare(b),
        customerName: c ? c.name.split(' ')[0] : '', status: b.status,
      };
    }

    function bookingView(b, viewer) {
      const v = getVillage(b.villageId);
      const c = store.users[b.customerId];
      const isCustomer = viewer && viewer.id === b.customerId;
      const privileged = viewer && (isAssigned(b, viewer.id) || isAdmin(viewer));
      const providers = activeAssignments(b).map((a) => {
        const u = store.users[a.providerId], p = store.providers[a.providerId];
        return { id: u.id, name: u.name, phone: u.phone, vehicle: p.vehicle || '', rating: ratingOf(p), jobsDone: p.jobsDone, distanceKm: round1(haversineKm(p, v)) };
      });
      return {
        id: b.id, service: b.service, task: b.task, date: b.date, slot: b.slot, quantity: b.quantity,
        needed: b.needed, filled: providers.length, village: { id: v.id, en: v.en, hi: v.hi },
        landmark: b.landmark, notes: b.notes, status: b.status, price: b.price, payoutShare: payoutShare(b),
        history: b.history, rescheduleCount: b.rescheduleCount, rating: b.rating, dispute: b.dispute, cancel: b.cancel,
        createdAt: b.createdAt, startsAt: slotStart(b), endsAt: slotEnd(b), completedAt: b.completedAt,
        pin: isCustomer ? b.pin : undefined,
        providers: isCustomer || privileged ? providers : undefined,
        customer: privileged ? { name: c.name, phone: c.phone } : undefined,
        noShow: ['requested', 'confirmed'].includes(b.status) && providers.length > 0 && now() > slotStart(b) + RULES.noShowGraceHours * HOUR,
        lateCancelFee: ['requested', 'confirmed'].includes(b.status) && providers.length > 0 &&
          slotStart(b) - now() < RULES.lateWindowHours * HOUR && now() <= slotStart(b) + RULES.noShowGraceHours * HOUR
          ? RULES.cancelFeePerProvider * providers.length : 0,
      };
    }

    // ---- admin

    function requireAdmin(user) { if (!isAdmin(user)) throw forbidden('Admins only.'); }

    function adminOverview(user) {
      requireAdmin(user);
      const bookings = Object.values(store.bookings);
      const byStatus = {};
      for (const b of bookings) byStatus[b.status] = (byStatus[b.status] || 0) + 1;
      const done = bookings.filter((b) => b.status === 'completed' || b.status === 'disputed');
      const closed = bookings.filter((b) => !ACTIVE.has(b.status));
      const filled = closed.filter((b) => b.startedAt);
      const providers = Object.values(store.providers).map((p) => Object.assign({ id: p.userId, name: store.users[p.userId].name, phone: store.users[p.userId].phone }, providerView(p)));
      const byService = {};
      for (const b of bookings) byService[b.service] = (byService[b.service] || 0) + 1;
      return {
        totals: {
          users: Object.keys(store.users).length, providers: providers.length, bookings: bookings.length,
          gmv: done.reduce((s, b) => s + b.price.total, 0),
          platformRevenue: done.reduce((s, b) => s + b.price.platformFee, 0),
          fillRate: closed.length ? Math.round((filled.length / closed.length) * 100) : null,
        },
        byStatus, byService,
        pendingProviders: providers.filter((p) => !p.verified),
        suspendedProviders: providers.filter((p) => p.suspended),
        disputes: bookings.filter((b) => b.status === 'disputed').map((b) => bookingView(b, user)),
        recent: bookings.sort((a, b) => b.createdAt - a.createdAt).slice(0, 15).map((b) => bookingView(b, user)),
      };
    }

    function adminVerify(user, id, body) {
      requireAdmin(user);
      const p = store.providers[id];
      if (!p) throw notFound('Provider');
      if (body.verified != null) p.verified = !!body.verified;
      if (body.suspended != null) { p.suspended = !!body.suspended; if (!p.suspended) p.strikes = 0; }
      return providerView(p);
    }

    function adminResolve(user, id, body) {
      requireAdmin(user);
      const b = getBooking(id);
      if (b.status !== 'disputed') throw conflict('BAD_STATE', 'This booking has no open complaint.');
      const refund = Number(body.refund || 0);
      if (!Number.isInteger(refund) || refund < 0 || refund > b.price.total) throw bad('BAD_REFUND', `Refund must be a whole amount from ₹0 to ₹${b.price.total}.`);
      b.dispute.resolution = { refund, note: String(body.note || '').slice(0, 300), at: now(), by: user.id };
      log(b, 'completed', refund ? `Complaint resolved: ₹${refund} refunded` : 'Complaint resolved: no refund');
      return bookingView(b, user);
    }

    // ---- housekeeping: run before every request (lazy, so no cron is needed)

    function sweep() {
      const t = now();
      for (const b of Object.values(store.bookings)) {
        if (b.status === 'requested') {
          const n = activeAssignments(b).length;
          if (n === 0 && t > slotStart(b) + RULES.noShowGraceHours * HOUR) { restoreDues(b); log(b, 'expired', 'No provider accepted in time'); }
          else if (n > 0 && t > slotEnd(b)) { restoreDues(b); log(b, 'expired', 'Not started before the slot ended'); }
        } else if (b.status === 'confirmed' && t > slotEnd(b) + 6 * HOUR) {
          restoreDues(b); log(b, 'expired', 'Never started');
        }
      }
      for (const [k, s] of Object.entries(store.sessions)) if (t > s.expiresAt) delete store.sessions[k];
    }

    // ---- router

    const routes = [];
    const route = (method, pattern, auth, fn) => routes.push({ method, re: new RegExp('^' + pattern.replace(/:(\w+)/g, '(?<$1>[^/]+)') + '$'), auth, fn });

    route('GET', '/api/health', false, () => ({ ok: true, mode: devMode ? 'demo' : 'live', time: now() }));
    route('GET', '/api/catalog', false, () => ({ services: SERVICES, slots: SLOTS, units: UNITS, villages: VILLAGES, rules: RULES, today: todayIST(now()) }));
    route('GET', '/api/villages/nearest', false, (c) => nearestVillage(Number(c.query.lat), Number(c.query.lng)));
    route('POST', '/api/auth/otp', false, (c) => requestOtp(c.body));
    route('POST', '/api/auth/verify', false, (c) => verifyOtp(c.body));
    route('POST', '/api/auth/demo', false, (c) => demoLogin(c.body));
    route('POST', '/api/auth/logout', true, (c) => logout(c.token));
    route('GET', '/api/me', true, (c) => userView(c.user));
    route('PATCH', '/api/me', true, (c) => updateMe(c.user, c.body));
    route('POST', '/api/quote', true, (c) => quote(c.user, c.body));
    route('POST', '/api/bookings', true, (c) => createBooking(c.user, c.body));
    route('GET', '/api/bookings', true, (c) => myBookings(c.user));
    route('GET', '/api/bookings/:id', true, (c) => viewBooking(c.user, c.params.id));
    route('POST', '/api/bookings/:id/cancel', true, (c) => cancelBooking(c.user, c.params.id, c.body));
    route('POST', '/api/bookings/:id/reschedule', true, (c) => rescheduleBooking(c.user, c.params.id, c.body));
    route('POST', '/api/bookings/:id/accept', true, (c) => acceptBooking(c.user, c.params.id));
    route('POST', '/api/bookings/:id/withdraw', true, (c) => withdrawBooking(c.user, c.params.id));
    route('POST', '/api/bookings/:id/start', true, (c) => startBooking(c.user, c.params.id, c.body));
    route('POST', '/api/bookings/:id/complete', true, (c) => completeBooking(c.user, c.params.id, c.body));
    route('POST', '/api/bookings/:id/rate', true, (c) => rateBooking(c.user, c.params.id, c.body));
    route('POST', '/api/bookings/:id/dispute', true, (c) => disputeBooking(c.user, c.params.id, c.body));
    route('POST', '/api/provider', true, (c) => registerProvider(c.user, c.body));
    route('POST', '/api/provider/online', true, (c) => setOnline(c.user, c.body));
    route('GET', '/api/provider/jobs', true, (c) => providerJobs(c.user));
    route('GET', '/api/admin/overview', true, (c) => adminOverview(c.user));
    route('POST', '/api/admin/providers/:id', true, (c) => adminVerify(c.user, c.params.id, c.body));
    route('POST', '/api/admin/bookings/:id/resolve', true, (c) => adminResolve(c.user, c.params.id, c.body));

    function handle(method, url, body, token) {
      try {
        const [path, qs] = String(url).split('?');
        const query = {};
        if (qs) for (const part of qs.split('&')) { const [k, v] = part.split('='); query[decodeURIComponent(k)] = decodeURIComponent(v || ''); }
        let pathMatched = false;
        for (const r of routes) {
          const m = path.match(r.re);
          if (!m) continue;
          pathMatched = true;
          if (r.method !== method) continue;
          sweep();
          const user = authUser(token);
          if (r.auth && !user) throw new AppError(401, 'UNAUTHORIZED', 'Please log in again.');
          const data = r.fn({ body: body && typeof body === 'object' ? body : {}, params: m.groups || {}, query, user, token });
          return { status: 200, body: data };
        }
        if (pathMatched) throw new AppError(405, 'METHOD_NOT_ALLOWED', 'Method not allowed.');
        throw notFound('Route');
      } catch (e) {
        if (e instanceof AppError) return { status: e.status, body: { error: { code: e.code, message: e.message } } };
        if (opts.onError) opts.onError(e);
        return { status: 500, body: { error: { code: 'INTERNAL', message: 'Something went wrong. Please try again.' } } };
      }
    }

    return { store, handle, sweep, isDevMode: () => devMode };
  }

  // -------------------------------------------------------------- demo seed

  // Seeds a believable pilot: providers across the cluster plus sample bookings,
  // so the hosted demo opens in a working state. Synthetic people only.
  function seedDemo(app, t) {
    const call = (m, p, b, tok) => {
      const r = app.handle(m, p, b, tok);
      if (r.status !== 200) throw new Error(`seed ${m} ${p}: ${JSON.stringify(r.body)}`);
      return r.body;
    };
    const login = (phone, name) => call('POST', '/api/auth/demo', { phone, name }).token;
    const admin = login('9999999999', 'KhetSaathi Ops');
    const provs = [
      ['9811100001', 'Ramesh Yadav', 'tractor', ['plough', 'rotavator', 'sowing', 'trolley'], 'pipraich', 'Mahindra 575 DI, UP53 AT 4411'],
      ['9811100002', 'Sunil Nishad', 'tractor', ['plough', 'harvester', 'trolley'], 'bhathat', 'Swaraj 744, UP53 BK 2290'],
      ['9811100003', 'Harish Maurya', 'tractor', ['plough', 'sowing', 'rotavator'], 'sahjanwa', 'Sonalika DI 745, UP53 CF 7781'],
      ['9811100011', 'Geeta Devi', 'labour', ['weeding', 'transplanting', 'harvesting', 'general'], 'jungle', ''],
      ['9811100012', 'Rajkumar Paswan', 'labour', ['irrigation', 'spraying', 'general', 'weeding'], 'jungle', ''],
      ['9811100013', 'Sita Nishad', 'labour', ['transplanting', 'weeding', 'harvesting'], 'pipraich', ''],
      ['9811100014', 'Mohan Chauhan', 'labour', ['harvesting', 'irrigation', 'general', 'spraying'], 'bhathat', ''],
      ['9811100015', 'Phool Kumari', 'labour', ['weeding', 'general', 'transplanting'], 'khorabar', ''],
      ['9811100021', 'Anil Vishwakarma', 'mechanic', ['tractor_repair', 'pump_repair', 'equipment_repair'], 'gkp', ''],
      ['9811100022', 'Salim Ansari', 'mechanic', ['pump_repair', 'equipment_repair'], 'chauri', ''],
      ['9811100031', 'Ram Prasad Singh', 'farmer', ['field_manager', 'crop_advice'], 'jungle', ''],
      ['9811100032', 'Kamla Devi', 'farmer', ['crop_advice', 'field_manager'], 'campierganj', ''],
    ];
    const tokens = {};
    for (const [phone, name, type, skills, villageId, vehicle] of provs) {
      tokens[phone] = login(phone, name);
      const me = call('POST', '/api/provider', { type, skills, villageId, vehicle }, tokens[phone]);
      call('POST', `/api/admin/providers/${me.id}`, { verified: true }, admin);
    }
    // One unverified applicant waiting in the admin queue.
    const pending = login('9811100041', 'Deepak Gupta');
    call('POST', '/api/provider', { type: 'tractor', skills: ['plough', 'trolley'], villageId: 'khorabar', vehicle: 'Eicher 380, UP53 DD 1001' }, pending);

    const cust = login('9876543210', 'Vinod Tiwari');
    const today = todayIST(t);
    const d1 = addDays(today, 1), d2 = addDays(today, 2), d3 = addDays(today, 4);
    const b1 = call('POST', '/api/bookings', { service: 'tractor', task: 'plough', date: d1, slot: 'morning', quantity: 3, villageId: 'jungle', landmark: 'Behind the primary school, near the tube well' }, cust);
    call('POST', `/api/bookings/${b1.id}/accept`, {}, tokens['9811100001']);
    const b2 = call('POST', '/api/bookings', { service: 'labour', task: 'transplanting', date: d2, slot: 'full', quantity: 4, villageId: 'jungle', notes: 'Paddy nursery is ready, 2 bigha' }, cust);
    call('POST', `/api/bookings/${b2.id}/accept`, {}, tokens['9811100011']);
    call('POST', `/api/bookings/${b2.id}/accept`, {}, tokens['9811100013']);
    call('POST', '/api/bookings', { service: 'mechanic', task: 'pump_repair', date: d1, slot: 'afternoon', villageId: 'jungle', notes: 'Diesel pump not starting' }, cust);
    call('POST', '/api/bookings', { service: 'farmer', task: 'crop_advice', date: d3, slot: 'morning', villageId: 'jungle', notes: 'Yellow leaves on wheat' }, cust);
    return { adminPhone: '9999999999', customerPhone: '9876543210' };
  }

  return {
    createApp, createEmptyStore, seedDemo, computePrice, maxQuantity, normPhone, haversineKm,
    todayIST, addDays, istTime, SERVICES, SLOTS, UNITS, VILLAGES, RULES, AppError,
  };
});
