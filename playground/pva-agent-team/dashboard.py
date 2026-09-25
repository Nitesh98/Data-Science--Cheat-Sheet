"""
Dashboard: one self-contained HTML page from the same tools the agents use.
No LLM, no libraries -- the numbers are exactly what the agents see.

    python3 dashboard.py        # -> out/<date>/dashboard.html (open it in a browser)

Charts: KPI tiles, daily GMV actual vs plan, GMV gap by funnel driver, today's hourly
PvA (category vs the problem slice) + that slice's size availability, weekly trend and
brand table. Light/dark follows your OS; the button toggles it. Every chart has a
"Show data" table underneath.
"""
import json

import action_tools
import config
import pack_tools
import tools


DRIVER_NAMES = {"sessions": "Sessions", "lv_per_session": "List views / session", "pdp_ctr": "PDP click-through",
                "consideration": "Consideration", "checkout": "Checkout", "upt": "Units / order", "asp": "ASP"}


def gather():
    mtd = tools.get_pva("mtd")["rows"][0]
    intr = tools.get_pva("intraday")["rows"][0]
    land = action_tools.month_landing()["category"]
    d_from, d_to, _ = tools._window("mtd")
    act = {r["date"]: r["g"] for r in tools._query(
        "SELECT date, SUM(gmv) g FROM fact_hourly WHERE date BETWEEN ? AND ? GROUP BY date", [d_from, d_to])}
    plan = tools._query("SELECT date, SUM(gmv) g FROM plan_daily WHERE date BETWEEN ? AND ? GROUP BY date ORDER BY date",
                        [d_from, d_to])
    bridge = tools.gmv_bridge("mtd")

    # the worst intraday slice right now (brand x article type)
    worst = tools.merch_health("intraday")["rows"][0]
    slice_f = {"brand": worst["brand"], "article_type": worst["article_type"]}
    cat_h = tools.intraday_by_hour()["hours"]
    sl_h = {h["hour"]: h for h in tools.intraday_by_hour(slice_f)["hours"]}
    size_h = tools.merch_by_hour(**slice_f)["hours"]

    models = {r["brand"]: r["commercial_model"] for r in tools._query("SELECT DISTINCT brand, commercial_model FROM dim_style")}
    brands = [{**r, "model": models[r["brand"]]} for r in tools.brand_table("mtd")]

    m, i = mtd["metrics"], intr["metrics"]
    return {
        "as_of": f"{config.AS_OF_DATE:%d %b %Y}, {config.AS_OF_HOUR:02d}:00",
        "thresholds": {"volume": config.VOLUME_THRESHOLD, "rate": config.RATE_THRESHOLD},
        "hero": {"label": "GMV vs plan, month to date", "pva": m["gmv"]["pva"], "actual": m["gmv"]["actual"],
                 "gap": mtd["gmv_gap_inr"]},
        "tiles": [
            {"label": "Month landing vs MoP", "pva": land["landing_pva"], "note": f"gap {land['gap_to_mop_inr']}", "gap": land["gap_to_mop_inr"]},
            {"label": "GMV today so far", "pva": i["gmv"]["pva"], "gap": intr["gmv_gap_inr"]},
            {"label": "GM, month to date", "pva": m["gm"]["pva"]},
            {"label": "Sessions, month to date", "pva": m["sessions"]["pva"]},
            {"label": "Conversion, month to date", "pva": m["conversion"]["pva"]},
            {"label": "ASP, month to date", "pva": m["asp"]["pva"]},
        ],
        "daily": {"x": [p["date"][5:] for p in plan],
                  "actual": [round(act.get(p["date"], 0)) for p in plan], "plan": [round(p["g"]) for p in plan]},
        "bridge": [{"label": DRIVER_NAMES[d["driver"]], "group": d["group"], "value": d["gmv_impact_inr"]}
                   for d in bridge["detail"]],
        "bridge_total": {"plan": bridge["gmv_plan"], "actual": bridge["gmv_actual"], "gap": bridge["gmv_gap_inr"]},
        "slice_name": f"{worst['brand']} {worst['article_type']}",
        "hourly": {"x": [f"{h['hour']:02d}:00" for h in cat_h],
                   "category": [h["gmv_pva"] for h in cat_h],
                   "slice": [sl_h.get(h["hour"], {}).get("gmv_pva") for h in cat_h]},
        "size": {"x": [f"{h['hour']:02d}:00" for h in size_h], "values": [h["size_availability"] for h in size_h],
                 "target": worst["size_availability_target"]},
        "weekly": pack_tools.weekly_trend()["weeks"],
        "brands": brands,
    }


PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Footwear PvA Dashboard</title>
<style>
:root {
  color-scheme: light;
  --page: #f9f9f7; --surface: #fcfcfb; --ink: #0b0b0b; --ink2: #52514e; --muted: #898781;
  --grid: #e1e0d9; --axis: #c3c2b7; --border: rgba(11,11,11,0.10);
  --s1: #2a78d6; --s2: #eb6834; --neg: #e34948; --pos: #2a78d6; --ref: #898781;
  --good-ink: #006300; --bad-ink: #d03b3b;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    color-scheme: dark;
    --page: #0d0d0d; --surface: #1a1a19; --ink: #ffffff; --ink2: #c3c2b7; --muted: #898781;
    --grid: #2c2c2a; --axis: #383835; --border: rgba(255,255,255,0.10);
    --s1: #3987e5; --s2: #d95926; --neg: #e66767; --pos: #3987e5; --ref: #898781;
    --good-ink: #0ca30c; --bad-ink: #e66767;
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --page: #0d0d0d; --surface: #1a1a19; --ink: #ffffff; --ink2: #c3c2b7; --muted: #898781;
  --grid: #2c2c2a; --axis: #383835; --border: rgba(255,255,255,0.10);
  --s1: #3987e5; --s2: #d95926; --neg: #e66767; --pos: #3987e5; --ref: #898781;
  --good-ink: #0ca30c; --bad-ink: #e66767;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--page); color: var(--ink);
  font: 14px/1.45 system-ui, -apple-system, "Segoe UI", sans-serif; }
main { max-width: 1200px; margin: 0 auto; padding: 24px 16px 48px; }
header { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; flex-wrap: wrap; }
h1 { font-size: 20px; margin: 0; font-weight: 600; }
.sub { color: var(--ink2); margin: 4px 0 0; }
button { font: inherit; color: var(--ink); background: var(--surface); border: 1px solid var(--border);
  border-radius: 8px; padding: 6px 12px; cursor: pointer; }
.grid { display: grid; gap: 16px; margin-top: 16px; }
.kpis { grid-template-columns: minmax(240px, 1.3fr) repeat(3, minmax(0, 1fr)); }
.kpis .hero { grid-row: span 2; display: flex; flex-direction: column; justify-content: center; }
@media (max-width: 760px) {
  .kpis { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .kpis .hero { grid-column: 1 / -1; grid-row: auto; }
  .hero .value { font-size: 48px; }
}
.two { grid-template-columns: repeat(auto-fit, minmax(min(100%, 460px), 1fr)); }
.card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 16px; min-width: 0; }
.card h2 { font-size: 14px; font-weight: 600; margin: 0; }
.card .cap { color: var(--ink2); font-size: 13px; margin: 2px 0 8px; }
.tile .label { color: var(--ink2); font-size: 13px; }
.tile .value { font-size: 26px; font-weight: 600; margin-top: 4px; }
.hero .value { font-size: 52px; line-height: 1.1; }
.delta { font-size: 13px; margin-top: 2px; }
.delta.good { color: var(--good-ink); } .delta.bad { color: var(--bad-ink); }
.legend { display: flex; gap: 16px; flex-wrap: wrap; color: var(--ink2); font-size: 12px; margin-bottom: 4px; }
.legend span { display: inline-flex; align-items: center; gap: 6px; }
.key { width: 16px; height: 2px; border-radius: 1px; display: inline-block; }
.key.box { width: 10px; height: 10px; border-radius: 2px; }
svg { display: block; width: 100%; overflow: visible; }
svg text { fill: var(--muted); font-size: 11px; font-variant-numeric: tabular-nums; }
svg text.lab { fill: var(--ink2); }
details { margin-top: 8px; color: var(--ink2); font-size: 12px; }
summary { cursor: pointer; }
.scroll { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; font-variant-numeric: tabular-nums; font-size: 12px; }
th, td { text-align: right; padding: 6px 8px; border-bottom: 1px solid var(--grid); white-space: nowrap; }
th:first-child, td:first-child, th.l, td.l { text-align: left; }
th { color: var(--ink2); font-weight: 600; }
td.bad { color: var(--bad-ink); }
#tip { position: fixed; pointer-events: none; background: var(--surface); color: var(--ink);
  border: 1px solid var(--border); border-radius: 8px; padding: 8px 10px; font-size: 12px;
  box-shadow: 0 4px 16px rgba(0,0,0,.12); display: none; z-index: 10; min-width: 140px; }
