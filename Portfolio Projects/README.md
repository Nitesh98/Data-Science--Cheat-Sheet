# Portfolio Projects — Men's Footwear, Revenue & Growth

Three connected case studies built to support a **Senior Manager, Analytics**
promotion case (same vertical) or a **pivot into Product Management** —
set in men's footwear e-commerce, the author's actual working domain.

**Read this before anything else:** all data here is **synthetically
generated** (seeded, reproducible — see each project's `generate_data.py` /
`simulate_experiment.py`). None of it is real Myntra data or any company's
real numbers. Every project says this again in its own README. The
deliverable is the *method* — SQL, statistics, experiment design, and
product prioritization done rigorously — not a specific number to
memorize and repeat in an interview as if it were real.

## The three projects

| # | Project | Demonstrates |
|---|---|---|
| [01](01-Category-Growth-Diagnostic/) | **Category Growth Diagnostic** | SQL (window functions, cohort analysis), a hand-rolled discount-elasticity regression, and — importantly — correctly flagging when a correlation is confounded rather than reporting it as causal. |
| [02](02-Pricing-AB-Test/) | **Pricing/Messaging A/B Test** | Experiment design written *before* results (hypothesis, power calculation), then a real statistical analysis (two-proportion z-test, Welch's t-test, implemented by hand) that produces a nuanced, not-a-clean-win recommendation. |
| [03](03-PM-Smart-Fit-PRD-and-Roadmap/) | **PM Case Study: PRD + Roadmap** | A full PRD for a feature whose problem statement is sized using Project 01's data, plus a RICE-scored roadmap that's computed from a CSV, not hand-ranked — including calling out RICE's own blind spot for infrastructure work. |

They share a spine: Project 01 surfaces a sizing/returns problem in Formal
Shoes; Project 02's experiment independently surfaces the same mechanism
from a UX angle; Project 03's PRD is built to fix it, and its roadmap has to
justify that fix against six other data-backed initiatives for a quarter of
eng time. That's deliberate — a hiring panel can pull on any thread and it
connects to the others, rather than three disconnected exercises.

## Shared infrastructure

- `svg_charts.py` — dependency-free SVG bar/line chart helper (no
  matplotlib available in this environment; charts are hand-built, not a
  cosmetic shortcut).
- `stats_lib.py` — hand-implemented two-proportion z-test, Welch's t-test,
  and a sample-size/power calculator (no scipy available; validated against
  known critical values, e.g. `norm_ppf(0.975) ≈ 1.9600`).
- `.gitignore` — excludes the large generated CSVs/DBs (regenerate them with
  each project's own script; they're deterministic/seeded).

## Run everything from scratch

```bash
cd "01-Category-Growth-Diagnostic" && python3 generate_data.py && python3 run_sql.py && python3 analysis.py && cd ..
cd "02-Pricing-AB-Test" && python3 simulate_experiment.py && python3 analyze_experiment.py && cd ..
cd "03-PM-Smart-Fit-PRD-and-Roadmap" && python3 rice_score.py && cd ..
```

No external packages required — Python 3 standard library only, so this
runs anywhere without an environment setup step.

## Using this for your resume / LinkedIn

Each project's own doc (`executive_summary.md`, `readout.md`,
`roadmap_prioritization.md`) ends with a short, resume-style framing of the
work. Adapt the language to your actual voice before using it — the value
of a portfolio piece in an interview is being able to go two levels deeper
than the bullet point, not reciting it.
