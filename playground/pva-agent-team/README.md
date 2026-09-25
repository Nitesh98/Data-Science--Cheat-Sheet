# PvA Agent Team: "Why is PvA low?"

A team of AI agents that does the daily plan-vs-actual diagnosis for a men's footwear category.
It tracks MTD and intraday PvA for GMV, GM and every funnel metric, explains the gap in rupees,
checks pricing and rebate decisions, and rules supply (broken sizes, live styles, new season) in or out.
Then it **acts**: it puts a rupee value on each fix, splits a rebate budget, tests price options, forecasts
where the month lands and re-phases the remaining days. Finally it drafts the Slack note and exec summary.
**A human approves the draft before anything goes out.**

> Everything here uses **synthetic, seeded data**. The brands, numbers and events are made up.
> Never point it at real company data without the right approvals.

This is the next step after [`../agent-from-scratch/`](../agent-from-scratch/). That folder has one
agent with one loop. This one has several agents, each with its own job and its own tools, handing
work to each other.

## The team

| Agent | Question it answers | Tools it may use |
|---|---|---|
| **PvA Monitor** | Where are we vs plan, MTD and right now? What's flagged? When did it break today? | `get_pva`, `intraday_by_hour` |
| **Funnel Analyst** | Which funnel step and which slice (brand, channel, city tier...) explains the rupees? | `gmv_bridge`, `get_pva`, `run_sql` |
| **Pricing & Rebate Analyst** | Did our OR/SOR price decisions or MP rebates cause it? What's the GMV vs GM trade-off? | `pricing_check`, `gmv_bridge`, `run_sql` |
| **Merchandising Analyst** | Is it supply? Live styles, size availability (broken sizes), new-season share. Rules supply in or out for each brand behind plan and flags risks that haven't hit GMV yet | `merch_health`, `merch_by_hour`, `intraday_by_hour`, `get_pva`, `run_sql` |
| *Stage 2: act (each one sees the stage-1 findings)* | | |
| **MP Rebate Allocator** | Should we spend more MP rebate, and on which brand? Uses *fitted* elasticities; "don't spend it" is a valid answer | `rebate_status`, `estimate_elasticity`, `simulate_rebate`, `optimize_rebate` |
| **OR/SOR Pricing Optimizer** | What discount should OR/SOR brands run for the rest of the month? Shows the GMV vs GM trade-off for hold / partial / full rollback | `estimate_elasticity`, `price_scan`, `pricing_check` |
| **Plan & Landing Analyst** | Where does the month land vs MoP? What's each fix worth? Do the actions close the gap? It re-phases the remaining days' targets | `month_landing`, `restore_to_plan`, `action_coverage`, `rephase_plan` |
| **Writer** | Turns the findings into a 5-line Slack note and a one-page exec summary | none (only `submit_draft`) |
| **Reviewer** | Re-runs the tools and checks every number before you see it | all read tools + `submit_review` |
| **You** | Final approval | `python3 run_team.py --approve` |

```
STAGE 1: diagnose        STAGE 2: act (sees stage 1)
Monitor ─┐               Rebate Allocator ─┐
Funnel  ─┤               Pricing Optimizer ┼─> Plan & Landing ─> Writer ─> Reviewer ─(issues?)─> Writer ...
Pricing ─┼──────────────>                  ┘   (sees everything)                      ─> DRAFT ─> YOU approve
Merch   ─┘
```

**How the action tools project the future** (`action_tools.py`): take the last 7 full days' funnel
rates per brand × article type, apply them to the remaining plan traffic, and move one lever at a time.
The price lever works through the **elasticity fitted from this month's data** (sale days and price
changes provide the variation). GM follows each brand's commercial terms in `dim_style`: OR = GMV − COGS,
SOR = a fixed margin share, MP = commission − the rebate we fund.

**Why plain Python runs the order instead of a "boss" LLM:** this review is the same every day, so a
fixed pipeline is cheaper and more predictable. The *thinking inside each step* is where the LLM helps.
The same trade-off comes up with any agent system: use agents where the path isn't known in advance
and a normal workflow where it is.

**Why the agents never do arithmetic:** every number comes from a deterministic tool in `tools.py`.
The LLM decides *which* slice to look at and *what it means*, and the tool does the math. That is also
what lets the Reviewer check the Writer: it re-runs the same tool and compares.

## The funnel (the KPI tree the agents use)

```
GMV = Sessions × LV/session × PDP CTR × Consideration × Checkout × UPT × ASP
      (traffic)  \___________ Conversion = Orders / Sessions _________/
                              (PDP/LV)   (ATC/PDP)     (Orders/ATC)
```

`gmv_bridge` splits the GMV gap across these seven factors using a log-mean (LMDI)
decomposition, so **the pieces add up exactly to the rupee gap**. No "interaction" leftover.

Flag thresholds are in `config.py`:

- **Volumes** (sessions, LV, PDP, ATC, orders, units, GMV, GM): below 95% MTD or below 90% intraday.
- **Rates**: below 97% MTD or below 95% intraday.

## Running it

```bash
cd playground/pva-agent-team

python3 run_team.py --offline      # no API key: rule-based stand-ins, same outputs, runs anywhere
python3 run_team.py                # the real agent team (needs a key, see below)
python3 run_team.py --approve      # after you've read the draft
```

With a key, on your own machine (recommended):

