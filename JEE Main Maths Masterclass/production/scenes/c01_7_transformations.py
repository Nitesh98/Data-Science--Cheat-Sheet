"""C01.7 — Graphs of simple functions: transformations (representative sequence).

Syllabus: U7.04 "Graphs of simple functions" (with U7.01 domain/range tracking).
Registry: F.TR.01–04, E.C01.7.1–4. Teaching loop: question → intuition →
formal → conditions → mechanism → worked example → trap → recall → connection → recap.
Axes use EQUAL unit scale on x and y.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from manim import *
import style as S
from style import T, M
from narrated import NarratedScene

XR, YR, UNIT = (-5, 7), (-2, 6), 0.56
GRAPH_CENTER = LEFT * 3.6 + DOWN * 0.35
PANEL_X = 3.6
PANEL_W = 6.7


def clip_parabola(h, k, ymax=YR[1] - 0.15):
    """x-interval where (x-h)^2 + k stays inside the visible window."""
    if ymax <= k:
        return None
    r = np.sqrt(ymax - k)
    lo, hi = max(XR[0] + 0.05, h - r), min(XR[1] - 0.25, h + r)
    return (lo, hi) if hi > lo else None


class C01_7_Transformations(NarratedScene):
    CHAPTER = "C01"
    CHAPTER_TITLE = "Sets, relations & functions"
    SECTION = "C01.7"
    SECTION_TITLE = "Graph transformations"

    # ------------------------------------------------------------------ helpers
    def make_axes(self):
        g = S.eq_axes(XR, YR, unit=UNIT)
        g.move_to(GRAPH_CENTER)
        self.ax = g.ax
        note = T("equal scale on both axes", size=20, color=S.MUTED).next_to(g, DOWN, buff=0.12).align_to(g, LEFT)
        return g, note

    def fplot(self, fn, lo, hi, color=S.OUTPUT, width=6, dashed=False, step=0.01):
        # never draw outside the visible window: restrict a monotone piece to where it is in range
        xs = np.linspace(lo, hi, 1201)
        ys = np.array([fn(v) for v in xs])
        ok = np.where((ys >= YR[0] + 0.05) & (ys <= YR[1] - 0.05))[0]
        lo, hi = xs[ok[0]], xs[ok[-1]]
        p = self.ax.plot(fn, x_range=[lo, hi, min(step, (hi - lo) / 50)], color=color, stroke_width=width,
                         use_smoothing=False)
        return DashedVMobject(p, num_dashes=60, dashed_ratio=0.55) if dashed else p

    def right_panel(self, height=5.9, title=None):
        p = S.panel(PANEL_W, height, title).move_to(RIGHT * PANEL_X + DOWN * 0.3)
        return p

    # ------------------------------------------------------------------ scene
    def construct(self):
        self.title_card()
        self.intuition_shift()
        self.formal_rules()
        self.conditions_domain()
        self.mechanism_modulus()
        self.worked_example()
        self.trap()
        self.recall()
        self.connection_and_recap()

    # 0. QUESTION -----------------------------------------------------------
    def title_card(self):
        self.mark("C01.7", "Graph transformations")
        self.cue("motif")
        kicker = T("C01 · SETS, RELATIONS & FUNCTIONS  ·  SECTION 7", size=24, color=S.MUTED, weight=BOLD)
        title = T("Graph Transformations", size=76, font=S.DISPLAY_FONT, weight=BOLD)
        sub = T("Unit 7 · Graphs of simple functions", size=30, color=S.MUTED)
        VGroup(kicker, title, sub).arrange(DOWN, buff=0.35).shift(UP * 1.2)
        q_tag = S.tag("QUESTION", S.FOCUS)
        q = M(r"\text{If you know the graph of } f,\ \text{where is }\ y = f(", r"x-2", r")", r"+1", r"\ ?", size=46)
        q[1].set_color(S.INPUT); q[3].set_color(S.OUTPUT)
        qg = VGroup(q_tag, q).arrange(DOWN, buff=0.35).shift(DOWN * 1.4)
        self.play(FadeIn(kicker, shift=DOWN * 0.2), Write(title), FadeIn(sub), run_time=1.6)
        self.say("चलो, functions के सबसे useful tool से शुरुआत करते हैं: graph transformations.",
                 FadeIn(qg, shift=UP * 0.2), hold=0.3)
        self.say("Question यह है: | अगर हमें f का graph पता है, | तो y equals f of x minus 2, plus 1 का graph कहाँ होगा?",
                 Create(qbox := S.focus_box(q)), hold=0.6)
        self.play(FadeOut(VGroup(kicker, title, sub, qg, qbox)), run_time=0.8)
        self.chrome()

    # 1. INTUITION ------------------------------------------------------------
    def intuition_shift(self):
        axes, note = self.make_axes()
        self.say("Base function लेते हैं: f of x equals x squared. | इसका vertex origin पर है।",
                 Create(axes), FadeIn(note), run_time=2.2)
        h, k = ValueTracker(0), ValueTracker(0)
        self.h, self.k = h, k

        def para():
            iv = clip_parabola(h.get_value(), k.get_value())
            return self.fplot(lambda X: (X - h.get_value()) ** 2 + k.get_value(), *iv)
        base = self.fplot(lambda X: X ** 2, *clip_parabola(0, 0))
        lab = M(r"f(x)=x^2", size=36, color=S.OUTPUT).move_to(self.ax.c2p(-3.4, 1.0))
        self.play(Create(base), FadeIn(lab), run_time=1.5)

        # point-tracking argument: g(3) = f(1)
        panel = self.right_panel(5.9, "WHY RIGHT, NOT LEFT?")
        l1 = M(r"g(x) = f(x-2)", size=40)
        l2 = M(r"g(", r"3", r") = f(", r"3-2", r") = f(", r"1", r")", size=40)
        l2[1].set_color(S.INPUT); l2[3].set_color(S.INPUT); l2[5].set_color(S.INPUT)
        l3 = T("g does at x = 3 what f did at x = 1", size=26, color=S.MUTED)
        VGroup(l1, l2, l3).arrange(DOWN, buff=0.45, aligned_edge=LEFT).move_to(panel[0]).shift(UP * 0.6)
        self.play(FadeIn(panel), Write(l1), run_time=1.2)
        x3 = S.dot(self.ax, 3, 0, color=S.INPUT)
        x1 = S.dot(self.ax, 1, 0, color=S.INPUT)
        p1 = S.dot(self.ax, 1, 1, color=S.OUTPUT)
        p3 = S.dot(self.ax, 3, 1, color=S.FOCUS)
        back = CurvedArrow(x3.get_center() + DOWN * 0.15, x1.get_center() + DOWN * 0.15, angle=-PI / 3, color=S.INPUT)
        up = DashedLine(x1.get_center(), p1.get_center(), color=S.OUTPUT)
        carry = Arrow(p1.get_center(), p3.get_center(), buff=0.08, color=S.FOCUS, stroke_width=5)
        self.say("Shift समझने के लिए एक point track करते हैं। | g of 3 निकालना है, तो 3 minus 2 यानी 1 पर f को देखना पड़ेगा।",
                 FadeIn(x3), Write(l2), run_time=2.0)
        self.say("f of 1 is 1. | तो g की height x equals 3 पर वही है, जो f की height x equals 1 पर थी।",
                 Create(back), FadeIn(x1), Create(up), FadeIn(p1), run_time=2.2)
        self.say("मतलब f जो काम 1 पर करता था, g वही काम 3 पर करता है। | यानी हर point 2 units right खिसकता है, left नहीं।",
                 GrowArrow(carry), FadeIn(p3), FadeIn(l3), run_time=1.8, sfx="accent")
        ghost = self.fplot(lambda X: X ** 2, *clip_parabola(0, 0), color=S.GHOST, width=4, dashed=True)
        moving = always_redraw(para)
        self.remove(base)
        self.add(ghost, moving)
        self.play(FadeOut(VGroup(back, up, carry, x1, x3, p1)), run_time=0.5)
        vx = always_redraw(lambda: S.dot(self.ax, h.get_value(), k.get_value(), color=S.FOCUS))
        self.add(vx)
        self.say("अब पूरा graph slide करते देखो। | Original curve dashed ghost बनकर पीछे रहेगा।",
                 h.animate.set_value(2), run_time=2.6, sfx="move")
        self.remove(p3)
        kl = M(r"+1", size=40, color=S.OUTPUT)
        l4 = M(r"y = f(x-2)", r"+1", size=40); l4[1].set_color(S.OUTPUT)
        l4.next_to(l3, DOWN, buff=0.55).align_to(l3, LEFT)
        self.say("अब बाहर वाला plus 1. | यह output में जुड़ता है, इसलिए graph सीधा 1 unit ऊपर जाता है।",
                 k.animate.set_value(1), Write(l4), run_time=2.0, sfx="move")
        vlab = M(r"(2,\,1)", size=34, color=S.FOCUS).next_to(self.ax.c2p(2, 1), DR, buff=0.12)
        ans = VGroup(T("vertex", size=24, color=S.MUTED), M(r"(0,0)\ \to\ (2,1)", size=38, color=S.FOCUS)).arrange(RIGHT, buff=0.25)
        ans.next_to(l4, DOWN, buff=0.45).align_to(l4, LEFT)
        self.say("Vertex origin से 2 comma 1 पर पहुँच गया। | ध्यान दो: shape बिल्कुल वही है, सिर्फ position बदली। | Translation में shape invariant रहता है।",
                 FadeIn(vlab), FadeIn(ans), sfx="accent", hold=0.8)
        self.panel_items = VGroup(panel, l1, l2, l3, l4, ans)
        self.graph_items = VGroup(ghost, vlab, lab)
        self.moving, self.vx, self.axes_g, self.note = moving, vx, axes, note

    # 2. FORMAL STATEMENT -------------------------------------------------------
    def formal_rules(self):
        self.play(FadeOut(self.panel_items), run_time=0.6)
        panel = self.right_panel(6.3, "THE RULES  (f known, constants real)")
        rows = [
            (M(r"y=f(x-h)+k", size=36), T("shift right h, up k", size=24)),
            (M(r"y=a\,f(x),\ a>0", size=36), T("vertical stretch ×a", size=24)),
            (M(r"y=-f(x)", size=36), T("reflect in x-axis", size=24)),
            (M(r"y=f(bx),\ b>0", size=36), T("horizontal squeeze ÷b", size=24)),
            (M(r"y=f(-x)", size=36), T("reflect in y-axis", size=24)),
        ]
        grid = VGroup(*[VGroup(a, b).arrange(DOWN, buff=0.14, aligned_edge=LEFT) for a, b in rows])
        grid.arrange(DOWN, buff=0.3, aligned_edge=LEFT)
        inside = VGroup(grid[0][0], grid[3][0], grid[4][0])
        self.say("अब formal rules देखते हैं। | f पता है, और सारे constants real हैं।",
                 FadeIn(panel), LaggedStart(*[FadeIn(g, shift=RIGHT * 0.2) for g in grid], lag_ratio=0.25), run_time=3.0)
        tip = VGroup(S.tag("RULE OF THUMB", S.PARAM),
                     T("inside x  →  horizontal, feels opposite", size=24, color=S.INPUT),
                     T("outside  →  vertical, exactly as written", size=24, color=S.OUTPUT)).arrange(DOWN, buff=0.18, aligned_edge=LEFT)
        body = VGroup(grid, tip).arrange(DOWN, buff=0.45, aligned_edge=LEFT)
        S.fit(body, Rectangle(width=PANEL_W - 0.9, height=panel[0].height - 1.5), pad=0)
        body.move_to(panel[0]).shift(DOWN * 0.35)
        self.play(FadeOut(self.note), run_time=0.3)
        boxes = VGroup(*[S.focus_box(mob, color=S.INPUT) for mob in inside])
        self.say("Rule of thumb याद रखो: | जो बदलाव x के अंदर होता है, वह horizontal होता है, और उल्टा लगता है। | जो बदलाव बाहर होता है, वह vertical है, और जैसा लिखा है वैसा ही।",
                 FadeIn(tip), *[Create(b) for b in boxes],
                 run_time=1.5, hold=0.8)
        self.play(FadeOut(boxes), run_time=0.4)
        self.say("इसीलिए f of 2x graph को दो गुना चौड़ा नहीं करता, | बल्कि horizontally आधा कर देता है।", hold=0.6)
        self.rules = VGroup(panel, grid)
        self.tip = tip

    # 3. CONDITIONS ------------------------------------------------------------
    def conditions_domain(self):
        self.play(FadeOut(VGroup(self.moving, self.vx, self.graph_items, self.tip, self.rules)), run_time=0.8)
        self.remove(self.moving, self.vx)
        panel = self.right_panel(5.9, "CONDITIONS TRAVEL TOO")
        c1 = M(r"\text{dom}\,\sqrt{x} = [0,\infty)", size=38, color=S.INPUT)
        c2 = M(r"\text{dom}\,\sqrt{x-2} = [2,\infty)", size=38, color=S.INPUT)
        c3 = M(r"\text{range stays } [0,\infty)", size=38, color=S.OUTPUT)
        warn = VGroup(T("a = 0 is not a stretch: graph collapses to y = 0", size=23, color=S.RESTRICT),
                      T("b = 0 is not allowed: f(0·x) is constant", size=23, color=S.RESTRICT))
        warn.arrange(DOWN, buff=0.18, aligned_edge=LEFT)
        S.fit(VGroup(c1, c2, c3, warn).arrange(DOWN, buff=0.45, aligned_edge=LEFT), panel[0]).move_to(panel[0])
        s = ValueTracker(0)
        curve = always_redraw(lambda: self.fplot(lambda X: np.sqrt(max(X - s.get_value(), 0)),
                                                 s.get_value(), XR[1] - 0.25))
        end = always_redraw(lambda: S.dot(self.ax, s.get_value(), 0, color=S.OUTPUT, closed=True))
        dom = always_redraw(lambda: Line(self.ax.c2p(s.get_value(), 0), self.ax.c2p(XR[1] - 0.25, 0),
                                         color=S.INPUT, stroke_width=12, stroke_opacity=0.55))
        rng = Line(self.ax.c2p(0, 0), self.ax.c2p(0, YR[1] - 0.2), color=S.OUTPUT, stroke_width=12, stroke_opacity=0.45)
        lab = M(r"y=\sqrt{x}", size=36, color=S.OUTPUT).move_to(self.ax.c2p(4.5, 3.4))
        self.say("Transformations सिर्फ curve नहीं, conditions को भी move करती हैं। | Square root of x का domain zero से infinity है, zero included.",
                 FadeIn(panel), Write(c1), Create(curve), FadeIn(end), FadeIn(dom), FadeIn(rng), FadeIn(lab), run_time=2.5)
        lab2 = M(r"y=\sqrt{x-2}", size=36, color=S.OUTPUT).move_to(self.ax.c2p(4.8, 3.4))
        self.say("Square root of x minus 2 में endpoint 2 पर shift हो जाता है। | Closed dot भी उसी के साथ जाता है, क्योंकि x equals 2 allowed है।",
                 s.animate.set_value(2), Transform(lab, lab2), Write(c2), run_time=2.4, sfx="move")
        self.say("पर range नहीं बदली, | क्योंकि horizontal shift outputs को touch नहीं करता।",
                 Write(c3), Indicate(rng, color=S.OUTPUT), run_time=1.6)
        self.say("दो restrictions भी नोट करो। | a equals zero कोई stretch नहीं है, पूरा graph flat हो जाता है। | और b zero नहीं हो सकता।",
                 FadeIn(warn, shift=UP * 0.1), run_time=1.2, hold=0.8)
        self.play(FadeOut(VGroup(panel, c1, c2, c3, warn, curve, end, dom, rng, lab)), run_time=0.8)
        self.remove(curve, end, dom)

    # 4. VISUAL MECHANISM: |f(x)| and f(|x|) -----------------------------------
    def mechanism_modulus(self):
        F = lambda X: X ** 2 - 4 * X + 3
        L, Rr = 2 - np.sqrt(7) + 0.02, 2 + np.sqrt(7) - 0.02   # F <= 5.98 inside window
        left = self.fplot(F, L, 1)
        arch = self.fplot(F, 1, 3)
        right = self.fplot(F, 3, Rr)
        panel = self.right_panel(5.9, "TWO DIFFERENT MODULUS MOVES")
        lab = M(r"f(x)=x^2-4x+3=(x-1)(x-3)", size=34, color=S.OUTPUT)
        m1 = M(r"y=|f(x)|", size=40, color=S.OUTPUT)
        m1d = T("outputs below the x-axis flip up", size=24, color=S.MUTED)
        m2 = M(r"y=f(|x|)", size=40, color=S.INPUT)
        m2d = T("left half replaced by mirror of right half", size=24, color=S.MUTED)
        body = VGroup(lab, m1, m1d, m2, m2d).arrange(DOWN, buff=0.3, aligned_edge=LEFT)
        m1.shift(DOWN * 0.25); m1d.shift(DOWN * 0.25); m2.shift(DOWN * 0.55); m2d.shift(DOWN * 0.55)
        S.fit(body, panel[0]).move_to(panel[0]).shift(UP * 0.1)
        self.say("अब modulus वाले दो transformations, जिनमें students सबसे ज़्यादा confuse होते हैं। | Function लेते हैं x squared minus 4x plus 3, यानी x minus 1 times x minus 3.",
                 Create(VGroup(left, arch, right)), FadeIn(panel), FadeIn(lab), run_time=2.5)
        neg = self.fplot(F, 1, 3, color=S.RESTRICT, width=7, dashed=True)
        self.say("1 और 3 के बीच outputs negative हैं। | यही हिस्सा बदलेगा।", FadeIn(neg), Write(m1), run_time=1.4)
        flipped = self.fplot(lambda X: -F(X), 1, 3, color=S.OUTPUT)
        self.say("Mod f of x में negative outputs positive बन जाते हैं, | तो बस यह arch x-axis में reflect होकर ऊपर आता है।",
                 Transform(arch, flipped), FadeOut(neg), FadeIn(m1d), run_time=2.2, sfx="move")
        c1, c3 = S.dot(self.ax, 1, 0, color=S.RESTRICT), S.dot(self.ax, 3, 0, color=S.RESTRICT)
        corner = T("corners at x = 1, 3", size=22, color=S.RESTRICT).next_to(self.ax.c2p(2, 0), DOWN, buff=0.35)
        self.say("x equals 1 और 3 पर sharp corners बनते हैं। | इन्हें याद रखना, ये differentiability में फिर आएँगे।",
                 FadeIn(c1), FadeIn(c3), FadeIn(corner), run_time=1.2, hold=0.6)
        # f(|x|)
        orig_arch = self.fplot(F, 1, 3)
        self.play(FadeOut(VGroup(c1, c3, corner)), Transform(arch, orig_arch), run_time=1.0)
        gone = VGroup(self.fplot(F, L, 0, color=S.RESTRICT, width=7, dashed=True))
        keep_left = self.fplot(F, 0, 1)
        self.remove(left); self.add(gone[0], keep_left)
        self.say("अब f of mod x. | यहाँ input पर modulus है, तो negative x का अपना graph discard हो जाता है।",
                 Write(m2), FadeOut(gone, run_time=1.6), run_time=1.6)
        right_half = VGroup(keep_left, arch, right)
        mirror = right_half.copy().set_color(S.INPUT)
        self.play(FadeIn(mirror), run_time=0.3)
        mirrored_target = VGroup(*[self.fplot(lambda X: F(-X), -b, -a, color=S.OUTPUT)
                                  for a, b in ((0, 1), (1, 3), (3, Rr))])
        self.say("और right half का mirror image left में आ जाता है, | क्योंकि f of mod x हमेशा even function है।",
                 Transform(mirror, mirrored_target), FadeIn(m2d), run_time=2.2, sfx="move")
        sym = DashedLine(self.ax.c2p(0, YR[0] + 0.2), self.ax.c2p(0, YR[1] - 0.2), color=S.INPUT)
        self.say("Graph अब y-axis के बारे में symmetric है। | फर्क याद रखो: mod f outputs को बदलता है, f of mod x inputs को।",
                 Create(sym), run_time=1.2, sfx="accent", hold=0.6)
        self.play(FadeOut(VGroup(right_half, mirror, sym, lab, panel, m1, m1d, m2, m2d)), run_time=0.8)

    # 5. WORKED EXAMPLE ---------------------------------------------------------
    def worked_example(self):
        self.mark("C01.7-ex", "Worked example: |x^2-4x+3| = k")
        F = lambda X: X ** 2 - 4 * X + 3
        L, Rr = 2 - np.sqrt(7) + 0.02, 2 + np.sqrt(7) - 0.02
        g = VGroup(self.fplot(F, L, 1), self.fplot(lambda X: -F(X), 1, 3), self.fplot(F, 3, Rr))
        lab = M(r"y=|x^2-4x+3|", size=34, color=S.OUTPUT).move_to(self.ax.c2p(-2.8, 3.2))
        panel = self.right_panel(6.1, "WORKED EXAMPLE · original")
        q = VGroup(M(r"|x^2-4x+3| = k", size=42),
                   T("(i) For which k are there exactly 3 real solutions?", size=24),
                   T("(ii) For which k are there exactly 4?", size=24)).arrange(DOWN, buff=0.25, aligned_edge=LEFT)
        S.fit(q, Rectangle(width=PANEL_W - 0.3, height=3), pad=0)
        q.move_to(panel[0]).align_to(panel[0], UP).shift(DOWN * 0.75)
        self.play(FadeIn(panel), Write(q[0]), FadeIn(q[1:]), run_time=1.5)
        self.say("अब एक exam-style question. | Mod of x squared minus 4x plus 3 equals k. | किस k के लिए exactly तीन real solutions हैं? और किस के लिए चार?",
                 hold=0.5)
        self.say("Pause करो, और पहले खुद सोचो।", hold=0.2)
        self.think(8)
        cue = VGroup(S.tag("RECOGNITION CUE", S.PARAM),
                     T("modulus equation  →  count where y = k meets the graph", size=23)).arrange(DOWN, buff=0.15, aligned_edge=LEFT)
        cue.next_to(q, DOWN, buff=0.4).align_to(q, LEFT)
        S.fit(cue, Rectangle(width=PANEL_W - 0.3, height=2))
        self.say("Recognition cue: | modulus वाली equation में solutions गिनने हों, तो graph बनाओ, | और horizontal line y equals k कितनी बार काटती है, वो गिनो।",
                 Create(g), FadeIn(cue), run_time=2.4)
        kv = ValueTracker(-0.6)

        def roots(kk):
            out = []
            if kk >= 0:
                d1 = 1 + kk
                out += [2 - np.sqrt(d1), 2 + np.sqrt(d1)]
                if kk < 1:
                    out += [2 - np.sqrt(1 - kk), 2 + np.sqrt(1 - kk)]
                elif abs(kk - 1) < 1e-9:
                    out += [2.0]
            return sorted(set(np.round(out, 9)))

        line = always_redraw(lambda: DashedLine(self.ax.c2p(XR[0] + 0.1, kv.get_value()),
                                                self.ax.c2p(XR[1] - 0.8, kv.get_value()),
                                                color=S.PARAM, stroke_width=4))
        dots = always_redraw(lambda: VGroup(*[S.dot(self.ax, r, kv.get_value(), color=S.FOCUS, r=0.08)
                                              for r in roots(kv.get_value())]))
        readout = always_redraw(lambda: VGroup(
            M(r"k=", size=36, color=S.PARAM),
            DecimalNumber(kv.get_value(), num_decimal_places=2, font_size=36, color=S.PARAM),
            M(r"\ \Rightarrow\ ", size=36),
            Integer(len(roots(kv.get_value())), font_size=40, color=S.FOCUS),
            T(" solutions", size=26, color=S.FOCUS)).arrange(RIGHT, buff=0.12)
            .next_to(self.axes_g, DOWN, buff=0.05).align_to(self.axes_g, LEFT).shift(RIGHT * 0.3))
        self.add(line, dots, readout)
        self.say("k negative हो तो line graph के नीचे है: zero solutions. | Mod कभी negative नहीं होता।", hold=0.3)
        self.say("k equals zero पर line सिर्फ x-intercepts छूती है: दो solutions, 1 और 3.",
                 kv.animate.set_value(0), run_time=1.5, sfx="move")
        self.say("k zero और 1 के बीच हो, तो line दोनों outer branches और flipped arch, सबको काटती है: चार solutions.",
                 kv.animate.set_value(0.55), run_time=1.8)
        self.say("k equals 1 पर line arch की top को बस छूती है। | Outer branches से दो, top से एक: exactly तीन.",
                 kv.animate.set_value(1), run_time=1.8, sfx="accent")
        self.say("और k 1 से बड़ा हो, तो फिर से सिर्फ दो।", kv.animate.set_value(2.4), run_time=1.8, hold=0.2)
        self.play(kv.animate.set_value(1), run_time=1.2)
        # algebraic verification
        self.play(FadeOut(VGroup(q[1:], cue)), run_time=0.5)
        v = VGroup(T("VERIFY at k = 1", size=24, color=S.MUTED, weight=BOLD),
                   M(r"x^2-4x+3=1 \Rightarrow x=2\pm\sqrt2", size=34),
                   M(r"x^2-4x+3=-1 \Rightarrow (x-2)^2=0 \Rightarrow x=2", size=34),
                   M(r"\text{total} = 2+1 = 3\ \checkmark", size=36, color=S.OK),
                   M(r"\text{(i) } k=1 \qquad \text{(ii) } 0<k<1", size=40, color=S.FOCUS))
        v.arrange(DOWN, buff=0.3, aligned_edge=LEFT)
        S.fit(v, Rectangle(width=PANEL_W - 0.3, height=4.2))
        v.next_to(q[0], DOWN, buff=0.45).align_to(q[0], LEFT)
        self.say("अब algebra से verify करते हैं। | Mod equals 1 का मतलब है expression equals 1 या expression equals minus 1.",
                 FadeIn(v[0]), Write(v[1]), run_time=2.0, dense=True)
        self.say("पहली से x equals 2 plus minus root 2: दो roots. | दूसरी से x minus 2 का square zero, यानी repeated root x equals 2.",
                 Write(v[2]), run_time=2.0, dense=True)
        self.say("Total तीन distinct solutions. | Graph और algebra agree करते हैं।", Write(v[3]), run_time=1.2, sfx="accent")
        self.say("Answer: | part one में k equals 1, | part two में k zero और 1 के बीच, open interval.",
                 Write(v[4]), run_time=1.4, sfx="release", hold=1.5)
        self.example_items = VGroup(g, panel, q[0], v)
        self.ex_line, self.ex_dots, self.ex_readout = line, dots, readout

    # 6. TRAP ---------------------------------------------------------------------
    def trap(self):
        self.remove(self.ex_line, self.ex_dots, self.ex_readout)
        self.play(FadeOut(self.example_items), run_time=0.8)
        self.mark("C01.7-trap", "Trap: f(x-2) shifts left?")
        panel = self.right_panel(5.9, None)
        ttag = S.tag("TRAP", S.RESTRICT).move_to(panel[0].get_corner(UL) + RIGHT * 0.75 + DOWN * 0.45)
        w1 = M(r"y=(x-2)^2", size=40)
        w2 = T("\"minus 2, so move left\"", size=28, color=S.RESTRICT)
        w3 = M(r"\text{test: } x=2 \Rightarrow y=0", size=38, color=S.OK)
        w4 = T("vertex is at x = +2 → RIGHT", size=28, color=S.OK)
        VGroup(w1, w2, w3, w4).arrange(DOWN, buff=0.4, aligned_edge=LEFT).move_to(panel[0]).shift(DOWN * 0.2)
        wrong = self.fplot(lambda X: (X + 2) ** 2, *clip_parabola(-2, 0), color=S.RESTRICT, dashed=True)
        cross = M(r"\times", size=60, color=S.RESTRICT).move_to(self.ax.c2p(-2, 4.8))
        self.say("अब एक बहुत common trap. | Y equals x minus 2 का square देखकर लगता है: minus 2 है, तो left जाओ।",
                 FadeIn(panel), FadeIn(ttag), Write(w1), FadeIn(w2), Create(wrong), run_time=2.0, sfx="wrong")
        self.music("off")
        self.wait(1.2)            # brief silence before the correction
        right = self.fplot(lambda X: (X - 2) ** 2, *clip_parabola(2, 0))
        self.say("एक सेकंड रुककर check करो। | x equals 2 रखो: y zero आता है। | मतलब vertex x equals plus 2 पर है, यानी right.",
                 Write(w3), FadeIn(cross), Create(right), FadeIn(w4), run_time=2.4)
        self.music("on")
        self.say("Reusable lesson: | sign से guess मत करो, एक point plug करके check करो।", sfx="accent", hold=0.8)
        self.play(FadeOut(VGroup(panel, ttag, w1, w2, w3, w4, wrong, cross, right)), run_time=0.8)

    # 7. ACTIVE RECALL ------------------------------------------------------------
    def recall(self):
        self.mark("C01.7-recall", "Recall: predict y = 2 - |x-1|")
        panel = self.right_panel(5.9, None)
        rtag = S.tag("ACTIVE RECALL", S.FOCUS).move_to(panel[0].get_corner(UL) + RIGHT * 1.25 + DOWN * 0.45)
        q = M(r"\text{Predict: } y = 2-|x-1|", size=42)
        hint = T("vertex? opens which way? range?", size=26, color=S.MUTED)
        VGroup(q, hint).arrange(DOWN, buff=0.3, aligned_edge=LEFT).move_to(panel[0]).shift(UP * 1.6)
        self.say("अब तुम्हारी बारी। | Graph बनने से पहले predict करो: y equals 2 minus mod of x minus 1. | Vertex कहाँ है, graph किस तरफ खुलता है, और range क्या है?",
                 FadeIn(panel), FadeIn(rtag), Write(q), FadeIn(hint), run_time=2.0)
        self.think(7)
        lo, hi = XR[0] + 0.1, XR[1] - 0.3
        steps = [
            (lambda X: abs(X), M(r"|x|", size=34)),
            (lambda X: abs(X - 1), M(r"|x-1|\ \text{(right 1)}", size=34)),
            (lambda X: -abs(X - 1), M(r"-|x-1|\ \text{(flip)}", size=34)),
            (lambda X: 2 - abs(X - 1), M(r"2-|x-1|\ \text{(up 2)}", size=34, color=S.FOCUS)),
        ]

        def piece(fn):  # exact corner: plot two straight pieces meeting at the vertex
            return VGroup(self.fplot(fn, max(lo, -6), 1 if fn is not steps[0][0] else 0, step=0.05),
                          self.fplot(fn, 1 if fn is not steps[0][0] else 0, hi, step=0.05))
        cur = piece(steps[0][0])
        col = VGroup(*[s[1] for s in steps]).arrange(DOWN, buff=0.14, aligned_edge=LEFT).next_to(hint, DOWN, buff=0.35).align_to(hint, LEFT)
        self.say("Mod x के V से शुरू करो।", Create(cur), FadeIn(col[0]), run_time=1.2)
        for fn, lab in steps[1:]:
            nxt = piece(fn)
            self.play(Transform(cur, nxt), FadeIn(lab), run_time=1.2)
            self.cue("move")
            self.wait(0.4)
        vtx = S.dot(self.ax, 1, 2, color=S.FOCUS)
        ans = VGroup(M(r"\text{vertex }(1,2),\ \text{opens down}", size=32, color=S.OK),
                     M(r"\text{range }(-\infty,2]", size=32, color=S.OK)).arrange(DOWN, buff=0.15, aligned_edge=LEFT)
        ans.next_to(col, DOWN, buff=0.3).align_to(col, LEFT)
        self.say("Right 1, फिर flip, फिर 2 ऊपर। | Vertex 1 comma 2, graph नीचे खुलता है, | और range minus infinity से 2 तक, 2 included.",
                 FadeIn(vtx), Write(ans), run_time=1.6, sfx="release", hold=1.0)
        self.play(FadeOut(VGroup(panel, rtag, q, hint, col, cur, vtx, ans)), run_time=0.8)

    # 8. CONNECTION + RECAP ------------------------------------------------------------
    def connection_and_recap(self):
        self.mark("C01.7-recap", "Connection and recap")
        F = lambda X: X ** 2 - 4 * X + 3
        L, Rr = 2 - np.sqrt(7) + 0.02, 2 + np.sqrt(7) - 0.02
        g = VGroup(self.fplot(F, L, 1), self.fplot(lambda X: -F(X), 1, 3), self.fplot(F, 3, Rr))
        c = VGroup(S.dot(self.ax, 1, 0, color=S.RESTRICT), S.dot(self.ax, 3, 0, color=S.RESTRICT))
        panel = self.right_panel(5.9, "WHERE THIS RETURNS")
        items = VGroup(
            VGroup(S.tag("C10", S.PARAM, 22), T("corners: continuous but not differentiable", size=24)).arrange(RIGHT, buff=0.25),
            VGroup(S.tag("C13", S.PARAM, 22), T("area uses |f|, not signed f", size=24)).arrange(RIGHT, buff=0.25),
            VGroup(S.tag("C02", S.PARAM, 22), T("roots = where the graph meets y = k", size=24)).arrange(RIGHT, buff=0.25),
        ).arrange(DOWN, buff=0.45, aligned_edge=LEFT).move_to(panel[0])
        self.say("Connection: | यही corners chapter 10 में दिखाएँगे कि continuous होना differentiable होने की guarantee नहीं है। | Chapter 13 में area निकालते वक्त भी mod f ही आएगा।",
                 Create(g), FadeIn(c), FadeIn(panel), LaggedStart(*[FadeIn(i) for i in items], lag_ratio=0.3), run_time=3.0)
        self.play(FadeOut(VGroup(g, c, panel, items, self.axes_g)), run_time=0.8)
        # recap card
        self.cue("motif", gain_db=-4)
        card = S.panel(13.2, 6.6, None).move_to(DOWN * 0.15)
        head = T("RECAP · Graph transformations", size=34, weight=BOLD).next_to(card[0].get_corner(UL), DR, buff=0.35)
        col1 = VGroup(
            T("MENTAL MODEL", size=22, color=S.MUTED, weight=BOLD),
            T("inside x: horizontal, opposite", size=26, color=S.INPUT),
            T("outside: vertical, as written", size=26, color=S.OUTPUT),
            T("conditions (domain, endpoints) move too", size=26),
            T("FORMULAS + CONDITIONS", size=22, color=S.MUTED, weight=BOLD),
            M(r"f(x-h)+k:\ \text{right } h,\ \text{up } k", size=32),
            M(r"a f(x),\ f(bx):\ a\neq0,\ b\neq0", size=32),
            M(r"|f(x)|\ \text{flips outputs};\ f(|x|)\ \text{is even}", size=32),
        ).arrange(DOWN, buff=0.2, aligned_edge=LEFT)
        col2 = VGroup(
            T("METHOD CUE", size=22, color=S.MUTED, weight=BOLD),
            T("count solutions of |g(x)| = k → draw, slide y = k", size=24),
            T("TRAPS", size=22, color=S.RESTRICT, weight=BOLD),
            T("f(x−2) is RIGHT, not left — plug a point", size=24),
            T("f(2x) squeezes, it does not stretch", size=24),
            T("|f(x)| ≠ f(|x|)", size=24),
            T("SELF-CHECK", size=22, color=S.FOCUS, weight=BOLD),
            M(r"\text{x-intercepts of } y=|x-2|-1\ ?", size=32),
        ).arrange(DOWN, buff=0.2, aligned_edge=LEFT)
        cols = VGroup(col1, col2).arrange(RIGHT, buff=0.8, aligned_edge=UP)
        S.fit(cols, Rectangle(width=card[0].width - 0.4, height=card[0].height - 1.3), pad=0.2)
        cols.next_to(head, DOWN, buff=0.35).align_to(head, LEFT)
        self.say("Recap. | Inside x का बदलाव horizontal और उल्टा, outside का vertical और सीधा। | Domain और endpoints भी साथ चलते हैं।",
                 FadeIn(card), FadeIn(head), FadeIn(col1), run_time=2.0, hold=1.0)
        self.say("Traps: f of x minus 2 right जाता है, f of 2x squeeze करता है, | और mod f, f of mod x के बराबर नहीं है।",
                 FadeIn(col2[:6]), run_time=1.5, hold=1.0)
        self.say("Self-check: | y equals mod of x minus 2, minus 1 के x-intercepts कहाँ हैं?", FadeIn(col2[6:]), run_time=1.0)
        self.think(6, where=DOWN * 2.85 + RIGHT * 4.3)
        a = M(r"x = 1,\ 3\ \checkmark", size=34, color=S.OK).next_to(col2[7], DOWN, buff=0.2).align_to(col2[7], LEFT)
        self.say("Answer: x equals 1 और 3, | क्योंकि mod of x minus 2 equals 1.", Write(a), sfx="release", hold=2.0)
        self.play(FadeOut(VGroup(card, head, col1, col2, a)), run_time=1.0)
        self.wait(0.5)
