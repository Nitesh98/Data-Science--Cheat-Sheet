"""
Synthetic order-level dataset for the Men's Footwear category diagnostic.

IMPORTANT: This is SIMULATED data, not real Myntra data. It is built to
have realistic, internally-consistent patterns (seasonality, discount
elasticity, cohort retention, channel mix, sizing-driven returns) so the
downstream SQL/Python analyses have real signal to recover -- while making
no claim about actual company numbers. Use it to demonstrate *method*,
and say so plainly if asked in an interview.

Run:
    python3 generate_data.py
Produces:
    orders.csv  (~45k rows, 24 months: Jan 2023 - Dec 2024)
"""
import csv
import math
import random
from datetime import date

random.seed(42)

N_MONTHS = 24
START_YEAR, START_MONTH = 2023, 1

SUB_CATEGORIES = ["Sneakers", "Casual Shoes", "Formal Shoes", "Sports Shoes", "Sandals & Floaters"]
SUB_CATEGORY_WEIGHTS = [0.38, 0.22, 0.12, 0.20, 0.08]  # Sneakers dominate men's footwear online
BASELINE_DISCOUNT = {  # category baseline discount %, before seasonal/promo effects
    "Sneakers": 0.22, "Casual Shoes": 0.28, "Formal Shoes": 0.18, "Sports Shoes": 0.25, "Sandals & Floaters": 0.30,
}
LIST_PRICE_RANGE = {  # (min, max) MRP in INR by sub-category
    "Sneakers": (1999, 6999), "Casual Shoes": (999, 3499), "Formal Shoes": (1499, 4999),
    "Sports Shoes": (1499, 5999), "Sandals & Floaters": (499, 1999),
}
RETURN_BASE_RATE = {  # sizing-fit driven return propensity
    "Sneakers": 0.09, "Casual Shoes": 0.07, "Formal Shoes": 0.14, "Sports Shoes": 0.10, "Sandals & Floaters": 0.05,
}
BRAND_TIERS = ["Value", "Mid", "Premium"]
BRAND_TIER_WEIGHTS = [0.35, 0.45, 0.20]
BRAND_TIER_MULT = {"Value": 0.7, "Mid": 1.0, "Premium": 1.6}
CHANNELS = ["Organic/Direct", "Paid Search", "Paid Social", "Affiliate", "Email/CRM"]
CHANNEL_WEIGHTS_NEW = [0.30, 0.28, 0.24, 0.10, 0.08]   # acquisition mix
CHANNEL_WEIGHTS_REPEAT = [0.45, 0.12, 0.10, 0.05, 0.28]  # repeat purchases skew organic/CRM
CITY_TIERS = ["Tier 1", "Tier 2", "Tier 3"]
CITY_TIER_WEIGHTS = [0.42, 0.36, 0.22]

ELASTICITY = 1.9          # sensitivity of demand to discount above baseline
RETENTION_CURVE = {0: 1.00, 1: 0.32, 2: 0.20, 3: 0.15, 4: 0.12, 5: 0.10}  # month-since-acquisition -> active prob


def month_index_to_ym(idx):
    y, m = START_YEAR, START_MONTH + idx
    y += (m - 1) // 12
    m = (m - 1) % 12 + 1
    return y, m


def seasonality_multiplier(y, m):
    # Festive season (Oct-Nov) and End-of-Season-Sale (Jan, Jul) spikes typical of Indian fashion e-commerce
    if m in (10, 11):
        return 1.55
    if m in (1, 7):
        return 1.30
    if m in (6,):  # summer dip for closed footwear, partially offset by sandals -- kept simple
        return 0.92
    return 1.0


def discount_for_month(subcat, y, m):
    base = BASELINE_DISCOUNT[subcat]
    bump = 0.0
    if m in (10, 11):
        bump += 0.14
    if m in (1, 7):
        bump += 0.10
    noise = random.gauss(0, 0.015)
    return max(0.05, min(0.65, base + bump + noise))