```bash
pip install anthropic
export ANTHROPIC_API_KEY=sk-ant-...     # from console.anthropic.com. Never paste it into a chat.
python3 run_team.py
```

`llm.py` uses the official `anthropic` SDK when it's installed. If it isn't installed (as in the
Claude Code sandbox), it sends the identical request with Python's built-in `urllib`. The agent loop
is the same either way.

A full run makes roughly 30–60 API calls on `claude-opus-5`. To try it cheaply, set
`MODEL = "claude-sonnet-5"` in `config.py`.

### What you get: `out/<date>/draft/`

| File | What |
|---|---|
| `slack_note.md` | 5 lines: PvA, gap in INR, top 3 reasons, top 3 actions, the ask |
| `exec_summary.md` | One page: KPI table, GMV bridge, root causes, pricing trade-offs, intraday alert, actions |
| `brand_table.csv` | Per brand: plan, actual, PvA, gap, GM PvA, funnel PvAs, discount pp, worst size availability, month-landing PvA and main driver (deterministic) |
| `queries.sql` | Every query the agents ran, to port to your real warehouse |
| `transcript.md` | What each specialist found |

`--approve` copies the draft to `out/<date>/approved/` and stamps it.

## The planted story (spoilers: try the agents first!)

`data.py` hides eight things in the September 2026 data. A good run finds all eight:

1. **Stridex (OR) price hike** from Sep 10 (discount 35% → 28%). Consideration is down and GMV
   is ~₹1.6 Cr behind plan, but GM is *above* plan. Is it the right trade?
2. **Vantage (MP) rebate budget ran out** on Sep 16 (8% → 2%). GMV is down, but GM is way up
   because rebates come out of our margin.
3. **App traffic in Tier-2 and Tier-3 cities down 20%** since Sep 18 (a paused campaign). This is
   the single biggest rupee driver.
4. **Coastline (SOR)** is running ~5% *above* plan. It's a tailwind that hides some of the misses.
5. **Today from 11:00, UrbanKick sneakers consideration halves.** This only shows up intraday. The
   Merchandising Analyst finds *why*: sizes 8–10 sold out during the morning, and size availability
   fell from 87% to 46%, exactly when demand dropped.
6. **Supply is fine for Stridex and Vantage.** Their misses really are price and rebate, and the Merch
   Analyst should *rule supply out* rather than pile on.
7. **Formale's new-season (autumn-winter) stock is late.** New-season share is ~13% vs a 35% target.
   There's no GMV hit yet, so it's an early warning for October.
8. **Brands respond differently to discount.** Trekko is most responsive, Redline least. The Rebate
   Allocator should *fit* this from the data before splitting a budget.

**What the action stage should conclude** (the offline run gets these numbers):

- The month lands at **~95% of MoP (about ₹8.1 Cr short)** on the current run-rate. Hitting plan would need
  +31% on every remaining day, so it isn't realistic.
- **Restarting the Tier-2/3 app campaigns** is worth **~₹2.5 Cr** and **fixing UrbanKick sizes** ~₹1.25 Cr.
  Together they close about half the gap.
- **Rebates are poor value here.** The whole ₹50 L top-up buys only ~₹11 L of GMV (₹0.23 per rebate rupee)
  and costs ~₹46 L of GM. The honest recommendation is not to spend it.
- **The Stridex price hike was the right call on margin.** Rolling back to 35% adds ~₹13 L of GMV but costs
  ~₹32 L of GM.

## Files

| File | What |
|---|---|
| `config.py` | Dates, thresholds, model. Change settings here. |
| `data.py` | Builds the synthetic warehouse (`data/footwear.db`, SQLite): plan phasing AOP → MoP → DoD, hourly actuals, hourly supply (`inventory_hourly`, `merch_plan`) |
| `tools.py` | Diagnosis tools: PvA, GMV bridge, intraday by hour, pricing check, merch health, merch by hour, read-only SQL. It also logs every query. |
| `action_tools.py` | Action tools: the projection engine, elasticity fit, rebate status / simulate / optimise, price scan, month landing, re-phasing, restore-to-plan, action coverage |
| `llm.py` | The agent loop, with the SDK or the urllib fallback |
| `agents.py` | Each agent's job description and tool list, plus the offline stand-ins |
| `run_team.py` | The orchestrator and the approval step |

## Roadmap: the rest of your job, as agents

Built on the same pattern: tools do the math, agents do the reasoning, the Reviewer checks, you approve.

| Next agent | Would do | New tools it needs |
|---|---|---|
| **AOP Builder** | Build next year's AOP → MoP → DoD from history, seasonality and growth targets. The re-phasing half is already done by the Plan & Landing Analyst. | `build_aop`, seasonality fit |
| **Brand Planner** | Brand-level plans and brand-partner performance packs | `brand_pack` |
| **Monthly Review Pack** | Monthly KPI tables, commentary and deck bullets | reuse all tools + a deck writer |
| **Dashboard Builder** | Turn the recurring queries in `queries.sql` into dashboard specs | — |

✅ Built so far: **Merchandising Analyst**, **MP Rebate Allocator**, **OR/SOR Pricing Optimizer**, **Plan & Landing Analyst**.

Good next exercise: change `REBATE_TOPUP_INR` in `config.py`, or an elasticity in `data.py`
(e.g. make Trekko 5.0), and see whether the Rebate Allocator changes its mind.
