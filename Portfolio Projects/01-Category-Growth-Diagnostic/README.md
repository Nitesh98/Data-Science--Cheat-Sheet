# Category Growth Diagnostic — Men's Footwear

A revenue & growth analytics case study styled after the kind of quarterly
category deep-dive a Manager/Senior Manager, Analytics would own: where is
growth coming from, is it healthy or discount-fuelled, which cohorts and
channels are actually working, and what would I tell leadership to do next.

> **Data note:** `orders.csv` is **synthetically generated** by
> `generate_data.py` (seeded, reproducible) — it is *not* real Myntra or any
> company's data. It's built with realistic e-commerce dynamics (seasonality,
> discount-driven demand, customer retention decay, sizing-driven returns) so
> the analyses below have genuine signal to recover. Say this plainly if
> asked about it — the value here is the *method*, not the numbers.

## What's in here

| File | Purpose |
|---|---|
| `generate_data.py` | Builds `orders.csv` — 24 months of order-level data (~119k rows). |
| `sql_queries/*.sql` | Five analysis queries (window functions, cohort analysis, segment breakdowns). |
| `run_sql.py` | Loads the CSV into a real SQLite DB and executes every query, saving results to `sql_queries/results/`. |
| `analysis.py` | Python-only analysis: discount-elasticity regression (hand-rolled OLS), cohort retention curve, channel & city-tier breakdowns. Writes `charts/*.svg` and `findings.json`. |
| `executive_summary.md` | The business-facing readout — resume-ready bullets in STAR format. |

## Run it yourself

No external packages needed — everything is Python 3 standard library.

```bash
python3 generate_data.py   # -> orders.csv
python3 run_sql.py         # -> sql_queries/results/*.md (real SQLite output)
python3 analysis.py        # -> charts/*.svg, findings.json
```

Every number in `executive_summary.md` is pulled from `findings.json`,
which this script regenerates — rerun it and the numbers should match
exactly (the generator is seeded for reproducibility).

## Why this shape

A resume bullet like *"analyzed revenue growth"* is forgettable. This case
study is built to defend, in an interview, each of the harder questions a
hiring panel actually asks:

- *"How did you separate real demand growth from discount-driven noise?"*
  → see the elasticity regression and its confounding caveat below.
- *"How do you know a cohort/channel is actually working, not just cheap?"*
  → retention curve + new-customer share by channel, not just revenue.
- *"Can you write SQL a data engineer wouldn't wince at?"*
  → `sql_queries/` uses window functions and cohort logic, actually executed
    against a real (if small) database, not typed from memory.
