/*
 * Reel 01 -- "Your data is lying" (Simpson's paradox).  25 seconds, 1080x1920.
 *
 *   0.0  hook: kinetic type slams in, glitch on LYING
 *   3.5  chart: 40 campaigns pop in -> the average line says "more spend = fewer sales"
 *  10.0  split by region -> every group's own line slopes UP
 *  15.3  the name, and the hidden-variable diagram
 *  20.6  call to action
 */
(() => {
  const { E, P, win, lerp, clamp, set, mix, fmt } = M;
  const $ = s => document.querySelector(s);
  const $$ = s => [...document.querySelectorAll(s)];
  const D = DATA, DUR = 25.0, NEUTRAL = "#E9E7FF", VIO = "#9A7CFF", CY = "#38E1FF", LIE = "#FF4D6D", TRUTH = "#B6FF3C", AMBER = "#FFC247";
  const NS = "http://www.w3.org/2000/svg";
  const el = (tag, attrs, parent) => { const n = document.createElementNS(NS, tag); for (const k in attrs) n.setAttribute(k, attrs[k]); parent.appendChild(n); return n; };

  // ------------------------------------------------------------ mood (background colours)
  const mood = [
    { t: 0, c: ["#6A4CFF", "#FF3D8B", "#1FB8FF"] }, { t: 3.4, c: ["#3B4CFF", "#6A4CFF", "#1FB8FF"] },
    { t: 7.6, c: ["#FF2D55", "#8A1C4C", "#FF7A3D"] }, { t: 11.2, c: ["#2BE3A0", "#1FB8FF", "#6A4CFF"] },
    { t: 15.2, c: ["#FFB020", "#9A5CFF", "#FF3D8B"] }, { t: 20.4, c: ["#6A4CFF", "#FF3D8B", "#1FB8FF"] },
  ];

  // ------------------------------------------------------------ sound cues
  [[0.36, "hit", .8], [0.62, "hit", .7], [1.38, "hit", 1.25], [2.15, "tick", .5], [3.05, "whoosh", .55],
   [3.75, "whoosh", .25], [6.8, "riser", .4], [7.92, "buzz", .45], [7.92, "hit", 1], [10.3, "whoosh", .4],
   [11.4, "riser", .3], [12.6, "chime", .55], [15.05, "whoosh", .55], [15.5, "hit", 1], [17.6, "whoosh", .3],
   [18.4, "pop", 1.2], [19.1, "chime", .35], [20.3, "whoosh", .55], [21.4, "hit", .9], [21.7, "hit", .9],
   [22.0, "hit", .9], [22.3, "hit", 1.1], [23.3, "pop", 1], [23.7, "pop", 1.3]].forEach(([t, ty, v]) => M.cue(t, ty, v));
  for (let t = 7.0; t < 7.9; t += 0.11) M.cue(t, "tick", .3);
  for (let t = 11.6; t < 12.6; t += 0.14) M.cue(t, "tick", .25);

  // ------------------------------------------------------------ chart construction
  const gridG = $("#grid"), axesG = $("#axes"), dotsG = $("#dots"), linesG = $("#lines"), labelsG = $("#labels");
  [5, 10, 15, 20].forEach(v => el("line", { x1: D.X(0), x2: D.X(10), y1: D.Y(v), y2: D.Y(v), stroke: "rgba(255,255,255,.09)", "stroke-width": 2, "stroke-dasharray": "6 10" }, gridG));
  const axX = el("path", { d: `M${D.X(0)} ${D.Y(0)}H${D.X(10)}`, stroke: "#F4F3FF", "stroke-width": 5, "stroke-linecap": "round", fill: "none", pathLength: 1, "stroke-dasharray": 1 }, axesG);
  const axY = el("path", { d: `M${D.X(0)} ${D.Y(0)}V${D.Y(20)}`, stroke: "#F4F3FF", "stroke-width": 5, "stroke-linecap": "round", fill: "none", pathLength: 1, "stroke-dasharray": 1 }, axesG);
  const labY = el("text", { x: D.X(0), y: D.Y(20) - 22, fill: "#9B98B8", "font-family": "JetBrains Mono", "font-weight": 700, "font-size": 29, "letter-spacing": 2 }, labelsG); labY.textContent = "SALES";
  const labX = el("text", { x: D.X(10), y: D.Y(0) + 56, fill: "#9B98B8", "font-family": "JetBrains Mono", "font-weight": 700, "font-size": 29, "letter-spacing": 2, "text-anchor": "end" }, labelsG); labX.textContent = "AD SPEND";

  const R = M.rng(3);
  const dots = D.pts.map((p, i) => {
    const c = el("circle", { cx: D.X(p.x), cy: D.Y(p.y), r: 0, fill: NEUTRAL }, dotsG);
    return { c, p, i, delay: 4.2 + R() * 1.6, phase: R() * 6.28 };
  });
  dots.filter((_, i) => i % 2 === 0).forEach(d => M.cue(d.delay, "pop", 0.8 + R() * 0.7));

  const lineAll = el("line", { stroke: LIE, "stroke-width": 11, "stroke-linecap": "round", filter: "url(#glow)" }, linesG);
  const lineG = D.g.map((_, i) => el("line", { stroke: i ? CY : VIO, "stroke-width": 11, "stroke-linecap": "round", filter: "url(#glow)" }, linesG));
  const pos = (f, x) => [D.X(x), D.Y(f.m * x + f.b)];

  // ------------------------------------------------------------ explanation diagram
  const dia = $("#dia");
  const node = (cx, cy, w, label, color) => {
    const g = el("g", {}, dia);
    el("rect", { x: cx - w / 2, y: cy - 58, width: w, height: 116, rx: 58, fill: "rgba(10,8,24,.75)", stroke: color, "stroke-width": 5 }, g);
    const t = el("text", { x: cx, y: cy + 15, fill: color, "text-anchor": "middle", "font-family": "Space Grotesk", "font-weight": 700, "font-size": 46, "letter-spacing": -1 }, g); t.textContent = label;
    return g;
  };
  const ring = el("rect", { x: 375, y: 632, width: 330, height: 116, rx: 58, fill: "none", stroke: AMBER, "stroke-width": 5 }, dia);
  const nR = node(540, 690, 330, "REGION", AMBER), nA = node(250, 1030, 360, "AD SPEND", VIO), nS = node(830, 1030, 310, "SALES", CY);
  const arrow = (x1, y1, x2, y2, color, dash) => {
    const ln = el("line", { x1, y1, x2, y2, stroke: color, "stroke-width": 9, "stroke-linecap": "round", pathLength: 1, "stroke-dasharray": dash || "1 1" }, dia);
    const ang = Math.atan2(y2 - y1, x2 - x1) * 180 / Math.PI;
    const head = el("polygon", { points: "0,0 -30,-17 -30,17", fill: color, transform: `translate(${x2} ${y2}) rotate(${ang})` }, dia);
    return { ln, head, x1, y1, x2, y2 };
  };
  const aRA = arrow(450, 756, 300, 966, AMBER), aRS = arrow(630, 756, 780, 966, AMBER), aAS = arrow(440, 1030, 664, 1030, "#F4F3FF");
  aAS.ln.setAttribute("stroke-dasharray", "22 16"); aAS.ln.removeAttribute("pathLength");
  const real = el("text", { x: 552, y: 1110, fill: TRUTH, "text-anchor": "middle", "font-family": "JetBrains Mono", "font-weight": 700, "font-size": 34, "letter-spacing": 2 }, dia); real.textContent = "REAL EFFECT: +";
  const hid = el("text", { x: 540, y: 560, fill: AMBER, "text-anchor": "middle", "font-family": "JetBrains Mono", "font-weight": 700, "font-size": 30, "letter-spacing": 3 }, dia); hid.textContent = "THE HIDDEN VARIABLE";

  // title letters
  const t1 = M.chars($("#eT1"), "SIMPSON’S"), t2 = M.chars($("#eT2"), "PARADOX");

  // ------------------------------------------------------------ small helpers
  const slam = (e, t, t0, from = 2.4, dur = 0.38, extra = {}) => {
    const p = P(t, t0, dur, E.outExpo);
    set(e, { s: lerp(from, 1, p), o: clamp(p * 4), blur: (1 - p) * 26, ...extra });
  };
  const words = (cap, t, t0, t1, stag = 0.075) => {                // word-by-word pop with fade-out at the end
    const k = win(t, t0, t1, 0.0001) * (1 - P(t, t1 - 0.28, 0.28));
    $$(`${cap} .w`).forEach((w, i) => {
      const p = P(t, t0 + i * stag, 0.4, E.outBack);
      set(w, { y: (1 - p) * 46, s: lerp(0.8, 1, p), o: clamp(p * 3) * (t < t1 ? 1 : k) });
    });
    $(cap).style.visibility = t >= t0 && t <= t1 ? "visible" : "hidden";
  };
  const SHAKES = [[0.36, 10], [0.62, 10], [1.38, 24], [7.92, 22], [12.6, 10], [15.5, 16], [21.4, 9], [21.7, 9], [22.0, 9], [22.3, 14]];

  // ================================================================= RENDER
  function render(t) {
    // camera shake + chip
    let dx = 0, dy = 0;
    for (const [t0, a] of SHAKES) { const [x, y] = M.shake(t, t0, a, 0.55); dx += x; dy += y; }
    set($("#cam"), { x: dx, y: dy });
    set($("#chip"), { o: P(t, 0.25, 0.5), y: (1 - P(t, 0.25, 0.5, E.outBack)) * -30 });

    // ---- wipes between scenes (a gradient bar sweeping across the screen)
    let wo = 0, wx = -1900;
    for (const w0 of [3.05, 14.75, 20.1]) {
      const u = (t - w0) / 0.75;
      if (u >= 0 && u <= 1) { wo = 1; wx = lerp(-1900, 1900, E.inOutCubic(u)); }
    }
    set($("#wipe"), { x: wx, r: 12, o: wo });

    // ---- 1. HOOK ---------------------------------------------------------------------------
    const hookO = 1 - P(t, 2.95, 0.4, E.inCubic);
    set($("#hook"), { o: hookO, s: 1 + 0.18 * (1 - hookO), blur: (1 - hookO) * 16 });
    const [hY, hO] = $$("#hA .w"), [hI, hL] = $$("#hB .w");
    slam(hY, t, 0.36); slam(hO, t, 0.62); slam(hI, t, 1.12, 1.8, 0.3);
    const g = M.glitch(t, [[1.38, 1.65], [2.3, 2.46]], 12);
    slam(hL, t, 1.38, 3.2, 0.32, { skx: g * 0.9 });
    hL.style.textShadow = g ? `${g}px 0 #00F0FF, ${-g}px 0 #FF2DA0` : `0 0 40px rgba(255,77,109,.55)`;
    set($("#hS"), { o: P(t, 2.05, 0.4), y: (1 - P(t, 2.05, 0.6, E.outCubic)) * 30 }); M.reveal($("#hS"), P(t, 2.05, 0.7, E.outCubic));
    // the "lying" trend line: rises confidently, wobbles, RGB-splits on the glitch beats
    const spP = P(t, 1.7, 1.1, E.inOutCubic), sg = M.glitch(t, [[1.38, 1.65], [2.3, 2.46]], 10);
    const spPts = Array.from({ length: 25 }, (_, i) => [90 + i * 37.5, 250 - i * 7.5 - 22 * Math.sin(i * 0.9) + Math.sin(t * 3 + i * 1.3) * 7]);
    const spD = dx_ => "M" + spPts.map(([x, y]) => `${(x + dx_).toFixed(1)} ${y.toFixed(1)}`).join("L");
    [["#spW", 0], ["#spC", sg + 4], ["#spM", -sg - 4]].forEach(([id, o]) => { const e = $(id); e.setAttribute("d", spD(o)); e.setAttribute("stroke-dashoffset", 1 - spP); });
    set($("#spark"), { o: P(t, 1.7, 0.3) });
    $("#hook").style.visibility = hookO > 0.01 ? "visible" : "hidden";

    // ---- 2. CHART --------------------------------------------------------------------------
    const cO = win(t, 3.4, 15.0, 0.35) * (t < 15 ? 1 : 1 - P(t, 14.75, 0.3));
    set($("#chartScene"), { o: cO });
    $("#chartScene").style.visibility = cO > 0.01 ? "visible" : "hidden";
    axX.setAttribute("stroke-dashoffset", 1 - P(t, 3.7, 0.7, E.outCubic));
    axY.setAttribute("stroke-dashoffset", 1 - P(t, 3.8, 0.7, E.outCubic));
    gridG.style.opacity = P(t, 4.0, 0.6); labelsG.style.opacity = P(t, 4.2, 0.5);

    // dots: spring in, recolour as a wave from left to right at 10.5s, gentle float
    for (const d of dots) {
      const pop = P(t, d.delay, 0.55, E.spring), wave = 10.5 + (d.p.x / 10) * 0.9, q = P(t, wave, 0.4, E.inOutCubic);
      const col = M.mix(NEUTRAL, d.p.g ? CY : VIO, q);
      d.c.setAttribute("r", Math.max(0, 12 * pop * (1 + 0.6 * Math.sin(Math.PI * q))));
      d.c.setAttribute("cy", D.Y(d.p.y) + Math.sin(t * 1.6 + d.phase) * 2.2);
      d.c.setAttribute("fill", col); d.c.setAttribute("opacity", clamp(pop * 3) * 0.95);
    }

    // overall (misleading) line: draws 6.9 -> 7.8, thumps at 7.92, dissolves at 10.0
    const pA = P(t, 6.9, 0.9, E.inOutCubic), [ax1, ay1] = pos(D.all, 0.4), [ax2, ay2] = pos(D.all, lerp(0.4, 9.7, pA));
    Object.entries({ x1: ax1, y1: ay1, x2: ax2, y2: ay2 }).forEach(([k, v]) => lineAll.setAttribute(k, v));
    lineAll.setAttribute("stroke-width", 11 + 9 * Math.exp(-(t - 7.92) * 9) * (t > 7.92 ? 1 : 0));
    lineAll.setAttribute("opacity", t < 6.9 ? 0 : 1 - P(t, 10.0, 0.5));

    // group lines
    D.g.forEach((f, i) => {
      const p = P(t, 11.5 + i * 0.2, 0.9, E.inOutCubic), [x1, y1] = pos(f, f.xmin - 0.2), [x2, y2] = pos(f, lerp(f.xmin - 0.2, f.xmax + 0.2, p));
      const L = lineG[i]; L.setAttribute("x1", x1); L.setAttribute("y1", y1); L.setAttribute("x2", x2); L.setAttribute("y2", y2);
      L.setAttribute("opacity", p > 0.001 ? 1 : 0);
    });

    // HUD numbers
    const h1 = win(t, 6.9, 10.4, 0.25) * (t > 10 ? 1 - P(t, 10.0, 0.4) : 1);
    $("#hud1").style.top = "322px"; set($("#hud1"), { o: h1, y: (1 - P(t, 6.9, 0.4, E.outBack)) * 40 });
    $("#hud1n").textContent = "▼ " + fmt(D.all.m * P(t, 7.0, 0.9, E.outCubic));
    const h2 = win(t, 11.5, 15.0, 0.3) * (t < 14.7 ? 1 : 1 - P(t, 14.7, 0.3));
    $("#hud2").style.top = "332px"; set($("#hud2"), { o: h2, y: (1 - P(t, 11.5, 0.4, E.outBack)) * 40 });
    $("#hud2a").textContent = "▲ " + fmt(D.g[0].m * P(t, 11.6, 0.9, E.outCubic));
    $("#hud2b").textContent = "▲ " + fmt(D.g[1].m * P(t, 11.8, 0.9, E.outCubic));

    // captions
    words("#c1", t, 4.5, 6.8); words("#c2", t, 8.0, 10.0); words("#c3", t, 10.2, 12.6); words("#c4", t, 12.8, 14.85);
    const jit = t > 8.0 && t < 10 ? Math.sin(t * 70) * 3 : 0;
    $("#fewer").style.textShadow = `${jit}px 0 #00F0FF, ${-jit}px 0 #FF2DA0`;

    // ---- 3. EXPLANATION --------------------------------------------------------------------
    const eO = win(t, 15.3, 20.5, 0.3) * (t < 20.2 ? 1 : 1 - P(t, 20.2, 0.3));
    set($("#explain"), { o: eO }); $("#explain").style.visibility = eO > 0.01 ? "visible" : "hidden";
    t1.forEach((c, i) => { const p = P(t, 15.55 + i * 0.05, 0.6, E.outElastic); set(c, { y: (1 - p) * -170, o: clamp(p * 6), r: (1 - p) * -8 }); });
    t2.forEach((c, i) => { const p = P(t, 15.95 + i * 0.05, 0.6, E.outElastic); set(c, { y: (1 - p) * -170, o: clamp(p * 6), r: (1 - p) * 8 }); });
    const q = P(t, 16.9, 0.7, E.inOutCubic);
    set($("#eTitle"), { y: -310 * q, s: 1 - 0.45 * q });
    set($("#eSub"), { o: P(t, 16.15, 0.4) * (1 - P(t, 16.8, 0.3)), y: (1 - P(t, 16.15, 0.5)) * 30 });

    const dO = P(t, 17.1, 0.4);
    dia.style.opacity = dO;
    set(nR, { o: 1 }); nR.style.opacity = P(t, 17.1, 0.4); nA.style.opacity = P(t, 17.3, 0.4); nS.style.opacity = P(t, 17.4, 0.4);
    hid.setAttribute("opacity", P(t, 17.3, 0.4));
    const rp = (t * 0.9) % 1;                                   // looping ripple around the hidden variable
    ring.setAttribute("opacity", P(t, 17.4, 0.4) * (1 - rp) * 0.8);
    ring.setAttribute("transform", `translate(540 690) scale(${1 + 0.32 * rp} ${1 + 0.55 * rp}) translate(-540 -690)`);
    for (const [a, t0] of [[aRA, 17.7], [aRS, 17.85]]) { const p = P(t, t0, 0.5, E.outCubic); a.ln.setAttribute("stroke-dashoffset", 1 - p); a.head.setAttribute("opacity", p > 0.95 ? 1 : 0); }
    const pS = P(t, 18.4, 0.5);
    aAS.ln.setAttribute("opacity", pS); aAS.ln.setAttribute("stroke-dashoffset", -t * 40); aAS.head.setAttribute("opacity", pS); real.setAttribute("opacity", pS);

    words("#e1", t, 17.9, 19.6, 0.06); words("#e2", t, 19.6, 20.3, 0.04);

    // ---- 4. CTA ------------------------------------------------------------------------------
    const kO = P(t, 20.4, 0.3);
    set($("#cta"), { o: kO }); $("#cta").style.visibility = kO > 0.01 ? "visible" : "hidden";
    set($("#ctaA"), { o: P(t, 20.7, 0.4), y: (1 - P(t, 20.7, 0.6)) * 30 });
    [["#k1", 21.4], ["#k2", 21.7], ["#k3", 22.0], ["#k4", 22.3]].forEach(([s, t0], i) => slam($(s), t, t0, i === 3 ? 2.8 : 2.3, 0.4));
    [["#p1", 23.3], ["#p2", 23.7]].forEach(([s, t0]) => { const p = P(t, t0, 0.7, E.outElastic); set($(s), { y: (1 - p) * 120, o: clamp(p * 4) }); });
  }

  M.boot({ duration: DUR, render, mood });
})();
