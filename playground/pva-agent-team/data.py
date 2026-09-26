"""
Builds a SYNTHETIC men's-footwear warehouse in SQLite (seeded, reproducible).
No real company data -- every brand, number and event below is made up.

    python3 data.py            # (re)builds data/footwear.db

Tables
------
dim_style     brand x article_type: commercial model (OR/SOR/MP), MRP, planned
              discount, planned Myntra rebate (MP only), price band
hour_curve    share of a day's traffic that lands in each hour (sums to 1)
plan_phasing  AOP -> MoP -> DoD: the weight each day of the month gets
plan_daily    phased plan per date x brand x article_type x channel x city_tier
fact_hourly   actuals per date x hour x brand x article_type x channel x city_tier
merch_plan    per brand x article_type: planned live styles + size-availability / new-season targets
inventory_hourly  supply snapshot per date x hour x brand x article_type: live styles,
              size availability (demand-weighted share of sizes in stock), broken-style %, new-season share

Funnel identity used everywhere (so every rupee of gap can be explained):
    GMV = Sessions x (LV/Session) x (PDP/LV) x (ATC/PDP) x (Orders/ATC) x UPT x ASP
                     \\_______________ Conversion = Orders/Sessions ___________/

HIDDEN STORY (what the agents should discover -- don't show them this file):
  1. Stridex (OR) price hike from Sep 10: discount 35% -> 28%. ASP up, consideration down, GM up.
  2. Vantage (MP) rebate budget exhausted from Sep 16: Myntra rebate 8% -> 2%.
  3. App traffic in Tier-2/Tier-3 cities down 20% from Sep 18 (campaign paused).
  4. Coastline (SOR) flip-flops/sandals running ~5% above plan (traffic tailwind).
  5. TODAY from 11:00: UrbanKick sneakers ATC/PDP collapses ~45% -- because sizes 8-10 sold out
     (size availability 87% -> ~45%, most styles "broken"). Only inventory_hourly shows the WHY.
  6. Supply is healthy for Stridex and Vantage -> their misses are price/rebate, not stock.
  7. Formale's autumn-winter (new season) shipment is late: new-season share stuck ~12% vs 35%
     target. No GMV hit yet -- an early-warning risk for October.
  8. Brands respond differently to discount (ELASTICITY below): Trekko most, Redline least.
     The Rebate Allocator should discover this before splitting a rebate budget.
"""
import math
import random
import sqlite3
from datetime import date, timedelta

import config

# brand, article_type, model, MRP, planned total discount, planned Myntra rebate (MP), traffic weight
STYLES = [
    ("Stridex",       "Sports Shoes", "OR",  4499, 0.35, 0.00, 1.4),
    ("Stridex",       "Casual Shoes", "OR",  2999, 0.35, 0.00, 0.8),
    ("UrbanKick",     "Sneakers",     "OR",  6999, 0.30, 0.00, 1.0),
    ("UrbanKick",     "Casual Shoes", "OR",  3299, 0.30, 0.00, 0.7),
    ("Formale",       "Formal Shoes", "SOR", 3499, 0.25, 0.00, 0.6),
    ("Oxbridge",      "Formal Shoes", "SOR", 2799, 0.30, 0.00, 0.5),
    ("Oxbridge",      "Casual Shoes", "SOR", 2499, 0.30, 0.00, 0.6),
    ("Coastline",     "Flip Flops",   "SOR",  899, 0.20, 0.00, 1.1),
    ("Coastline",     "Sandals",      "SOR", 1799, 0.25, 0.00, 0.7),
    ("Redline Sport", "Sports Shoes", "MP",  3999, 0.40, 0.05, 1.3),
    ("Redline Sport", "Flip Flops",   "MP",   799, 0.30, 0.05, 0.6),
    ("Vantage",       "Casual Shoes", "MP",  2499, 0.45, 0.08, 1.2),
    ("Vantage",       "Sneakers",     "MP",  3499, 0.45, 0.08, 1.0),
    ("Trekko",        "Sports Shoes", "MP",  2999, 0.50, 0.06, 0.9),
    ("Trekko",        "Sandals",      "MP",  1499, 0.45, 0.06, 0.6),
]
CHANNELS = {"App": 0.78, "Web": 0.22}
CITY_TIERS = {"Tier-1": 0.45, "Tier-2": 0.35, "Tier-3": 0.20}

CATEGORY_DAILY_SESSIONS = 900_000

# TRUE discount elasticity: % change in consideration per 1pp of discount. Hidden --
# the agents must ESTIMATE it from the data (tools estimate_elasticity).
ELASTICITY = {"Vantage": 2.2, "Redline Sport": 1.2, "Trekko": 2.6}
DEFAULT_ELASTICITY = 1.8

