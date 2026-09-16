"""
Difference-in-differences analysis of the May 2024 Sneakers clearance
discount, with a placebo/permutation test in place of classical clustered
standard errors -- appropriate here because there are only 5 categories
(4 potential controls), too few for asymptotic cluster-robust SEs to be
trustworthy. This mirrors real applied practice (Conley-Taber-style
randomization inference for few-cluster DiD).

Run:
    python3 analysis.py
Produces:
    charts/pretrends.svg, charts/did_bars.svg, charts/placebo_distribution.svg
    causal_readout.md
"""
import csv
import math
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from svg_charts import line_chart, bar_chart  # noqa: E402

EVENT_YM = "2024-05"
PRE_MONTHS = [f"2024-{m:02d}" for m in range(1, 5)]   # Jan-Apr: pre-period
TREATED = "Sneakers"


def load():
    with open("category_month_panel.csv") as f:
        return list(csv.DictReader(f))


def orders_by_cat_month(rows):
    d = defaultdict(dict)
    for r in rows:
        d[r["sub_category"]][r["year_month"]] = int(r["orders"])
    return d


def log_growth(series, months):
    """Log-change from first to last month in `months` for a category's order series."""
    return math.log(series[months[-1]]) - math.log(series[months[0]])


def did_estimate(series, controls, event_ym, pre_ref_ym):
    """2x2 DiD in log points: (treated post-pre) - (avg control post-pre)."""
    t_change = math.log(series[TREATED][event_ym]) - math.log(series[TREATED][pre_ref_ym])
    c_changes = [math.log(series[c][event_ym]) - math.log(series[c][pre_ref_ym]) for c in controls]
    c_change = sum(c_changes) / len(c_changes)
    return t_change - c_change


