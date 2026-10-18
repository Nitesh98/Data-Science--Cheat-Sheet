/*
 * Motion engine for reels.
 *
 * Every frame is a PURE FUNCTION OF TIME: render(t) positions everything for second `t`.
 * That makes renders deterministic and lets us capture frames in any order, in parallel.
 *
 *   M.P(t, start, dur, ease)   progress 0..1 of an animation that starts at `start`
 *   M.set(el, {x,y,s,r,o,blur}) transform / opacity / blur in one call
 *   M.cue(t, 'hit')            schedule a sound effect (rendered by sfx.py)
 *   M.boot({duration, render, mood})  wire everything up for the renderer
 */
(function () {
  const M = (window.M = {});

  // ---------------------------------------------------------------- maths
  M.clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
  M.lerp = (a, b, t) => a + (b - a) * t;

  // ------------------------------------------------------------- easings
  const c1 = 1.70158, c3 = c1 + 1, c4 = (2 * Math.PI) / 3;
  M.E = {
    lin: t => t,
    inCubic: t => t * t * t,
    outCubic: t => 1 - Math.pow(1 - t, 3),
    outQuart: t => 1 - Math.pow(1 - t, 4),
    inOutCubic: t => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2),
    outExpo: t => (t === 1 ? 1 : 1 - Math.pow(2, -10 * t)),
    inExpo: t => (t === 0 ? 0 : Math.pow(2, 10 * t - 10)),
    outBack: t => 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2),
    outElastic: t => (t === 0 ? 0 : t === 1 ? 1 : Math.pow(2, -10 * t) * Math.sin((t * 10 - 0.75) * c4) + 1),
    // damped spring that overshoots then settles (k = stiffness-ish)
    spring: t => 1 - Math.exp(-7 * t) * Math.cos(11 * t),
  };
  /** Progress of an animation: 0 before `s`, 1 after `s+d`, eased in between. */
  M.P = (t, s, d, e) => (e || M.E.outCubic)(M.clamp((t - s) / d));
  /** 1 while t is inside [a,b], fading in/out over `f` seconds at each end. */
  M.win = (t, a, b, f = 0.3) => M.clamp((t - a) / f) * M.clamp((b - t) / f);

  // ------------------------------------------------------- random & colour
  M.rng = seed => () => {            // mulberry32: tiny seeded PRNG
    seed |= 0; seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  M.rgb = hex => [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16));
  M.mix = (a, b, t) => {
    const A = M.rgb(a), B = M.rgb(b);
    return `rgb(${A.map((v, i) => Math.round(M.lerp(v, B[i], t))).join(",")})`;
  };
  M.rgba = (hex, a) => `rgba(${M.rgb(hex).join(",")},${a})`;

  // ------------------------------------------------------------- elements
  /** Apply transform/opacity/filter in one go. Unset keys keep neutral defaults. */
  M.set = (el, o) => {
    const { x = 0, y = 0, s = 1, sx = s, sy = s, r = 0, skx = 0, o: op = 1, blur = 0 } = o;
    el.style.transform = `translate3d(${x}px,${y}px,0) rotate(${r}deg) skewX(${skx}deg) scale(${sx},${sy})`;
    el.style.opacity = op;
    el.style.filter = blur > 0.05 ? `blur(${blur}px)` : "none";
  };
  /** Left-to-right wipe reveal (0..1). */
  M.reveal = (el, p) => { el.style.clipPath = `inset(-10% ${(1 - p) * 100}% -10% 0)`; };
  /** Split an element's text into inline-block letter spans; returns them. */
  M.chars = (el, text) => {
    el.innerHTML = [...text].map(c => `<span class="ch">${c === " " ? "&nbsp;" : c}</span>`).join("");
    return [...el.children];
  };
  /** Decaying camera shake: returns [dx, dy] px for an impact at t0. */
  M.shake = (t, t0, amp = 16, dur = 0.5) => {
    const u = (t - t0) / dur;
    if (u < 0 || u > 1) return [0, 0];
    const d = amp * Math.pow(1 - u, 2);
    return [Math.sin(t * 97.3) * d, Math.cos(t * 81.9) * d * 0.8];
  };
  /** RGB-split glitch offset in px (0 outside the glitch windows). */
  M.glitch = (t, windows, amp = 9) => {
    for (const [a, b] of windows) if (t >= a && t <= b) return Math.sin(t * 160) * amp * (0.4 + 0.6 * Math.abs(Math.sin(t * 47)));
    return 0;
  };
  M.fmt = (v, d = 2) => (v < 0 ? "−" : "+") + Math.abs(v).toFixed(d);

  // ----------------------------------------------------------- sound cues
  M.cues = [];
  M.cue = (t, type, v) => M.cues.push({ t, type, v });

  // ------------------------------------------------ aurora + grain backdrop
  // `mood` = [{t, c:[hex,hex,hex]}, ...] keyframes; colours blend between them.
  function makeBackground(mood) {
    const bg = document.getElementById("bg"), grain = document.getElementById("grain");
    const ctx = bg.getContext("2d"), gx = grain.getContext("2d");
    const tile = document.createElement("canvas"); tile.width = tile.height = 256;
    const tctx = tile.getContext("2d"), img = tctx.createImageData(256, 256), R = M.rng(99);
    for (let i = 0; i < img.data.length; i += 4) { const v = (R() * 255) | 0; img.data[i] = img.data[i + 1] = img.data[i + 2] = v; img.data[i + 3] = 255; }
    tctx.putImageData(img, 0, 0);
    const pat = gx.createPattern(tile, "repeat");
    const orbs = [
      { x: 0.2, y: 0.18, r: 0.75, ph: 0.0, sx: 0.35, sy: 0.25, ci: 0 },
      { x: 0.85, y: 0.42, r: 0.7, ph: 2.1, sx: 0.3, sy: 0.35, ci: 1 },
      { x: 0.3, y: 0.85, r: 0.8, ph: 4.2, sx: 0.4, sy: 0.3, ci: 2 },
    ];
    return function draw(t) {
      let a = mood[0], b = mood[0], k = 0;                 // find surrounding mood keyframes
      for (let i = 0; i < mood.length; i++) {
        if (t >= mood[i].t) { a = mood[i]; b = mood[Math.min(i + 1, mood.length - 1)]; }
      }
      if (b.t > a.t) k = M.E.inOutCubic(M.clamp((t - a.t) / Math.min(1.2, b.t - a.t)));
      const W = bg.width, H = bg.height;
      ctx.globalCompositeOperation = "source-over";
      ctx.fillStyle = "#090912"; ctx.fillRect(0, 0, W, H);
      ctx.globalCompositeOperation = "lighter";
      for (const o of orbs) {
        const cx = (o.x + Math.sin(t * o.sx + o.ph) * 0.18) * W, cy = (o.y + Math.cos(t * o.sy + o.ph) * 0.12) * H;
        const rad = o.r * W * (1 + 0.06 * Math.sin(t * 1.3 + o.ph));
        const col = M.mix(a.c[o.ci], b.c[o.ci], k);
        const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, rad);
        g.addColorStop(0, col.replace("rgb", "rgba").replace(")", ",0.42)"));
        g.addColorStop(1, col.replace("rgb", "rgba").replace(")", ",0)"));
        ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
      }
      // film grain: shift the noise tile by a hash of the frame number
      const f = Math.floor(t * 30), ox = (f * 97) % 256, oy = (f * 61) % 256;
      gx.clearRect(0, 0, grain.width, grain.height);
      gx.save(); gx.translate(-ox, -oy); gx.globalAlpha = 0.07; gx.fillStyle = pat;
      gx.fillRect(0, 0, grain.width + 256, grain.height + 256); gx.restore();
    };
  }

  // ----------------------------------------------------------------- boot
  M.boot = ({ duration, render, mood }) => {
    const drawBg = makeBackground(mood);
    window.DURATION = duration;
    window.CUES = M.cues;
    window.seek = t => {
      drawBg(t);
      render(t);
      const bar = document.getElementById("prog-fill");
      if (bar) bar.style.transform = `scaleX(${M.clamp(t / duration)})`;
    };
    Promise.all(["700 10px 'Space Grotesk'", "500 10px 'Space Grotesk'", "800 10px Inter", "500 10px Inter",
      "700 10px 'JetBrains Mono'", "500 10px 'JetBrains Mono'"].map(f => document.fonts.load(f)))
      .then(() => document.fonts.ready).then(() => { window.seek(0); window.READY = true; });
  };
})();