# Commercial terms (these ARE known to the business, so they go in dim_style)
COGS_PCT_OF_MRP = 0.45        # OR: we buy at 45% of MRP
SOR_MARGIN_SHARE = 0.27       # SOR: we keep 27% of GMV
MP_COMMISSION = 0.20          # MP: we keep 20% of GMV, minus any rebate we fund

# MP rebate budgets as a share of the planned monthly rebate spend. Vantage's ran out mid-month.
REBATE_BUDGET_SHARE = {"Redline Sport": 1.0, "Trekko": 1.0, "Vantage": 0.55}
PLAN_SESSION_AMBITION = 1.02          # AOP asks for 2% more traffic than the natural run-rate
EVENT_DAYS = {date(2026, 9, 12), date(2026, 9, 13), date(2026, 9, 14)}   # "Footwear Fest"

HOUR_WEIGHTS = [0.6, 0.35, 0.2, 0.15, 0.12, 0.15, 0.3, 0.6, 1.0, 1.3, 1.5, 1.7,
                1.8, 1.8, 1.7, 1.6, 1.6, 1.7, 1.9, 2.2, 2.5, 2.6, 2.2, 1.3]
HOUR_SHARE = [w / sum(HOUR_WEIGHTS) for w in HOUR_WEIGHTS]


def price_band(asp):
    if asp < 1000:
        return "<1k"
    if asp < 2000:
        return "1k-2k"
    if asp < 4000:
        return "2k-4k"
    return "4k+"


def day_weight(d):
    """DoD phasing: how much of the month's plan a given day carries."""
    w = 1.0
    if d.weekday() >= 5:
        w *= 1.18                      # weekend
    elif d.weekday() == 4:
        w *= 1.05                      # Friday
    if d.day <= 3:
        w *= 1.08                      # payday
    if d in EVENT_DAYS:
        w *= 1.45                      # sale event
    return w


def base_rates(style, channel, tier):
    """Natural funnel rates for a style/channel/tier (before any shocks)."""
    brand, at, model, mrp, disc, rebate, _ = style
    cheap = mrp < 2000
    rates = {
        "lv_per_session": 2.2,
        "pdp_ctr": 0.42,
        "consideration": 0.11 if cheap else 0.09,     # ATC / PDP
        "checkout": 0.34,                             # Orders / ATC
        "upt": 1.15 if at in ("Flip Flops", "Sandals") else 1.05,
    }
    if channel == "Web":
        rates["consideration"] *= 0.82
    rates["consideration"] *= {"Tier-1": 1.05, "Tier-2": 1.0, "Tier-3": 0.88}[tier]
    return rates


def shocks(d, hour, style, channel, tier):
    """The hidden story. Returns multipliers / discount changes for ACTUALS only."""
    brand, at, *_ = style
    s = {"sessions": 1.0, "consideration": 1.0, "disc_delta": 0.0, "rebate_delta": 0.0}
    if brand == "Stridex" and d >= date(2026, 9, 10):
        s["disc_delta"] = -0.07                       # price hike
    if brand == "Vantage" and d >= date(2026, 9, 16):
        s["disc_delta"] = -0.06                       # rebate budget exhausted
        s["rebate_delta"] = -0.06
    if channel == "App" and tier in ("Tier-2", "Tier-3") and d >= date(2026, 9, 18):
        s["sessions"] *= 0.80                         # campaign paused
    if brand == "Coastline":
        s["sessions"] *= 1.10                         # monsoon tailwind
    if brand == "UrbanKick" and at == "Sneakers" and d == config.AS_OF_DATE and hour >= 11:
        s["consideration"] *= 0.55                    # broken sizes today
    return s


def compute_cell(style, channel, tier, sessions, disc, rebate):
    """Turn sessions + price into the full funnel + money for one cell (floats)."""
    brand, at, model, mrp, *_ = style
    r = base_rates(style, channel, tier)
    plan_disc = style[4]
    # Discount elasticity: every 1pp less discount -> ~1.8% less consideration
    consideration = r["consideration"] * (1 + ELASTICITY.get(brand, DEFAULT_ELASTICITY) * (disc - plan_disc))
    lv = sessions * r["lv_per_session"]
    pdp = lv * r["pdp_ctr"]
    atc = pdp * consideration
    orders = atc * r["checkout"]
    units = orders * r["upt"]
    return dict(sessions=sessions, list_views=lv, pdp_views=pdp, atc=atc, orders=orders,
                units=units, mrp=mrp, disc=disc, rebate=rebate, model=model)


