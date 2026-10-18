"""Visual identity: semantic colours, type, and reusable on-screen components.

Colour roles are fixed for the whole series and are always reinforced by a
label or line style (never colour alone):
  INPUT  (x, domain)            teal   — solid
  OUTPUT (y, f(x), range)       amber  — solid
  PARAM  (h, k, a, b, m ...)    violet — solid
  RESTRICT (excluded / domain conditions / traps)  coral — dashed + "✗"/"≠" label
  FOCUS  (current step)         yellow — highlight box
  OK     (verified result)      green  — with "✓"
"""
from manim import *
import config as C

BG = "#0F1320"
PANEL = "#171C2B"
GRID = "#252C40"
TEXT = "#E6E9EF"
MUTED = "#8A93A6"
INPUT = "#5CC8C2"
OUTPUT = "#F2B45A"
PARAM = "#B39DFF"
RESTRICT = "#FF6B6B"
FOCUS = "#FFE066"
OK = "#7BD88F"
GHOST = "#56607A"

BODY_FONT = "Inter"            # SIL Open Font License 1.1
DISPLAY_FONT = "Inter Display"  # SIL Open Font License 1.1
MONO_FONT = "DejaVu Sans Mono"  # Bitstream Vera / public-domain-style licence

config.background_color = BG
if C.PREVIEW:
    config.pixel_width, config.pixel_height, config.frame_rate = 1280, 720, 15
else:
    config.pixel_width, config.pixel_height, config.frame_rate = C.WIDTH, C.HEIGHT, C.FPS

TEX = TexTemplate()
TEX.add_to_preamble(r"\usepackage{amsmath,amssymb}")
MathTex.set_default(tex_template=TEX, color=TEXT)
Tex.set_default(tex_template=TEX, color=TEXT)


def T(s, size=30, color=TEXT, weight=NORMAL, font=BODY_FONT, **kw):
    """Body text. Sizes are chosen for phone legibility at 1080p (>= 26)."""
    return Text(s, font=font, font_size=size, color=color, weight=weight, **kw)


def M(*s, size=44, color=TEXT, **kw):
    return MathTex(*s, font_size=size, color=color, **kw)


def eq_axes(x_range, y_range, unit=0.8, labels=True, x_label="x", y_label="y"):
    """Axes with EQUAL unit length on both axes (geometry is not distorted)."""
    ax = Axes(
        x_range=[*x_range, 1], y_range=[*y_range, 1],
        x_length=(x_range[1] - x_range[0]) * unit,
        y_length=(y_range[1] - y_range[0]) * unit,
        axis_config={"color": MUTED, "stroke_width": 2.5, "include_tip": True,
                     "tip_width": 0.18, "tip_height": 0.18, "include_ticks": True,
                     "tick_size": 0.06},
        x_axis_config={"numbers_to_include": [n for n in range(x_range[0] + 1, x_range[1]) if n != 0],
                       "font_size": 24},
        y_axis_config={"numbers_to_include": [n for n in range(y_range[0] + 1, y_range[1]) if n != 0],
                       "font_size": 24},
    )
    grid = NumberPlane(
        x_range=[*x_range, 1], y_range=[*y_range, 1],
        x_length=ax.x_length, y_length=ax.y_length,
        background_line_style={"stroke_color": GRID, "stroke_width": 1.2, "stroke_opacity": 0.8},
        axis_config={"stroke_opacity": 0},
    ).move_to(ax.c2p(*[(a + b) / 2 for a, b in (x_range, y_range)]))
    grid.shift(ax.c2p(0, 0) - grid.c2p(0, 0))
    g = VGroup(grid, ax)
    if labels:
        xl = MathTex(x_label, color=INPUT, font_size=34).next_to(ax.x_axis.get_end(), DR, buff=0.12)
        yl = MathTex(y_label, color=OUTPUT, font_size=34).next_to(ax.y_axis.get_end(), UL, buff=0.12)
        g.add(xl, yl)
    g.ax = ax
    return g


def dot(ax, x, y, color=OUTPUT, closed=True, r=0.07):
    """Closed dot = point included; open dot = point excluded (hole/endpoint)."""
    if closed:
        return Dot(ax.c2p(x, y), radius=r, color=color)
    return Circle(radius=r, color=color, stroke_width=4).set_fill(BG, 1).move_to(ax.c2p(x, y))


def tag(text, color=FOCUS, size=26):
    """Small rounded label (e.g. 'QUESTION', 'TRAP', 'RECALL')."""
    t = T(text, size=size, color=BG, weight=BOLD)
    box = RoundedRectangle(corner_radius=0.12, width=t.width + 0.4, height=t.height + 0.22,
                           fill_color=color, fill_opacity=1, stroke_width=0)
    return VGroup(box, t.move_to(box))


def panel(width, height, title=None):
    p = RoundedRectangle(corner_radius=0.2, width=width, height=height, fill_color=PANEL,
                         fill_opacity=0.96, stroke_color=GRID, stroke_width=2)
    g = VGroup(p)
    if title:
        g.add(T(title, size=24, color=MUTED, weight=BOLD).next_to(p.get_corner(UL), DR, buff=0.25))
    return g


def focus_box(mob, color=FOCUS, buff=0.12):
    return SurroundingRectangle(mob, color=color, buff=buff, corner_radius=0.08, stroke_width=4)


def header(chapter_id, chapter_title, section_title):
    """Top-left breadcrumb kept small so it never competes with the maths."""
    a = T(f"{chapter_id} · {chapter_title}", size=22, color=MUTED)
    b = T(section_title, size=22, color=TEXT, weight=BOLD)
    g = VGroup(a, b).arrange(RIGHT, buff=0.25).to_corner(UL, buff=0.35)
    return g


def progress_bar(chapter_id):
    """Segmented chapter progress indicator along the bottom edge."""
    n = len(C.CHAPTER_IDS)
    w = config.frame_width - 1.0
    segs = VGroup()
    idx = C.CHAPTER_IDS.index(chapter_id)
    for i in range(n):
        col = FOCUS if i == idx else (GHOST if i < idx else GRID)
        segs.add(Rectangle(width=w / n - 0.04, height=0.05, fill_color=col, fill_opacity=1, stroke_width=0))
    segs.arrange(RIGHT, buff=0.04).to_edge(DOWN, buff=0.18)
    return segs


def countdown(seconds, label="PAUSE & PREDICT"):
    """Ring that empties over `seconds` (driven by a ValueTracker in NarratedScene.think)."""
    vt = ValueTracker(0)
    ring_bg = Circle(radius=0.38, color=GRID, stroke_width=8)
    ring = always_redraw(lambda: Arc(radius=0.38, start_angle=PI / 2,
                                     angle=-TAU * (1 - vt.get_value()), color=FOCUS, stroke_width=8)
                         .move_arc_center_to(ring_bg.get_center()))
    lab = T(label, size=22, color=FOCUS, weight=BOLD).next_to(ring_bg, RIGHT, buff=0.25)
    g = VGroup(ring_bg, ring, lab)
    g.vt = vt
    return g


def fit(mob, box, pad=0.35):
    """Scale `mob` down (never up) so it fits inside `box` with padding; keeps text inside panels."""
    w, h = box.width - 2 * pad, box.height - 2 * pad
    sc = min(1.0, w / max(mob.width, 1e-6), h / max(mob.height, 1e-6))
    if sc < 1.0:
        mob.scale(sc)
    return mob
