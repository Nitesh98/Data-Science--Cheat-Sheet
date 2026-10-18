"""C00 — Opening problem: one line, one parabola.

Delivers a useful result inside the first minute (discriminant decides whether
the line meets the curve), then plants three questions that later chapters
answer (C11 tangent slope, C13 enclosed area, C20 probability).
Registry: E.C00.1, E.C00.2, E.C00.3. Axes use EQUAL unit scale.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from manim import *
import style as S
from style import T, M
from narrated import NarratedScene

XR, YR, UNIT = (-4, 4), (-1, 9), 0.62
GRAPH_CENTER = LEFT * 3.4 + DOWN * 0.3
PANEL_X, PANEL_W = 3.55, 6.6


class C00_Opening(NarratedScene):
    CHAPTER = "C00"
    CHAPTER_TITLE = "Opening problem"
    SECTION = "C00"
    SECTION_TITLE = "One line, one parabola"

    def panel(self, h=5.4, title=None):
        return S.panel(PANEL_W, h, title).move_to(RIGHT * PANEL_X + UP * 0.2)

    def construct(self):
        self.mark("C00", "Opening problem: one line, one parabola")
        self.cue("motif")
        self.chrome()
        g = S.eq_axes(XR, YR, unit=UNIT).move_to(GRAPH_CENTER)
        ax = self.ax = g.ax
        par = ax.plot(lambda x: x ** 2 + 1, x_range=[-np.sqrt(7.85), np.sqrt(7.85), 0.01], color=S.OUTPUT, stroke_width=6)
        plab = M(r"y=x^2+1", size=36, color=S.OUTPUT).move_to(ax.c2p(-2.9, 2.2))
        m = ValueTracker(0.5)

        def line():
            mv = m.get_value()
            # clip the line y = m x to the visible window
            xs = [x for x in np.linspace(XR[0] + 0.1, XR[1] - 0.3, 801) if YR[0] + 0.1 <= mv * x <= YR[1] - 0.1]
            return Line(ax.c2p(xs[0], mv * xs[0]), ax.c2p(xs[-1], mv * xs[-1]), color=S.PARAM, stroke_width=5)

        def hits():
            mv = m.get_value()
            D = mv * mv - 4
            if D < -1e-9:
                return VGroup()
            r = np.sqrt(max(D, 0))
            xs = sorted({round((mv - r) / 2, 9), round((mv + r) / 2, 9)})
            return VGroup(*[S.dot(ax, x, x * x + 1, color=S.FOCUS, r=0.09) for x in xs
                            if x * x + 1 <= YR[1] - 0.1])  # never draw outside the window

        def count():
            D = m.get_value() ** 2 - 4
            return 0 if D < -1e-9 else (1 if abs(D) <= 1e-9 else 2)

        L = always_redraw(line)
        H = always_redraw(hits)
        readout = always_redraw(lambda: VGroup(
            M(r"y=mx,\ \ m=", size=38, color=S.PARAM),
            DecimalNumber(m.get_value(), num_decimal_places=2, font_size=38, color=S.PARAM),
            T({0: "   misses the curve", 1: "   touches once", 2: "   cuts twice"}[count()], size=26,
              color=S.FOCUS)).arrange(RIGHT, buff=0.12).move_to(RIGHT * PANEL_X + DOWN * 3.05))
        q = VGroup()
        self.add(g, par, plab)
        self.say("सीधा problem से शुरू करते हैं। | एक parabola: y equals x squared plus 1. | और origin से गुज़रती एक line: y equals m x.",
                 Create(L), FadeIn(q), run_time=1.6)
        self.add(H, readout)
        self.say("Slope m बदलो, और देखो line parabola को कब काटती है।",
                 m.animate.set_value(3.2), run_time=3.0, sfx="move")
        self.play(m.animate.set_value(-3.2), run_time=4.0)
        self.play(m.animate.set_value(1.0), run_time=2.0)
        # useful result inside the first minute
        p = self.panel(5.4, "ANSWER IN ONE LINE OF ALGEBRA")
        a = VGroup(M(r"x^2+1 = m x", size=40),
                   M(r"x^2 - m x + 1 = 0", size=40),
                   M(r"D = m^2 - 4", size=42, color=S.FOCUS),
                   M(r"\text{meets} \iff m^2-4 \ge 0 \iff |m| \ge 2", size=36, color=S.OK))
        a.arrange(DOWN, buff=0.4, aligned_edge=LEFT)
        S.fit(a, p[0]).move_to(p[0])
        self.say("Meeting point पर दोनों का y equal होगा। | तो x squared plus 1 equals m x, यानी एक quadratic.",
                 FadeIn(p), Write(a[0]), Write(a[1]), run_time=2.2, dense=True)
        self.say("Real meeting point तभी है, जब discriminant zero या positive हो। | D equals m squared minus 4.",
                 Write(a[2]), run_time=1.4, dense=True)
        self.say("मतलब line curve से मिलती है, सिर्फ जब mod m, 2 या उससे ज़्यादा हो।",
                 Write(a[3]), run_time=1.4, sfx="accent")
        self.say("Graph से check करो: | m equals 2 पर line curve को सिर्फ छूती है।",
                 m.animate.set_value(2), run_time=2.0, hold=0.8)
        tp = M(r"(1,\,2)", size=34, color=S.FOCUS).next_to(ax.c2p(1, 2), RIGHT, buff=0.25)
        self.say("Touch point है 1 comma 2. | एक quadratic, एक discriminant, और geometry का answer मिल गया।",
                 FadeIn(tp), sfx="release", hold=0.8)
        # plant the questions that return later
        self.play(FadeOut(VGroup(p, a)), run_time=0.6)
        p2 = self.panel(5.4, "WE WILL RETURN TO THESE")
        qs = VGroup(
            VGroup(S.tag("C11", S.PARAM, 22), T("Why is the slope of the curve\nat (1, 2) exactly 2?", size=28)).arrange(RIGHT, buff=0.25),
            VGroup(S.tag("C13", S.PARAM, 22), T("For m = 3, what area is\ntrapped between them?", size=28)).arrange(RIGHT, buff=0.25),
            VGroup(S.tag("C20", S.PARAM, 22), T("m random in {−3, …, 3}:\nchance they meet?", size=28)).arrange(RIGHT, buff=0.25),
        ).arrange(DOWN, buff=0.5, aligned_edge=LEFT)
        S.fit(qs, p2[0]).move_to(p2[0])
        self.say("पर यही picture तीन और सवाल पूछती है, | जिनके लिए हमें नए tools चाहिए।", FadeIn(p2), run_time=1.0)
        self.say("पहला: | touch point पर curve का slope बिल्कुल 2 क्यों है? | यह derivative बताएगा, chapter 11 में।",
                 FadeIn(qs[0], shift=RIGHT * 0.2), run_time=1.0)
        m3 = 3.0
        r1, r2 = (3 - np.sqrt(5)) / 2, (3 + np.sqrt(5)) / 2
        region = ax.get_area(ax.plot(lambda x: 3 * x, x_range=[r1, r2]), x_range=[r1, r2],
                             bounded_graph=ax.plot(lambda x: x * x + 1, x_range=[r1, r2]),
                             color=S.FOCUS, opacity=0.35)
        self.remove(tp)
        self.say("दूसरा: | m equals 3 पर line और curve के बीच कितना area फँसा है? | यह integration बताएगा, chapter 13 में।",
                 m.animate.set_value(m3), FadeIn(qs[1], shift=RIGHT * 0.2), run_time=1.8)
        self.play(FadeIn(region), run_time=1.0)
        self.say("तीसरा: | अगर m, minus 3 से 3 तक का कोई random integer हो, | तो line के curve से मिलने का chance क्या है? | यह probability बताएगी, chapter 20 में।",
                 FadeIn(qs[2], shift=RIGHT * 0.2), run_time=1.0)
        self.think(5, label="KEEP THESE IN MIND", where=RIGHT * (PANEL_X - 1.2) + DOWN * 1.9)
        self.say("इन्हें याद रखना। | हर tool सीखने के बाद हम इसी picture पर वापस आएँगे। | चलो, शुरुआत करते हैं functions से।",
                 hold=1.0)
        self.play(FadeOut(VGroup(g, par, plab, q, region, p2, qs, L, H, readout)), run_time=1.0)
        self.remove(L, H, readout)
        self.wait(0.5)
