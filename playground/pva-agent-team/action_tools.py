"""
ACTION tools -- "what should we do, and what is it worth in rupees?"

Diagnosis tools (tools.py) look backwards. These look forwards: they project the
rest of the month from the last 7 days' run-rate and simulate levers:

    estimate_elasticity   how much consideration moves per 1pp discount, per brand (fitted on data)
    rebate_status         MP rebate budget vs spend
    simulate_rebate       one MP brand at a new rebate % -> rest-of-month GMV / GM / rebate cost
    optimize_rebate       split a rebate top-up across MP brands for the most GMV per rupee
    price_scan            OR/SOR brand: discount grid -> rest-of-month GMV / GM trade-off
    month_landing         where the month lands on current run-rate, per brand
    rephase_plan          the remaining days' targets needed to still hit MoP
    restore_to_plan       GMV recovered if one metric goes back to plan for a slice (traffic, sizes...)
    action_coverage       do the proposed actions close the gap?

The projection model (same funnel identity as everywhere else):
    units = sessions x LV/session x PDP CTR x consideration x checkout x UPT
    consideration' = consideration x (1 + elasticity x (new_discount - current_discount))
    GMV = units x MRP x (1 - discount);  GM from the commercial terms in dim_style
"""
from datetime import timedelta

import config
import tools

RUN_RATE_DAYS = 7
REBATE_CAP = 0.12          # never fund more than 12% of MRP as rebate
REBATE_STEP = 0.005        # optimiser moves in 0.5pp steps


def _dates():
    yday = config.AS_OF_DATE - timedelta(1)
    return (yday - timedelta(RUN_RATE_DAYS - 1)).isoformat(), yday.isoformat()


def _remaining_share():
    return 1 - tools._query("SELECT SUM(share) s FROM hour_curve WHERE hour < ?", [config.AS_OF_HOUR])[0]["s"]


# ---------------------------------------------------------------------------
# The projection engine
# ---------------------------------------------------------------------------
def _baseline(brand=None):
    """Per brand x article_type: last-7-day rates + remaining plan sessions for the month."""
    d0, d1 = _dates()
    w, p = ("AND f.brand = ?", [brand]) if brand else ("", [])
    act = tools._query(
        "SELECT f.brand, f.article_type, d.commercial_model, d.cogs_pct_of_mrp, d.sor_margin_share, d.mp_commission, "
        "SUM(f.sessions) sessions, SUM(f.list_views) lv, SUM(f.pdp_views) pdp, SUM(f.atc) atc, SUM(f.orders) orders, "
        "SUM(f.units) units, SUM(f.gmv) gmv, SUM(f.mrp_value) mrp_value, SUM(f.rebate_amt) rebate_amt "
        "FROM fact_hourly f JOIN dim_style d USING (brand, article_type) "
        f"WHERE f.date BETWEEN ? AND ? {w} GROUP BY f.brand, f.article_type", [d0, d1] + p)
    wp, pp = ("AND brand = ?", [brand]) if brand else ("", [])
    plan7 = {(r["brand"], r["article_type"]): r["s"] for r in tools._query(
        f"SELECT brand, article_type, SUM(sessions) s FROM plan_daily WHERE date BETWEEN ? AND ? {wp} "
        "GROUP BY brand, article_type", [d0, d1] + pp)}
    share_left = _remaining_share()
    rem = {(r["brand"], r["article_type"]): r["s"] for r in tools._query(
        "SELECT brand, article_type, SUM(CASE WHEN date = ? THEN sessions * ? ELSE sessions END) s "
        f"FROM plan_daily WHERE date >= ? {wp} GROUP BY brand, article_type",
        [config.AS_OF_DATE.isoformat(), share_left, config.AS_OF_DATE.isoformat()] + pp)}
    out = []
    for r in act:
        k = (r["brand"], r["article_type"])
        out.append({**r,
                    "sessions_pva_7d": r["sessions"] / plan7[k],
                    "remaining_sessions": rem.get(k, 0) * r["sessions"] / plan7[k],
                    "lv_rate": r["lv"] / r["sessions"], "pdp_rate": r["pdp"] / r["lv"],
                    "consideration": r["atc"] / r["pdp"], "checkout": r["orders"] / r["atc"],
                    "upt": r["units"] / r["orders"], "mrp": r["mrp_value"] / r["units"],
                    "discount": 1 - r["gmv"] / r["mrp_value"], "rebate": r["rebate_amt"] / r["mrp_value"]})
    return out


