# PRD — Smart Size & Fit Recommendation for Men's Footwear

**Owner:** [Your name] · **Status:** Draft for review · **Category:** Men's Footwear

## 1. Problem

Return rate varies sharply by sub-category — **Formal Shoes return at ~14%**
vs. a **~5–10% baseline** across the rest of men's footwear (Category Growth
Diagnostic, Project 01). Customer support tags a large share of footwear
returns as "didn't fit" rather than "changed mind" or "damaged," and the
Pricing A/B Test (Project 02) surfaced the same mechanism from a different
angle: a UX change that increased urgency (scarcity messaging) produced a
measurable *increase* in the return rate among converters — consistent with
users buying under time pressure without confirming fit first.

**These are two independent data points converging on the same root
cause: men buy footwear without confidence in size/fit, and the cost shows
up downstream as returns, not as a visible checkout-time problem.**

Returns are expensive in ways that don't show up in a single dashboard:
reverse logistics cost, restocking/damage write-offs, and — the part
leadership underweights — a bad size/fit experience measurably suppresses
whether that customer buys footwear from us again.

## 2. Goal

Reduce size/fit-driven returns in Men's Footwear **without adding checkout
friction or reducing conversion** — this is explicitly not a "make people
buy less" initiative.

### Non-goals

- Not attempting to solve returns fraud or reverse-logistics cost directly.
- Not a general-purpose size-chart redesign across all categories (Menswear
  footwear only, for v1 — the data case is built here, not elsewhere).
- Not requiring customers to enter foot measurements as a mandatory step
  (adds friction; see Risks).

## 3. Users & use cases

- **Primary:** a first-time or infrequent buyer of a given brand, uncertain
  whether that brand's sizing runs true, small, or large.
- **Secondary:** a repeat buyer of a brand where sizing has previously been
  inconsistent across styles (e.g. a sneaker vs. a formal last from the same
  brand).

## 4. Proposed solution — phased

| Phase | What ships | Data required |
|---|---|---|
| **MVP (this quarter)** | A "Runs small / True to size / Runs large" badge on the PDP, derived from aggregated verified-purchaser return reasons per brand+category. Static, refreshed weekly. | Return-reason tagging at intake (currently inconsistent — see Dependencies). |
| **V2** | Personalize the badge using the *shopper's own* past purchase+return/keep history across brands ("You kept a true-to-size Nike 9 — this brand tends to run half a size small for you"). | A cross-brand size-mapping model; enough per-user history to be confident. |
| **V3 (exploratory, not committed)** | ML fit predictor using purchase, return, and browsing signals; potentially foot-measurement input via app camera. | Substantially more data + a dedicated data science investment; out of scope until V2 proves the mechanism. |

MVP is deliberately the boring version: a badge, not a model. It tests
whether *showing* fit information moves the return rate at all before
investing in personalization.

## 5. Success metrics

| Metric | Type | Target |
|---|---|---|
| Size/fit-tagged return rate, Formal Shoes + Sneakers | Primary | -3pts within one quarter of full rollout |
| PDP → Add-to-Cart conversion rate | Guardrail | No statistically significant decrease |
| Size-related CS contact rate | Secondary | Directional decrease |

This should ship as an **A/B test**, not a blanket rollout — same discipline
as Project 02. Rollout without a control group would make it impossible to
attribute any change in return rate to this feature vs. seasonal drift.

## 6. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Return-reason data is inconsistently tagged today (garbage in, garbage out) | MVP explicitly scoped to only the two categories with cleanest data ("didn't fit" tagging), not launched category-wide. |
| A badge that's wrong erodes trust faster than no badge | Suppress the badge below a minimum sample size per brand+category rather than guessing. |
| Adding *any* PDP element could add friction, unlike the intent | Ship as an A/B test with conversion as a guardrail, exactly as in Project 02 — do not skip this step because the hypothesis "feels obviously good." |

## 7. Dependencies

- **Data platform:** standardized return-reason taxonomy at the point of
  return intake (currently a free-text field for a meaningful share of
  returns — needs a structured dropdown).
- **Catalog team:** brand+category mapping clean enough to aggregate at.

## 8. Open questions for review

1. Is "didn't fit" tagging clean enough *today* in Formal Shoes/Sneakers to
   trust an MVP launch, or does the data-quality dependency block this a
   full quarter?
2. Should V2 personalization live on PDP only, or also inform search
   ranking (e.g. deprioritize a brand+size combo with a bad personal fit
   history)? Deferred as a scope question, not a v1 decision.
