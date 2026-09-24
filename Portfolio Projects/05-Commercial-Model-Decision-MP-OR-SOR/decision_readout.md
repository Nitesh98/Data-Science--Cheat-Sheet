# Decision Readout — MP vs. OR vs. SOR

*(Synthetic simulation — see README. A paired Monte Carlo design: within
each trial, all three models see the identical order quantity and demand
draw, isolating the effect of who controls pricing/markdown. Demand
response to discount reuses Project 04's causal elasticity estimate.)*

## Headline: expected profit by model and demand-predictability tier

![Expected profit](charts/01_expected_profit.svg)

| Tier | MP | OR | SOR | Highest expected profit |
|---|---|---|---|---|
| Hot / predictable | Rs 914K | Rs 1724K | Rs 1529K | OR |
| Medium | Rs 442K | Rs 775K | Rs 702K | OR |
| Slow / high-uncertainty | Rs 180K | Rs 281K | Rs 268K | OR |

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
Return on capital employed for OR, by tier: Hot / predictable: 74%, Medium: 67%, Slow / high-uncertainty: 57%.
SOR captures nearly the same pricing-control upside as OR **without** that
capital exposure — the transfer-price mechanism prices the risk into the
brand's side of the deal instead.

## The decision rule this actually implies

**OR wins on raw expected profit in all three tiers** — that's the number
a naive read would stop at. But OR's *edge* over SOR shrinks, and its risk
grows, as demand gets harder to forecast:

| Tier | OR's profit edge over SOR | OR loss probability | Reward-per-risk (mean/sd): OR vs. SOR | Recommendation |
|---|---|---|---|---|
| Hot / predictable | +13% | 0.0% | 4.1 vs. 4.9 | OR |
| Medium | +10% | 3.3% | 2.3 vs. 2.8 | Genuine judgment call |
| Slow / high-uncertainty | +5% | 13.1% | 1.4 vs. 2.0 | SOR, unless the platform is explicitly risk-neutral |

**Hot / predictable:** **OR.** Expected-profit edge over SOR is +13%, loss probability is negligible (0.0%), and the extra risk of owning inventory is well contained at this predictability level — this is where taking the risk clearly pays for itself.

**Medium:** **Genuine judgment call.** OR still leads on expected profit (+10% over SOR), but its loss probability (3.3%) and reward-per-risk (2.3) are both worse than SOR's (2.8). A capital-rich, risk-neutral platform should still take OR; a more risk-averse one has a legitimate case for SOR instead.

**Slow / high-uncertainty:** **SOR, unless the platform is explicitly risk-neutral.** OR's expected-profit edge over SOR is only 5% here, while OR now carries a 13% chance of a loss-making season (vs. 0% for SOR) and the worst reward-per-unit-risk of the three models (1.4, vs. 2.0 for SOR). That small an expected-profit edge is a thin justification for underwriting real capital-loss risk.

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