def money(units, mrp, disc, rebate, model):
    gmv = units * mrp * (1 - disc)
    mrp_value = units * mrp
    rebate_amt = units * mrp * rebate
    if model == "OR":
        gm = gmv - units * mrp * COGS_PCT_OF_MRP # we own inventory: GMV - COGS
    elif model == "SOR":
        gm = gmv * SOR_MARGIN_SHARE              # fixed margin share
    else:
        gm = gmv * MP_COMMISSION - rebate_amt    # MP: commission minus our rebate
    return gmv, gm, mrp_value, rebate_amt


def stoch_round(x, rng):
    """Unbiased integer rounding so tiny hourly cells don't all round to 0."""
    return int(math.floor(x + rng.random()))


SIZE_TARGET = 0.85
NEW_SEASON_TARGET = 0.35


def size_availability(d, hour, style, rng):
    """Demand-weighted share of sizes in stock. Healthy ~0.87 unless the story says otherwise."""
    brand, at, *_ = style
    base = rng.gauss(0.87, 0.012)
    if brand == "UrbanKick" and at == "Sneakers" and d == config.AS_OF_DATE:
        # sizes 8-10 sell through during the morning, gone by 11:00 (matches the shock above)
        base = {8: 0.84, 9: 0.79, 10: 0.72}.get(hour, 0.46 if hour >= 11 else base)
    return min(base, 0.97)


def build_inventory(con, days):
    """Supply side. Separate RNG so the funnel actuals above stay identical."""
    rng = random.Random(7)
    plan_rows, inv_rows = [], []
    for st in STYLES:
        plan_rows.append((st[0], st[1], int(round(st[6] * 90)), SIZE_TARGET, NEW_SEASON_TARGET))
    con.executemany("INSERT INTO merch_plan VALUES (?,?,?,?,?)", plan_rows)
    for i, d in enumerate(days):
        if d > config.AS_OF_DATE:
            break
        for st, (_, _, live_plan, _, _) in zip(STYLES, plan_rows):
            live = int(round(live_plan * rng.gauss(1.0, 0.02)))
            # autumn-winter season lands through the month; Formale's shipment is late
            ns = 0.12 if st[0] == "Formale" else 0.22 + 0.18 * i / len(days)
            ns += rng.gauss(0, 0.01)
            for h in range(24):
                if d == config.AS_OF_DATE and h >= config.AS_OF_HOUR:
                    break
                sa = size_availability(d, h, st, rng)
                broken = max(0.0, min(1.0, 0.08 + (0.87 - sa) * 1.6 + rng.gauss(0, 0.01)))
                inv_rows.append((d.isoformat(), h, st[0], st[1], live, round(sa, 4), round(broken, 4), round(ns, 4)))
    con.executemany("INSERT INTO inventory_hourly VALUES (?,?,?,?,?,?,?,?)", inv_rows)
    con.execute("CREATE INDEX ix_inv ON inventory_hourly(date, hour)")