#tip .h { color: var(--ink2); margin-bottom: 4px; }
#tip .row { display: flex; align-items: center; gap: 6px; }
#tip .row b { font-weight: 600; margin-right: 4px; }
.focusable:focus { outline: 2px solid var(--s1); outline-offset: 1px; }
</style>
</head>
<body>
<main>
  <header>
    <div>
      <h1>Men's footwear: plan vs actual</h1>
      <p class="sub" id="asof"></p>
    </div>
    <button id="theme" type="button">Toggle dark mode</button>
  </header>

  <section class="grid kpis" id="kpis"></section>

  <section class="grid two">
    <div class="card"><h2>Daily GMV vs plan</h2><p class="cap">₹ crore, full days, month to date</p>
      <div class="legend"><span><i class="key" style="background:var(--s1)"></i>Actual</span><span><i class="key" style="background:var(--ref)"></i>Plan</span></div>
      <div id="daily"></div><details><summary>Show data</summary><div class="scroll" id="daily-t"></div></details></div>
    <div class="card"><h2>What explains the GMV gap</h2><p class="cap" id="bridge-cap"></p>
      <div class="legend"><span><i class="key box" style="background:var(--neg)"></i>Lost vs plan</span><span><i class="key box" style="background:var(--pos)"></i>Gained vs plan</span></div>
      <div id="bridge"></div><details><summary>Show data</summary><div class="scroll" id="bridge-t"></div></details></div>
  </section>

  <section class="grid two">
    <div class="card"><h2>Today, hour by hour: GMV vs plan</h2><p class="cap" id="hourly-cap"></p>
      <div class="legend" id="hourly-legend"></div>
      <div id="hourly"></div><details><summary>Show data</summary><div class="scroll" id="hourly-t"></div></details></div>
    <div class="card"><h2 id="size-title"></h2><p class="cap">Demand-weighted share of sizes in stock, today (gray line = target)</p>
      <div id="size"></div><details><summary>Show data</summary><div class="scroll" id="size-t"></div></details></div>
  </section>

  <section class="grid">
    <div class="card"><h2>Weekly trend</h2><p class="cap">Plan vs actual by week, month to date</p><div class="scroll" id="weekly"></div></div>
    <div class="card"><h2>Brands</h2><p class="cap">Month to date, biggest GMV shortfall first. Red = below the flag threshold.</p><div class="scroll" id="brands"></div></div>
  </section>
  <p class="sub" style="margin-top:16px;font-size:12px">Synthetic, seeded data. Built by dashboard.py from the same tools the agents use.</p>