def _project(b, elasticity, discount=None, rebate=None):
    """Rest-of-month GMV/GM for one baseline row at a (possibly new) discount / rebate."""
    new_disc = b["discount"] if discount is None else discount
    new_reb = b["rebate"] if rebate is None else rebate
    if rebate is not None and discount is None:              # MP: rebate moves the total discount
        new_disc = b["discount"] + (new_reb - b["rebate"])
    cons = b["consideration"] * (1 + elasticity * (new_disc - b["discount"]))
    units = b["remaining_sessions"] * b["lv_rate"] * b["pdp_rate"] * cons * b["checkout"] * b["upt"]
    gmv = units * b["mrp"] * (1 - new_disc)
    reb_cost = units * b["mrp"] * new_reb
    if b["commercial_model"] == "OR":
        gm = gmv - units * b["mrp"] * b["cogs_pct_of_mrp"]
    elif b["commercial_model"] == "SOR":
        gm = gmv * b["sor_margin_share"]
    else:
        gm = gmv * b["mp_commission"] - reb_cost
    return {"gmv": gmv, "gm": gm, "rebate_cost": reb_cost, "units": units, "discount": new_disc}


# ---------------------------------------------------------------------------
# Elasticity: fitted, not assumed
# ---------------------------------------------------------------------------
def estimate_elasticity(brand=None):
    """Per brand: OLS of daily consideration on daily discount (MTD). Variation comes from sale
    days and any price/rebate changes. Elasticity = slope / mean consideration = % change per 1pp."""
    d_from, d_to, _ = tools._window("mtd")
    w, p = ("AND f.brand = ?", [brand]) if brand else ("", [])
    rows = tools._query(
        "SELECT f.brand, f.date, SUM(f.atc) * 1.0 / SUM(f.pdp_views) consideration, "
        "1 - SUM(f.gmv) / SUM(f.mrp_value) discount FROM fact_hourly f "
        f"WHERE f.date BETWEEN ? AND ? {w} GROUP BY f.brand, f.date", [d_from, d_to] + p)
    by = {}
    for r in rows:
        by.setdefault(r["brand"], []).append((r["discount"], r["consideration"]))
    out = []
    for b, pts in sorted(by.items()):
        n = len(pts)
        mx = sum(x for x, _ in pts) / n
        my = sum(y for _, y in pts) / n
        sxx = sum((x - mx) ** 2 for x, _ in pts)
        sxy = sum((x - mx) * (y - my) for x, y in pts)
        syy = sum((y - my) ** 2 for _, y in pts)
        slope = sxy / sxx if sxx else 0.0
        r2 = (sxy * sxy / (sxx * syy)) if sxx and syy else 0.0
        out.append({"brand": b, "elasticity_pct_per_pp": round(slope / my, 2), "r2": round(r2, 2), "days": n,
                    "discount_range_pp": round((max(x for x, _ in pts) - min(x for x, _ in pts)) * 100, 1)})
    return {"method": "OLS daily consideration ~ discount, MTD", "brands": out,
            "note": "elasticity 1.8 = +1.8% consideration per +1pp discount. Low r2 or tiny discount range = unreliable."}


def _elasticities():
    return {r["brand"]: r["elasticity_pct_per_pp"] for r in estimate_elasticity()["brands"]}


