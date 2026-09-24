"""
Paired Monte Carlo simulation: for the SAME initial stock and the SAME
underlying demand draw, simulate a 16-week sell-through season under three
commercial models a platform like Myntra/Ajio runs with footwear brands:

  MP  (Marketplace)     -- brand owns inventory AND sets price/markdown.
                           Platform earns a commission on GMV, bears no
                           inventory risk, but has NO markdown control.
  OR  (Own Retail)       -- platform buys stock outright at wholesale cost,
                           controls pricing/markdown fully, bears full
                           write-off risk on unsold stock.
  SOR (Sale or Return)   -- platform controls pricing/markdown like OR, but
                           pays the brand only for units actually SOLD
                           (at a transfer price), and returns unsold stock
                           to the brand -- no write-off, no upfront capital.

KEY DESIGN CHOICE -- paired trials: within one trial, all three models see
the EXACT SAME order quantity and the EXACT SAME demand-shock draw. Only
the pricing/markdown policy and the P&L mechanics differ between them. This
isolates the effect of *who controls the markdown lever*, the same
identification discipline as Project 04's DiD design -- applied here to a
business decision instead of a stats question.

The demand-response-to-discount parameter reuses Project 04's CAUSAL
elasticity estimate (not Project 01's confounded one) for continuity across
the portfolio -- see 04-Causal-Discount-Effect-DiD/causal_readout.md.

Run:
    python3 simulate.py
Produces:
    simulation_results.csv
"""
import csv
import math
import random

random.seed(21)

SEASON_WEEKS = 16
MRP = 2500                      # representative men's footwear price point
UNIT_COST = 1200                # platform's wholesale buy-in cost (OR)
SOR_TRANSFER_PRICE = 1350       # brand's per-unit-SOLD charge under SOR (> unit cost:
                                 # the brand prices in the risk it's retaining)
COMMISSION_RATE_MP = 0.22       # platform's commission on GMV under marketplace model
SALVAGE_RATE_OR = 0.15          # unsold OR stock recovers 15% of cost via liquidation
CAUSAL_ELASTICITY = 1.1         # reused from Project 04's DiD estimate
DEMAND_DECAY_PER_WEEK = 0.04    # natural week-over-week interest decay, discount-independent

DEMAND_TIERS = {
    # (base weekly units at full price, demand-shock sd -- how unpredictable this tier's sell-through is)
    "Hot / predictable": (140, 0.15),
    "Medium": (70, 0.30),
    "Slow / high-uncertainty": (30, 0.50),
}

N_TRIALS_PER_TIER = 2000
FORECAST_BUFFER = 0.15  # order qty = forecast total demand * (1 + buffer)


def markdown_policy(weeks_of_inventory, weeks_remaining, model):
    """Returns the discount fraction (0-0.6) for this week, given current
    weeks-of-inventory and weeks left in the season. OR/SOR (platform
    controls price) use the same, more responsive policy. MP (brand
    controls price) uses a shallower, less responsive one -- the brand
    optimizes across its whole business, not this platform's overstock,
    a standard channel/agency friction in marketplace models."""
    if model in ("OR", "SOR"):
        if weeks_remaining <= 2 and weeks_of_inventory > 4:
            return 0.60
        if weeks_of_inventory > 12:
            return 0.40
        if weeks_of_inventory > 8:
            return 0.20
        return 0.0
    else:  # MP -- muted / delayed
        if weeks_remaining <= 2 and weeks_of_inventory > 6:
            return 0.40
        if weeks_of_inventory > 16:
            return 0.20
        return 0.0


def simulate_one(model, order_qty, base_demand, demand_shock):
    stock = order_qty
    trailing_rate = base_demand  # for weeks-of-inventory calc
    total_units_sold = 0
    total_gmv = 0.0
    total_platform_units_revenue = 0.0  # for SOR: (price - transfer) per unit sold

    for week in range(SEASON_WEEKS):
        weeks_remaining = SEASON_WEEKS - week
        woi = stock / trailing_rate if trailing_rate > 0 else 99
        discount = markdown_policy(woi, weeks_remaining, model)
        price = MRP * (1 - discount)

        decay = (1 - DEMAND_DECAY_PER_WEEK) ** week
        elasticity_lift = math.exp(CAUSAL_ELASTICITY * discount)
        demand_rate = base_demand * decay * elasticity_lift * demand_shock

        units_sold = min(stock, demand_rate)
        stock -= units_sold
        total_units_sold += units_sold
        total_gmv += units_sold * price
        if model == "SOR":
            total_platform_units_revenue += units_sold * (price - SOR_TRANSFER_PRICE)

        trailing_rate = max(demand_rate, 1e-6)

    unsold = stock

    if model == "MP":
        profit = COMMISSION_RATE_MP * total_gmv
        capital_employed = 0.0
    elif model == "OR":
        upfront_cost = order_qty * UNIT_COST
        salvage_recovery = unsold * UNIT_COST * SALVAGE_RATE_OR
        profit = total_gmv - upfront_cost + salvage_recovery
        capital_employed = upfront_cost
    else:  # SOR
        profit = total_platform_units_revenue
        capital_employed = 0.0

    sell_through_pct = 100 * total_units_sold / order_qty
    return {
        "units_sold": round(total_units_sold, 1),
        "unsold_units": round(unsold, 1),
        "sell_through_pct": round(sell_through_pct, 1),
        "gmv": round(total_gmv),
        "profit": round(profit),
        "capital_employed": round(capital_employed),
    }


def main():
    rows = []
    trial_id = 0
    for tier_name, (base_demand, shock_sd) in DEMAND_TIERS.items():
        for _ in range(N_TRIALS_PER_TIER):
            trial_id += 1
            # A single demand-shock draw per trial, shared across all three
            # models -- this SKU either sells better or worse than forecast,
            # consistently, through the season (paired design).
            demand_shock = max(0.1, random.lognormvariate(0, shock_sd))
            forecast_total = base_demand * sum((1 - DEMAND_DECAY_PER_WEEK) ** w for w in range(SEASON_WEEKS))
            order_qty = round(forecast_total * (1 + FORECAST_BUFFER))

            for model in ("MP", "OR", "SOR"):
                result = simulate_one(model, order_qty, base_demand, demand_shock)
                rows.append({
                    "trial_id": trial_id, "tier": tier_name, "model": model,
                    "order_qty": order_qty, "demand_shock": round(demand_shock, 3),
                    **result,
                })

    with open("simulation_results.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} rows ({trial_id} trials x 3 models) to simulation_results.csv")


if __name__ == "__main__":
    main()
