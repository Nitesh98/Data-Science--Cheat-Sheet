# Roadmap Prioritization — RICE Scoring

*(Scores computed by `rice_score.py` from `initiatives.csv` — rerun it and
this table regenerates; nothing below is hand-ranked.)*

## Ranked initiatives

| Rank | Initiative | Reach (k/mo) | Impact | Confidence | Effort (person-months) | RICE Score |
|---|---|---|---|---|---|---|
| 1 | Reallocate growth budget toward Paid Search/Social | 300 | 1 | 0.7 | 0.25 | **840.0** |
| 2 | Redesign discount calendar to reduce non-festive over-discounting | 300 | 1 | 0.2 | 0.5 | **120.0** |
| 3 | Post-purchase lifecycle campaign to fix month-1 retention drop | 250 | 2 | 0.4 | 2.0 | **100.0** |
| 4 | Smart Size & Fit Recommendation (MVP badge) | 180 | 2 | 0.6 | 3.0 | **72.0** |
| 5 | Scoped scarcity messaging rollout (low-stock threshold + size-guide prompt) | 60 | 1 | 0.8 | 0.75 | **64.0** |
| 6 | Tier 3 city fulfillment & logistics investment | 150 | 2 | 0.35 | 6.0 | **17.5** |
| 7 | Return-reason structured tagging at intake (data foundation) | 0 | 3 | 0.9 | 2.5 | **0.0** |

![RICE ranking](charts/rice_ranking.svg)

## Where each estimate comes from

- **Reallocate growth budget toward Paid Search/Social**: Project 01 channel analysis: those channels carry 60-66% new-customer share vs Organic's 34% -- budget-only change, no eng
- **Redesign discount calendar to reduce non-festive over-discounting**: Project 01 elasticity finding, but flagged there as confounded with seasonality -- low confidence until a clean causal test exists
- **Post-purchase lifecycle campaign to fix month-1 retention drop**: Project 01 cohort analysis: 100% -> 33.2% month-1 drop is the single largest retention lever found, but untested -- no experiment run yet
- **Smart Size & Fit Recommendation (MVP badge)**: PRD this doc; return-rate gap sized in Project 01 (Formal Shoes 14% vs ~5-10% baseline)
- **Scoped scarcity messaging rollout (low-stock threshold + size-guide prompt)**: Project 02 A/B test result: real data, not an estimate -- primary metric win with a guardrail regression needing this scoping
- **Tier 3 city fulfillment & logistics investment**: Project 01: Tier 3 grew fastest YoY (+75.2%) among city tiers, but causal driver unconfirmed and effort is largely ops/infra, not product
- **Return-reason structured tagging at intake (data foundation)**: Blocking dependency for the PRD above -- internal/enabling work, reach modeled as category-wide downstream enablement rather than direct user reach

## Reading the ranking, not just the score

A RICE score is a prioritization *input*, not an output to follow blindly —
here's the judgment layer on top of the numbers:

- **Scoped scarcity messaging** ranks highly on RICE despite modest reach,
  because it's the only initiative backed by an actual completed experiment
  (Project 02) rather than an estimate — its Confidence score (0.8) reflects
  that, and it should realistically be sequenced first: it's nearly shipped
  already, pending the scoping described in that project's readout.
- **Smart Size & Fit Recommendation** scores well but has a real
  dependency (structured return-reason tagging) that isn't itself high-RICE
  in isolation — it's infrastructure. Sequencing the data-foundation
  initiative *before* or *alongside* the PRD, rather than after, avoids
  building the feature on top of unreliable inputs.
- **Discount calendar redesign** has high reach but was deliberately given
  **low confidence (0.2)**, because Project 01 explicitly flagged that its
  underlying elasticity estimate is confounded with seasonality. A naive
  RICE exercise that took the raw elasticity number at face value would
  over-rank this — the honest confidence score is doing real work here,
  and this is exactly the kind of thing a prioritization review should
  catch before committing a quarter to it. Recommended next step: a small,
  seasonality-controlled test, not a full rollout, to earn a higher
  confidence score before it's re-ranked.
- **Tier 3 fulfillment investment** has high potential impact but the
  highest effort by far (ops/infra-heavy, not a product build) — it's
  reasonable to flag as a candidate for next quarter's planning rather than
  this one, once a smaller scoping study confirms the return on that
  investment.
- **Return-reason structured tagging scores 0.0 and ranks last** — not
  because it doesn't matter, but because RICE divides by a "Reach" number
  that's undefined for pure infrastructure work with no direct end-user
  reach. This is a known blind spot in applying RICE mechanically: it will
  always bury foundational/enabling work at the bottom, even when (as here)
  it's a hard blocker for a higher-ranked item. The fix isn't to fudge the
  Reach number to make the score look better — it's to recognize RICE
  ranks *user-facing bets against each other* and treat sequencing
  dependencies as a separate, non-negotiable layer on top of the score,
  which is what the sequencing below does.

## Suggested quarter sequencing (not purely RICE-order)

1. Ship the scoped scarcity-messaging fix (nearly done, real data behind it).
2. Kick off return-reason structured tagging (unblocks the PRD; low user-facing
   risk; can run in parallel with #1).
3. Begin Smart Size & Fit MVP once tagging data reaches usable quality.
4. Design (don't yet run) the post-purchase retention campaign as an A/B
   test — the underlying insight is strong, but it hasn't been tested yet,
   and deserves the same experimental rigor as the other two.
