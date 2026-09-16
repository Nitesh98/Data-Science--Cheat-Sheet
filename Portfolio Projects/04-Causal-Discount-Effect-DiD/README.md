# Causal Discount Effect — Difference-in-Differences

The direct follow-up promised in **Project 01**'s executive summary: that
project's discount-elasticity regression was flagged as confounded —
discounts and festive/EOSS seasonality move together, so a naive regression
can't tell you how much of the demand lift is the discount versus the
season. This project builds a cleaner comparison to answer that honestly.

> **Data note:** synthetic, seeded — see `generate_data.py`. The "true"
> causal elasticity is embedded in the generator so the analysis has a
> specific, known number to try to recover, and deliberately set *lower*
> than Project 01's confounded estimate (that's the whole point).

## The method, in one paragraph

In May 2024 — a month with no festive or EOSS effect on any category —
Sneakers alone ran a one-off inventory-clearance discount. No other
category's discount or seasonal environment changed. Comparing Sneakers'
order change (April → May) against the average change across the four
untouched categories over the same window — a difference-in-differences —
isolates the discount's own effect from the seasonal confound that
undermined Project 01's naive estimate. Because there are only 4 possible
control categories (too few for classical clustered standard errors to be
trustworthy), significance is assessed with a **permutation/placebo
test** instead: pretend each control was "treated" and see how extreme the
real effect looks against that placebo distribution.

## What's in here

| File | Purpose |
|---|---|
| `generate_data.py` | Builds the category-month panel with an isolated, non-seasonal discount event. |
| `analysis.py` | Parallel-trends check, the DiD estimate, and the placebo/permutation test. Writes `charts/*.svg` and `causal_readout.md`. |
| `causal_readout.md` | The full write-up, generated from the actual computed numbers. |

## Run it yourself

```bash
python3 generate_data.py   # -> category_month_panel.csv
python3 analysis.py        # -> charts/, causal_readout.md
```

## Why this is the strongest piece in the portfolio for a Senior Manager case

Projects 01–03 each demonstrate a skill. This one demonstrates *judgment
about a skill's limits* — noticing a naive analysis was confounded, fixing
it with a genuine (if imperfect) identification strategy, and then being
upfront that even the fix has a real statistical limitation (a permutation
test with only 4 placebo draws can't reach conventional significance
thresholds, and the write-up says so in plain language rather than hiding
it behind a p-value). That progression — naive estimate → recognizing the
confound → a causal design → honest limits of the causal design — is
usually what separates a "did the analysis" answer from a "how do you know
you can trust the analysis" answer in a Senior Manager loop.
