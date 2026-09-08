# PM Case Study — PRD + RICE-Scored Roadmap

A connected product-management artifact: a full PRD for a real footwear
e-commerce feature, plus a RICE-scored roadmap that shows how it competes
against six other initiatives for a quarter of eng time — most of them
pulled directly from the findings in Projects 01 and 02, not invented fresh.

## What's in here

| File | Purpose |
|---|---|
| `PRD_Smart_Size_Fit_Recommendation.md` | Full PRD: problem, goals/non-goals, phased solution, success metrics, risks, dependencies. |
| `initiatives.csv` | Seven candidate initiatives with Reach/Impact/Confidence/Effort inputs and a note on where each estimate comes from. |
| `rice_score.py` | Computes RICE scores from the CSV and writes `roadmap_prioritization.md` — the ranking is never hand-typed. |
| `roadmap_prioritization.md` | The generated, ranked roadmap with a judgment layer on top of the raw scores. |

## Run it yourself

```bash
python3 rice_score.py   # -> charts/rice_ranking.svg, roadmap_prioritization.md
```

## Why this is one case study, not three unrelated documents

The PRD's problem statement is sized using the return-rate gap found in
Project 01's category diagnostic. The roadmap's highest-confidence item
(scoped scarcity messaging) is ranked using the *actual* statistical result
from Project 02's A/B test, not a guess. And the roadmap write-up explicitly
flags where an initiative's confidence score should stay low because an
earlier project already surfaced a confound (the discount-calendar
initiative) — showing the analytical rigor carrying through into the
product-prioritization decision, which is the connective tissue a Senior
Manager Analytics → PM transition story needs to make explicit.
