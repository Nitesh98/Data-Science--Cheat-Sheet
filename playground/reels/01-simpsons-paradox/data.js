/* Synthetic, seeded data for Simpson's paradox. Slopes shown on screen are computed from it. */
(function () {
  const R = M.rng(7);
  const pts = [];
  for (let i = 0; i < 20; i++) { const x = 0.8 + R() * 4.1; pts.push({ g: 0, x, y: 13 + 0.7 * x + (R() - 0.5) * 3.4 }); } // Metro: spend little, sell a lot
  for (let i = 0; i < 20; i++) { const x = 5.4 + R() * 4.1; pts.push({ g: 1, x, y: 2.4 + 0.7 * x + (R() - 0.5) * 3.4 }); } // Tier-2: spend more, sell less

  function ols(p) {                                   // ordinary least squares line
    const n = p.length, mx = p.reduce((s, q) => s + q.x, 0) / n, my = p.reduce((s, q) => s + q.y, 0) / n;
    let sxy = 0, sxx = 0;
    for (const q of p) { sxy += (q.x - mx) * (q.y - my); sxx += (q.x - mx) ** 2; }
    const m = sxy / sxx, b = my - m * mx;
    return { m, b, xmin: Math.min(...p.map(q => q.x)), xmax: Math.max(...p.map(q => q.x)) };
  }
  window.DATA = {
    pts, all: ols(pts), g: [ols(pts.filter(p => p.g === 0)), ols(pts.filter(p => p.g === 1))],
    X: x => 110 + x * 88,            // data -> pixel mapping for the chart (x domain 0..10)
    Y: y => 1290 - y * 34,           //                                    (y domain 0..20)
  };
})();
