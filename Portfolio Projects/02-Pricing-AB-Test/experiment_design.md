# Experiment Design — Scarcity Messaging on Men's Sneaker PDPs

## Background

Category data (see Project 01) shows Sneakers is the largest men's footwear
sub-category by revenue share, with a PDP-to-cart conversion rate that the
growth team believes is being left on the table during non-sale periods
(most of the discount lift is concentrated in festive/EOSS windows).

**Idea:** add low-stock scarcity messaging ("Only 3 left in your size") to
the sneaker PDP for SKUs where it's true, to create urgency without needing
a discount.

## Hypothesis

- **H0:** Scarcity messaging has no effect on PDP → Add-to-Cart conversion rate.
- **H1:** Scarcity messaging increases PDP → Add-to-Cart conversion rate.

## Metrics

| Type | Metric | Why |
|---|---|---|
| **Primary** | PDP → Add-to-Cart conversion rate | Directly targeted by the change. |
| **Guardrail** | Average Order Value (AOV) | Urgency shouldn't push users toward cheaper "in-stock" alternatives. |
| **Guardrail** | Return rate | Urgency-driven purchases could increase size-related returns. |
| **Guardrail** | Checkout abandonment rate | Watch for anxiety/mistrust effects from scarcity messaging. |

## Design

- **Randomization unit:** session (cookie-based), to avoid a logged-in user
  seeing inconsistent messaging across devices within the test window.
- **Allocation:** 50/50 control vs. treatment.
- **Segment:** Men's Sneakers PDP traffic only; all channels included (no
  channel-specific effect assumed a priori).

## Sample size / duration

Baseline PDP → Cart conversion: **12.0%** (from historical category data).
Minimum detectable effect (MDE) we care about: **+8% relative lift**
(12.0% → ~12.96%) — smaller than that isn't worth the PM/eng effort to ship.

Using a two-sided two-proportion test, α = 0.05, power = 0.80:

```
n per group = ((z_α/2 + z_β)² × [p1(1-p1) + p2(1-p2)]) / (p2 - p1)²
            ≈ 18,600 sessions per arm   (see stats_lib.sample_size_two_proportions)
```

At an assumed ~2,500 sneaker-PDP sessions/day split across both arms
(~1,250/arm/day), that's **~15 days** to reach the required sample —
call it **3 weeks** to comfortably clear both weekday/weekend mix and one
full pay-cycle, and to avoid stopping the moment significance is first
crossed (peeking inflates false-positive rate).

## Analysis plan

1. Run the full pre-registered duration — no early stopping on a peek.
2. Two-proportion z-test on primary metric, report effect size + 95% CI, not
   just p-value.
3. Check all guardrails with the same rigor as the primary metric — a
   "win" that quietly breaks return rate is not a win.
4. If primary metric is significant and guardrails hold: recommend ship.
   If primary is significant but a guardrail regresses: recommend
   iterate (e.g. only show scarcity messaging above a stock threshold)
   rather than an automatic ship/kill decision.

## What actually happened

See `simulate_experiment.py` (synthetic session-level data with a
built-in true effect) and `analyze_experiment.py` for the executed
analysis — results in `readout.md`.