# ---------------------------------------------------------------------------
# MP rebates
# ---------------------------------------------------------------------------
def rebate_status():
    spent = {r["brand"]: r["s"] for r in tools._query(
        "SELECT brand, SUM(rebate_amt) s FROM fact_hourly WHERE date >= ? GROUP BY brand", [config.MONTH_START.isoformat()])}
    out = []
    for r in tools._query("SELECT b.brand, b.budget_inr, MAX(d.plan_rebate_pct) plan_rebate_pct FROM rebate_budget b "
                          "JOIN dim_style d USING (brand) GROUP BY b.brand"):
        base = _baseline(r["brand"])
        cur = sum(x["rebate_amt"] for x in base) / sum(x["mrp_value"] for x in base)
        out.append({"brand": r["brand"], "budget_inr": round(r["budget_inr"]), "spent_mtd_inr": round(spent.get(r["brand"], 0)),
                    "remaining_inr": round(r["budget_inr"] - spent.get(r["brand"], 0)),
                    "current_rebate_pct_7d": round(cur, 4), "plan_rebate_pct": r["plan_rebate_pct"]})
    return {"as_of": str(config.AS_OF_DATE), "brands": out}


def simulate_rebate(brand, rebate_pct):
    base = _baseline(brand)
    if not base or base[0]["commercial_model"] != "MP":
        return {"error": f"{brand} is not an MP brand"}
    e = _elasticities()[brand] / 1.0
    now = [_project(b, e) for b in base]
    new = [_project(b, e, rebate=rebate_pct) for b in base]
    s = lambda rows, k: sum(r[k] for r in rows)
    return {"brand": brand, "rest_of_month": True, "elasticity_used": e,
            "rebate_pct_now": round(base[0]["rebate"], 4), "rebate_pct_new": rebate_pct,
            "gmv_now": round(s(now, "gmv")), "gmv_new": round(s(new, "gmv")),
            "gmv_delta_inr": round(s(new, "gmv") - s(now, "gmv")),
            "gm_delta_inr": round(s(new, "gm") - s(now, "gm")),
            "extra_rebate_cost_inr": round(s(new, "rebate_cost") - s(now, "rebate_cost")),
            "gmv_per_rebate_inr": round((s(new, "gmv") - s(now, "gmv")) / max(1, s(new, "rebate_cost") - s(now, "rebate_cost")), 2)}


def optimize_rebate(budget_inr, max_gm_loss_inr=None):
    """Greedy: repeatedly give +0.5pp rebate to the MP brand with the best incremental GMV per extra
    rebate rupee, until the extra-rebate budget (or the GM-loss limit) is used up."""
    el = _elasticities()
    bases = {}
    for r in tools._query("SELECT DISTINCT brand FROM dim_style WHERE commercial_model = 'MP'"):
        bases[r["brand"]] = _baseline(r["brand"])
    cur = {b: v[0]["rebate"] for b, v in bases.items()}
    alloc = dict(cur)
    total = lambda b, reb: [_project(x, el[b], rebate=reb) for x in bases[b]]
    agg = lambda rows, k: sum(r[k] for r in rows)
    spent, gm_loss, steps = 0.0, 0.0, []
    while True:
        best = None
        for b in bases:
            if alloc[b] + REBATE_STEP > REBATE_CAP + 1e-9:
                continue
            a, n = total(b, alloc[b]), total(b, alloc[b] + REBATE_STEP)
            d_gmv = agg(n, "gmv") - agg(a, "gmv")
            d_cost = agg(n, "rebate_cost") - agg(a, "rebate_cost")
            d_gm = agg(n, "gm") - agg(a, "gm")
            if d_cost <= 0:
                continue
            ratio = d_gmv / d_cost
            if best is None or ratio > best[1]:
                best = (b, ratio, d_gmv, d_cost, d_gm)
        if best is None or spent + best[3] > budget_inr:
            break
        if max_gm_loss_inr is not None and gm_loss - best[4] > max_gm_loss_inr:
            break
        b, ratio, d_gmv, d_cost, d_gm = best
        alloc[b] += REBATE_STEP
        spent += d_cost
        gm_loss -= d_gm
        steps.append({"brand": b, "to_rebate_pct": round(alloc[b], 4), "gmv_per_rebate_inr": round(ratio, 2)})
    result = []
    for b in bases:
        a, n = total(b, cur[b]), total(b, alloc[b])
        result.append({"brand": b, "elasticity": el[b], "rebate_pct_now": round(cur[b], 4), "rebate_pct_new": round(alloc[b], 4),
                       "gmv_delta_inr": round(agg(n, "gmv") - agg(a, "gmv")),
                       "extra_rebate_cost_inr": round(agg(n, "rebate_cost") - agg(a, "rebate_cost")),
                       "gm_delta_inr": round(agg(n, "gm") - agg(a, "gm"))})
    return {"budget_inr": budget_inr, "rest_of_month": True, "allocation": result,
            "total_gmv_delta_inr": sum(r["gmv_delta_inr"] for r in result),
            "total_extra_rebate_inr": sum(r["extra_rebate_cost_inr"] for r in result),
            "total_gm_delta_inr": sum(r["gm_delta_inr"] for r in result),
            "step_order": steps[:40], "cap_pct": REBATE_CAP}


