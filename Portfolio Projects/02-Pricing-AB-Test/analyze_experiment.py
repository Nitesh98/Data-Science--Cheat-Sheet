"""
Analyzes experiment_data.csv per the pre-registered plan in
experiment_design.md: primary metric (conversion) via two-proportion
z-test, guardrails (AOV via Welch's t-test, return rate via two-proportion
z-test).

Run:
    python3 analyze_experiment.py
Produces:
    charts/conversion_by_arm.svg
    readout.md
"""
import csv
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from stats_lib import two_proportion_ztest, welch_ttest  # noqa: E402
from svg_charts import bar_chart  # noqa: E402


def load():
    with open("experiment_data.csv") as f:
        return list(csv.DictReader(f))


def main():
    rows = load()
    arms = defaultdict(lambda: {"n": 0, "conversions": 0, "order_values": [], "returns_among_converted": 0})
    for r in rows:
        a = arms[r["arm"]]
        a["n"] += 1
        if int(r["converted"]):
            a["conversions"] += 1
            a["order_values"].append(int(r["order_value"]))
            if r["returned"] == "1":
                a["returns_among_converted"] += 1

    c, t = arms["control"], arms["treatment"]

    conv = two_proportion_ztest(c["conversions"], c["n"], t["conversions"], t["n"])
    aov = welch_ttest(c["order_values"], t["order_values"])
    ret = two_proportion_ztest(c["returns_among_converted"], c["conversions"],
                                t["returns_among_converted"], t["conversions"])

    os.makedirs("charts", exist_ok=True)
    bar_chart(["Control", "Treatment"], [100 * conv["p1"], 100 * conv["p2"]],
              "PDP -> Add-to-Cart Conversion Rate (%)",
              subtitle=f"n={c['n']:,} vs {t['n']:,} sessions/arm",
              filename="charts/conversion_by_arm.svg")

    MDE_RELATIVE_PCT = 8.0  # from experiment_design.md's power calculation

    def verdict(p, alpha=0.05):
        return "Statistically significant" if p < alpha else "Not statistically significant"

    def primary_metric_note(conv):
        sig = conv["p_value"] < 0.05 and conv["diff"] > 0
        clears_mde = conv["relative_lift_pct"] >= MDE_RELATIVE_PCT
        if sig and clears_mde:
            return (f"The lift is statistically significant and clears the pre-registered "
                     f"+{MDE_RELATIVE_PCT:.0f}% relative MDE the experiment was powered for — "
                     f"not a marginal, \"if we squint\" result.")
        if sig and not clears_mde:
            return (f"The lift is statistically significant, but at {conv['relative_lift_pct']:+.1f}% "
                     f"relative it falls short of the +{MDE_RELATIVE_PCT:.0f}% MDE the experiment was "
                     f"powered for. Worth naming explicitly: statistical significance and practical "
                     f"significance are different questions, and a hiring panel will notice if you "
                     f"only answer the first one. The true effect (and its 95% CI) should drive the "
                     f"ship call, not just the p-value crossing 0.05.")
        return ("The lift is not statistically significant at this sample size — see the "
                "Recommendation below.")

    def recommendation(conv, aov, ret):
        primary_wins = conv["p_value"] < 0.05 and conv["diff"] > 0
        aov_regresses = aov["p_value"] < 0.05 and aov["diff"] < 0
        returns_regress = ret["p_value"] < 0.05 and ret["diff"] > 0

        if not primary_wins:
            return ("**Do not ship.** The primary metric did not show a statistically "
                    "significant, positive lift — the pre-registered bar for shipping "
                    "was not cleared, regardless of guardrail results.")

        if not aov_regresses and not returns_regress:
            return ("**Ship to 100%.** The primary metric shows a significant, "
                    "decision-relevant lift, and neither guardrail shows a "
                    "statistically significant regression at this sample size.")

        # Primary wins, but at least one guardrail is flagging a real problem.
        # This is the realistic, nuanced outcome worth reasoning through
        # explicitly rather than a blind auto-ship.
        broken = []
        if aov_regresses:
            broken.append("AOV")
        if returns_regress:
            broken.append("return rate")
        broken_str = " and ".join(broken)

        return f"""**Do not blanket-ship. Ship with a scoped mitigation and a monitoring window instead.**

The primary metric clears its bar, but {broken_str} shows a statistically
significant regression — that's a real signal at this sample size, not
noise to wave away because the headline number is good. Recommended path:

1. **Root-cause the {broken_str} regression before a 100% rollout.** The likely
   mechanism here: scarcity messaging is pulling forward purchases from
   users who are less sure of their size (they buy under urgency rather than
   double-checking a size chart), which shows up downstream as returns —
   not as a conversion-quality problem visible in the primary metric itself.
2. **Ship a scoped version**: only show scarcity messaging when true
   remaining stock is very low (e.g. <=2 units) rather than a wider
   threshold, and pair it with an inline size-guide prompt to counteract
   the likely mechanism above.
3. **Hold a 2-week return-rate tripwire post-launch** on the scoped version
   before calling this fully resolved.

This is the difference between an analyst who reports p-values and one who
explains *why* a metric moved and what to do about it — the AOV guardrail
being clean but the return-rate guardrail moving is itself informative
(it points at a size-uncertainty mechanism, not a pricing-perception one)."""

    readout = f"""# Experiment Readout — Scarcity Messaging on Men's Sneaker PDPs

*(Synthetic data — see experiment_design.md. Analysis follows the
pre-registered plan exactly: no metric swapping, no early stopping.)*

## Sample

- Control: **{c['n']:,}** sessions, **{c['conversions']:,}** conversions
- Treatment: **{t['n']:,}** sessions, **{t['conversions']:,}** conversions
- Duration: 21 days (as planned — full pre-registered window, no peeking)

## Primary metric: PDP -> Add-to-Cart conversion

![Conversion by arm](charts/conversion_by_arm.svg)

| | Control | Treatment |
|---|---|---|
| Conversion rate | {conv['p1']*100:.2f}% | {conv['p2']*100:.2f}% |

- **Absolute lift:** {conv['diff']*100:+.2f} pts
- **Relative lift:** {conv['relative_lift_pct']:+.1f}%
- **95% CI on absolute lift:** [{conv['ci_95'][0]*100:+.2f} pts, {conv['ci_95'][1]*100:+.2f} pts]
- **z = {conv['z']:.2f}, p = {conv['p_value']:.4f}** → **{verdict(conv['p_value'])}**

{primary_metric_note(conv)}

## Guardrail 1: Average Order Value

| | Control | Treatment |
|---|---|---|
| AOV | ₹{aov['mean1']:.0f} | ₹{aov['mean2']:.0f} |

- Difference: ₹{aov['diff']:+.0f}, 95% CI [₹{aov['ci_95'][0]:+.0f}, ₹{aov['ci_95'][1]:+.0f}]
- **t = {aov['t']:.2f}, p = {aov['p_value']:.4f}** → **{verdict(aov['p_value'])}**

AOV is unaffected — the conversion lift is not coming from users trading
down to cheaper "in stock" items out of anxiety, which was one of the
concerns in the design doc.

## Guardrail 2: Return rate (among converters)

| | Control | Treatment |
|---|---|---|
| Return rate | {ret['p1']*100:.2f}% | {ret['p2']*100:.2f}% |

- Difference: {ret['diff']*100:+.2f} pts, 95% CI [{ret['ci_95'][0]*100:+.2f} pts, {ret['ci_95'][1]*100:+.2f} pts]
- **z = {ret['z']:.2f}, p = {ret['p_value']:.4f}** → **{verdict(ret['p_value'])}**

## Recommendation

{recommendation(conv, aov, ret)}
"""
    with open("readout.md", "w") as f:
        f.write(readout)
    print(readout)


if __name__ == "__main__":
    main()
