"""
Aggregates simulation_results.csv into the actual decision the business
question needs answered: which commercial model (MP/OR/SOR) wins, and does
the answer change by how predictable a SKU's sell-through is?

Run:
    python3 analysis.py
Produces:
    charts/*.svg
    decision_readout.md
"""
import csv
import os
import statistics as stats
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from svg_charts import grouped_bar_chart, bar_chart  # noqa: E402

MODELS = ["MP", "OR", "SOR"]
TIERS = ["Hot / predictable", "Medium", "Slow / high-uncertainty"]


def load():
    with open("simulation_results.csv") as f:
        return list(csv.DictReader(f))


def group(rows, tier, model):
    return [r for r in rows if r["tier"] == tier and r["model"] == model]


def main():
    rows = load()
    os.makedirs("charts", exist_ok=True)

    profit_mean = defaultdict(dict)
    profit_std = defaultdict(dict)
    sellthrough_mean = defaultdict(dict)
    pct_loss = defaultdict(dict)
    roce_or = {}

    for tier in TIERS:
        for model in MODELS:
            g = group(rows, tier, model)
            profits = [float(r["profit"]) for r in g]
            profit_mean[tier][model] = stats.mean(profits)
            profit_std[tier][model] = stats.pstdev(profits)
            sellthrough_mean[tier][model] = stats.mean(float(r["sell_through_pct"]) for r in g)
            pct_loss[tier][model] = 100 * sum(1 for p in profits if p < 0) / len(profits)
        capital = [float(r["capital_employed"]) for r in group(rows, tier, "OR")]
        or_profits = [float(r["profit"]) for r in group(rows, tier, "OR")]
        roce_or[tier] = 100 * stats.mean(or_profits) / stats.mean(capital)

    # ---- Chart 1: expected profit by model x tier ----
    grouped_bar_chart(TIERS, {m: [round(profit_mean[t][m]) for t in TIERS] for m in MODELS},
                       "Expected Platform Profit by Model & Demand Tier", subtitle="INR, per SKU-season, mean of 2,000 paired trials",
                       filename="charts/01_expected_profit.svg",
                       value_fmt=lambda v: f"{v/1000:.0f}K")

    # ---- Chart 2: profit risk (std dev) by model x tier ----
    grouped_bar_chart(TIERS, {m: [round(profit_std[t][m]) for t in TIERS] for m in MODELS},
                       "Profit Volatility by Model & Demand Tier", subtitle="Std. dev. of profit across trials -- higher = riskier",
                       filename="charts/02_profit_risk.svg",
                       value_fmt=lambda v: f"{v/1000:.0f}K")

    # ---- Chart 3: sell-through by model x tier (the control effect) ----
    grouped_bar_chart(TIERS, {m: [round(sellthrough_mean[t][m], 1) for t in TIERS] for m in MODELS},
                       "Sell-Through Rate by Model & Demand Tier", subtitle="% of ordered units sold by season end",
                       filename="charts/03_sell_through.svg",
                       value_fmt=lambda v: f"{v:.0f}%")

    # ---- Chart 4: P(loss) -- downside risk, most relevant for OR ----
    grouped_bar_chart(TIERS, {m: [round(pct_loss[t][m], 1) for t in TIERS] for m in MODELS},
                       "Probability of a Loss-Making Season by Model & Tier", subtitle="% of trials where platform profit < 0",
                       filename="charts/04_loss_probability.svg",
                       value_fmt=lambda v: f"{v:.0f}%")

    # Winner per tier (by expected profit)
    winner = {t: max(MODELS, key=lambda m: profit_mean[t][m]) for t in TIERS}
    reward_per_risk = {t: {m: profit_mean[t][m] / profit_std[t][m] for m in MODELS} for t in TIERS}
    or_edge_over_sor_pct = {t: 100 * (profit_mean[t]["OR"] - profit_mean[t]["SOR"]) / profit_mean[t]["SOR"] for t in TIERS}

    def tier_recommendation(t):
        edge = or_edge_over_sor_pct[t]
        or_loss = pct_loss[t]["OR"]
        if or_loss >= 10:
            return (f"**SOR, unless the platform is explicitly risk-neutral.** OR's expected-profit edge over SOR "
                     f"is only {edge:.0f}% here, while OR now carries a {or_loss:.0f}% chance of a loss-making "
                     f"season (vs. 0% for SOR) and the worst reward-per-unit-risk of the three models "
                     f"({reward_per_risk[t]['OR']:.1f}, vs. {reward_per_risk[t]['SOR']:.1f} for SOR). That small "
                     f"an expected-profit edge is a thin justification for underwriting real capital-loss risk.")
        if or_loss >= 2:
            return (f"**Genuine judgment call.** OR still leads on expected profit (+{edge:.0f}% over SOR), but its "
                     f"loss probability ({or_loss:.1f}%) and reward-per-risk ({reward_per_risk[t]['OR']:.1f}) are "
                     f"both worse than SOR's ({reward_per_risk[t]['SOR']:.1f}). A capital-rich, risk-neutral platform "
                     f"should still take OR; a more risk-averse one has a legitimate case for SOR instead.")
        return (f"**OR.** Expected-profit edge over SOR is +{edge:.0f}%, loss probability is negligible "
                f"({or_loss:.1f}%), and the extra risk of owning inventory is well contained at this predictability "
                f"level — this is where taking the risk clearly pays for itself.")

    readout = f"""# Decision Readout — MP vs. OR vs. SOR

*(Synthetic simulation — see README. A paired Monte Carlo design: within
each trial, all three models see the identical order quantity and demand
draw, isolating the effect of who controls pricing/markdown. Demand
response to discount reuses Project 04's causal elasticity estimate.)*

## Headline: expected profit by model and demand-predictability tier

![Expected profit](charts/01_expected_profit.svg)

| Tier | MP | OR | SOR | Highest expected profit |
|---|---|---|---|---|
""" + "\n".join(
        f"| {t} | Rs {profit_mean[t]['MP']/1000:.0f}K | Rs {profit_mean[t]['OR']/1000:.0f}K | Rs {profit_mean[t]['SOR']/1000:.0f}K | {winner[t]} |"
        for t in TIERS
    ) + f"""

Raw expected profit says "always pick OR" — but that's not the same
question as "which model should the platform actually choose," once risk
is on the table. See the decision rule below.

## Why control matters even before you look at risk

![Sell-through](charts/03_sell_through.svg)

Sell-through is meaningfully higher under OR/SOR than MP **at every tier**
— not because the platform is smarter than the brand, but because the
platform controls the markdown trigger and the brand does not. A brand
selling the same style across many channels optimizes markdowns for its
whole business, not for this platform's specific overstock — a standard
channel/agency friction. Losing pricing control costs real sell-through
before a single rupee of inventory risk is even considered.

## But control isn't free — it comes with risk

![Profit risk](charts/02_profit_risk.svg)
![Loss probability](charts/04_loss_probability.svg)

OR's profit volatility is dramatically higher than MP's or SOR's,
especially in the **Slow / high-uncertainty** tier — because OR is the only
model where the platform's own capital is on the line if a style flops.
Return on capital employed for OR, by tier: {", ".join(f"{t}: {roce_or[t]:.0f}%" for t in TIERS)}.
SOR captures nearly the same pricing-control upside as OR **without** that
capital exposure — the transfer-price mechanism prices the risk into the
brand's side of the deal instead.

## The decision rule this actually implies

**OR wins on raw expected profit in all three tiers** — that's the number
a naive read would stop at. But OR's *edge* over SOR shrinks, and its risk
grows, as demand gets harder to forecast:

| Tier | OR's profit edge over SOR | OR loss probability | Reward-per-risk (mean/sd): OR vs. SOR | Recommendation |
|---|---|---|---|---|
""" + "\n".join(
        f"| {t} | +{or_edge_over_sor_pct[t]:.0f}% | {pct_loss[t]['OR']:.1f}% | {reward_per_risk[t]['OR']:.1f} vs. {reward_per_risk[t]['SOR']:.1f} | {tier_recommendation(t).split('.')[0].strip('*')} |"
        for t in TIERS
    ) + "\n\n" + "\n\n".join(f"**{t}:** {tier_recommendation(t)}" for t in TIERS) + f"""

**MP never wins on either dimension in this model** — it has the lowest
expected profit *and* (because it deploys no capital and earns a thin,
stable commission slice) the least risk, making it the floor option: only
worth choosing when the platform has essentially zero risk appetite, or a
brand relationship that mandates marketplace terms, not a genuine
profit-maximizing choice on these numbers.

## Honest caveats

- **The MP "muted markdown" policy is a modeling assumption, not a
  measured one.** It represents a real, well-understood channel-conflict
  mechanism (brands don't optimize markdowns for one platform's overstock),
  but its exact shape here (thresholds, discount depth) is illustrative.
  The qualitative direction — platform-controlled models sell through
  faster — is far more defensible than the precise magnitude.
- **SOR's transfer price and OR's wholesale cost are also illustrative,**
  not sourced from a real commercial agreement. In practice these are
  negotiated per brand/category and materially change where the OR/SOR
  crossover sits — this model's real value is the *framework*
  (predictability tier → commercial model), not these specific numbers.
- **The paired design assumes the order quantity would be the same
  regardless of who's buying.** In reality, a brand buying for MP and a
  platform buying for OR may size the initial order differently given
  their own risk appetite — a refinement worth adding before using this
  for a real negotiation, not before using it to explain the mechanism.
"""
    with open("decision_readout.md", "w") as f:
        f.write(readout)
    print(readout)


if __name__ == "__main__":
    main()