# ---------------------------------------------------------------------------
# OR/SOR pricing
# ---------------------------------------------------------------------------
def price_scan(brand, discounts=None):
    base = _baseline(brand)
    if not base:
        return {"error": f"unknown brand {brand}"}
    if base[0]["commercial_model"] == "MP":
        return {"error": f"{brand} is MP -- the brand sets price; use simulate_rebate instead"}
    e = _elasticities()[brand]
    plan = tools._query("SELECT AVG(plan_discount_pct) p FROM dim_style WHERE brand = ?", [brand])[0]["p"]
    now = [_project(b, e) for b in base]
    cur_disc = 1 - sum(r["gmv"] for r in now) / sum(r["units"] * b["mrp"] for r, b in zip(now, base))
    grid = discounts or [round(x / 100, 3) for x in range(20, 51, 2)]
    rows = []
    for d in grid:
        new = [_project(b, e, discount=d) for b in base]
        g, m = sum(r["gmv"] for r in new), sum(r["gm"] for r in new)
        rows.append({"discount_pct": d, "gmv_inr": round(g), "gm_inr": round(m), "gm_pct": round(m / g, 4) if g else None,
                     "gmv_delta_vs_now_inr": round(g - sum(r["gmv"] for r in now)),
                     "gm_delta_vs_now_inr": round(m - sum(r["gm"] for r in now))})
    return {"brand": brand, "commercial_model": base[0]["commercial_model"], "rest_of_month": True,
            "elasticity_used": e, "current_discount_pct": round(cur_disc, 4), "plan_discount_pct": plan,
            "grid": rows, "note": "Pick on the GMV-vs-GM trade-off; GM for SOR is a fixed share so GMV and GM move together."}


# ---------------------------------------------------------------------------
# Plan: landing + re-phasing
# ---------------------------------------------------------------------------
def month_landing():
    el = _elasticities()
    mop = {r["brand"]: r["g"] for r in tools._query("SELECT brand, SUM(gmv) g FROM plan_daily GROUP BY brand")}
    mtd = {r["brand"]: r["g"] for r in tools._query(
        "SELECT brand, SUM(gmv) g FROM fact_hourly WHERE date >= ? GROUP BY brand", [config.MONTH_START.isoformat()])}
    rows = []
    for brand in sorted(mop):
        proj = sum(_project(b, el[brand])["gmv"] for b in _baseline(brand))
        land = mtd.get(brand, 0) + proj
        rows.append({"brand": brand, "mop_gmv": round(mop[brand]), "actual_so_far": round(mtd.get(brand, 0)),
                     "projected_rest_of_month": round(proj), "landing_gmv": round(land),
                     "landing_pva": round(land / mop[brand], 4), "gap_to_mop_inr": round(land - mop[brand])})
    tot = {k: sum(r[k] for r in rows) for k in ("mop_gmv", "actual_so_far", "projected_rest_of_month", "landing_gmv", "gap_to_mop_inr")}
    tot["landing_pva"] = round(tot["landing_gmv"] / tot["mop_gmv"], 4)
    return {"as_of": f"{config.AS_OF_DATE} {config.AS_OF_HOUR:02d}:00", "method": f"actuals so far + last-{RUN_RATE_DAYS}-day run-rate on remaining plan",
            "category": tot, "brands": rows}


