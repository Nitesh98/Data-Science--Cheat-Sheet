# Commercial Model Decision: MP vs. OR vs. SOR

A pricing-and-inventory-control model for the actual commercial question a
fashion e-commerce platform (Myntra, Ajio, and similar) faces with every
brand: **which commercial model should we run this brand/category under?**

- **MP (Marketplace)** — the brand owns inventory *and* sets price; the
  platform earns a commission on GMV, with no pricing or inventory control.
- **OR (Own Retail)** — the platform buys stock outright at wholesale cost,
  and controls pricing/markdown fully — but also bears full write-off risk
  on unsold stock.
- **SOR (Sale or Return)** — the platform controls pricing/markdown like
  OR, but pays the brand only for units actually **sold** (a transfer
  price), and returns unsold stock to the brand — no upfront capital, no
  write-off.

> **Data note:** the simulation is synthetic and seeded — see
> `simulate.py`. Unit economics (wholesale cost, SOR transfer price,
> commission rate) are illustrative, not sourced from a real deal. The
> framework — and the *qualitative* finding that pricing control matters —
> is the deliverable; see the caveats in `decision_readout.md`.

## The method

A **paired Monte Carlo simulation**: within each trial, all three models
see the *identical* order quantity and the *identical* underlying demand
draw for a 16-week footwear selling season. Only the markdown policy and
the resulting P&L mechanics differ between models. This isolates the
effect of *who controls the pricing lever* — the same identification
discipline as Project 04's difference-in-differences design, applied here
to a business decision instead of a stats question.

The demand-response-to-discount parameter reuses **Project 04's causal
elasticity estimate** (not Project 01's confounded one) — this is the
first project in the portfolio that actually *uses* that number to drive a
decision, rather than just estimating it.

## What's in here

| File | Purpose |
|---|---|
| `simulate.py` | Runs 6,000 paired trials (3 demand-predictability tiers x 2,000 trials) across MP/OR/SOR. |
| `analysis.py` | Aggregates results into expected profit, risk (volatility, loss probability), and sell-through by model & tier — and writes `decision_readout.md` with a recommendation *generated from* those numbers, not asserted ahead of them. |
| `decision_readout.md` | The full write-up. |
| `../svg_charts.py` | Gained a `grouped_bar_chart` helper for this project (comparing 3 models across 3 tiers) — shared back into the portfolio's chart library. |

## Run it yourself

```bash
python3 simulate.py    # -> simulation_results.csv
python3 analysis.py    # -> charts/, decision_readout.md
```

## Why the result isn't a clean "X always wins"

OR wins on raw expected profit in every tier tested — a naive read stops
there. But OR's profit *edge* over SOR shrinks (13% → 10% → 5%) and its
loss probability *grows* (0% → 3.3% → 13.1%) as demand gets harder to
forecast, while SOR holds a consistently better reward-per-unit-risk
throughout. The actual recommendation this generates is **tier-dependent on risk, not
on raw profit** — OR for predictable movers, a genuine risk-tolerance
judgment call in the middle, and SOR for high-uncertainty styles unless the
platform is explicitly risk-neutral. `analysis.py`'s recommendation text is
generated programmatically from the computed loss-probability and
reward-per-risk numbers for each tier — rerun the simulation with different
assumptions and the recommendation will correctly change with it, the same
discipline used for Project 02's experiment readout.
