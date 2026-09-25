"""
The agents' TOOLS -- plain Python functions over the SQLite warehouse.

Design rule: agents never do arithmetic. Every number in a report comes from
one of these deterministic functions, so the Reviewer can re-run the same
tool and check it. Every query is logged, so you get the exact SQL to port
to your real warehouse.
"""
import json
import math
import re
import sqlite3
from datetime import timedelta

import config

SQL_LOG = []           # every query run this session -> saved as queries.sql

DIMENSIONS = ["brand", "article_type", "commercial_model", "price_band", "channel", "city_tier"]
VOLUMES = ["sessions", "list_views", "pdp_views", "atc", "orders", "units", "gmv", "gm"]
RATES = ["lv_per_session", "pdp_ctr", "consideration", "checkout", "conversion", "upt", "asp", "aov", "gm_pct"]
# Factors whose product is exactly GMV (the funnel bridge)
BRIDGE = ["sessions", "lv_per_session", "pdp_ctr", "consideration", "checkout", "upt", "asp"]
BRIDGE_GROUP = {"sessions": "Traffic", "lv_per_session": "Conversion", "pdp_ctr": "Conversion",
                "consideration": "Conversion", "checkout": "Conversion", "upt": "UPT", "asp": "ASP"}


# ---------------------------------------------------------------------------
# Plumbing
# ---------------------------------------------------------------------------
def _connect():
    if not config.DB_PATH.exists():
        raise FileNotFoundError(f"{config.DB_PATH} missing -- run `python3 data.py` first")
    # mode=ro -> the database physically cannot be modified through this connection
    con = sqlite3.connect(f"file:{config.DB_PATH}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def _log(sql, params):
    shown = sql
    for p in params:
        shown = shown.replace("?", f"'{p}'" if isinstance(p, str) else str(p), 1)
    shown = re.sub(r"\s+", " ", shown).strip()
    if shown not in SQL_LOG:
        SQL_LOG.append(shown)


def _query(sql, params=()):
    _log(sql, params)
    with _connect() as con:
        return [dict(r) for r in con.execute(sql, params).fetchall()]


def _window(period):
    """Returns (date_from, date_to, hour_cutoff_or_None, plan_multiplier_sql)."""
    today = config.AS_OF_DATE.isoformat()
    if period == "mtd":                           # full days, 1st .. yesterday
        yday = (config.AS_OF_DATE - timedelta(1)).isoformat()
        return config.MONTH_START.isoformat(), yday, None
    if period == "intraday":                      # today, hours before AS_OF_HOUR
        return today, today, config.AS_OF_HOUR
    raise ValueError("period must be 'mtd' or 'intraday'")


def _where(filters, alias):
    clauses, params = [], []
    for dim, val in (filters or {}).items():
        if dim not in DIMENSIONS:
            raise ValueError(f"unknown dimension '{dim}'. Use one of {DIMENSIONS}")
        col = f"d.{dim}" if dim in ("commercial_model", "price_band") else f"{alias}.{dim}"
        clauses.append(f"{col} = ?")
        params.append(val)
    return clauses, params


def _aggregate(period, group_by=None, filters=None):
    """Actual and plan totals per group. Returns {group_key: {"actual":{..}, "plan":{..}}}."""
    d_from, d_to, hour_cut = _window(period)
    gcols = [g for g in ([group_by] if group_by else [])]
    for g in gcols:
        if g not in DIMENSIONS:
            raise ValueError(f"group_by must be one of {DIMENSIONS}")
    sel = lambda a: ", ".join((f"d.{g}" if g in ("commercial_model", "price_band") else f"{a}.{g}") + f" AS {g}" for g in gcols)
    sums = ", ".join(f"SUM({{a}}.{m}) AS {m}" for m in VOLUMES + ["mrp_value", "rebate_amt"])

    # actuals
    w, p = _where(filters, "f")
    w = ["f.date BETWEEN ? AND ?"] + w
    p = [d_from, d_to] + p
    if hour_cut is not None:
        w.append("f.hour < ?")
        p.append(hour_cut)
    sql_a = (f"SELECT {sel('f') + ', ' if gcols else ''}{sums.format(a='f')} "
             f"FROM fact_hourly f JOIN dim_style d USING (brand, article_type) "
             f"WHERE {' AND '.join(w)}" + (f" GROUP BY {', '.join(gcols)}" if gcols else ""))
    actual = _query(sql_a, p)

    # plan (daily plan x share of the day elapsed, for intraday)
    w, p = _where(filters, "pl")
    w = ["pl.date BETWEEN ? AND ?"] + w
    p = [d_from, d_to] + p
    scale = "1.0"
    if hour_cut is not None:
        scale = f"(SELECT SUM(share) FROM hour_curve WHERE hour < {int(hour_cut)})"
    sums_p = ", ".join(f"SUM(pl.{m}) * {scale} AS {m}" for m in VOLUMES + ["mrp_value", "rebate_amt"])
    sql_p = (f"SELECT {sel('pl') + ', ' if gcols else ''}{sums_p} "
             f"FROM plan_daily pl JOIN dim_style d USING (brand, article_type) "
             f"WHERE {' AND '.join(w)}" + (f" GROUP BY {', '.join(gcols)}" if gcols else ""))
    plan = _query(sql_p, p)

    key = lambda r: tuple(r[g] for g in gcols) or ("Category",)
    out = {}
    for r in plan:
        out.setdefault(key(r), {})["plan"] = r
    for r in actual:
        out.setdefault(key(r), {})["actual"] = r
    return {" / ".join(map(str, k)): v for k, v in out.items() if "actual" in v and "plan" in v}


def _derive(t):
    """Totals -> funnel rates. Division by zero -> None."""
    div = lambda a, b: (a / b) if b else None
    return {
        **{m: t[m] for m in VOLUMES},
        "lv_per_session": div(t["list_views"], t["sessions"]),
        "pdp_ctr": div(t["pdp_views"], t["list_views"]),
        "consideration": div(t["atc"], t["pdp_views"]),
        "checkout": div(t["orders"], t["atc"]),
        "conversion": div(t["orders"], t["sessions"]),
        "upt": div(t["units"], t["orders"]),
        "asp": div(t["gmv"], t["units"]),
        "aov": div(t["gmv"], t["orders"]),
        "gm_pct": div(t["gm"], t["gmv"]),
        "discount_pct": 1 - t["gmv"] / t["mrp_value"] if t["mrp_value"] else None,
        "rebate_pct": div(t["rebate_amt"], t["mrp_value"]),
    }


def _r(x, nd=4):
    return None if x is None else round(x, nd)


def _pva_block(period, a, p):
    """Actual vs plan for every metric + flags."""
    A, P = _derive(a), _derive(p)
    rows, flags = {}, []
    for m in VOLUMES + RATES:
        pva = (A[m] / P[m]) if (A[m] is not None and P[m]) else None
        rows[m] = {"actual": _r(A[m], 5), "plan": _r(P[m], 5), "pva": _r(pva)}
        limit = (config.VOLUME_THRESHOLD if m in VOLUMES else config.RATE_THRESHOLD)[period]
        if pva is not None and pva < limit:
            flags.append(f"{m} at {pva:.1%} of plan (flag < {limit:.0%})")
    for m in ("discount_pct", "rebate_pct"):
        rows[m] = {"actual": _r(A[m]), "plan": _r(P[m]), "diff_pp": _r((A[m] - P[m]) * 100, 2)}
    rows["gmv_gap_inr"] = round(A["gmv"] - P["gmv"])
    return rows, flags


# ---------------------------------------------------------------------------
# TOOL 1: PvA for every metric, optionally sliced by one dimension
# ---------------------------------------------------------------------------
def get_pva(period, group_by=None, filters=None):
    data = _aggregate(period, group_by, filters)
    result = []
    for k, v in data.items():
        rows, flags = _pva_block(period, v["actual"], v["plan"])
        result.append({"group": k, "gmv_gap_inr": rows.pop("gmv_gap_inr"), "flags": flags, "metrics": rows})
    result.sort(key=lambda r: r["gmv_gap_inr"])      # biggest shortfall first
    return {"period": period, "as_of": f"{config.AS_OF_DATE} {config.AS_OF_HOUR:02d}:00",
            "group_by": group_by, "filters": filters or {}, "rows": result}


# ---------------------------------------------------------------------------
# TOOL 2: GMV bridge -- how many rupees of the gap each funnel step explains
# ---------------------------------------------------------------------------
def gmv_bridge(period, filters=None):
    """Log-mean (LMDI) decomposition: contributions add up EXACTLY to the GMV gap."""
    v = _aggregate(period, None, filters).get("Category")
    if not v:
        return {"error": "no data for these filters"}
    A, P = _derive(v["actual"]), _derive(v["plan"])
    ga, gp = A["gmv"], P["gmv"]
    lmean = (ga - gp) / math.log(ga / gp) if abs(ga - gp) > 1e-9 else gp
    steps = []
    for f in BRIDGE:
        c = lmean * math.log(A[f] / P[f])
        steps.append({"driver": f, "group": BRIDGE_GROUP[f], "pva": _r(A[f] / P[f]), "gmv_impact_inr": round(c)})
    groups = {}
    for s in steps:
        groups[s["group"]] = groups.get(s["group"], 0) + s["gmv_impact_inr"]
    return {"period": period, "filters": filters or {}, "gmv_plan": round(gp), "gmv_actual": round(ga),
            "gmv_gap_inr": round(ga - gp), "gmv_pva": _r(ga / gp),
            "summary_by_group": groups, "detail": steps,
            "note": "Negative = rupees lost vs plan. Traffic x Conversion x UPT x ASP; conversion split into LV/session, PDP CTR, consideration (ATC/PDP), checkout (orders/ATC)."}


# ---------------------------------------------------------------------------
# TOOL 3: Hour-by-hour PvA for today (to see WHEN something broke)
# ---------------------------------------------------------------------------
def intraday_by_hour(filters=None):
    today = config.AS_OF_DATE.isoformat()
    w, p = _where(filters, "f")
    sql_a = ("SELECT f.hour, SUM(f.sessions) sessions, SUM(f.pdp_views) pdp_views, SUM(f.atc) atc, "
             "SUM(f.orders) orders, SUM(f.gmv) gmv FROM fact_hourly f JOIN dim_style d USING (brand, article_type) "
             f"WHERE {' AND '.join(['f.date = ?'] + w)} GROUP BY f.hour ORDER BY f.hour")
    act = _query(sql_a, [today] + p)
    w, p = _where(filters, "pl")
    sql_p = ("SELECT h.hour, SUM(pl.sessions)*h.share sessions, SUM(pl.pdp_views)*h.share pdp_views, "
             "SUM(pl.atc)*h.share atc, SUM(pl.orders)*h.share orders, SUM(pl.gmv)*h.share gmv "
             "FROM plan_daily pl JOIN dim_style d USING (brand, article_type) CROSS JOIN hour_curve h "
             f"WHERE {' AND '.join(['pl.date = ?'] + w)} GROUP BY h.hour ORDER BY h.hour")
    plan = {r["hour"]: r for r in _query(sql_p, [today] + p)}
    rows = []
    for a in act:
        pl = plan[a["hour"]]
        cons_a = a["atc"] / a["pdp_views"] if a["pdp_views"] else None
        cons_p = pl["atc"] / pl["pdp_views"]
        rows.append({"hour": a["hour"], "gmv_pva": _r(a["gmv"] / pl["gmv"]),
                     "sessions_pva": _r(a["sessions"] / pl["sessions"]),
                     "consideration_pva": _r(cons_a / cons_p) if cons_a else None,
                     "orders": a["orders"], "orders_plan": round(pl["orders"], 1)})
    return {"date": today, "filters": filters or {}, "hours": rows}


# ---------------------------------------------------------------------------
# TOOL 4: Pricing & rebate check per brand (OR/SOR: our price; MP: our rebate)
# ---------------------------------------------------------------------------
def pricing_check(period):
    data = _aggregate(period, "brand")
    models = {r["brand"]: r["commercial_model"] for r in _query("SELECT DISTINCT brand, commercial_model FROM dim_style")}
    out = []
    for brand, v in data.items():
        A, P = _derive(v["actual"]), _derive(v["plan"])
        disc_pp = (A["discount_pct"] - P["discount_pct"]) * 100
        cons = A["consideration"] / P["consideration"] - 1
        out.append({
            "brand": brand, "commercial_model": models[brand],
            "lever": "rebate (Myntra-funded)" if models[brand] == "MP" else "selling price / discount",
            "discount_pct_actual": _r(A["discount_pct"]), "discount_pct_plan": _r(P["discount_pct"]),
            "discount_diff_pp": _r(disc_pp, 2),
            "rebate_pct_actual": _r(A["rebate_pct"]), "rebate_pct_plan": _r(P["rebate_pct"]),
            "asp_pva": _r(A["asp"] / P["asp"]), "consideration_pva": _r(A["consideration"] / P["consideration"]),
            "gmv_pva": _r(A["gmv"] / P["gmv"]), "gm_pva": _r(A["gm"] / P["gm"]),
            "gm_pct_actual": _r(A["gm_pct"]), "gm_pct_plan": _r(P["gm_pct"]),
            "implied_consideration_change_per_pp_discount": _r(cons * 100 / disc_pp, 3) if abs(disc_pp) >= 1 else None,
        })
    out.sort(key=lambda r: r["discount_diff_pp"])
    return {"period": period, "brands": out,
            "note": "discount_diff_pp < 0 = we are cheaper-than-planned-discount (i.e. pricier). For MP, discount drop usually = rebate cut."}


# ---------------------------------------------------------------------------
# TOOL 5: Read-only SQL for anything the fixed tools don't cover
# ---------------------------------------------------------------------------
def run_sql(query):
    q = query.strip().rstrip(";")
    if ";" in q or not re.match(r"(?is)^\s*(select|with)\b", q):
        return {"error": "Only a single SELECT/WITH statement is allowed."}
    try:
        rows = _query(q)
    except sqlite3.Error as e:
        return {"error": str(e)}
    return {"row_count": len(rows), "rows": rows[:100], "truncated": len(rows) > 100}


def schema():
    with _connect() as con:
        return "\n".join(r[0] for r in con.execute("SELECT sql FROM sqlite_master WHERE type='table'"))


# ---------------------------------------------------------------------------
# Brand-level table for the report (deterministic, not written by an LLM)
# ---------------------------------------------------------------------------
def brand_table(period="mtd"):
    rows = []
    for r in get_pva(period, "brand")["rows"]:
        br = gmv_bridge(period, {"brand": r["group"]})
        worst = min(br["detail"], key=lambda s: s["gmv_impact_inr"])
        m = r["metrics"]
        rows.append({
            "brand": r["group"],
            "gmv_plan": round(m["gmv"]["plan"]), "gmv_actual": round(m["gmv"]["actual"]),
            "gmv_pva": m["gmv"]["pva"], "gmv_gap_inr": r["gmv_gap_inr"],
            "gm_pva": m["gm"]["pva"], "sessions_pva": m["sessions"]["pva"],
            "conversion_pva": m["conversion"]["pva"], "asp_pva": m["asp"]["pva"],
            "discount_diff_pp": m["discount_pct"]["diff_pp"],
            "main_driver": f"{worst['driver']} ({worst['gmv_impact_inr']:+,} INR)" if worst["gmv_impact_inr"] < 0 else "on/above plan",
        })
    return rows


# ---------------------------------------------------------------------------
# Tool schemas the LLM sees (name, description, JSON schema) + dispatcher
# ---------------------------------------------------------------------------
_PERIOD = {"type": "string", "enum": ["mtd", "intraday"],
           "description": "mtd = 1st of month to yesterday (full days). intraday = today up to the current hour."}
_FILTERS = {"type": "object", "description": f"Optional exact-match filters, keys from {DIMENSIONS}. "
            "e.g. {\"brand\": \"Vantage\"} or {\"channel\": \"App\", \"city_tier\": \"Tier-2\"}",
            "additionalProperties": {"type": "string"}}

TOOL_SPECS = {
    "get_pva": {
        "description": "Plan-vs-Actual for EVERY metric: volumes (sessions, list_views, pdp_views, atc, orders, units, gmv, gm) "
                       "and rates (lv_per_session, pdp_ctr, consideration=ATC/PDP, checkout=orders/ATC, conversion, upt, asp, aov, gm_pct), "
                       "plus discount/rebate pp vs plan and flags for metrics below threshold. Optionally slice by one dimension. "
                       "Rows are sorted biggest GMV shortfall first.",
        "input_schema": {"type": "object", "properties": {
            "period": _PERIOD,
            "group_by": {"type": "string", "enum": DIMENSIONS, "description": "Optional dimension to slice by."},
            "filters": _FILTERS}, "required": ["period"]},
    },
    "gmv_bridge": {
        "description": "Explains the GMV gap vs plan in rupees by funnel step (sessions, LV/session, PDP CTR, consideration, checkout, UPT, ASP). "
                       "Contributions sum exactly to the gap. Use filters to bridge a single brand/channel/etc.",
        "input_schema": {"type": "object", "properties": {"period": _PERIOD, "filters": _FILTERS}, "required": ["period"]},
    },
    "intraday_by_hour": {
        "description": "Today's hour-by-hour PvA (GMV, sessions, consideration, orders). Use it to find WHEN an intraday problem started.",
        "input_schema": {"type": "object", "properties": {"filters": _FILTERS}},
    },
    "pricing_check": {
        "description": "Per brand: commercial model (OR/SOR = we set price; MP = brand sets price, we fund rebate), "
                       "discount % and rebate % vs plan, ASP / consideration / GMV / GM PvA, and implied discount elasticity.",
        "input_schema": {"type": "object", "properties": {"period": _PERIOD}, "required": ["period"]},
    },
    "run_sql": {
        "description": "Run ONE read-only SQLite SELECT against the warehouse for anything the other tools don't cover "
                       "(e.g. two-dimension slices, daily trends). Max 100 rows returned. Schema:\n" ,
        "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
    },
}

_FUNCS = {"get_pva": get_pva, "gmv_bridge": gmv_bridge, "intraday_by_hour": intraday_by_hour,
          "pricing_check": pricing_check, "run_sql": run_sql}


def tool_definitions(names):
    """The `tools=[...]` list for the API, restricted to what one agent may use."""
    defs = []
    for n in names:
        spec = dict(TOOL_SPECS[n])
        if n == "run_sql":
            spec["description"] = spec["description"] + schema() + \
                "\nfact_hourly has actuals (date 'YYYY-MM-DD', hour 0-23). plan_daily is daily; join dim_style for commercial_model/price_band."
        defs.append({"name": n, **spec})
    return defs


def execute(name, args):
    """Run a tool the model asked for. Args are model-generated -> treated as untrusted."""
    if name not in _FUNCS:
        return json.dumps({"error": f"unknown tool {name}"}), True
    try:
        return json.dumps(_FUNCS[name](**args), default=str), False
    except (TypeError, ValueError, FileNotFoundError) as e:
        return json.dumps({"error": str(e)}), True
