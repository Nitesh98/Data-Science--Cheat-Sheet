"""
Builds Portfolio_Overview.pptx -- a 10-slide walkthrough of the four
portfolio case studies, for interview/promotion-packet use.

Every number below is transcribed from an already-computed, committed
output file (cited in each comment) -- the same numbers verified in
findings.json, the SQL results, and each project's readout -- not
re-derived here. This script only handles layout.

Built with pptx_builder.py (pure Python stdlib -- no pptxgenjs/python-pptx;
see README.md in this folder for why).

Run:
    python3 build_deck.py
Produces:
    Portfolio_Overview.pptx
"""
from pptx_builder import Presentation

# ---- Palette: "Midnight Executive" (navy / ice blue / white) ----
NAVY = "1E2761"
ICE = "CADCFC"
WHITE = "FFFFFF"
INK = "0B0B0B"
SECONDARY = "52514E"
MUTED = "898781"
CARD_BG = "EEF2FB"
GOOD = "0CA30C"
BAD = "D03B3B"
GRID = "E1E0D9"

W, H = 13.333, 7.5
MARGIN = 0.7


def tag(slide, text, x=MARGIN, y=0.5):
    slide.add_rect(x, y, 2.6, 0.4, fill=NAVY, radius=True)
    slide.add_textbox(x, y, 2.6, 0.4, [(text, 12, WHITE, True)], align="ctr", anchor="ctr")


def title(slide, text, x=MARGIN, y=1.0, w=None, color=NAVY, size=30):
    w = w or (W - 2 * MARGIN)
    slide.add_textbox(x, y, w, 0.7, [(text, size, color, True)], align="l", anchor="t")


def icon_row(slide, x, y, w, number_or_letter, heading, body, accent=NAVY, body_color=SECONDARY):
    slide.add_ellipse(x, y, 0.5, 0.5, fill=accent, text=str(number_or_letter), size=16)
    slide.add_textbox(x + 0.7, y - 0.05, w - 0.7, 0.35, [(heading, 14, INK, True)])
    slide.add_textbox(x + 0.7, y + 0.28, w - 0.7, 0.75, [(body, 11.5, body_color, False)])


def stat_card(slide, x, y, w, h, big, label, bg=CARD_BG, big_color=NAVY, label_color=SECONDARY, radius=True):
    slide.add_rect(x, y, w, h, fill=bg, radius=radius)
    slide.add_textbox(x + 0.25, y + 0.15, w - 0.5, h * 0.55, [(big, 34, big_color, True)], align="l", anchor="b")
    slide.add_textbox(x + 0.25, y + h * 0.6, w - 0.5, h * 0.4 - 0.15, [(label, 12, label_color, False)], align="l", anchor="t")


def footer(slide, text, color=MUTED):
    slide.add_textbox(MARGIN, H - 0.45, W - 2 * MARGIN, 0.3, [(text, 9, color, False)])


