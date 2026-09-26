"""
Tools for the periodic packs (brand-partner packs, monthly review).

    brand_scorecard   everything about ONE brand in one call, split into what is
                      shareable with the brand partner and what is Myntra-internal
    weekly_trend      week-by-week PvA for the month so far (category or a slice)
"""
from datetime import timedelta

import config
import tools


def weekly_trend(filters=None):
    """Mon-Sun weeks of the month so far (full days only) with PvA for the key metrics."""
    d_from, d_to, _ = tools._window("mtd")
    w, p = tools._where(filters, "f")
    act = tools._query(
        "SELECT strftime('%W', f.date) wk, MIN(f.date) start, MAX(f.date) end, SUM(f.sessions) sessions, "
        "SUM(f.list_views) list_views, SUM(f.pdp_views) pdp_views, SUM(f.atc) atc, SUM(f.orders) orders, "
        "SUM(f.units) units, SUM(f.gmv) gmv, SUM(f.gm) gm, SUM(f.mrp_value) mrp_value, SUM(f.rebate_amt) rebate_amt "
        "FROM fact_hourly f JOIN dim_style d USING (brand, article_type) "
        f"WHERE {' AND '.join(['f.date BETWEEN ? AND ?'] + w)} GROUP BY wk ORDER BY wk", [d_from, d_to] + p)
    w, p = tools._where(filters, "pl")
    plan = {r["wk"]: r for r in tools._query(
        "SELECT strftime('%W', pl.date) wk, SUM(pl.sessions) sessions, SUM(pl.list_views) list_views, "
        "SUM(pl.pdp_views) pdp_views, SUM(pl.atc) atc, SUM(pl.orders) orders, SUM(pl.units) units, SUM(pl.gmv) gmv, "
        "SUM(pl.gm) gm, SUM(pl.mrp_value) mrp_value, SUM(pl.rebate_amt) rebate_amt "
        "FROM plan_daily pl JOIN dim_style d USING (brand, article_type) "
        f"WHERE {' AND '.join(['pl.date BETWEEN ? AND ?'] + w)} GROUP BY wk", [d_from, d_to] + p)}
    weeks = []
    for a in act:
        A, P = tools._derive(a), tools._derive(plan[a["wk"]])
        weeks.append({"week": f"{a['start']} to {a['end']}", "days": (
            (config.AS_OF_DATE.fromisoformat(a["end"]) - config.AS_OF_DATE.fromisoformat(a["start"])).days + 1),
            "gmv_actual": round(A["gmv"]), "gmv_plan": round(P["gmv"]),
            **{f"{m}_pva": tools._r(A[m] / P[m]) for m in ("gmv", "gm", "sessions", "conversion", "consideration", "asp")},
            "discount_diff_pp": tools._r((A["discount_pct"] - P["discount_pct"]) * 100, 2)})
    return {"filters": filters or {}, "weeks": weeks}


def brand_scorecard(brand):
    """One brand, all angles. 'shareable' is safe to show the brand partner;
    'internal_only' (GM, rebate budgets, other brands) must never go in a brand pack."""
    import action_tools as A
    pva = tools.get_pva("mtd", filters={"brand": brand})["rows"]
    if not pva:
        return {"error": f"unknown brand {brand}"}
    m = pva[0]["metrics"]
    cat = tools.get_pva("mtd")["rows"][0]["metrics"]
    model = tools._query("SELECT DISTINCT commercial_model FROM dim_style WHERE brand = ?", [brand])[0]["commercial_model"]
    by_at = tools.get_pva("mtd", "article_type", {"brand": brand})["rows"]
    bridge = tools.gmv_bridge("mtd", {"brand": brand})
    supply = tools.merch_health("mtd", {"brand": brand})["rows"]
    supply_now = tools.merch_health("intraday", {"brand": brand})["rows"]
    landing = next(r for r in A.month_landing()["brands"] if r["brand"] == brand)
    elastic = A.estimate_elasticity(brand)["brands"][0]
    funnel = ["sessions", "lv_per_session", "pdp_ctr", "consideration", "checkout", "conversion", "upt", "asp"]
    shareable = {
        "brand": brand, "commercial_model": model,
        "gmv": {"plan": round(m["gmv"]["plan"]), "actual": round(m["gmv"]["actual"]), "pva": m["gmv"]["pva"]},
        "share_of_category_gmv": tools._r(m["gmv"]["actual"] / cat["gmv"]["actual"]),
        "funnel_pva": {k: m[k]["pva"] for k in funnel},
        "funnel_vs_category_pva": {k: tools._r(m[k]["pva"] - cat[k]["pva"]) for k in funnel},
        "discount_pct": {"actual": m["discount_pct"]["actual"], "plan": m["discount_pct"]["plan"]},
        "by_article_type": [{"article_type": r["group"], "gmv_pva": r["metrics"]["gmv"]["pva"],
                             "gmv_gap_inr": r["gmv_gap_inr"], "flags": r["flags"]} for r in by_at],
        "gmv_bridge_by_group": bridge["summary_by_group"],
        "supply": [{k: s[k] for k in ("article_type", "live_styles", "live_styles_plan", "size_availability",
                                       "broken_style_pct", "new_season_share", "flags")} for s in supply],
        "supply_right_now": [{k: s[k] for k in ("article_type", "size_availability", "broken_style_pct", "flags")} for s in supply_now],
        "month_landing": {"landing_pva": landing["landing_pva"], "landing_gmv": landing["landing_gmv"], "mop_gmv": landing["mop_gmv"]},
        "weekly": weekly_trend({"brand": brand})["weeks"],
    }
    internal = {"gm_pva": m["gm"]["pva"], "gm_pct_actual": m["gm_pct"]["actual"], "gm_pct_plan": m["gm_pct"]["plan"],
                "elasticity_pct_per_pp": elastic["elasticity_pct_per_pp"], "elasticity_r2": elastic["r2"]}
    if model == "MP":
        internal["rebate"] = next((r for r in A.rebate_status()["brands"] if r["brand"] == brand), None)
    return {"shareable": shareable, "internal_only": internal,
            "rule": "Brand packs may use 'shareable' only. Never show GM, margins, rebate budgets, elasticities or other brands' numbers."}


SPECS = {
    "weekly_trend": {
        "description": "Week-by-week (Mon-Sun) PvA for GMV, GM, sessions, conversion, consideration, ASP, and discount pp, "
                       "month to date. Optional filters (brand, channel, city_tier, ...).",
        "input_schema": {"type": "object", "properties": {"filters": tools._FILTERS}}},
    "brand_scorecard": {
        "description": "Everything about ONE brand: GMV PvA, share of category, funnel PvA vs category, article types, GMV bridge, "
                       "supply, month landing, weekly trend -- split into 'shareable' (OK for the brand partner) and "
                       "'internal_only' (GM, rebate budget, elasticity: never put these in a brand pack).",
        "input_schema": {"type": "object", "properties": {"brand": {"type": "string"}}, "required": ["brand"]}},
}
FUNCS = {"weekly_trend": weekly_trend, "brand_scorecard": brand_scorecard}
