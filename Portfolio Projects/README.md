# Portfolio Projects — Men's Footwear, Revenue & Growth

Four connected case studies built to support a **Senior Manager, Analytics**
promotion case (same vertical) or a **pivot into Product Management** —
set in men's footwear e-commerce, the author's actual working domain.

**Read this before anything else:** all data here is **synthetically
generated** (seeded, reproducible — see each project's `generate_data.py` /
`simulate_experiment.py`). None of it is real Myntra data or any company's
real numbers. Every project says this again in its own README. The
deliverable is the *method* — SQL, statistics, experiment design, and
product prioritization done rigorously — not a specific number to
memorize and repeat in an interview as if it were real.

## The four projects

| # | Project | Demonstrates |
|---|---|---|
| [01](01-Category-Growth-Diagnostic/) | **Category Growth Diagnostic** | SQL (window functions, cohort analysis), a hand-rolled discount-elasticity regression, and — importantly — correctly flagging when a correlation is confounded rather than reporting it as causal. |
| [02](02-Pricing-AB-Test/) | **Pricing/Messaging A/B Test** | Experiment design written *before* results (hypothesis, power calculation), then a real statistical analysis (two-proportion z-test, Welch's t-test, implemented by hand) that produces a nuanced, not-a-clean-win recommendation. |
| [03](03-PM-Smart-Fit-PRD-and-Roadmap/) | **PM Case Study: PRD + Roadmap** | A full PRD for a feature whose problem statement is sized using Project 01's data, plus a RICE-scored roadmap that's computed from a CSV, not hand-ranked — including calling out RICE's own blind spot for infrastructure work. |
| [04](04-Causal-Discount-Effect-DiD/) | **Causal Discount Effect (DiD)** | The direct follow-up to Project 01's confound: an isolated natural-experiment comparison (difference-in-differences) plus a permutation test in place of unreliable few-cluster standard errors — recovers a smaller, more defensible discount effect than the naive regression. |

They share a spine: Project 01 surfaces a sizing/returns problem in Formal
Shoes *and* flags its own discount-elasticity estimate as confounded;
Project 02's experiment independently surfaces the sizing/returns mechanism
from a UX angle; Project 03's PRD is built to fix it, with a roadmap that
has to justify that fix against six other data-backed initiatives; Project
04 goes back and actually resolves Project 01's confound with a proper
causal design. That's deliberate — a hiring panel can pull on any thread
and it connects to the others, rather than four disconnected exercises.

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
cd "04-Causal-Discount-Effect-DiD" && python3 generate_data.py && python3 analysis.py && cd ..
```

No external packages required — Python 3 standard library only, so this
runs anywhere without an environment setup step.

## Using this for your resume / LinkedIn

Each project's own doc (`executive_summary.md`, `readout.md`,
`roadmap_prioritization.md`, `causal_readout.md`) ends with a short,
resume-style framing of the work. Adapt the language to your actual voice before using it — the value
of a portfolio piece in an interview is being able to go two levels deeper
than the bullet point, not reciting it.
