"""
Synthetic category-month panel for a difference-in-differences (DiD) test —
the direct follow-up promised in Project 01's executive summary, where a
naive discount/demand regression was flagged as confounded by seasonality.

The natural experiment: in **May 2024** (a seasonally flat month — no
festive or EOSS calendar event touches any category), Sneakers runs a
one-off inventory-clearance discount (+15pts over its usual baseline) that
has NOTHING to do with the seasonal calendar. Every other sub-category
follows its normal trend+seasonality that month, untouched. That's what
makes May 2024 usable for causal identification: unlike Project 01's
festive/EOSS discounts, this shock is uncorrelated with any independent
demand driver.

A known TRUE_CAUSAL_ELASTICITY is embedded (smaller than Project 01's
confounded ~2.56 estimate, on purpose) so the DiD analysis has a real,
specific number to try to recover.

Run:
    python3 generate_data.py
Produces:
    category_month_panel.csv
"""
import csv
import random
from datetime import date

random.seed(11)

SUB_CATEGORIES = ["Sneakers", "Casual Shoes", "Formal Shoes", "Sports Shoes", "Sandals & Floaters"]
TREATED = "Sneakers"
BASE_LEVEL = {"Sneakers": 2200, "Casual Shoes": 1300, "Formal Shoes": 700, "Sports Shoes": 1150, "Sandals & Floaters": 480}
BASELINE_DISCOUNT = {"Sneakers": 0.22, "Casual Shoes": 0.28, "Formal Shoes": 0.18, "Sports Shoes": 0.25, "Sandals & Floaters": 0.30}

EVENT_YM = "2024-05"
EVENT_EXTRA_DISCOUNT = 0.15         # Sneakers-only, May 2024 only
TRUE_CAUSAL_ELASTICITY = 1.1        # deliberately smaller than Project 01's confounded ~2.56

MONTHS = [f"2024-{m:02d}" for m in range(1, 13)]


def seasonality(m):
    if m in (10, 11):
        return 1.55
    if m in (1, 7):
        return 1.30
    if m == 6:
        return 0.92
    return 1.0


def main():
    rows = []
    # small category-specific drift so pre-trends are realistically *close*
    # to parallel rather than mechanically identical
    drift = {cat: random.uniform(0.995, 1.02) for cat in SUB_CATEGORIES}

    for idx, ym in enumerate(MONTHS, start=1):
        month_num = int(ym.split("-")[1])
        for cat in SUB_CATEGORIES:
            base = BASE_LEVEL[cat] * (drift[cat] ** idx) * seasonality(month_num)
            noise = random.gauss(1.0, 0.035)
            discount = BASELINE_DISCOUNT[cat]
            if month_num in (10, 11):
                discount += 0.14
            if month_num in (1, 7):
                discount += 0.10

            is_event = (cat == TREATED and ym == EVENT_YM)
            if is_event:
                discount += EVENT_EXTRA_DISCOUNT
                causal_lift = (2.718281828 ** (TRUE_CAUSAL_ELASTICITY * EVENT_EXTRA_DISCOUNT))
            else:
                causal_lift = 1.0

            orders = round(base * noise * causal_lift)
            avg_price = 3200 if cat == "Sneakers" else {"Casual Shoes": 1900, "Formal Shoes": 2600,
                                                          "Sports Shoes": 2800, "Sandals & Floaters": 900}[cat]
            revenue = round(orders * avg_price * (1 - discount))

            rows.append({
                "year_month": ym, "month_index": idx, "sub_category": cat,
                "is_treated_group": int(cat == TREATED), "is_event_month": int(ym == EVENT_YM),
                "orders": orders, "avg_discount_pct": round(discount, 3), "revenue": revenue,
            })

    with open("category_month_panel.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} category-month rows ({len(SUB_CATEGORIES)} categories x {len(MONTHS)} months) "
          f"to category_month_panel.csv. Event: {TREATED} in {EVENT_YM}, true causal elasticity = {TRUE_CAUSAL_ELASTICITY}")


if __name__ == "__main__":
    main()