def build():
    rng = random.Random(42)
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if config.DB_PATH.exists():
        config.DB_PATH.unlink()
    con = sqlite3.connect(config.DB_PATH)
    con.executescript("""
        CREATE TABLE dim_style (brand TEXT, article_type TEXT, commercial_model TEXT, mrp REAL,
            plan_discount_pct REAL, plan_rebate_pct REAL, price_band TEXT,
            cogs_pct_of_mrp REAL, sor_margin_share REAL, mp_commission REAL,
            PRIMARY KEY (brand, article_type));
        CREATE TABLE hour_curve (hour INTEGER PRIMARY KEY, share REAL);
        CREATE TABLE plan_phasing (date TEXT PRIMARY KEY, day_type TEXT, weight REAL, share_of_month REAL);
        CREATE TABLE plan_daily (date TEXT, brand TEXT, article_type TEXT, channel TEXT, city_tier TEXT,
            sessions REAL, list_views REAL, pdp_views REAL, atc REAL, orders REAL, units REAL,
            gmv REAL, gm REAL, mrp_value REAL, rebate_amt REAL);
        CREATE TABLE fact_hourly (date TEXT, hour INTEGER, brand TEXT, article_type TEXT, channel TEXT,
            city_tier TEXT, sessions INTEGER, list_views INTEGER, pdp_views INTEGER, atc INTEGER,
            orders INTEGER, units INTEGER, gmv REAL, gm REAL, mrp_value REAL, rebate_amt REAL);
        CREATE TABLE merch_plan (brand TEXT, article_type TEXT, live_styles_plan INTEGER,
            size_availability_target REAL, new_season_share_target REAL, PRIMARY KEY (brand, article_type));
        CREATE TABLE inventory_hourly (date TEXT, hour INTEGER, brand TEXT, article_type TEXT,
            live_styles INTEGER, size_availability REAL, broken_style_pct REAL, new_season_share REAL);
    """)

    for st in STYLES:
        brand, at, model, mrp, disc, rebate, _ = st
        con.execute("INSERT INTO dim_style VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (brand, at, model, mrp, disc, rebate, price_band(mrp * (1 - disc)),
                     COGS_PCT_OF_MRP if model == "OR" else None, SOR_MARGIN_SHARE if model == "SOR" else None,
                     MP_COMMISSION if model == "MP" else None))
    con.executemany("INSERT INTO hour_curve VALUES (?,?)", list(enumerate(HOUR_SHARE)))

    days = [config.MONTH_START + timedelta(n) for n in range((config.MONTH_END - config.MONTH_START).days + 1)]
    weights = {d: day_weight(d) for d in days}
    avg_w = sum(weights.values()) / len(days)
    for d in days:
        day_type = "event" if d in EVENT_DAYS else "weekend" if d.weekday() >= 5 else "weekday"
        con.execute("INSERT INTO plan_phasing VALUES (?,?,?,?)",
                    (d.isoformat(), day_type, round(weights[d], 4), weights[d] / sum(weights.values())))

    total_style_w = sum(s[6] for s in STYLES)
    plan_rows, fact_rows = [], []
    for d in days:
        event_disc = 0.05 if d in EVENT_DAYS else 0.0
        for st in STYLES:
            style_sessions = CATEGORY_DAILY_SESSIONS * st[6] / total_style_w * weights[d] / avg_w
            day_noise = rng.gauss(1, 0.04)
            for ch, ch_share in CHANNELS.items():
                for tier, tier_share in CITY_TIERS.items():
                    cell_sessions = style_sessions * ch_share * tier_share
                    plan_disc, plan_reb = st[4] + event_disc, st[5]

                    # ---- plan (daily grain, floats) ----
                    p = compute_cell(st, ch, tier, cell_sessions * PLAN_SESSION_AMBITION, plan_disc, plan_reb)
                    gmv, gm, mrpv, reb = money(p["units"], p["mrp"], plan_disc, plan_reb, p["model"])
                    plan_rows.append((d.isoformat(), st[0], st[1], ch, tier) + tuple(
                        round(x, 2) for x in (p["sessions"], p["list_views"], p["pdp_views"], p["atc"],
                                              p["orders"], p["units"], gmv, gm, mrpv, reb)))

                    # ---- actuals (hourly grain, only up to "now") ----
                    if d > config.AS_OF_DATE:
                        continue
                    for h in range(24):
                        if d == config.AS_OF_DATE and h >= config.AS_OF_HOUR:
                            break
                        s = shocks(d, h, st, ch, tier)
                        disc = plan_disc + s["disc_delta"]
                        reb_pct = plan_reb + s["rebate_delta"]
                        sess = cell_sessions * HOUR_SHARE[h] * day_noise * s["sessions"] * rng.gauss(1, 0.03)
                        a = compute_cell(st, ch, tier, sess, disc, reb_pct)
                        a["atc"] *= s["consideration"] * rng.gauss(1, 0.02)
                        # re-derive downstream after the consideration shock
                        r = base_rates(st, ch, tier)
                        n = {k: stoch_round(a[k], rng) for k in ("sessions", "list_views", "pdp_views", "atc")}
                        n["orders"] = stoch_round(n["atc"] * r["checkout"], rng)
                        n["units"] = stoch_round(n["orders"] * r["upt"], rng)
                        gmv, gm, mrpv, reb = money(n["units"], st[3], disc, reb_pct, st[2])
                        fact_rows.append((d.isoformat(), h, st[0], st[1], ch, tier, n["sessions"],
                                          n["list_views"], n["pdp_views"], n["atc"], n["orders"],
                                          n["units"], round(gmv, 2), round(gm, 2), round(mrpv, 2), round(reb, 2)))

    con.executemany("INSERT INTO plan_daily VALUES (" + ",".join("?" * 15) + ")", plan_rows)
    con.executemany("INSERT INTO fact_hourly VALUES (" + ",".join("?" * 16) + ")", fact_rows)
    con.execute("CREATE INDEX ix_fact ON fact_hourly(date, hour)")
    build_inventory(con, days)
    con.execute("CREATE TABLE rebate_budget (brand TEXT PRIMARY KEY, month TEXT, budget_inr REAL)")
    for brand, share in REBATE_BUDGET_SHARE.items():
        planned = con.execute("SELECT SUM(rebate_amt) FROM plan_daily WHERE brand = ?", (brand,)).fetchone()[0]
        con.execute("INSERT INTO rebate_budget VALUES (?,?,?)",
                    (brand, config.MONTH_START.strftime("%Y-%m"), round(planned * share, -5)))
    con.commit()
    con.close()
    print(f"Built {config.DB_PATH} -- {len(plan_rows):,} plan rows, {len(fact_rows):,} hourly actual rows")


if __name__ == "__main__":
    build()