def rephase_plan():
    """Spread the remaining gap to MoP over the remaining days, in proportion to DoD phasing weights."""
    land = month_landing()["category"]
    share_left = _remaining_share()
    days = tools._query(
        "SELECT p.date, ph.day_type, ph.weight, SUM(p.gmv) * (CASE WHEN p.date = ? THEN ? ELSE 1 END) plan_gmv "
        "FROM plan_daily p JOIN plan_phasing ph USING (date) WHERE p.date >= ? GROUP BY p.date ORDER BY p.date",
        [config.AS_OF_DATE.isoformat(), share_left, config.AS_OF_DATE.isoformat()])
    projected = land["projected_rest_of_month"]
    remaining_plan = sum(d["plan_gmv"] for d in days)
    need = land["mop_gmv"] - land["actual_so_far"]
    out = []
    for d in days:
        w = d["plan_gmv"] / remaining_plan
        out.append({"date": d["date"] + (" (rest of today)" if d["date"] == config.AS_OF_DATE.isoformat() else ""),
                    "day_type": d["day_type"], "original_target": round(d["plan_gmv"]),
                    "rephased_target": round(need * w), "run_rate_projection": round(projected * w)})
    return {"mop_gmv": land["mop_gmv"], "actual_so_far": land["actual_so_far"], "needed_rest_of_month": round(need),
            "run_rate_rest_of_month": round(projected),
            "required_uplift_vs_run_rate": round(need / projected - 1, 4), "days": out}


def restore_to_plan(metric, filters=None, basis="last7"):
    """Rest-of-month GMV recovered if one metric (e.g. sessions for App/Tier-2, or consideration for
    a broken-size style) goes back to plan for the slice. basis = which window shows the problem:
    'last7' (7 full days) or 'intraday' (today so far)."""
    if metric not in tools.RATES + tools.VOLUMES:
        return {"error": f"metric must be one of {tools.RATES + tools.VOLUMES}"}
    v = tools._aggregate(basis, None, filters).get("Category")
    if not v:
        return {"error": "no data for these filters"}
    A, P = tools._derive(v["actual"]), tools._derive(v["plan"])
    pva, gmv_pva = A[metric] / P[metric], A["gmv"] / P["gmv"]
    w, p = tools._where(filters, "pl")
    rem_plan = tools._query(
        "SELECT SUM(CASE WHEN pl.date = ? THEN pl.gmv * ? ELSE pl.gmv END) g FROM plan_daily pl "
        f"JOIN dim_style d USING (brand, article_type) WHERE {' AND '.join(['pl.date >= ?'] + w)}",
        [config.AS_OF_DATE.isoformat(), _remaining_share(), config.AS_OF_DATE.isoformat()] + p)[0]["g"]
    projected = rem_plan * gmv_pva
    uplift = projected * (1 / pva - 1) if pva < 1 else 0.0
    return {"metric": metric, "filters": filters or {}, "basis": basis, "metric_pva": round(pva, 4),
            "slice_gmv_pva": round(gmv_pva, 4), "rest_of_month_gmv_projected": round(projected),
            "gmv_recovered_if_restored_inr": round(uplift),
            "note": "Assumes the rest of the funnel holds at its current rate for this slice."}


def action_coverage(actions):
    """actions: [{"action": str, "gmv_inr": number, "gm_inr": number?}] -> total vs remaining gap."""
    gap = -month_landing()["category"]["gap_to_mop_inr"]
    tot = sum(a.get("gmv_inr", 0) for a in actions)
    return {"gap_to_mop_inr": round(gap), "actions_gmv_inr": round(tot),
            "gm_impact_inr": round(sum(a.get("gm_inr", 0) for a in actions)),
            "coverage": round(tot / gap, 4) if gap > 0 else None,
            "remaining_gap_inr": round(gap - tot), "actions": actions}


