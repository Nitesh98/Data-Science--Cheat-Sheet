# Pricing / Messaging A/B Test — Men's Sneaker PDP

An experimentation case study: full design (hypothesis, metrics, power
calculation) written *before* looking at any results, then a real
statistical analysis run against simulated session data.

> **Data note:** `experiment_data.csv` is **synthetically simulated** with a
> known, injected true effect (see `simulate_experiment.py`) — not a real
> Myntra experiment. The point is to demonstrate the design → analysis →
> recommendation discipline end to end, including how to write up a result
> that *isn't* a clean win (this one has a real guardrail regression).

## What's in here

| File | Purpose |
|---|---|
| `experiment_design.md` | Hypothesis, metrics, sample-size/power calculation, analysis plan — written up front. |
| `simulate_experiment.py` | Generates session-level experiment data with a known true effect. |
| `analyze_experiment.py` | Runs the pre-registered analysis (two-proportion z-test, Welch's t-test) and writes `readout.md` from the actual computed numbers — no hardcoded conclusions. |
| `../stats_lib.py` | Shared, dependency-free implementation of the statistical tests (no scipy in this environment — implemented by hand, validated against known critical values). |
| `readout.md` | The final write-up, generated fresh each run. |

## Run it yourself

```bash
python3 simulate_experiment.py   # -> experiment_data.csv
python3 analyze_experiment.py    # -> charts/, readout.md
```

## Why this one matters for an interview

Most take-home / portfolio A/B tests show a clean win because that's easy to
write up. This one deliberately doesn't fully cooperate: the primary metric
wins, but a guardrail metric (return rate) shows a real, statistically
significant regression, and the effect size lands just under the
pre-registered MDE despite being significant. `analyze_experiment.py`
generates its recommendation *programmatically from the actual test
results* — rerun the simulation with a different seed and the write-up's
conclusion will correctly change with it. That's the behavior worth pointing
to: the write-up reasons from the numbers, it doesn't perform a foregone
conclusion.