</main>
<div id="tip" role="tooltip"></div>
<script id="data" type="application/json">__DATA__</script>
<script>
(function () {
  const D = JSON.parse(document.getElementById("data").textContent);
  const NS = "http://www.w3.org/2000/svg";
  const $ = (id) => document.getElementById(id);
  const el = (tag, attrs, parent) => { const e = document.createElementNS(NS, tag);
    for (const k in attrs) e.setAttribute(k, attrs[k]); if (parent) parent.appendChild(e); return e; };
  const h = (tag, text, cls) => { const e = document.createElement(tag); if (text != null) e.textContent = text; if (cls) e.className = cls; return e; };
  const pct = (v, d = 1) => v == null ? "–" : (v * 100).toFixed(d) + "%";
  const cr = (v) => "₹" + (v / 1e7).toFixed(2) + " Cr";
  const lakh = (v) => (v < 0 ? "−" : "+") + "₹" + Math.abs(v / 1e5).toFixed(1) + " L";
  const money = (v) => Math.abs(v) < 5000 ? "≈ ₹0" : Math.abs(v) >= 1e7 ? (v < 0 ? "−" : "+") + "₹" + Math.abs(v / 1e7).toFixed(2) + " Cr" : lakh(v);

  // theme toggle -- wins over the OS setting both ways
  $("theme").addEventListener("click", () => {
    const dark = document.documentElement.dataset.theme
      ? document.documentElement.dataset.theme === "dark"
      : matchMedia("(prefers-color-scheme: dark)").matches;
    document.documentElement.dataset.theme = dark ? "light" : "dark";
  });

  // ---- tooltip (textContent only: labels are data) ----
  const tip = $("tip");
  function showTip(evt, head, rows) {
    tip.replaceChildren(h("div", head, "h"));
    rows.forEach(([color, name, value]) => {
      const r = h("div", null, "row");
      if (color) { const k = h("i", null, "key"); k.style.background = color; r.appendChild(k); }
      r.appendChild(h("b", value)); r.appendChild(h("span", name)); tip.appendChild(r);
    });
    tip.style.display = "block";
    const x = evt.clientX ?? (evt.target.getBoundingClientRect().left), y = evt.clientY ?? evt.target.getBoundingClientRect().top;
    const w = tip.offsetWidth; tip.style.left = Math.min(x + 12, innerWidth - w - 8) + "px"; tip.style.top = (y + 12) + "px";
  }
  const hideTip = () => { tip.style.display = "none"; };

  function table(target, head, rows, badCols) {
    const t = h("table"), tr = h("tr");
    head.forEach((c) => tr.appendChild(h("th", c))); t.appendChild(h("thead")).appendChild(tr);
    const tb = t.appendChild(h("tbody"));
    rows.forEach((r) => { const row = h("tr"); r.forEach((c, i) => { const td = h("td", c.text ?? c);
      if (c.bad) td.className = "bad"; if (c.l) td.classList.add("l"); row.appendChild(td); }); tb.appendChild(row); });
    target.replaceChildren(t);
  }

  function niceTicks(lo, hi, n) {
    const raw = (hi - lo) / n, mag = Math.pow(10, Math.floor(Math.log10(raw)));
    const step = [1, 2, 2.5, 5, 10].map((k) => k * mag).find((s) => s >= raw);
    const a = Math.floor(lo / step) * step, b = Math.ceil(hi / step) * step, out = [];
    for (let v = a; v <= b + step / 2; v += step) out.push(+v.toFixed(10));
    return out;
  }

  // ---- line chart: one y-axis, crosshair + tooltip ----
  function lineChart(target, { x, series, fmt, tickFmt, ref, yMin, yMax, height = 220 }) {
    const W = Math.max(280, target.clientWidth), H = height, m = { t: 12, r: 64, b: 24, l: 48 };
    const vals = series.flatMap((s) => s.values).filter((v) => v != null).concat(ref != null ? [ref] : []);
    let lo = yMin ?? Math.min(...vals), hi = yMax ?? Math.max(...vals);
    const ticks = niceTicks(yMin ?? lo, yMax ?? hi, 4); lo = ticks[0]; hi = ticks[ticks.length - 1];
    const X = (i) => m.l + (i * (W - m.l - m.r)) / Math.max(1, x.length - 1);
    const Y = (v) => m.t + (1 - (v - lo) / (hi - lo)) * (H - m.t - m.b);
    const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": series.map((s) => s.name).join(" and ") });
    for (const v of ticks) {                  // recessive grid + clean ticks
      const y = Y(v);
      el("line", { x1: m.l, x2: W - m.r, y1: y, y2: y, stroke: "var(--grid)", "stroke-width": 1 }, svg);
      el("text", { x: m.l - 6, y: y + 4, "text-anchor": "end" }, svg).textContent = tickFmt(v);
    }
    const step = Math.ceil(x.length / Math.max(2, Math.floor((W - m.l - m.r) / 60)));   // no colliding x labels
    x.forEach((lab, i) => { if (i % step === 0)
      el("text", { x: X(i), y: H - 6, "text-anchor": "middle" }, svg).textContent = lab; });
    if (ref != null) el("line", { x1: m.l, x2: W - m.r, y1: Y(ref), y2: Y(ref), stroke: "var(--ref)", "stroke-width": 1 }, svg);
    series.forEach((s) => {
      let d = "", pen = false;
      s.values.forEach((v, i) => { if (v == null) { pen = false; return; } d += (pen ? "L" : "M") + X(i) + " " + Y(v); pen = true; });
      el("path", { d, fill: "none", stroke: s.color, "stroke-width": 2, "stroke-linejoin": "round", "stroke-linecap": "round" }, svg);
      const li = s.values.map((v, i) => v == null ? -1 : i).filter((i) => i >= 0).pop();
      el("circle", { cx: X(li), cy: Y(s.values[li]), r: 4, fill: s.color, stroke: "var(--surface)", "stroke-width": 2 }, svg);
      if (s.endLabel) el("text", { x: X(li) + 8, y: Y(s.values[li]) + 4, class: "lab" }, svg).textContent = s.endLabel(s.values[li]);
    });
    const cross = el("line", { y1: m.t, y2: H - m.b, stroke: "var(--axis)", "stroke-width": 1, visibility: "hidden" }, svg);
    const hit = el("rect", { x: m.l, y: m.t, width: W - m.l - m.r, height: H - m.t - m.b, fill: "transparent", tabindex: 0, class: "focusable" }, svg);
    const at = (i, evt) => { cross.setAttribute("x1", X(i)); cross.setAttribute("x2", X(i)); cross.setAttribute("visibility", "visible");
      showTip(evt, x[i], series.map((s) => [s.color, s.name, s.values[i] == null ? "–" : fmt(s.values[i])])); };
    let cur = x.length - 1;
    hit.addEventListener("pointermove", (e) => { const r = svg.getBoundingClientRect();
      const px = ((e.clientX - r.left) / r.width) * W; cur = Math.max(0, Math.min(x.length - 1, Math.round(((px - m.l) / (W - m.l - m.r)) * (x.length - 1)))); at(cur, e); });
    hit.addEventListener("keydown", (e) => { if (e.key === "ArrowLeft") cur = Math.max(0, cur - 1); else if (e.key === "ArrowRight") cur = Math.min(x.length - 1, cur + 1); else return;
      const b = hit.getBoundingClientRect(); at(cur, { clientX: b.left + ((X(cur) - m.l) / (W - m.l - m.r)) * b.width, clientY: b.top }); });
    hit.addEventListener("pointerleave", () => { cross.setAttribute("visibility", "hidden"); hideTip(); });
    hit.addEventListener("blur", () => { cross.setAttribute("visibility", "hidden"); hideTip(); });
    target.replaceChildren(svg);
  }

  // ---- horizontal diverging bars from zero ----
  function divergingBars(target, items) {
    const W = Math.max(280, target.clientWidth), row = 30, lab = W < 480 ? 104 : 160, gut = 72;
    const m = { t: 4, r: gut, b: 4, l: lab + gut };
    const H = m.t + m.b + row * items.length;
    const negMax = Math.max(0, ...items.map((d) => -d.value)), posMax = Math.max(0, ...items.map((d) => d.value));
    const k = (W - m.l - m.r) / ((negMax + posMax) || 1), Z = m.l + negMax * k;
    const S = (v) => v * k;
    const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "GMV gap by funnel driver" });
    el("line", { x1: Z, x2: Z, y1: 0, y2: H, stroke: "var(--axis)", "stroke-width": 1 }, svg);
    items.forEach((d, i) => {
      const y = m.t + i * row + (row - 16) / 2, w = Math.abs(S(d.value)), x0 = d.value < 0 ? Z - w : Z;
      el("text", { x: 0, y: y + 12, class: "lab" }, svg).textContent = d.label;
      const r = 4, bw = Math.max(w, 1), neg = d.value < 0;
      // square at the baseline, 4px rounded at the data end
      const path = neg
        ? `M${Z} ${y} H${x0 + r} Q${x0} ${y} ${x0} ${y + r} V${y + 16 - r} Q${x0} ${y + 16} ${x0 + r} ${y + 16} H${Z} Z`
        : `M${Z} ${y} H${Z + bw - r} Q${Z + bw} ${y} ${Z + bw} ${y + r} V${y + 16 - r} Q${Z + bw} ${y + 16} ${Z + bw - r} ${y + 16} H${Z} Z`;
      const bar = el("path", { d: w < 2 * r ? `M${x0} ${y} h${bw} v16 h${-bw} Z` : path, fill: neg ? "var(--neg)" : "var(--pos)", tabindex: 0, class: "focusable" }, svg);
      el("text", { x: neg ? x0 - 6 : Z + bw + 6, y: y + 12, "text-anchor": neg ? "end" : "start", class: "lab" }, svg).textContent = money(d.value);
      const hitR = el("rect", { x: m.l, y: m.t + i * row, width: W - m.l - m.r, height: row, fill: "transparent" }, svg);
      const on = (e) => { bar.setAttribute("opacity", 0.8); showTip(e, d.label + " (" + d.group + ")", [[null, "vs plan, month to date", money(d.value)]]); };
      const off = () => { bar.setAttribute("opacity", 1); hideTip(); };
      [hitR, bar].forEach((t) => { t.addEventListener("pointermove", on); t.addEventListener("pointerleave", off); });
      bar.addEventListener("focus", (e) => { const b = bar.getBoundingClientRect(); on({ clientX: b.right, clientY: b.top }); });
      bar.addEventListener("blur", off);
    });
    target.replaceChildren(svg);
  }

  // ---- KPI tiles ----
  $("asof").textContent = "As of " + D.as_of + " · MTD = 1st to yesterday · flags: volumes < " +
    pct(D.thresholds.volume.mtd, 0) + " MTD / " + pct(D.thresholds.volume.intraday, 0) + " today";
  const kp = $("kpis");
  const tile = (t, hero) => {
    const c = h("div", null, "card tile" + (hero ? " hero" : ""));
    c.appendChild(h("div", t.label, "label"));
    c.appendChild(h("div", pct(t.pva), "value"));
    const up = t.pva >= 1, d = h("div", (up ? "▲ " : "▼ ") + pct(Math.abs(t.pva - 1)) + (up ? " above" : " below") + " plan"
      + (t.gap != null ? " · " + money(t.gap) : ""), "delta " + (up ? "good" : "bad"));
    c.appendChild(d); return c;
  };
  kp.appendChild(tile(D.hero, true));
  D.tiles.forEach((t) => kp.appendChild(tile(t)));

  function render() {
    lineChart($("daily"), { x: D.daily.x, fmt: cr, tickFmt: (v) => (v / 1e7).toFixed(0), series: [
      { name: "Actual", values: D.daily.actual, color: "var(--s1)", endLabel: (v) => "Actual " + (v / 1e7).toFixed(1) },
      { name: "Plan", values: D.daily.plan, color: "var(--ref)", endLabel: (v) => "Plan " + (v / 1e7).toFixed(1) }] });
    divergingBars($("bridge"), D.bridge);
    lineChart($("hourly"), { x: D.hourly.x, fmt: (v) => pct(v), tickFmt: (v) => pct(v, 0), ref: 1, series: [
      { name: "Category", values: D.hourly.category, color: "var(--s1)", endLabel: (v) => pct(v, 0) },
      { name: D.slice_name, values: D.hourly.slice, color: "var(--s2)", endLabel: (v) => pct(v, 0) }] });
    lineChart($("size"), { x: D.size.x, fmt: (v) => pct(v), tickFmt: (v) => pct(v, 0), ref: D.size.target, yMin: 0, yMax: 1,
      series: [{ name: "Size availability", values: D.size.values, color: "var(--s2)", endLabel: (v) => pct(v, 0) }] });
  }

  $("bridge-cap").textContent = "₹, month to date: plan " + cr(D.bridge_total.plan) + " → actual " + cr(D.bridge_total.actual) +
    " (" + money(D.bridge_total.gap) + "). The bars add up exactly to the gap.";
  $("hourly-cap").textContent = "GMV as % of the hourly plan. Gray line = 100% of plan.";
  const hl = $("hourly-legend");
  [["var(--s1)", "Category"], ["var(--s2)", D.slice_name]].forEach(([c, n]) => { const s = h("span"); const k = h("i", null, "key");
    k.style.background = c; s.appendChild(k); s.appendChild(document.createTextNode(n)); hl.appendChild(s); });
  $("size-title").textContent = "Why: sizes ran out in " + D.slice_name;

  table($("daily-t"), ["Date", "Actual", "Plan", "PvA"], D.daily.x.map((d, i) => [d, cr(D.daily.actual[i]), cr(D.daily.plan[i]), pct(D.daily.actual[i] / D.daily.plan[i])]));
  table($("bridge-t"), ["Driver", "Group", "₹ vs plan"], D.bridge.map((d) => [{ text: d.label, l: 1 }, { text: d.group, l: 1 }, money(d.value)]));
  table($("hourly-t"), ["Hour", "Category", D.slice_name], D.hourly.x.map((x, i) => [x, pct(D.hourly.category[i]), pct(D.hourly.slice[i])]));
  table($("size-t"), ["Hour", "Size availability"], D.size.x.map((x, i) => [x, pct(D.size.values[i])]));
  const vt = D.thresholds.volume.mtd, rt = D.thresholds.rate.mtd;
  table($("weekly"), ["Week", "Days", "GMV", "GMV PvA", "GM PvA", "Sessions PvA", "Conversion PvA", "ASP PvA", "Discount vs plan"],
    D.weekly.map((w) => [{ text: w.week, l: 1 }, w.days, cr(w.gmv_actual), { text: pct(w.gmv_pva), bad: w.gmv_pva < vt },
      pct(w.gm_pva), { text: pct(w.sessions_pva), bad: w.sessions_pva < vt }, { text: pct(w.conversion_pva), bad: w.conversion_pva < rt },
      pct(w.asp_pva), (w.discount_diff_pp > 0 ? "+" : "") + w.discount_diff_pp.toFixed(1) + " pp"]));
  table($("brands"), ["Brand", "Model", "GMV plan", "GMV actual", "GMV PvA", "Gap", "GM PvA", "Sessions PvA", "Conversion PvA", "ASP PvA", "Discount vs plan", "Worst size avail.", "Month landing", "Main driver"],
    D.brands.map((b) => [{ text: b.brand, l: 1 }, { text: b.model, l: 1 }, cr(b.gmv_plan), cr(b.gmv_actual), { text: pct(b.gmv_pva), bad: b.gmv_pva < vt },
      money(b.gmv_gap_inr), pct(b.gm_pva), { text: pct(b.sessions_pva), bad: b.sessions_pva < vt }, { text: pct(b.conversion_pva), bad: b.conversion_pva < rt },
      pct(b.asp_pva), (b.discount_diff_pp > 0 ? "+" : "") + b.discount_diff_pp.toFixed(1) + " pp", pct(b.size_availability_min, 0),
      { text: pct(b.month_landing_pva), bad: b.month_landing_pva < vt }, { text: b.main_driver, l: 1 }]));

  render();
  let rt2; addEventListener("resize", () => { clearTimeout(rt2); rt2 = setTimeout(render, 150); });
})();
</script>
</body>
</html>
"""


def build():
    if not config.DB_PATH.exists():
        import data
        data.build()
    data_json = json.dumps(gather()).replace("</", "<\\/")      # safe inside <script>
    folder = config.OUT_DIR / config.AS_OF_DATE.isoformat()
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "dashboard.html"
    path.write_text(PAGE.replace("__DATA__", data_json))
    print(f"Dashboard -> {path}")
    return path


if __name__ == "__main__":
    build()
