"""
Minimal, dependency-free SVG chart helpers shared across the portfolio
projects. No matplotlib/pandas available in this environment, so charts are
hand-built SVG -- following the house palette (see dataviz skill reference)
for readability and colorblind-safe categorical colors.

Only two chart types are implemented: a multi-series line chart and a
grouped/simple bar chart. That covers every chart used in these projects.
"""

# Palette (validated categorical order; light-surface only -- static assets
# embedded in Markdown/GitHub, not a live theme-aware artifact).
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
BASELINE = "#c3c2b7"
SURFACE = "#fcfcfb"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#4a3aa7"]
FONT = "system-ui, -apple-system, 'Segoe UI', sans-serif"

W, H = 720, 420
PAD_L, PAD_R, PAD_T, PAD_B = 70, 30, 40, 50


def _scale(v, vmin, vmax, out_min, out_max):
    if vmax == vmin:
        return (out_min + out_max) / 2
    return out_min + (v - vmin) / (vmax - vmin) * (out_max - out_min)


def _fmt(v):
    if abs(v) >= 1_000_000:
        return f"{v/1_000_000:.1f}M"
    if abs(v) >= 1_000:
        return f"{v/1_000:.0f}K"
    return f"{v:g}"


def line_chart(x_labels, series, title, y_label="", subtitle="", filename=None):
    """series: dict[name] -> list[float], same length as x_labels."""
    all_vals = [v for vals in series.values() for v in vals]
    vmin, vmax = min(0, min(all_vals)), max(all_vals)
    vmax *= 1.1 if vmax > 0 else 0.9

    plot_w = W - PAD_L - PAD_R
    plot_h = H - PAD_T - PAD_B
    n = len(x_labels)

    def px(i):
        return PAD_L + (i / max(1, n - 1)) * plot_w

    def py(v):
        return PAD_T + plot_h - _scale(v, vmin, vmax, 0, plot_h)

    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
           f'viewBox="0 0 {W} {H}" font-family="{FONT}">']
    svg.append(f'<rect width="{W}" height="{H}" fill="{SURFACE}"/>')
    svg.append(f'<text x="{PAD_L}" y="22" font-size="15" font-weight="600" fill="{INK_PRIMARY}">{title}</text>')
    if subtitle:
        svg.append(f'<text x="{PAD_L}" y="36" font-size="11" fill="{INK_SECONDARY}">{subtitle}</text>')

    # gridlines + y-axis labels (4 bands)
    for i in range(5):
        v = vmin + (vmax - vmin) * i / 4
        y = py(v)
        svg.append(f'<line x1="{PAD_L}" y1="{y:.1f}" x2="{W - PAD_R}" y2="{y:.1f}" stroke="{GRIDLINE}" stroke-width="1"/>')
        svg.append(f'<text x="{PAD_L - 8}" y="{y+4:.1f}" font-size="10" fill="{INK_MUTED}" text-anchor="end">{_fmt(v)}</text>')

    # x-axis labels (thin every Nth to avoid crowding)
    step = max(1, n // 8)
    for i in range(0, n, step):
        svg.append(f'<text x="{px(i):.1f}" y="{H - PAD_B + 18}" font-size="10" fill="{INK_MUTED}" text-anchor="middle">{x_labels[i]}</text>')

    for si, (name, vals) in enumerate(series.items()):
        color = SERIES[si % len(SERIES)]
        pts = " ".join(f"{px(i):.1f},{py(v):.1f}" for i, v in enumerate(vals))
        svg.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>')
        # small end-of-line direct label
        last_x, last_y = px(n - 1), py(vals[-1])
        svg.append(f'<circle cx="{last_x:.1f}" cy="{last_y:.1f}" r="3.5" fill="{color}"/>')
        svg.append(f'<text x="{last_x + 8:.1f}" y="{last_y + 4:.1f}" font-size="11" fill="{color}" font-weight="600">{name}</text>')

    svg.append(f'<line x1="{PAD_L}" y1="{PAD_T + plot_h}" x2="{W - PAD_R}" y2="{PAD_T + plot_h}" stroke="{BASELINE}" stroke-width="1.5"/>')
    svg.append("</svg>")
    out = "\n".join(svg)
    if filename:
        with open(filename, "w") as f:
            f.write(out)
    return out


def bar_chart(labels, values, title, subtitle="", filename=None, color=None, highlight_idx=None):
    color = color or SERIES[0]
    vmax = max(values) * 1.15 if values else 1
    vmin = min(0, min(values)) if values else 0

    plot_w = W - PAD_L - PAD_R
    plot_h = H - PAD_T - PAD_B
    n = len(labels)
    band = plot_w / n
    bar_w = band * 0.55

    def py(v):
        return PAD_T + plot_h - _scale(v, vmin, vmax, 0, plot_h)

    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
           f'viewBox="0 0 {W} {H}" font-family="{FONT}">']
    svg.append(f'<rect width="{W}" height="{H}" fill="{SURFACE}"/>')
    svg.append(f'<text x="{PAD_L}" y="22" font-size="15" font-weight="600" fill="{INK_PRIMARY}">{title}</text>')
    if subtitle:
        svg.append(f'<text x="{PAD_L}" y="36" font-size="11" fill="{INK_SECONDARY}">{subtitle}</text>')

    for i in range(5):
        v = vmin + (vmax - vmin) * i / 4
        y = py(v)
        svg.append(f'<line x1="{PAD_L}" y1="{y:.1f}" x2="{W - PAD_R}" y2="{y:.1f}" stroke="{GRIDLINE}" stroke-width="1"/>')
        svg.append(f'<text x="{PAD_L - 8}" y="{y+4:.1f}" font-size="10" fill="{INK_MUTED}" text-anchor="end">{_fmt(v)}</text>')

    zero_y = py(0)
    for i, (lab, v) in enumerate(zip(labels, values)):
        x = PAD_L + i * band + (band - bar_w) / 2
        y = py(v)
        h = abs(zero_y - y)
        top = min(y, zero_y)
        bar_color = SERIES[2] if (highlight_idx is not None and i == highlight_idx) else color
        svg.append(f'<rect x="{x:.1f}" y="{top:.1f}" width="{bar_w:.1f}" height="{max(h,1):.1f}" rx="3" fill="{bar_color}"/>')
        svg.append(f'<text x="{x + bar_w/2:.1f}" y="{top - 6:.1f}" font-size="10" fill="{INK_SECONDARY}" text-anchor="middle">{_fmt(v)}</text>')
        svg.append(f'<text x="{x + bar_w/2:.1f}" y="{H - PAD_B + 16}" font-size="10" fill="{INK_MUTED}" text-anchor="middle">{lab}</text>')

    svg.append(f'<line x1="{PAD_L}" y1="{zero_y:.1f}" x2="{W - PAD_R}" y2="{zero_y:.1f}" stroke="{BASELINE}" stroke-width="1.5"/>')
    svg.append("</svg>")
    out = "\n".join(svg)
    if filename:
        with open(filename, "w") as f:
            f.write(out)
    return out