def retention_prob(months_since_acq, discount_delta):
    base = RETENTION_CURVE.get(months_since_acq)
    if base is None:
        base = max(0.02, 0.09 * (0.93 ** (months_since_acq - 6)))
    # discount above the customer's home-category baseline nudges reactivation
    return min(0.95, max(0.0, base * (1 + ELASTICITY * discount_delta)))


def new_cohort_size(idx, y, m):
    trend = 1400 * (1.020 ** idx)  # ~2%/month underlying acquisition growth
    return trend * seasonality_multiplier(y, m)


class Customer:
    __slots__ = ("cid", "acq_month_idx", "subcat", "channel", "city_tier")

    def __init__(self, cid, acq_month_idx, subcat, channel, city_tier):
        self.cid = cid
        self.acq_month_idx = acq_month_idx
        self.subcat = subcat
        self.channel = channel
        self.city_tier = city_tier


def gen_price(subcat, brand_tier):
    lo, hi = LIST_PRICE_RANGE[subcat]
    base = random.uniform(lo, hi)
    return round(base * BRAND_TIER_MULT[brand_tier] / 10) * 10


def main():
    customers = []
    rows = []
    order_id = 1

    for idx in range(N_MONTHS):
        y, m = month_index_to_ym(idx)

        # 1) acquire new customers this month
        n_new = int(round(new_cohort_size(idx, y, m)))
        for _ in range(n_new):
            subcat = random.choices(SUB_CATEGORIES, SUB_CATEGORY_WEIGHTS)[0]
            channel = random.choices(CHANNELS, CHANNEL_WEIGHTS_NEW)[0]
            city_tier = random.choices(CITY_TIERS, CITY_TIER_WEIGHTS)[0]
            cust = Customer(len(customers) + 1, idx, subcat, channel, city_tier)
            customers.append(cust)

        # 2) decide activations for ALL customers acquired in this or an earlier month
        month_discount_cache = {sc: discount_for_month(sc, y, m) for sc in SUB_CATEGORIES}
        for cust in customers:
            k = idx - cust.acq_month_idx
            if k < 0:
                continue
            disc = month_discount_cache[cust.subcat]
            delta = disc - BASELINE_DISCOUNT[cust.subcat]
            is_acq_order = (k == 0)
            prob = 1.0 if is_acq_order else retention_prob(k, delta)
            if random.random() > prob:
                continue

            n_orders_this_month = 1 if random.random() > 0.08 else 2
            for _ in range(n_orders_this_month):
                brand_tier = random.choices(BRAND_TIERS, BRAND_TIER_WEIGHTS)[0]
                list_price = gen_price(cust.subcat, brand_tier)
                discount_pct = round(month_discount_cache[cust.subcat] + random.gauss(0, 0.03), 3)
                discount_pct = max(0.0, min(0.70, discount_pct))
                units = 1 if random.random() > 0.12 else 2
                final_price = round(list_price * (1 - discount_pct))
                channel = cust.channel if k > 0 else cust.channel
                if k > 0:  # repeat purchase channel mix differs from acquisition
                    channel = random.choices(CHANNELS, CHANNEL_WEIGHTS_REPEAT)[0]
                returned = random.random() < (RETURN_BASE_RATE[cust.subcat] * (1 + 0.4 * discount_pct))
                order_date = date(y, m, random.randint(1, 28))

                rows.append({
                    "order_id": order_id,
                    "order_date": order_date.isoformat(),
                    "year_month": f"{y:04d}-{m:02d}",
                    "customer_id": cust.cid,
                    "is_new_customer": int(is_acq_order),
                    "months_since_acquisition": k,
                    "sub_category": cust.subcat,
                    "brand_tier": brand_tier,
                    "list_price": list_price,
                    "discount_pct": discount_pct,
                    "final_price": final_price,
                    "units": units,
                    "revenue": final_price * units,
                    "marketing_channel": channel,
                    "city_tier": cust.city_tier,
                    "returned": int(returned),
                })
                order_id += 1

    rows.sort(key=lambda r: r["order_date"])
    fieldnames = list(rows[0].keys())
    with open("orders.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    print(f"Wrote {len(rows)} orders across {len(customers)} customers to orders.csv")


if __name__ == "__main__":
    main()