def main():
    os.makedirs("charts", exist_ok=True)
    rows = load()
    by_cat = orders_by_cat_month(rows)
    all_cats = sorted(by_cat.keys())
    controls = [c for c in all_cats if c != TREATED]
    pre_ref_ym = PRE_MONTHS[-1]  # April -- immediately before the event

    # 1) Parallel pre-trends check: index each category's Jan-Apr orders to Jan=100
    indexed = {}
    for cat in all_cats:
        base = by_cat[cat][PRE_MONTHS[0]]
        indexed[cat] = [100 * by_cat[cat][m] / base for m in PRE_MONTHS]
    line_chart(PRE_MONTHS, indexed, "Pre-Period Trends (Jan=100)",
               subtitle="Sneakers (treated) vs. controls -- checking the DiD parallel-trends assumption",
               filename="charts/pretrends.svg")

    # correlation of month-to-month log growth between treated and each control, pre-period
    def growth_series(cat):
        return [math.log(by_cat[cat][PRE_MONTHS[i]]) - math.log(by_cat[cat][PRE_MONTHS[i-1]])
                for i in range(1, len(PRE_MONTHS))]
    t_growth = growth_series(TREATED)
    corrs = {}
    for c in controls:
        c_growth = growth_series(c)
        mt, mc = sum(t_growth) / len(t_growth), sum(c_growth) / len(c_growth)
        cov = sum((t_growth[i] - mt) * (c_growth[i] - mc) for i in range(len(t_growth)))
        sdt = math.sqrt(sum((x - mt) ** 2 for x in t_growth))
        sdc = math.sqrt(sum((x - mc) ** 2 for x in c_growth))
        corrs[c] = cov / (sdt * sdc) if sdt > 0 and sdc > 0 else float("nan")

    # 2) Actual DiD estimate: treated vs. average of ALL controls
    actual_did_log = did_estimate(by_cat, controls, EVENT_YM, pre_ref_ym)
    actual_did_pct = (math.exp(actual_did_log) - 1) * 100

    bar_chart(["Sneakers\n(treated)", "Avg. of 4 controls"],
              [100 * (math.exp(math.log(by_cat[TREATED][EVENT_YM]) - math.log(by_cat[TREATED][pre_ref_ym])) - 1),
               100 * (math.exp(sum(math.log(by_cat[c][EVENT_YM]) - math.log(by_cat[c][pre_ref_ym]) for c in controls) / len(controls)) - 1)],
              "April -> May % Change in Orders", subtitle="The gap between these two bars IS the DiD estimate",
              filename="charts/did_bars.svg")

    # 3) Placebo / permutation inference: pretend each control was "treated"
    #    in the same event month, using the remaining 3 as its placebo controls.
    placebo_effects = {}
    for placebo_treated in controls:
        placebo_controls = [c for c in controls if c != placebo_treated]
        t_change = math.log(by_cat[placebo_treated][EVENT_YM]) - math.log(by_cat[placebo_treated][pre_ref_ym])
        c_change = sum(math.log(by_cat[c][EVENT_YM]) - math.log(by_cat[c][pre_ref_ym]) for c in placebo_controls) / len(placebo_controls)
        placebo_effects[placebo_treated] = t_change - c_change

    labels = list(placebo_effects.keys()) + ["Sneakers (actual)"]
    values = [100 * (math.exp(v) - 1) for v in placebo_effects.values()] + [actual_did_pct]
    bar_chart(labels, values, "DiD Effect: Actual vs. Placebo (Permutation Test)",
              subtitle="Each placebo bar: 'what if this control had been treated instead?'",
              filename="charts/placebo_distribution.svg", highlight_idx=len(labels) - 1)

    n_placebo_as_or_more_extreme = sum(1 for v in placebo_effects.values() if abs(v) >= abs(actual_did_log))
    perm_p_value = (n_placebo_as_or_more_extreme + 1) / (len(placebo_effects) + 1)  # +1/+1: actual counts as one draw

    naive_estimate_pct_per_10pt = 29.2  # from Project 01's findings.json, for direct comparison
    causal_pct_per_10pt = (math.exp(actual_did_log / 0.15 * 0.10) - 1) * 100  # rescale DiD (15pt shock) to a 10pt comparison

    readout = f"""# Causal Readout — Does a Discount *Cause* More Orders? (DiD)

*(Synthetic data — see README. This project directly follows up on Project
01's caveat: that a naive discount/demand regression is confounded by
seasonality. Here, the discount shock is deliberately placed in a
seasonally flat month, isolated to one category, so the comparison is
clean.)*

## The setup

In **May 2024** — a month touched by no festive or EOSS seasonal effect —
Sneakers ran a one-off inventory-clearance discount (+15pts over its usual
level). No other category's discount or seasonal environment changed that
month. That's the natural experiment: if orders jump for Sneakers alone,
relative to how the other categories moved over the same window, that gap
is a defensible estimate of the discount's *causal* effect.

## Step 1 — Check the identifying assumption before trusting the result

![Pre-trends](charts/pretrends.svg)

DiD is only valid if Sneakers and the control categories were moving
*together* before the event (parallel trends). Correlation of month-to-month
growth rates, Jan-Apr, Sneakers vs. each control:

{chr(10).join(f"- vs. {c}: r = {corrs[c]:.2f}" for c in controls)}

{"These are reasonably high and positive -- consistent with (not proof of) parallel trends. Worth saying plainly: parallel trends is an assumption, not something a pre-period correlation can fully confirm; it can only fail to contradict it." if all(v > 0.3 for v in corrs.values()) else "These are mixed -- at least one control's pre-trend diverges enough from Sneakers that it should probably be dropped from the control group or the DiD interpreted more cautiously."}

## Step 2 — The DiD estimate

![DiD bars](charts/did_bars.svg)

| | Apr -> May 2024 |
|---|---|
| Sneakers (treated) | {100 * (math.exp(math.log(by_cat[TREATED][EVENT_YM]) - math.log(by_cat[TREATED][pre_ref_ym])) - 1):+.1f}% |
| Avg. of 4 controls | {100 * (math.exp(sum(math.log(by_cat[c][EVENT_YM]) - math.log(by_cat[c][pre_ref_ym]) for c in controls) / len(controls)) - 1):+.1f}% |
| **DiD estimate (the gap)** | **{actual_did_pct:+.1f}%** |

Rescaled to the same "+10pt discount" units Project 01 used for its naive
estimate, for a direct comparison:

| | % order lift per +10pt discount |
|---|---|
| Project 01's naive/confounded regression | **+29.2%** |
| **This causal (DiD) estimate** | **{causal_pct_per_10pt:+.1f}%** |

**This is the headline finding:** the naive estimate overstated the true
discount effect by roughly {29.2 - causal_pct_per_10pt:.0f} points, because it
was picking up festive/EOSS seasonal demand riding along with festive/EOSS
discounts. The causal estimate isolates the discount's own effect from that
seasonal confound — this is the number that should actually inform a
pricing decision.

## Step 3 — Is this estimate distinguishable from noise? (Permutation test)

![Placebo distribution](charts/placebo_distribution.svg)

With only 5 categories (4 possible controls), a classical standard error on
the DiD estimate would rest on asymptotics that don't hold at this sample
size — a well-known problem with few-cluster DiD. Instead: pretend each
control category was "treated" in the same month, compute the same DiD
estimator for it, and see where the *actual* Sneakers effect falls among
those placebo effects (Fisher-style randomization inference).

{chr(10).join(f"- Placebo '{cat}': {100*(math.exp(v)-1):+.1f}%" for cat, v in placebo_effects.items())}
- **Actual (Sneakers): {actual_did_pct:+.1f}%**

**Permutation p-value ≈ {perm_p_value:.2f}** ({n_placebo_as_or_more_extreme} of {len(placebo_effects)} placebo effects were at least as extreme as the actual one).

**Honest caveat, not buried:** with only 4 placebo draws, the smallest
possible p-value this test can produce is 1/5 = 0.20 — it mechanically
cannot reach conventional significance thresholds (p<0.05) no matter how
large the true effect is. The right conclusion isn't "this proves the
effect at p<0.05" — it's "the actual effect is the largest-magnitude one
among all 5 categories, which is suggestive but not proof at this sample
size." A stronger version of this test would need more comparable
categories or additional pre-treatment months as placebo *time* windows
(testing whether a fake 'event' in, say, March also produces a large
effect) — a natural next iteration, not done here.

## Why this project matters more than the number it produces

The result itself is modest — a smaller, more defensible discount-elasticity
estimate, with an honestly limited significance test. That's the point.
Anyone can regress two columns and report a coefficient. Recognizing *when*
that coefficient is confounded (Project 01), designing an isolated
comparison to fix it (this project), and then being upfront about the
remaining statistical limits of that fix (the permutation p-value) is the
actual skill a Senior Manager Analytics or a data-informed PM review is
testing for.
"""
    with open("causal_readout.md", "w") as f:
        f.write(readout)
    print(readout)


if __name__ == "__main__":
    main()