def build():
    prs = Presentation()

    # ================= Slide 1: Title =================
    s = prs.add_slide(bg_color=NAVY)
    s.add_textbox(1.0, 2.5, W - 2.0, 1.6,
                  [("Men's Footwear", 44, WHITE, True), ("Revenue & Growth Portfolio", 44, WHITE, True)],
                  align="ctr", anchor="ctr")
    s.add_textbox(1.0, 4.2, W - 2.0, 0.6,
                  [("Four connected case studies in analytics rigor and product judgment", 16, ICE, False)],
                  align="ctr", anchor="t")
    s.add_textbox(1.0, H - 0.9, W - 2.0, 0.4,
                  [("Synthetic, seeded data throughout -- a demonstration of method, not real company figures", 10.5, ICE, False)],
                  align="ctr", anchor="t")

    # ================= Slide 2: Overview + data note =================
    s = prs.add_slide(bg_color=WHITE)
    title(s, "What's inside")
    cards = [
        ("01", "Category Growth Diagnostic",
         "SQL + a hand-rolled statistics model: what's really driving 74% YoY growth, and what's just noise."),
        ("02", "Pricing / Messaging A/B Test",
         "A pre-registered experiment on scarcity messaging -- design, power calc, and an honest, nuanced call."),
        ("03", "PM Case Study: PRD + Roadmap",
         "A product spec and a RICE-scored roadmap, grounded directly in the analytics findings."),
        ("04", "Causal Discount Test (DiD)",
         "Resolving Project 01's own confound with a real natural-experiment design."),
    ]
    cw, ch, gap = (W - 2 * MARGIN - 0.4) / 2, 2.15, 0.4
    for i, (num, head, body) in enumerate(cards):
        cx = MARGIN + (i % 2) * (cw + gap)
        cy = 1.9 + (i // 2) * (ch + 0.3)
        s.add_rect(cx, cy, cw, ch, fill=CARD_BG, radius=True)
        s.add_ellipse(cx + 0.3, cy + 0.3, 0.6, 0.6, fill=NAVY, text=num, size=18)
        s.add_textbox(cx + 1.1, cy + 0.28, cw - 1.35, 0.5, [(head, 15, NAVY, True)])
        s.add_textbox(cx + 1.1, cy + 0.8, cw - 1.35, ch - 1.0, [(body, 11.5, SECONDARY, False)])
    s.add_rect(MARGIN, 6.6, W - 2 * MARGIN, 0.55, fill=ICE, radius=True)
    s.add_textbox(MARGIN + 0.25, 6.6, W - 2 * MARGIN - 0.5, 0.55,
                  [("Note: every dataset here is synthetically generated and seeded (see each project's generate_data.py) "
                    "-- this demonstrates method, not real Myntra numbers.", 10.5, NAVY, False)], anchor="ctr")

    # ================= Slide 3: Project 01 headline =================
    # Source: 01-Category-Growth-Diagnostic/findings.json + sql_queries/results/01_monthly_revenue_and_growth.md
    s = prs.add_slide(bg_color=WHITE)
    tag(s, "PROJECT 01")
    title(s, "Category Growth Diagnostic", y=1.0)
    stat_card(s, MARGIN, 1.9, 3.6, 1.9, "+73.8%", "YoY revenue growth\n(Rs 12.1 Cr -> Rs 21.1 Cr, Y1 to Y2)")
    s.add_textbox(MARGIN, 4.0, 3.6, 0.4, [("Quarterly revenue trend (Rs Cr):", 11, SECONDARY, True)])
    # quarterly revenue computed from the monthly SQL result (8 quarters, Jan'23-Dec'24)
    quarters = ["23 Q1", "23 Q2", "23 Q3", "23 Q4", "24 Q1", "24 Q2", "24 Q3", "24 Q4"]
    q_values = [1.88, 2.59, 3.33, 4.33, 4.60, 4.75, 5.38, 6.38]
    s.add_bar_chart(4.9, 1.9, W - MARGIN - 4.9, 3.3, quarters, q_values, NAVY,
                     value_fmt=lambda v: f"{v:.1f}", highlight_idx=7, highlight_color=GOOD)
    icon_row(s, MARGIN, 5.55, 3.7, "R", "Retention",
             "100% -> 33.2% (month 1) -> 7.6% (month 6) -- the month-1 drop is the single largest lever found.")
    icon_row(s, MARGIN + 4.1, 5.55, 3.7, "C", "Channels",
             "Paid Search/Social carry 60-66% new-customer share vs. Organic's 34% -- true acquisition engines.")
    icon_row(s, MARGIN + 8.2, 5.55, 3.7, "G", "Geography",
             "Tier 3 cities grew fastest YoY (+75.2%) -- not purely a metro story.")
    footer(s, "Source: findings.json, sql_queries/results/ -- 01-Category-Growth-Diagnostic")

    # ================= Slide 4: Project 01 -- the confound =================
    s = prs.add_slide(bg_color=WHITE)
    tag(s, "PROJECT 01 -- METHODOLOGY")
    title(s, "Rigor beats a good-looking number")
    lcw = (W - 2 * MARGIN - 0.4) / 2
    s.add_rect(MARGIN, 2.0, lcw, 3.6, fill=CARD_BG, radius=True)
    s.add_textbox(MARGIN + 0.3, 2.25, lcw - 0.6, 0.4, [("Naive regression", 14, NAVY, True)])
    s.add_textbox(MARGIN + 0.3, 2.75, lcw - 0.6, 1.0, [("+29.2%", 46, NAVY, True)])
    s.add_textbox(MARGIN + 0.3, 3.75, lcw - 0.6, 1.6,
                  [("order lift per +10pt discount, from a log-log regression on the raw data (n=120 category-months, R²=0.145)", 12, SECONDARY, False)])
    s.add_rect(MARGIN + lcw + 0.4, 2.0, lcw, 3.6, fill=NAVY, radius=True)
    s.add_textbox(MARGIN + lcw + 0.7, 2.25, lcw - 0.6, 0.4, [("The catch", 14, WHITE, True)])
    s.add_textbox(MARGIN + lcw + 0.7, 2.75, lcw - 0.6, 2.6,
                  [("Deep discounts cluster in festive/EOSS months -- which are independently high-demand periods. "
                    "This regression cannot tell \"the discount caused it\" apart from \"it was going to happen "
                    "anyway, in a month that also carried a discount.\"", 13, ICE, False)])
    s.add_textbox(MARGIN, 5.85, W - 2 * MARGIN, 0.6,
                  [("-> See Project 04: an isolated natural experiment resolves this confound directly.", 13, NAVY, True)])
    footer(s, "Source: 01-Category-Growth-Diagnostic/executive_summary.md")

    # ================= Slide 5: Project 02 design + results =================
    # Source: 02-Pricing-AB-Test/experiment_design.md + readout.md
    s = prs.add_slide(bg_color=WHITE)
    tag(s, "PROJECT 02")
    title(s, "Pricing / Messaging A/B Test")
    s.add_rect(MARGIN, 1.9, 4.3, 3.9, fill=CARD_BG, radius=True)
    s.add_textbox(MARGIN + 0.3, 2.1, 3.7, 0.4, [("Design (written before results)", 13, NAVY, True)])
    design_lines = [
        "Hypothesis: scarcity messaging lifts PDP -> Cart conversion",
        "Primary metric: conversion rate; guardrails: AOV, return rate",
        "Power calc: ~18,600 sessions/arm (80% power, +8% MDE)",
        "Duration: 21 days, no early stopping",
    ]
    yy = 2.6
    for ln in design_lines:
        s.add_ellipse(MARGIN + 0.3, yy, 0.16, 0.16, fill=NAVY)
        s.add_textbox(MARGIN + 0.6, yy - 0.14, 3.7, 0.55, [(ln, 11.5, SECONDARY, False)])
        yy += 0.68
    s.add_bar_chart(5.5, 1.9, W - MARGIN - 5.5, 3.3, ["Control", "Treatment"], [12.09, 12.91], NAVY,
                     value_fmt=lambda v: f"{v:.2f}%", highlight_idx=1, highlight_color=GOOD)
    s.add_textbox(5.5, 5.3, W - MARGIN - 5.5, 0.4, [("PDP -> Cart conversion rate", 11, SECONDARY, True)], align="ctr")
    s.add_textbox(MARGIN, 6.0, W - 2 * MARGIN, 0.7,
                  [("z = 2.85, p = 0.0044 -> statistically significant -- but +6.8% relative lift falls just short of the +8% MDE the test was powered for.", 13, INK, False)])
    footer(s, "Source: 02-Pricing-AB-Test/readout.md")

    # ================= Slide 6: Project 02 -- guardrail nuance =================
    s = prs.add_slide(bg_color=WHITE)
    tag(s, "PROJECT 02 -- GUARDRAILS")
    title(s, "A win with a catch")
    s.add_bar_chart(MARGIN, 1.9, 4.6, 3.5, ["Control", "Treatment"], [9.61, 11.45], NAVY,
                     value_fmt=lambda v: f"{v:.2f}%", highlight_idx=1, highlight_color=BAD)
    s.add_textbox(MARGIN, 5.35, 4.6, 0.4, [("Return rate (among converters)", 11, SECONDARY, True)], align="ctr")
    s.add_textbox(MARGIN, 5.85, 4.6, 0.5, [("+1.84 pts, p = 0.0156 -> a real regression, not noise", 11.5, BAD, True)])
    s.add_rect(5.9, 1.9, W - MARGIN - 5.9, 4.5, fill=NAVY, radius=True)
    s.add_textbox(6.2, 2.15, W - MARGIN - 6.2, 0.4, [("Recommendation", 14, WHITE, True)])
    s.add_textbox(6.2, 2.65, W - MARGIN - 6.4, 3.5,
                  [("Do not blanket-ship. AOV is clean, but the return-rate guardrail moved -- likely urgency "
                    "pulling forward size-uncertain purchases.", 12.5, ICE, False),
                   ("", 6, ICE, False),
                   ("Ship a scoped version: only below a low-stock threshold, paired with an inline size-guide "
                    "prompt. Hold a 2-week return-rate tripwire before calling it resolved.", 12.5, WHITE, True)])
    footer(s, "Source: 02-Pricing-AB-Test/readout.md")

    # ================= Slide 7: Project 03 PRD + RICE =================
    # Source: 03-PM-Smart-Fit-PRD-and-Roadmap/roadmap_prioritization.md, initiatives.csv
    s = prs.add_slide(bg_color=WHITE)
    tag(s, "PROJECT 03")
    title(s, "PM Case Study: PRD + RICE Roadmap")
    s.add_rect(MARGIN, 1.9, 4.1, 4.5, fill=CARD_BG, radius=True)
    s.add_textbox(MARGIN + 0.3, 2.1, 3.5, 0.4, [("Smart Size & Fit Recommendation", 13, NAVY, True)])
    prd_lines = [
        "Problem: Formal Shoes return ~14% vs ~5-10% baseline -- a sizing/fit gap sized directly from Project 01",
        "MVP: a static brand-fit badge, not a model -- test the mechanism before personalizing",
        "Guardrail: ship as an A/B test; conversion must not regress",
    ]
    yy = 2.6
    for ln in prd_lines:
        s.add_ellipse(MARGIN + 0.3, yy, 0.16, 0.16, fill=NAVY)
        s.add_textbox(MARGIN + 0.6, yy - 0.14, 3.3, 0.9, [(ln, 11.5, SECONDARY, False)])
        yy += 1.05
    initiatives = ["Budget\nreallocation", "Discount\ncalendar", "Retention\ncampaign", "Smart Fit\nMVP",
                   "Scarcity\nmsg. (scoped)", "Tier 3\nfulfillment", "Return-reason\ntagging"]
    rice_scores = [840.0, 120.0, 100.0, 72.0, 64.0, 17.5, 0.0]
    s.add_bar_chart(5.4, 1.9, W - MARGIN - 5.4, 4.5, initiatives, rice_scores, NAVY,
                     value_fmt=lambda v: f"{v:g}", highlight_idx=6, highlight_color=BAD)
    s.add_textbox(5.4, 6.35, W - MARGIN - 5.4, 0.3, [("RICE score, 7 initiatives (computed, not hand-ranked)", 10.5, SECONDARY, True)], align="ctr")
    footer(s, "Source: 03-PM-Smart-Fit-PRD-and-Roadmap/roadmap_prioritization.md")

    # ================= Slide 8: Project 03 -- reading the ranking =================
    s = prs.add_slide(bg_color=WHITE)
    tag(s, "PROJECT 03 -- JUDGMENT")
    title(s, "A score is an input, not an answer")
    icon_row(s, MARGIN, 2.1, W - 2 * MARGIN, 1,
             "Real data beats a good estimate",
             "Scoped scarcity messaging ranks high on confidence (0.8) because it's backed by an actual completed "
             "experiment (Project 02) -- not a guess. It should be sequenced first: nearly shipped already.")
    icon_row(s, MARGIN, 3.5, W - 2 * MARGIN, 2,
             "A confidence score can do real work",
             "Discount-calendar redesign scores 120 on reach and effort alone -- but Project 01 already flagged its "
             "elasticity estimate as confounded, so confidence was deliberately set low (0.2). A naive score would over-rank it.")
    icon_row(s, MARGIN, 4.9, W - 2 * MARGIN, 3,
             "RICE has a blind spot -- know it",
             "Return-reason tagging scores 0.0 because RICE divides by \"reach,\" which is undefined for pure "
             "infrastructure work. It's still sequenced first in practice: it's a hard blocker for the PRD above.")
    footer(s, "Source: 03-PM-Smart-Fit-PRD-and-Roadmap/roadmap_prioritization.md")

    # ================= Slide 9: Project 04 causal DiD =================
    # Source: 04-Causal-Discount-Effect-DiD/causal_readout.md
    s = prs.add_slide(bg_color=WHITE)
    tag(s, "PROJECT 04")
    title(s, "Closing the loop: does a discount really cause demand?")
    s.add_bar_chart(MARGIN, 2.0, 5.6, 3.4, ["Naive\n(confounded)", "Causal\n(DiD)"], [29.2, 13.8], NAVY,
                     value_fmt=lambda v: f"{v:.1f}%", highlight_idx=1, highlight_color=GOOD)
    s.add_textbox(MARGIN, 5.5, 5.6, 0.4, [("% order lift per +10pt discount", 11, SECONDARY, True)], align="ctr")
    s.add_rect(6.9, 2.0, W - MARGIN - 6.9, 3.9, fill=CARD_BG, radius=True)
    s.add_textbox(7.2, 2.2, W - MARGIN - 7.4, 0.4, [("How it's identified", 13, NAVY, True)])
    s.add_textbox(7.2, 2.7, W - MARGIN - 7.4, 1.3,
                  [("Sneakers ran an isolated clearance discount in a seasonally flat month (May) -- no other "
                    "category or season changed. Difference-in-differences vs. 4 untouched categories isolates "
                    "the discount's own effect.", 11.5, SECONDARY, False)])
    s.add_textbox(7.2, 4.1, W - MARGIN - 7.4, 0.4, [("Parallel-trends check:", 12, NAVY, True)])
    s.add_textbox(7.2, 4.45, W - MARGIN - 7.4, 0.4, [("r = 0.67 to 0.96 across the 4 controls, pre-period", 11.5, SECONDARY, False)])
    s.add_textbox(7.2, 4.95, W - MARGIN - 7.4, 0.4, [("Significance (permutation test):", 12, NAVY, True)])
    s.add_textbox(7.2, 5.3, W - MARGIN - 7.4, 0.55,
                  [("p ≈ 0.20 -- with only 4 placebo draws, this is the test's own floor, stated plainly rather than hidden.", 11.5, SECONDARY, False)])
    footer(s, "Source: 04-Causal-Discount-Effect-DiD/causal_readout.md")

    # ================= Slide 10: Closing =================
    s = prs.add_slide(bg_color=NAVY)
    s.add_textbox(MARGIN, 0.8, W - 2 * MARGIN, 0.8, [("Why this portfolio", 32, WHITE, True)])
    icon_row(s, MARGIN, 2.1, W - 2 * MARGIN, 1, "One thread, four layers",
             "SQL -> statistics -> experiment design -> causal inference -> product prioritization, all pointed at the same sizing/returns problem.",
             accent=ICE, body_color=ICE)
    icon_row(s, MARGIN, 3.3, W - 2 * MARGIN, 2, "Caveats are on purpose",
             "A flagged confound, a stated permutation-test floor, a RICE blind spot named out loud -- the judgment is the deliverable, not just the numbers.",
             accent=ICE, body_color=ICE)
    icon_row(s, MARGIN, 4.5, W - 2 * MARGIN, 3, "Built to be verified",
             "Every chart and stat here is generated by a script in the repo -- rerun it and the numbers reproduce exactly.",
             accent=ICE, body_color=ICE)
    s.add_textbox(MARGIN, 6.3, W - 2 * MARGIN, 0.5,
                  [("github.com/Nitesh98/Data-Science--Cheat-Sheet -- Portfolio Projects/", 12, WHITE, True)])
    s.add_textbox(MARGIN, 6.75, W - 2 * MARGIN, 0.4,
                  [("Synthetic data throughout -- ask me anything about the method.", 10.5, ICE, False)])

    prs.save("Portfolio_Overview.pptx")
    print(f"Wrote Portfolio_Overview.pptx ({len(prs.slides)} slides)")


if __name__ == "__main__":
    build()