# ---------------------------------------------------------------------------
# Registration into tools.py's registry
# ---------------------------------------------------------------------------
_BRAND = {"type": "string", "description": "Brand name exactly as in dim_style."}
SPECS = {
    "estimate_elasticity": {
        "description": "Fit each brand's discount elasticity (% change in consideration per +1pp discount) from MTD daily data, with r2.",
        "input_schema": {"type": "object", "properties": {"brand": _BRAND}}},
    "rebate_status": {
        "description": "MP brands: monthly rebate budget, spent MTD, remaining, current (7-day) vs plan rebate %.",
        "input_schema": {"type": "object", "properties": {}}},
    "simulate_rebate": {
        "description": "Rest-of-month GMV, GM and extra rebate cost if ONE MP brand's Myntra rebate is set to rebate_pct (e.g. 0.08).",
        "input_schema": {"type": "object", "properties": {"brand": _BRAND, "rebate_pct": {"type": "number"}},
                         "required": ["brand", "rebate_pct"]}},
    "optimize_rebate": {
        "description": "Split an EXTRA rebate budget (INR, rest of month) across MP brands for the most GMV per rebate rupee "
                       "(greedy, 0.5pp steps, 12% cap). Optional max_gm_loss_inr limit.",
        "input_schema": {"type": "object", "properties": {"budget_inr": {"type": "number"}, "max_gm_loss_inr": {"type": "number"}},
                         "required": ["budget_inr"]}},
    "price_scan": {
        "description": "OR/SOR brand only: rest-of-month GMV and GM across a grid of discount % (default 20%-50%), vs current trajectory.",
        "input_schema": {"type": "object", "properties": {"brand": _BRAND,
                         "discounts": {"type": "array", "items": {"type": "number"}, "description": "Optional custom grid, e.g. [0.28, 0.32, 0.35]"}},
                         "required": ["brand"]}},
    "month_landing": {
        "description": "Where the month lands vs MoP (monthly plan) per brand and category: actual so far + run-rate projection.",
        "input_schema": {"type": "object", "properties": {}}},
    "rephase_plan": {
        "description": "Re-phased daily GMV targets for the remaining days to still hit MoP, vs original DoD targets and run-rate.",
        "input_schema": {"type": "object", "properties": {}}},
    "restore_to_plan": {
        "description": "Rest-of-month GMV recovered if ONE metric returns to plan for a slice -- e.g. metric='sessions' with "
                       "filters {channel: App, city_tier: Tier-2} (restart a paused campaign), or metric='consideration' with "
                       "{brand, article_type} and basis='intraday' (fix broken sizes seen today).",
        "input_schema": {"type": "object", "properties": {
            "metric": {"type": "string"},
            "filters": {"type": "object", "additionalProperties": {"type": "string"}},
            "basis": {"type": "string", "enum": ["last7", "intraday"]}}, "required": ["metric"]}},
    "action_coverage": {
        "description": "Add up proposed actions' rest-of-month GMV (and GM) impacts and compare to the gap to MoP.",
        "input_schema": {"type": "object", "properties": {"actions": {"type": "array", "items": {"type": "object", "properties": {
            "action": {"type": "string"}, "gmv_inr": {"type": "number"}, "gm_inr": {"type": "number"}},
            "required": ["action", "gmv_inr"]}}}, "required": ["actions"]}},
}
FUNCS = {"estimate_elasticity": estimate_elasticity, "rebate_status": rebate_status, "simulate_rebate": simulate_rebate,
         "optimize_rebate": optimize_rebate, "price_scan": price_scan, "month_landing": month_landing,
         "rephase_plan": rephase_plan, "restore_to_plan": restore_to_plan, "action_coverage": action_coverage}
