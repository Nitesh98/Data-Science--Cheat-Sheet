/* KhetSaathi web app. Plain JS, no build step.
 * Talks to the server's /api when there is one; otherwise runs core.js inside the
 * browser ("demo mode", saved in localStorage) so the app works as a static page. */
(function () {
  'use strict';
  const K = window.KhetCore;
  const view = document.getElementById('view');

  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const store = {
    get(k, d) { try { const v = localStorage.getItem('ks.' + k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem('ks.' + k, JSON.stringify(v)); } catch (e) { /* storage blocked: stay in memory */ } },
    del(k) { try { localStorage.removeItem('ks.' + k); } catch (e) { /* ignore */ } },
  };
  const navLang = (navigator.language || '').toLowerCase().startsWith('hi') ? 'hi' : 'en';
  const S = { lang: store.get('lang', navLang), token: store.get('token', null), me: null, cat: null, mode: null, liveMode: false, offset: 0, draft: null, ui: {}, quoteSeq: 0 };

  // ------------------------------------------------------------ words

  const W = {
    tagline: ['Farm help, booked from your phone', 'खेती की मदद, फ़ोन से बुक करें'],
    loginLead: ['Tractor, farm workers, mechanic or an experienced farmer at your field. Pay in cash after the work is done.', 'ट्रैक्टर, मज़दूर, मिस्त्री या अनुभवी किसान — आपके खेत पर। काम के बाद नकद भुगतान।'],
    mobile: ['Mobile number', 'मोबाइल नंबर'],
    getOtp: ['Get OTP', 'OTP भेजें'],
    otp: ['6-digit OTP', '6 अंकों का OTP'],
    otpSent: ['OTP sent to', 'OTP भेजा गया'],
    yourName: ['Your name', 'आपका नाम'],
    verify: ['Log in', 'लॉग इन करें'],
    changeNo: ['Change number', 'नंबर बदलें'],
    demoOtp: ['Demo: SMS is not connected, so your OTP is', 'डेमो: SMS जुड़ा नहीं है, आपका OTP है'],
    namaste: ['Namaste', 'नमस्ते'],
    whatNeed: ['What do you need at your field?', 'खेत पर क्या चाहिए?'],
    from: ['from', 'शुरू'],
    myBookings: ['Your bookings', 'आपकी बुकिंग'],
    noBookings: ['No bookings yet. Pick a service above.', 'अभी कोई बुकिंग नहीं। ऊपर से सेवा चुनें।'],
    navBook: ['Book', 'बुक करें'], navBookings: ['Bookings', 'बुकिंग'], navEarn: ['Earn', 'कमाएं'], navAdmin: ['Admin', 'एडमिन'],
    back: ['← Back', '← वापस'],
    work: ['Type of work', 'काम का प्रकार'],
    village: ['Village', 'गाँव'],
    nearMe: ['Use my location', 'मेरी लोकेशन लें'],
    landmark: ['How to find your field', 'खेत कैसे पहुँचें'],
    landmarkPh: ['e.g. behind the school, near the tube well', 'जैसे: स्कूल के पीछे, ट्यूबवेल के पास'],
    date: ['Date', 'तारीख'],
    time: ['Time', 'समय'],
    howMuch: ['How much work', 'कितना काम'],
    notes: ['Anything else?', 'और कुछ?'],
    notesPh: ['Crop, field size, what to bring…', 'फसल, खेत का साइज़, क्या लाना है…'],
    priceTitle: ['Price', 'कीमत'],
    work_: ['Work', 'काम'], travel: ['Travel', 'आने-जाने का'], fee: ['Service fee', 'सेवा शुल्क'], dues: ['Earlier cancellation fee', 'पिछला रद्द शुल्क'], total: ['Total', 'कुल'],
    travelEst: ['estimated', 'अनुमानित'],
    freeNearby: ['free nearby now', 'अभी पास में खाली'],
    payCash: ['Pay in cash or UPI after the work. Price is locked when you book.', 'काम के बाद नकद या UPI से भुगतान। बुकिंग के समय कीमत तय।'],
    visitNote: ['Visit fee only. Parts and repair labour are billed on site.', 'सिर्फ विज़िट फीस। पुर्ज़े और मरम्मत का खर्च मौके पर।'],
    confirmBook: ['Confirm booking', 'बुकिंग पक्की करें'],
    booked: ['Booked. Nearby providers have been alerted.', 'बुक हो गया। पास के लोगों को सूचना भेजी गई।'],
    pinTitle: ['Start PIN', 'शुरू करने का PIN'],
    pinHelp: ['Give this PIN only when the provider is at your field.', 'यह PIN तभी बताएं जब व्यक्ति खेत पर पहुँच जाए।'],
    providers: ['Who is coming', 'कौन आ रहा है'],
    waitingFor: ['Looking for', 'खोज रहे हैं'],
    of: ['of', 'में से'],
    waitingOne: ['Alerting nearby providers. You will see their name and phone here once someone accepts.', 'पास के लोगों को सूचना भेजी है। कोई काम लेगा तो उसका नाम और नंबर यहाँ दिखेगा।'],
    timeline: ['Updates', 'अपडेट'],
    cancel: ['Cancel booking', 'बुकिंग रद्द करें'],
    cancelFree: ['Cancelling now is free.', 'अभी रद्द करना मुफ़्त है।'],
    cancelFee: ['A provider is already on the way to plan your job. Cancelling now costs', 'व्यक्ति ने आपका काम पक्का कर लिया है। अभी रद्द करने पर शुल्क'],
    cancelFeeTail: ['added to your next booking.', 'अगली बुकिंग में जुड़ेगा।'],
    noShow: ['Provider has not arrived 2 hours after start time. You can cancel free.', 'शुरू होने के 2 घंटे बाद भी कोई नहीं आया। आप मुफ़्त में रद्द कर सकते हैं।'],
    yesCancel: ['Yes, cancel', 'हाँ, रद्द करें'], keep: ['Keep booking', 'बुकिंग रखें'],
    move: ['Change date (rain?)', 'तारीख बदलें (बारिश?)'], moveOnce: ['You can change the date once, free.', 'तारीख एक बार मुफ़्त बदल सकते हैं।'], moveBtn: ['Move booking', 'बुकिंग आगे करें'],
    rate: ['Rate the work', 'काम को रेटिंग दें'], rateBtn: ['Submit rating', 'रेटिंग भेजें'], comment: ['Comment (optional)', 'टिप्पणी (वैकल्पिक)'],
    complain: ['Report a problem', 'शिकायत करें'], complainPh: ['What went wrong?', 'क्या गड़बड़ हुई?'], complainBtn: ['Send complaint', 'शिकायत भेजें'],
    customer: ['Customer', 'ग्राहक'], call: ['Call', 'कॉल करें'],
    askPin: ['Ask the customer for the 4-digit PIN', 'ग्राहक से 4 अंकों का PIN लें'], startBtn: ['Start work', 'काम शुरू करें'],
    actualQty: ['Actual work done', 'असल में कितना काम हुआ'], partsBill: ['Parts + repair labour (₹)', 'पुर्ज़े + मरम्मत (₹)'], completeBtn: ['Mark work complete', 'काम पूरा हुआ'],
    collect: ['Collect from customer', 'ग्राहक से लें'], yourShare: ['Your earning', 'आपकी कमाई'],
    withdraw: ['I cannot come', 'मैं नहीं आ पाऊँगा'], withdrawWarn: ['Withdrawing less than 12 hours before start gives you a strike. 3 strikes pause your account.', 'शुरू होने से 12 घंटे से कम पहले मना करने पर 1 स्ट्राइक। 3 स्ट्राइक पर खाता रुकेगा।'], yesWithdraw: ['Yes, withdraw', 'हाँ, मना करें'],
    earnTitle: ['Earn with KhetSaathi', 'KhetSaathi से कमाएं'],
    earnLead: ['Own a tractor, work in fields, repair machines or know farming well? Get jobs from nearby villages.', 'ट्रैक्टर है, खेत में काम करते हैं, मशीन ठीक करते हैं या खेती में माहिर हैं? पास के गाँवों से काम पाएं।'],
    iOffer: ['What do you offer?', 'आप क्या देते हैं?'], iCanDo: ['Work you can do', 'आप कौन-सा काम कर सकते हैं'],
    homeVillage: ['Your village', 'आपका गाँव'], radius: ['How far can you travel (km)', 'कितनी दूर जा सकते हैं (किमी)'],
    vehicle: ['Tractor model and number', 'ट्रैक्टर मॉडल और नंबर'], join: ['Join as provider', 'जुड़ें'], save: ['Save changes', 'बदलाव सेव करें'],
    pendingVerify: ['We are checking your documents. You will start getting jobs once verified (usually within a day).', 'हम आपके कागज़ जाँच रहे हैं। जाँच के बाद काम मिलने लगेगा (आमतौर पर एक दिन में)।'],
    suspended: ['Your account is paused after 3 strikes. Call support to restart.', '3 स्ट्राइक के बाद खाता रुका है। फिर शुरू करने के लिए सपोर्ट को कॉल करें।'],
    online: ['Available for new jobs', 'नए काम के लिए उपलब्ध'],
    offers: ['New jobs near you', 'आपके पास नए काम'], noOffers: ['No new jobs right now. Keep "available" on; new jobs show up here.', 'अभी कोई नया काम नहीं। "उपलब्ध" चालू रखें, नए काम यहाँ दिखेंगे।'],
    offline: ['You are not available. Switch on to see jobs.', 'आप उपलब्ध नहीं हैं। काम देखने के लिए चालू करें।'],
    myJobs: ['Your jobs', 'आपके काम'], accept: ['Accept job', 'काम लें'], accepted: ['Job accepted. Customer details are now visible.', 'काम मिल गया। ग्राहक की जानकारी अब दिखेगी।'],
    rating: ['Rating', 'रेटिंग'], jobsDone: ['Jobs done', 'पूरे काम'], earnings: ['Earned', 'कमाई'], strikes: ['Strikes', 'स्ट्राइक'],
    editProfile: ['Edit profile', 'प्रोफ़ाइल बदलें'], away: ['km away', 'किमी दूर'],
    adminTitle: ['Operations', 'संचालन'], verifyQ: ['Waiting for verification', 'जाँच बाकी'], verifyBtn: ['Verify', 'मंज़ूर करें'],
    suspendedQ: ['Paused providers', 'रुके हुए प्रदाता'], restore: ['Restore', 'फिर चालू करें'],
    disputes: ['Open complaints', 'खुली शिकायतें'], refund: ['Refund ₹', 'वापसी ₹'], resolve: ['Resolve', 'निपटाएं'],
    recent: ['Latest bookings', 'हाल की बुकिंग'], nothing: ['Nothing here.', 'कुछ नहीं।'],
    demoBar: ['Demo', 'डेमो'], tryAs: ['Try as', 'इस रूप में देखें'], jump: ['⏩ Jump to job time', '⏩ काम के समय पर जाएं'], reset: ['Reset demo', 'डेमो रीसेट'],
    demoClock: ['Demo clock', 'डेमो घड़ी'],
    netErr: ['No internet. Check your connection and try again.', 'इंटरनेट नहीं है। कनेक्शन देखें और फिर कोशिश करें।'],
    loggedOut: ['Logged out', 'लॉग आउट हो गए'],
  };
  const t = (k) => (W[k] ? W[k][S.lang === 'hi' ? 1 : 0] : k);
  const nm = (o) => (o ? (S.lang === 'hi' ? o.hi : o.en) : '');
  const STATUS = {
    requested: ['Finding provider', 'व्यक्ति खोज रहे हैं'], confirmed: ['Confirmed', 'पक्का'], in_progress: ['Work in progress', 'काम चालू'],
    completed: ['Completed', 'पूरा'], cancelled: ['Cancelled', 'रद्द'], expired: ['Expired', 'समय निकल गया'], disputed: ['Complaint open', 'शिकायत दर्ज'],
  };
  const pill = (s) => `<span class="pill st-${esc(s)}">${esc(STATUS[s] ? STATUS[s][S.lang === 'hi' ? 1 : 0] : s)}</span>`;
  const rupees = (n) => '₹' + Math.round(n).toLocaleString('en-IN');
  const fmtDate = (d) => new Date(d + 'T00:00:00Z').toLocaleDateString(S.lang === 'hi' ? 'hi-IN' : 'en-IN', { weekday: 'short', day: 'numeric', month: 'short', timeZone: 'UTC' });
  const fmtTime = (ms) => new Date(ms).toLocaleString(S.lang === 'hi' ? 'hi-IN' : 'en-IN', { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit', timeZone: 'Asia/Kolkata' });
  const qtyLabel = (task, q) => {
    const u = K.UNITS[task.unit];
    return task.unit === 'visit' || task.unit === 'day' ? nm(u) : `${q} ${nm(u)}`;
  };

  // ------------------------------------------------------------ backend

  let local = null;
  const now = () => Date.now() + S.offset;

  async function initBackend() {
    try {
      const r = await fetch('api/health', { cache: 'no-store' });
      const j = await r.json();
      if (j && j.ok) { S.mode = 'server'; S.liveMode = j.mode === 'live'; return; }
    } catch (e) { /* no server: static hosting */ }
    S.mode = 'local';
    S.offset = store.get('offset', 0);
    const saved = store.get('store', null);
    local = K.createApp({ store: saved || undefined, now });
    if (!saved) { K.seedDemo(local, now()); saveLocal(); }
  }
  function saveLocal() { if (local) store.set('store', local.store); }

  async function api(method, path, body) {
    let status, data;
    if (S.mode === 'server') {
      let res;
      try {
        res = await fetch(path.replace(/^\//, ''), {
          method, cache: 'no-store',
          headers: Object.assign({ 'Content-Type': 'application/json' }, S.token ? { Authorization: 'Bearer ' + S.token } : {}),
          body: body ? JSON.stringify(body) : undefined,
        });
      } catch (e) { throw Object.assign(new Error(t('netErr')), { code: 'NETWORK' }); }
      status = res.status;
      data = await res.json().catch(() => ({ error: { message: t('netErr') } }));
    } else {
      const out = local.handle(method, path, body ? JSON.parse(JSON.stringify(body)) : {}, S.token);
      status = out.status; data = JSON.parse(JSON.stringify(out.body));
      saveLocal();
    }
    if (status === 401 && S.token) { setToken(null); S.me = null; go('login'); }
    if (status !== 200) throw Object.assign(new Error((data.error && data.error.message) || 'Error'), { code: data.error && data.error.code });
    return data;
  }

  function setToken(tok) { S.token = tok; if (tok) store.set('token', tok); else store.del('token'); }

  // ------------------------------------------------------------ ui helpers

  let toastTimer;
  function toast(msg) {
    const el = document.getElementById('toast');
    el.textContent = msg; el.hidden = false;
    clearTimeout(toastTimer); toastTimer = setTimeout(() => { el.hidden = true; }, 3200);
  }
  const errBox = (e) => `<div class="note err" role="alert">${esc(e.message || e)}</div>`;
  function go(hash) { if (location.hash === '#' + hash) route(); else location.hash = hash; }
  function busy(btn, on) { if (btn) btn.disabled = on; }

  function renderChrome(active) {
    document.documentElement.lang = S.lang;
    document.getElementById('lang-btn').textContent = S.lang === 'hi' ? 'English' : 'हिंदी';
    document.getElementById('out-btn').hidden = !S.me;
    document.getElementById('out-btn').title = S.lang === 'hi' ? 'लॉग आउट' : 'Log out';
    const nav = document.getElementById('nav');
    nav.hidden = !S.me;
    if (!S.me) return;
    const items = [['home', '🌾', 'navBook'], ['bookings', '📋', 'navBookings'], ['earn', '💰', 'navEarn']];
    if (S.me.isAdmin) items.push(['admin', '📊', 'navAdmin']);
    document.getElementById('nav-in').innerHTML = items.map(([h, ic, k]) =>
      `<a href="#${h}" ${active === h ? 'aria-current="page"' : ''}><span class="ic" aria-hidden="true">${ic}</span>${esc(t(k))}</a>`).join('');
  }

  const DEMO_USERS = [
    ['9876543210', 'Vinod · customer', 'विनोद · ग्राहक'],
    ['9811100001', 'Ramesh · tractor', 'रमेश · ट्रैक्टर'],
    ['9811100011', 'Geeta · farm worker', 'गीता · मज़दूर'],
    ['9811100013', 'Sita · farm worker', 'सीता · मज़दूर'],
    ['9811100021', 'Anil · mechanic', 'अनिल · मिस्त्री'],
    ['9811100031', 'Ram Prasad · farmer', 'राम प्रसाद · किसान'],
    ['9999999999', 'Ops · admin', 'ऑप्स · एडमिन'],
  ];
  function demoBar() {
    if (S.mode === 'server' && S.liveMode) return '';
    const cur = S.me ? S.me.phone : '';
    const opts = DEMO_USERS.map(([p, en, hi]) => `<option value="${p}" ${p === cur ? 'selected' : ''}>${esc(S.lang === 'hi' ? hi : en)}</option>`).join('');
    const localTools = S.mode === 'local'
      ? `<div class="demo-row"><button class="btn ghost sm" data-act="jump" type="button">${t('jump')}</button><button class="btn ghost sm" data-act="reset" type="button">${t('reset')}</button></div>
         <span class="small muted">${t('demoClock')}: <span class="num">${esc(fmtTime(now()))}</span></span>` : '';
    return `<div class="demo"><div class="demo-row"><b>${t('demoBar')}</b><label class="small" for="demo-user">${t('tryAs')}</label>
      <select id="demo-user" data-act="demo-user">${cur && !DEMO_USERS.some((d) => d[0] === cur) ? `<option selected>${esc(S.me.name)}</option>` : ''}${opts}</select></div>${localTools}</div>`;
  }

  // ------------------------------------------------------------ screens

  function screenLogin() {
    const st = S.ui.login || {};
    view.innerHTML = `
      <div class="hero-login">
        <div class="icons-strip" aria-hidden="true"><span>🚜</span><span>👷</span><span>🔧</span><span>👨‍🌾</span></div>
        <h1>${t('tagline')}</h1>
        <p class="muted">${t('loginLead')}</p>
      </div>
      ${st.phone ? `
      <form data-form="verify" class="form" novalidate>
        <p>${t('otpSent')} <b class="num">+91 ${esc(st.phone)}</b></p>
        ${st.devOtp ? `<div class="note info">${t('demoOtp')} <b class="num">${esc(st.devOtp)}</b></div>` : ''}
        <div class="field"><label for="otp">${t('otp')}</label>
          <input id="otp" name="code" class="otp-input" type="text" inputmode="numeric" autocomplete="one-time-code" maxlength="6" required></div>
        ${st.isNewUser ? `<div class="field"><label for="uname">${t('yourName')}</label><input id="uname" name="name" type="text" autocomplete="name" maxlength="40"></div>` : ''}
        <div id="login-err"></div>
        <button class="btn block" type="submit">${t('verify')}</button>
        <button class="btn ghost block" type="button" data-act="change-no">${t('changeNo')}</button>
      </form>` : `
      <form data-form="otp" class="form" novalidate>
        <div class="field"><label for="phone">${t('mobile')}</label>
          <input id="phone" name="phone" type="tel" inputmode="numeric" autocomplete="tel" placeholder="98765 43210" maxlength="14" required></div>
        <div id="login-err"></div>
        <button class="btn block" type="submit">${t('getOtp')}</button>
      </form>`}
      ${demoBar()}`;
    renderChrome('');
  }

  async function screenHome() {
    const [bookings] = await Promise.all([api('GET', '/api/bookings')]);
    const services = Object.entries(S.cat.services).map(([id, s]) => {
      const min = Math.min(...Object.values(s.tasks).map((x) => x.rate * (K.UNITS[x.unit].slotPriced ? K.SLOTS.morning.factor : 1)));
      return `<a class="svc" href="#book-${id}"><span class="emo" aria-hidden="true">${s.icon}</span><h3>${esc(nm(s))}</h3><p>${esc(nm(s.tagline))}</p><span class="from">${t('from')} ${rupees(min)}</span></a>`;
    }).join('');
    const active = bookings.filter((b) => ['requested', 'confirmed', 'in_progress', 'disputed'].includes(b.status));
    view.innerHTML = `
      <div class="hello"><p class="muted">${t('namaste')}, ${esc(S.me.name)}</p><h1>${t('whatNeed')}</h1></div>
      <div class="services">${services}</div>
      ${S.me.dues ? `<div class="note warn">${t('dues')}: <b>${rupees(S.me.dues)}</b></div>` : ''}
      <div class="section"><div class="section-h"><h2>${t('myBookings')}</h2>${bookings.length > active.length ? `<a href="#bookings" class="small">${bookings.length}</a>` : ''}</div>
        <div class="list">${active.length ? active.map(bookingCard).join('') : `<div class="empty">${t('noBookings')}</div>`}</div></div>
      ${demoBar()}`;
    renderChrome('home');
  }

  async function screenBookings() {
    const bookings = await api('GET', '/api/bookings');
    view.innerHTML = `<h1>${t('myBookings')}</h1>
      <div class="list">${bookings.length ? bookings.map(bookingCard).join('') : `<div class="empty">${t('noBookings')}</div>`}</div>${demoBar()}`;
    renderChrome('bookings');
  }

  function bookingCard(b) {
    const s = S.cat.services[b.service], task = s.tasks[b.task];
    const forProvider = b.offer || (b.pin === undefined && !S.me.isAdmin);
    const money = `<span class="price">${rupees(forProvider ? b.payoutShare : b.price.total)}</span>`;
    const crew = b.needed > 1 ? ` · ${b.filled}/${b.needed}` : '';
    return `<a class="card" href="#b-${esc(b.id)}">
      <div class="row"><span class="bk-ic" aria-hidden="true">${s.icon}</span>
        <div class="bk-main"><h3>${esc(nm(task))}</h3><p class="small muted">${esc(fmtDate(b.date))} · ${esc(nm(K.SLOTS[b.slot]))}</p></div>${money}</div>
      <div class="row between wrap"><span class="small muted">📍 ${esc(nm(b.village))}${b.distanceKm != null ? ` · ${b.distanceKm} ${t('away')}` : ''} · ${esc(qtyLabel(task, b.quantity))}${crew}</span>${b.offer ? '' : pill(b.status)}</div></a>`;
  }

  // ---- booking form

  function screenBook(serviceId) {
    const s = S.cat.services[serviceId];
    if (!s) return go('home');
    if (!S.draft || S.draft.service !== serviceId) {
      const tomorrow = K.addDays(S.cat.today, 1);
      S.draft = { service: serviceId, task: Object.keys(s.tasks)[0], villageId: store.get('village', 'jungle'), landmark: store.get('landmark', ''), date: tomorrow, slot: 'morning', quantity: null, notes: '' };
    }
    const d = S.draft, task = s.tasks[d.task], unit = K.UNITS[task.unit];
    const max = K.maxQuantity(task, d.slot);
    if (d.quantity == null || d.quantity < unit.min) d.quantity = task.unit === 'acre' ? 2 : task.unit === 'worker_day' ? 3 : unit.min;
    if (d.quantity > max) d.quantity = max;
    const maxDate = K.addDays(S.cat.today, S.cat.rules.bookingHorizonDays);
    view.innerHTML = `
      <a class="back" href="#home">${t('back')}</a>
      <div class="row"><span class="bk-ic" aria-hidden="true">${s.icon}</span><div><h1>${esc(nm(s))}</h1><p class="small muted">${esc(nm(s.tagline))}</p></div></div>
      <form data-form="book" class="form" novalidate>
        <fieldset class="field" style="border:0;padding:0;margin:0"><legend class="lbl">${t('work')}</legend>
          <div class="choices">${Object.entries(s.tasks).map(([id, x]) => `<label class="choice"><input type="radio" name="task" value="${id}" data-draft ${id === d.task ? 'checked' : ''}><span>${esc(nm(x))}<small>${rupees(x.rate)} / ${esc(nm(K.UNITS[x.unit]).replace(/s$/, ''))}</small></span></label>`).join('')}</div>
        </fieldset>
        <div class="field"><label for="villageId">${t('village')}</label>
          <select id="villageId" name="villageId" data-draft>${S.cat.villages.map((v) => `<option value="${v.id}" ${v.id === d.villageId ? 'selected' : ''}>${esc(nm(v))}</option>`).join('')}</select>
          <button class="btn ghost sm" type="button" data-act="locate" style="align-self:flex-start">📍 ${t('nearMe')}</button></div>
        <div class="field"><label for="landmark">${t('landmark')}</label><input id="landmark" name="landmark" type="text" maxlength="120" value="${esc(d.landmark)}" placeholder="${esc(t('landmarkPh'))}" data-draft></div>
        <div class="field"><label for="date">${t('date')}</label><input id="date" name="date" type="date" min="${S.cat.today}" max="${maxDate}" value="${esc(d.date)}" data-draft></div>
        <fieldset class="field" style="border:0;padding:0;margin:0"><legend class="lbl">${t('time')}</legend>
          <div class="choices">${Object.entries(K.SLOTS).map(([id, x]) => `<label class="choice"><input type="radio" name="slot" value="${id}" data-draft ${id === d.slot ? 'checked' : ''}><span>${esc(nm(x))}</span></label>`).join('')}</div></fieldset>
        ${unit.max > 1 ? `<div class="field"><span class="lbl" id="qty-l">${t('howMuch')}</span>
          <div class="stepper" role="group" aria-labelledby="qty-l"><button type="button" data-act="qty" data-d="-1" aria-label="less" ${d.quantity <= unit.min ? 'disabled' : ''}>−</button>
          <output id="qty-out">${esc(qtyLabel(task, d.quantity))}</output>
          <button type="button" data-act="qty" data-d="1" aria-label="more" ${d.quantity >= max ? 'disabled' : ''}>+</button></div>
          <span class="hint">${unit.perSlotHour ? (S.lang === 'hi' ? `इस समय में अधिकतम ${max} ${nm(unit)}` : `Up to ${max} ${nm(unit)} fit in this time`) : ''}</span></div>` : ''}
        <div class="field"><label for="notes">${t('notes')}</label><textarea id="notes" name="notes" maxlength="300" placeholder="${esc(t('notesPh'))}" data-draft>${esc(d.notes)}</textarea></div>
        <div id="quote" class="quote" aria-live="polite"><span class="muted small">…</span></div>
        <div id="book-err"></div>
        <button class="btn block" type="submit" id="book-btn">${t('confirmBook')}</button>
      </form>`;
    renderChrome('home');
    refreshQuote();
  }

  let quoteTimer;
  function refreshQuote() {
    clearTimeout(quoteTimer);
    quoteTimer = setTimeout(async () => {
      const el = document.getElementById('quote'); if (!el) return;
      const seq = ++S.quoteSeq;
      try {
        const q = await api('POST', '/api/quote', S.draft);
        if (seq !== S.quoteSeq) return; // a newer quote is on its way
        const p = q.price, s = S.cat.services[S.draft.service];
        el.innerHTML = `
          <div class="qline"><span>${t('work_')} · ${esc(qtyLabel(s.tasks[S.draft.task], p.quantity))}${p.slotFactor < 1 ? ' · ½' : ''}</span><span>${rupees(p.base)}</span></div>
          ${s.travel ? `<div class="qline"><span>${t('travel')} · ${p.travelKm} km${q.travelEstimated ? ` (${t('travelEst')})` : ''}</span><span>${rupees(p.travel)}</span></div>` : ''}
          <div class="qline"><span>${t('fee')}</span><span>${rupees(p.platformFee)}</span></div>
          ${p.dues ? `<div class="qline"><span>${t('dues')}</span><span>${rupees(p.dues)}</span></div>` : ''}
          <div class="qline total"><span>${t('total')}</span><span>${rupees(p.total)}</span></div>
          ${q.availableProviders ? `<span class="avail">● ${q.availableProviders} ${t('freeNearby')}</span>` : ''}
          ${q.warning ? `<div class="note warn">${esc(q.warning)}</div>` : ''}
          <span class="small muted">${q.billable ? t('visitNote') + ' ' : ''}${t('payCash')}</span>`;
        document.getElementById('book-btn').disabled = false;
      } catch (e) {
        if (seq !== S.quoteSeq) return;
        el.innerHTML = errBox(e);
        const btn = document.getElementById('book-btn'); if (btn) btn.disabled = true;
      }
    }, 150);
  }

  // ---- booking detail

  async function screenBooking(id) {
    const b = await api('GET', '/api/bookings/' + encodeURIComponent(id));
    const s = S.cat.services[b.service], task = s.tasks[b.task];
    const isCustomer = b.pin !== undefined; // only the customer is ever sent the PIN
    const isProvider = !!(b.providers && b.providers.some((p) => p.id === S.me.id));
    const ui = S.ui[id] || (S.ui[id] = {});
    const back = b.offer || isProvider ? '#earn' : S.me.isAdmin && !isCustomer ? '#admin' : '#bookings';
    let html = `<a class="back" href="${back}">${t('back')}</a>
      <div class="row"><span class="bk-ic" aria-hidden="true">${s.icon}</span><div class="bk-main"><h1>${esc(nm(task))}</h1>
        <p class="muted small">${esc(b.id)} · ${esc(fmtDate(b.date))} · ${esc(nm(K.SLOTS[b.slot]))}</p></div></div>
      <div class="row wrap">${b.offer ? '' : pill(b.status)}${b.needed > 1 ? `<span class="small muted">👷 ${b.filled}/${b.needed}</span>` : ''}</div>`;

    if (b.offer) {
      html += `<div class="card"><dl class="kv">
        <dt>${t('village')}</dt><dd>📍 ${esc(nm(b.village))} · ${b.distanceKm} ${t('away')}</dd>
        ${b.landmark ? `<dt>${t('landmark')}</dt><dd>${esc(b.landmark)}</dd>` : ''}
        <dt>${t('howMuch')}</dt><dd>${esc(qtyLabel(task, b.quantity))}</dd>
        ${b.notes ? `<dt>${t('notes')}</dt><dd>${esc(b.notes)}</dd>` : ''}
        <dt>${t('yourShare')}</dt><dd class="price">${rupees(b.payoutShare)}</dd></dl></div>
        <div id="act-err"></div><button class="btn block" data-act="accept" data-id="${esc(b.id)}" type="button">${t('accept')}</button>`;
      view.innerHTML = html + demoBar();
      return renderChrome('earn');
    }

    if (isCustomer && ['requested', 'confirmed'].includes(b.status)) {
      html += `<div class="pin"><div><span class="small">${t('pinTitle')}</span><p>${t('pinHelp')}</p></div><b class="num">${esc(b.pin)}</b></div>`;
    }
    if (b.noShow && isCustomer) html += `<div class="note warn">${t('noShow')}</div>`;

    // people
    if (b.providers) {
      const people = b.providers.map((p) => `<div class="row between wrap"><div><b>${esc(p.name)}</b> ${p.rating ? `<span class="small">★ ${p.rating}</span>` : ''}
        <p class="small muted">${p.vehicle ? esc(p.vehicle) + ' · ' : ''}${p.jobsDone} ${t('jobsDone').toLowerCase()} · ${p.distanceKm} ${t('away')}</p></div>
        <span><span class="phone">${esc(p.phone)}</span> <a class="btn ghost sm" href="tel:+91${esc(p.phone)}">${t('call')}</a></span></div>`).join('');
      const waiting = b.status === 'requested' && b.filled < b.needed ? `<p class="small muted">${b.needed > 1 ? `${t('waitingFor')} ${b.needed - b.filled} ${t('of')} ${b.needed}…` : t('waitingOne')}</p>` : '';
      if (people || waiting) html += `<div class="card"><h3>${t('providers')}</h3>${people}${waiting}</div>`;
    }
    if (b.customer) {
      html += `<div class="card"><h3>${t('customer')}</h3><div class="row between wrap"><b>${esc(b.customer.name)}</b>
        <span><span class="phone">${esc(b.customer.phone)}</span> <a class="btn ghost sm" href="tel:+91${esc(b.customer.phone)}">${t('call')}</a></span></div>
        <p class="small">📍 ${esc(nm(b.village))}${b.landmark ? ' · ' + esc(b.landmark) : ''}</p>${b.notes ? `<p class="small muted">${esc(b.notes)}</p>` : ''}</div>`;
    } else if (b.landmark || b.notes) {
      html += `<div class="card"><p class="small">📍 ${esc(nm(b.village))}${b.landmark ? ' · ' + esc(b.landmark) : ''}</p>${b.notes ? `<p class="small muted">${esc(b.notes)}</p>` : ''}</div>`;
    }

    // price
    const p = b.price;
    html += `<div class="quote"><div class="qline"><span>${t('work_')} · ${esc(qtyLabel(task, p.quantity))}</span><span>${rupees(p.base)}</span></div>
      ${p.extra ? `<div class="qline"><span>${t('partsBill')}</span><span>${rupees(p.extra)}</span></div>` : ''}
      ${s.travel ? `<div class="qline"><span>${t('travel')} · ${p.travelKm} km</span><span>${rupees(p.travel)}</span></div>` : ''}
      <div class="qline"><span>${t('fee')}</span><span>${rupees(p.platformFee)}</span></div>
      ${p.dues ? `<div class="qline"><span>${t('dues')}</span><span>${rupees(p.dues)}</span></div>` : ''}
      <div class="qline total"><span>${isProvider && b.status === 'completed' ? t('collect') : t('total')}</span><span>${rupees(p.total)}</span></div>
      ${isProvider ? `<div class="qline"><span>${t('yourShare')}</span><span>${rupees(b.payoutShare)}</span></div>` : ''}
      ${b.dispute && b.dispute.resolution ? `<div class="note ok">${t('refund')}${esc(b.dispute.resolution.refund)}</div>` : ''}</div>`;

    html += '<div id="act-err"></div>';

    // actions: provider
    if (isProvider) {
      if (b.status === 'confirmed' || (b.status === 'requested' && b.needed > 1 && b.filled > 0)) {
        html += `<form data-form="start" data-id="${esc(b.id)}" class="card form" novalidate><h3>${t('startBtn')}</h3>
          <div class="field"><label for="pin">${t('askPin')}</label><input id="pin" name="pin" class="otp-input" type="text" inputmode="numeric" maxlength="4" required></div>
          <button class="btn block" type="submit">${t('startBtn')}</button></form>`;
      }
      if (b.status === 'in_progress') {
        const unit = K.UNITS[task.unit];
        html += `<form data-form="complete" data-id="${esc(b.id)}" class="card form" novalidate><h3>${t('completeBtn')}</h3>
          ${unit.adjustable ? `<div class="field"><label for="aqty">${t('actualQty')} (${esc(nm(unit))})</label><input id="aqty" name="quantity" type="number" inputmode="decimal" step="${unit.step}" min="${unit.step}" max="${b.quantity * 2}" value="${b.quantity}"></div>` : ''}
          ${task.billable ? `<div class="field"><label for="extra">${t('partsBill')}</label><input id="extra" name="extra" type="number" inputmode="numeric" min="0" max="50000" step="1" value="0"></div>` : ''}
          <button class="btn block" type="submit">${t('completeBtn')}</button></form>`;
      }
      if (['requested', 'confirmed'].includes(b.status)) {
        html += ui.confirm === 'withdraw'
          ? `<div class="card"><p>${t('withdrawWarn')}</p><div class="btn-row"><button class="btn danger" data-act="withdraw" data-id="${esc(b.id)}" type="button">${t('yesWithdraw')}</button><button class="btn ghost" data-act="ui" data-id="${esc(b.id)}" data-k="confirm" data-v="" type="button">${t('keep')}</button></div></div>`
          : `<button class="btn ghost block" data-act="ui" data-id="${esc(b.id)}" data-k="confirm" data-v="withdraw" type="button">${t('withdraw')}</button>`;
      }
    }

    // actions: customer
    if (isCustomer) {
      if (['requested', 'confirmed'].includes(b.status)) {
        if (ui.confirm === 'cancel') {
          const msg = b.noShow ? t('noShow') : b.lateCancelFee ? `${t('cancelFee')} <b>${rupees(b.lateCancelFee)}</b>, ${t('cancelFeeTail')}` : t('cancelFree');
          html += `<div class="card"><p>${msg}</p><div class="btn-row"><button class="btn danger" data-act="cancel" data-id="${esc(b.id)}" type="button">${t('yesCancel')}</button><button class="btn ghost" data-act="ui" data-id="${esc(b.id)}" data-k="confirm" data-v="" type="button">${t('keep')}</button></div></div>`;
        } else if (ui.confirm === 'move') {
          html += `<form data-form="move" data-id="${esc(b.id)}" class="card form" novalidate><h3>${t('move')}</h3><p class="small muted">${t('moveOnce')}</p>
            <div class="field"><label for="mdate">${t('date')}</label><input id="mdate" name="date" type="date" min="${S.cat.today}" max="${K.addDays(S.cat.today, 30)}" value="${esc(K.addDays(b.date, 1))}"></div>
            <div class="field"><label for="mslot">${t('time')}</label><select id="mslot" name="slot">${Object.entries(K.SLOTS).map(([k, x]) => `<option value="${k}" ${k === b.slot ? 'selected' : ''}>${esc(nm(x))}</option>`).join('')}</select></div>
            <div class="btn-row"><button class="btn" type="submit">${t('moveBtn')}</button><button class="btn ghost" data-act="ui" data-id="${esc(b.id)}" data-k="confirm" data-v="" type="button">${t('keep')}</button></div></form>`;
        } else {
          html += `<div class="btn-row">${b.rescheduleCount < 1 && !b.noShow ? `<button class="btn ghost" data-act="ui" data-id="${esc(b.id)}" data-k="confirm" data-v="move" type="button">${t('move')}</button>` : ''}
            <button class="btn danger" data-act="ui" data-id="${esc(b.id)}" data-k="confirm" data-v="cancel" type="button">${t('cancel')}</button></div>`;
        }
      }
      if ((b.status === 'completed' || b.status === 'disputed') && !b.rating) {
        const st = ui.stars || 0;
        html += `<form data-form="rate" data-id="${esc(b.id)}" class="card form" novalidate><h3>${t('rate')}</h3>
          <div class="stars" role="radiogroup">${[1, 2, 3, 4, 5].map((n) => `<label class="${n <= st ? 'on' : ''}" aria-label="${n}"><input type="radio" name="stars" value="${n}" data-act="star" data-id="${esc(b.id)}" ${n === st ? 'checked' : ''}>★</label>`).join('')}</div>
          <div class="field"><label for="rc">${t('comment')}</label><input id="rc" name="comment" type="text" maxlength="300"></div>
          <button class="btn block" type="submit" ${st ? '' : 'disabled'}>${t('rateBtn')}</button></form>`;
      }
      if (b.rating) html += `<p class="muted">★ ${b.rating.stars}/5 ${b.rating.comment ? '· ' + esc(b.rating.comment) : ''}</p>`;
      if (b.status === 'completed' && !b.dispute && now() - b.completedAt < S.cat.rules.disputeWindowHours * 3600e3) {
        html += ui.confirm === 'complain'
          ? `<form data-form="dispute" data-id="${esc(b.id)}" class="card form" novalidate><h3>${t('complain')}</h3><div class="field"><label for="dr">${t('complainPh')}</label><textarea id="dr" name="reason" maxlength="500" required></textarea></div><button class="btn block" type="submit">${t('complainBtn')}</button></form>`
          : `<button class="btn ghost block" data-act="ui" data-id="${esc(b.id)}" data-k="confirm" data-v="complain" type="button">${t('complain')}</button>`;
      }
    }

    html += `<div class="section"><h3>${t('timeline')}</h3><ol class="timeline">${b.history.slice().reverse().map((h) => `<li>${esc(h.note || h.status)}<time>${esc(fmtTime(h.at))}</time></li>`).join('')}</ol></div>`;
    view.innerHTML = html + demoBar();
    renderChrome(isProvider ? 'earn' : S.me.isAdmin && !isCustomer ? 'admin' : 'bookings');
  }

  // ---- provider

  async function screenEarn() {
    const prov = S.me.provider;
    if (!prov || S.ui.editProfile) return screenJoin(prov);
    const data = await api('GET', '/api/provider/jobs');
    const p = data.provider, s = S.cat.services[p.type];
    const status = p.suspended ? `<div class="note err">${t('suspended')}</div>` : !p.verified ? `<div class="note warn">${t('pendingVerify')}</div>` : '';
    const active = data.jobs.filter((j) => ['requested', 'confirmed', 'in_progress'].includes(j.status));
    const past = data.jobs.filter((j) => !['requested', 'confirmed', 'in_progress'].includes(j.status));
    view.innerHTML = `
      <div class="row"><span class="bk-ic" aria-hidden="true">${s.icon}</span><div class="bk-main"><h1>${esc(S.me.name)}</h1><p class="small muted">${esc(nm(s))} · 📍 ${esc(nm(p.village))} · ${p.radiusKm} km</p></div>
        <button class="btn ghost sm" data-act="edit-profile" type="button">${t('editProfile')}</button></div>
      ${status}
      <div class="tiles"><div class="tile"><div class="k">${t('earnings')}</div><div class="v">${rupees(data.earnings)}</div></div>
        <div class="tile"><div class="k">${t('jobsDone')}</div><div class="v">${p.jobsDone}</div></div>
        <div class="tile"><div class="k">${t('rating')}</div><div class="v">${p.rating ? '★ ' + p.rating : '–'}</div></div>
        <div class="tile"><div class="k">${t('strikes')}</div><div class="v">${p.strikes}/3</div></div></div>
      <label class="switch card" for="online"><input id="online" type="checkbox" data-act="online" ${p.online ? 'checked' : ''}><span><b>${t('online')}</b></span></label>
      ${active.length ? `<div class="section"><h2>${t('myJobs')}</h2><div class="list">${active.map(bookingCard).join('')}</div></div>` : ''}
      <div class="section"><h2>${t('offers')}</h2><div class="list">${!p.online ? `<div class="empty">${t('offline')}</div>` : data.offers.length ? data.offers.map((o) => `${bookingCard(o)}`).join('') : `<div class="empty">${t('noOffers')}</div>`}</div></div>
      ${past.length ? `<div class="section"><h3 class="muted">${S.lang === 'hi' ? 'पुराने काम' : 'Past jobs'}</h3><div class="list">${past.slice(0, 10).map(bookingCard).join('')}</div></div>` : ''}
      ${demoBar()}`;
    renderChrome('earn');
  }

  function screenJoin(prov) {
    const j = S.ui.join || (S.ui.join = prov ? { type: prov.type, skills: prov.skills.slice(), villageId: prov.villageId, radiusKm: prov.radiusKm, vehicle: prov.vehicle } : { type: 'labour', skills: [], villageId: store.get('village', 'jungle'), radiusKm: null, vehicle: '' });
    const s = S.cat.services[j.type];
    view.innerHTML = `
      ${prov ? `<a class="back" href="#earn" data-act="cancel-edit">${t('back')}</a>` : ''}
      <div><h1>${t('earnTitle')}</h1><p class="muted">${t('earnLead')}</p></div>
      <form data-form="join" class="form" novalidate>
        <fieldset class="field" style="border:0;padding:0;margin:0"><legend class="lbl">${t('iOffer')}</legend>
          <div class="services">${Object.entries(S.cat.services).map(([id, x]) => `<label class="choice"><input type="radio" name="type" value="${id}" data-join ${id === j.type ? 'checked' : ''} ${prov && id !== prov.type ? 'disabled' : ''}><span style="height:100%"><span style="font-size:1.6rem">${x.icon}</span><br>${esc(nm(x))}</span></label>`).join('')}</div></fieldset>
        <fieldset class="field" style="border:0;padding:0;margin:0"><legend class="lbl">${t('iCanDo')}</legend>
          <div class="choices">${Object.entries(s.tasks).map(([id, x]) => `<label class="choice"><input type="checkbox" name="skills" value="${id}" data-join ${j.skills.includes(id) ? 'checked' : ''}><span>${esc(nm(x))}</span></label>`).join('')}</div></fieldset>
        <div class="field"><label for="jv">${t('homeVillage')}</label><select id="jv" name="villageId" data-join>${S.cat.villages.map((v) => `<option value="${v.id}" ${v.id === j.villageId ? 'selected' : ''}>${esc(nm(v))}</option>`).join('')}</select></div>
        <div class="field"><label for="jr">${t('radius')}</label><input id="jr" name="radiusKm" type="number" inputmode="numeric" min="1" max="${s.radiusKm}" value="${esc(j.radiusKm || s.radiusKm)}" data-join><span class="hint">1–${s.radiusKm} km</span></div>
        ${j.type === 'tractor' ? `<div class="field"><label for="jveh">${t('vehicle')}</label><input id="jveh" name="vehicle" type="text" maxlength="60" placeholder="Mahindra 575 DI, UP53 AB 1234" value="${esc(j.vehicle)}" data-join></div>` : ''}
        <div id="join-err"></div>
        <button class="btn block" type="submit">${prov ? t('save') : t('join')}</button>
      </form>${demoBar()}`;
    renderChrome('earn');
  }

  // ---- admin

  async function screenAdmin() {
    if (!S.me.isAdmin) return go('home');
    const o = await api('GET', '/api/admin/overview');
    const tl = o.totals;
    const provRow = (p, act, label) => `<div class="card"><div class="row between wrap"><div><b>${esc(p.name)}</b> <span class="phone small">${esc(p.phone)}</span>
      <p class="small muted">${esc(nm(S.cat.services[p.type]))} · ${esc(nm(p.village))}${p.vehicle ? ' · ' + esc(p.vehicle) : ''} · ${p.skills.length} skills</p></div>
      <button class="btn sm" data-act="${act}" data-id="${esc(p.id)}" type="button">${label}</button></div></div>`;
    view.innerHTML = `
      <h1>${t('adminTitle')}</h1>
      <div class="tiles">
        <div class="tile"><div class="k">GMV</div><div class="v">${rupees(tl.gmv)}</div></div>
        <div class="tile"><div class="k">${S.lang === 'hi' ? 'फ़ीस आय' : 'Fee revenue'}</div><div class="v">${rupees(tl.platformRevenue)}</div></div>
        <div class="tile"><div class="k">${S.lang === 'hi' ? 'बुकिंग' : 'Bookings'}</div><div class="v">${tl.bookings}</div></div>
        <div class="tile"><div class="k">${S.lang === 'hi' ? 'भरने की दर' : 'Fill rate'}</div><div class="v">${tl.fillRate == null ? '–' : tl.fillRate + '%'}</div></div>
        <div class="tile"><div class="k">${S.lang === 'hi' ? 'प्रदाता' : 'Providers'}</div><div class="v">${tl.providers}</div></div>
        <div class="tile"><div class="k">${S.lang === 'hi' ? 'उपयोगकर्ता' : 'Users'}</div><div class="v">${tl.users}</div></div></div>
      <div id="act-err"></div>
      <div class="section"><h2>${t('verifyQ')} · ${o.pendingProviders.length}</h2><div class="list">${o.pendingProviders.map((p) => provRow(p, 'verify', t('verifyBtn'))).join('') || `<div class="empty">${t('nothing')}</div>`}</div></div>
      ${o.suspendedProviders.length ? `<div class="section"><h2>${t('suspendedQ')}</h2><div class="list">${o.suspendedProviders.map((p) => provRow(p, 'restore', t('restore'))).join('')}</div></div>` : ''}
      <div class="section"><h2>${t('disputes')} · ${o.disputes.length}</h2><div class="list">${o.disputes.map((b) => `
        <form class="card form" data-form="resolve" data-id="${esc(b.id)}" novalidate><div class="row between"><a href="#b-${esc(b.id)}"><b>${esc(b.id)}</b></a><span class="price">${rupees(b.price.total)}</span></div>
          <p class="small">“${esc(b.dispute.reason)}”</p>
          <div class="row"><label for="rf-${esc(b.id)}" class="small">${t('refund')}</label><input id="rf-${esc(b.id)}" name="refund" type="number" min="0" max="${b.price.total}" value="0" style="max-width:120px"><button class="btn sm" type="submit">${t('resolve')}</button></div></form>`).join('') || `<div class="empty">${t('nothing')}</div>`}</div></div>
      <div class="section"><h2>${t('recent')}</h2><div class="table-wrap"><table><thead><tr><th>ID</th><th>${S.lang === 'hi' ? 'सेवा' : 'Service'}</th><th>${t('date')}</th><th>${t('village')}</th><th>${S.lang === 'hi' ? 'स्थिति' : 'Status'}</th><th>₹</th></tr></thead><tbody>
        ${o.recent.map((b) => `<tr><td><a href="#b-${esc(b.id)}">${esc(b.id)}</a></td><td>${S.cat.services[b.service].icon} ${esc(nm(S.cat.services[b.service].tasks[b.task]))}</td><td>${esc(b.date)}</td><td>${esc(nm(b.village))}</td><td>${pill(b.status)}</td><td>${rupees(b.price.total)}</td></tr>`).join('')}
      </tbody></table></div></div>
      ${demoBar()}`;
    renderChrome('admin');
  }

  // ------------------------------------------------------------ router

  async function route() {
    const h = (location.hash || '#home').slice(1);
    if (!S.me && h !== 'login') {
      if (S.token) { try { S.me = await api('GET', '/api/me'); } catch (e) { S.me = null; } }
      if (!S.me) { if (h !== 'login') { history.replaceState(null, '', '#login'); } return screenLogin(); }
    }
    if (S.me && h === 'login') return go('home');
    try {
      if (h === 'login') return screenLogin();
      if (h === 'bookings') return await screenBookings();
      if (h === 'earn') return await screenEarn();
      if (h === 'admin') return await screenAdmin();
      if (h.startsWith('book-')) return screenBook(h.slice(5));
      if (h.startsWith('b-')) return await screenBooking(h.slice(2));
      return await screenHome();
    } catch (e) {
      view.innerHTML = `${errBox(e)}<a class="btn ghost" href="#home">${t('back')}</a>${demoBar()}`;
    }
  }

  async function refreshMe() { S.me = await api('GET', '/api/me'); }

  // ------------------------------------------------------------ events

  document.addEventListener('click', async (ev) => {
    const el = ev.target.closest('[data-act]');
    if (!el || el.tagName === 'SELECT' || el.type === 'checkbox' || el.type === 'radio') return;
    const act = el.dataset.act, id = el.dataset.id;
    const errEl = document.getElementById('act-err');
    try {
      if (act === 'lang') { S.lang = S.lang === 'hi' ? 'en' : 'hi'; store.set('lang', S.lang); return route(); }
      if (act === 'logout') { try { await api('POST', '/api/auth/logout', {}); } catch (e) { /* already gone */ } setToken(null); S.me = null; S.ui = {}; toast(t('loggedOut')); return go('login'); }
      if (act === 'change-no') { S.ui.login = {}; return screenLogin(); }
      if (act === 'qty') {
        const task = S.cat.services[S.draft.service].tasks[S.draft.task], unit = K.UNITS[task.unit];
        S.draft.quantity = Math.round((S.draft.quantity + Number(el.dataset.d) * unit.step) * 10) / 10;
        return screenBook(S.draft.service);
      }
      if (act === 'locate') {
        if (!navigator.geolocation) throw new Error('Location is not available on this device. Choose your village from the list.');
        navigator.geolocation.getCurrentPosition(async (pos) => {
          try {
            const r = await api('GET', `/api/villages/nearest?lat=${pos.coords.latitude}&lng=${pos.coords.longitude}`);
            S.draft.villageId = r.village.id; screenBook(S.draft.service); toast(`📍 ${nm(r.village)} (${r.distanceKm} km)`);
          } catch (e) { toast(e.message); }
        }, () => toast(S.lang === 'hi' ? 'लोकेशन नहीं मिली। सूची से गाँव चुनें।' : 'Could not get your location. Choose your village from the list.'), { timeout: 8000 });
        return;
      }
      if (act === 'ui') { S.ui[id] = Object.assign(S.ui[id] || {}, { [el.dataset.k]: el.dataset.v || null }); return route(); }
      if (act === 'accept') { busy(el, true); await api('POST', `/api/bookings/${id}/accept`, {}); toast(t('accepted')); return route(); }
      if (act === 'cancel') { busy(el, true); const b = await api('POST', `/api/bookings/${id}/cancel`, { reason: 'customer' }); S.ui[id] = {}; await refreshMe(); toast(b.history[b.history.length - 1].note); return route(); }
      if (act === 'withdraw') { busy(el, true); await api('POST', `/api/bookings/${id}/withdraw`, {}); S.ui[id] = {}; await refreshMe(); return go('earn'); }
      if (act === 'edit-profile') { S.ui.editProfile = true; S.ui.join = null; return route(); }
      if (act === 'cancel-edit') { ev.preventDefault(); S.ui.editProfile = false; S.ui.join = null; return route(); }
      if (act === 'verify' || act === 'restore') { busy(el, true); await api('POST', `/api/admin/providers/${id}`, act === 'verify' ? { verified: true } : { suspended: false }); return route(); }
      if (act === 'jump') {
        const h = location.hash.slice(1);
        if (h.startsWith('b-')) { // on a booking: jump to that booking's start
          const cur = await api('GET', '/api/bookings/' + encodeURIComponent(h.slice(2)));
          if (cur.startsAt > now() && ['requested', 'confirmed'].includes(cur.status)) {
            S.offset += cur.startsAt - now() + 5 * 60e3; store.set('offset', S.offset);
            toast(`⏩ ${fmtTime(now())}`); return route();
          }
        }
        const mine = S.me.provider ? (await api('GET', '/api/provider/jobs')).jobs : [];
        const all = (await api('GET', '/api/bookings')).concat(mine).filter((b) => ['requested', 'confirmed'].includes(b.status) && b.startsAt > now());
        if (!all.length) return toast(S.lang === 'hi' ? 'आगे कोई काम नहीं है।' : 'No upcoming job to jump to.');
        const next = Math.min(...all.map((b) => b.startsAt));
        S.offset += next - now() + 5 * 60e3; store.set('offset', S.offset);
        toast(`⏩ ${fmtTime(now())}`); return route();
      }
      if (act === 'reset') { store.del('store'); store.del('offset'); store.del('token'); location.hash = 'login'; location.reload(); return; }
    } catch (e) {
      busy(el, false);
      if (errEl) errEl.innerHTML = errBox(e); else toast(e.message);
    }
  });

  document.addEventListener('change', async (ev) => {
    const el = ev.target;
    try {
      if (el.dataset.act === 'demo-user') {
        const r = await api('POST', '/api/auth/demo', { phone: el.value });
        setToken(r.token); S.me = r.user; S.ui = {}; S.draft = null;
        return go(r.user.isAdmin ? 'admin' : r.user.provider ? 'earn' : 'home');
      }
      if (el.dataset.act === 'online') { await api('POST', '/api/provider/online', { online: el.checked }); await refreshMe(); return route(); }
      if (el.dataset.act === 'star') { S.ui[el.dataset.id] = Object.assign(S.ui[el.dataset.id] || {}, { stars: Number(el.value) }); return route(); }
      if (el.hasAttribute('data-draft')) {
        const v = el.value;
        S.draft[el.name] = v;
        if (el.name === 'villageId') store.set('village', v);
        if (el.name === 'task' || el.name === 'slot') { if (el.name === 'task') S.draft.quantity = null; return screenBook(S.draft.service); }
        return refreshQuote();
      }
      if (el.hasAttribute('data-join')) {
        const j = S.ui.join;
        if (el.name === 'type') { j.type = el.value; j.skills = []; j.radiusKm = null; return screenJoin(S.me.provider); }
        if (el.name === 'skills') { j.skills = Array.from(document.querySelectorAll('input[name="skills"]:checked')).map((x) => x.value); return; }
        j[el.name] = el.value;
      }
    } catch (e) { toast(e.message); }
  });

  document.addEventListener('input', (ev) => {
    const el = ev.target;
    if (el.hasAttribute('data-draft') && (el.name === 'landmark' || el.name === 'notes')) {
      S.draft[el.name] = el.value;
      if (el.name === 'landmark') store.set('landmark', el.value);
    }
    if (el.hasAttribute('data-join') && el.type !== 'radio' && el.type !== 'checkbox') S.ui.join[el.name] = el.value;
  });

  document.addEventListener('submit', async (ev) => {
    const form = ev.target.closest('[data-form]');
    if (!form) return;
    ev.preventDefault();
    const kind = form.dataset.form, id = form.dataset.id;
    const f = Object.fromEntries(new FormData(form));
    const btn = form.querySelector('[type="submit"]');
    const errEl = form.querySelector('[id$="-err"]') || document.getElementById('act-err');
    busy(btn, true);
    try {
      if (kind === 'otp') {
        const phone = K.normPhone(f.phone);
        const r = await api('POST', '/api/auth/otp', { phone });
        S.ui.login = { phone, devOtp: r.devOtp, isNewUser: r.isNewUser };
        screenLogin();
        const o = document.getElementById('otp'); if (o) o.focus();
        return;
      }
      if (kind === 'verify') {
        const r = await api('POST', '/api/auth/verify', { phone: S.ui.login.phone, code: f.code, name: f.name });
        setToken(r.token); S.me = r.user; S.ui = {};
        return go('home');
      }
      if (kind === 'book') {
        const b = await api('POST', '/api/bookings', S.draft);
        S.draft = null; await refreshMe(); toast(t('booked'));
        return go('b-' + b.id);
      }
      if (kind === 'start') { await api('POST', `/api/bookings/${id}/start`, { pin: f.pin }); return route(); }
      if (kind === 'complete') {
        const body = {};
        if (f.quantity != null) body.quantity = Number(f.quantity);
        if (f.extra != null) body.extra = Number(f.extra);
        const b = await api('POST', `/api/bookings/${id}/complete`, body);
        toast(`${t('collect')}: ${rupees(b.price.total)}`); await refreshMe(); return route();
      }
      if (kind === 'move') { await api('POST', `/api/bookings/${id}/reschedule`, { date: f.date, slot: f.slot }); S.ui[id] = {}; return route(); }
      if (kind === 'rate') { await api('POST', `/api/bookings/${id}/rate`, { stars: Number(f.stars), comment: f.comment }); return route(); }
      if (kind === 'dispute') { await api('POST', `/api/bookings/${id}/dispute`, { reason: f.reason }); S.ui[id] = {}; return route(); }
      if (kind === 'resolve') { await api('POST', `/api/admin/bookings/${id}/resolve`, { refund: Number(f.refund || 0) }); return route(); }
      if (kind === 'join') {
        const j = S.ui.join;
        const r = await api('POST', '/api/provider', { type: j.type, skills: j.skills, villageId: j.villageId, radiusKm: j.radiusKm == null || j.radiusKm === '' ? null : Number(j.radiusKm), vehicle: j.vehicle });
        S.me = r; S.ui.editProfile = false; S.ui.join = null;
        return go('earn');
      }
    } catch (e) {
      if (errEl) errEl.innerHTML = errBox(e); else toast(e.message);
    } finally { busy(btn, false); }
  });

  window.addEventListener('hashchange', route);

  (async function boot() {
    await initBackend();
    try { S.cat = await api('GET', '/api/catalog'); } catch (e) { view.innerHTML = errBox(e); return; }
    route();
  })();
})();
