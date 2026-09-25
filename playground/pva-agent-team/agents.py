"""
The team. Each agent = a job description (system prompt) + the tools it may use.

    Monitor         -> "Where are we vs plan, MTD and right now? What's flagged?"
    Funnel Analyst  -> "Which funnel step and which slice explains the rupees?"
    Pricing Analyst -> "Did our price (OR/SOR) or rebate (MP) decisions cause it?"
    Merch Analyst   -> "Is it supply? Live styles, broken sizes, new-season share"
  --- stage 2: act (each sees the stage-1 findings) ---
    Rebate Allocator  -> "Should we spend more MP rebate, and on which brand?"
    Pricing Optimizer -> "What discount should OR/SOR brands run for the rest of the month?"
    Plan & Landing    -> "Where does the month land, what's each action worth, is it enough?"
    Writer          -> Slack note + exec summary from the four findings
    Reviewer        -> Re-checks every number with the same tools; approves or sends back

Each agent also has an OFFLINE stand-in: simple rules over the same tools, so
`python3 run_team.py --offline` works without an API key. The real agents
reason far better -- the offline path exists to test the plumbing and to show
you the raw facts the LLM agents start from.
"""
from datetime import timedelta

import config
import tools

CONTEXT = f"""You are part of an analytics agent team for the men's footwear category of an Indian fashion e-commerce company
(ALL data is synthetic). Today is {config.AS_OF_DATE} and intraday data is loaded up to {config.AS_OF_HOUR:02d}:00.
Glossary: AOP = annual operating plan; MoP = monthly plan; DoD phasing = the daily split of the monthly plan;
PvA = actual / plan; MTD = 1st of month to yesterday; GM = gross margin (Myntra's). Commercial models:
OR = outright (we own inventory and set price); SOR = sale-or-return (we set price, fixed margin share);
MP = marketplace (brand sets price; we can only fund extra discount via rebate, which comes out of our GM).
Funnel: GMV = Sessions x LV/session x PDP CTR x Consideration (ATC/PDP) x Checkout (orders/ATC) x UPT x ASP.
Flags: volumes below {config.VOLUME_THRESHOLD['mtd']:.0%} MTD / {config.VOLUME_THRESHOLD['intraday']:.0%} intraday; rates below
{config.RATE_THRESHOLD['mtd']:.0%} MTD / {config.RATE_THRESHOLD['intraday']:.0%} intraday.
Rules: never compute numbers in your head -- quote them from tool output. Express money in INR lakh / crore
(1 crore = 100 lakh = 10,000,000). Be concise; bullet points; lead with the biggest rupee impact."""

AGENTS = {
    "monitor": {
        "title": "PvA Monitor",
        "tools": ["get_pva", "intraday_by_hour"],
        "effort": "medium",
        "system": CONTEXT + """
YOUR JOB: the tracker. Report MTD and intraday PvA for GMV, GM and EVERY funnel metric, top of funnel
(sessions, list views, PDP views) to bottom (consideration, ATC, checkout, orders, units, ASP).
List every flagged metric. For intraday, if something is flagged, find the hour it started and which
brand/article_type it sits in. Do not explain root causes beyond that -- other agents do that.""",
    },
    "funnel": {
        "title": "Funnel Analyst",
        "tools": ["gmv_bridge", "get_pva", "run_sql"],
        "effort": "high",
        "system": CONTEXT + """
YOUR JOB: explain the MTD GMV gap in rupees. Start with gmv_bridge for the category, then slice the biggest
negative driver by dimensions (brand, channel, city_tier, article_type, price_band, commercial_model) until you
find WHERE it is concentrated. Use run_sql for two-dimension slices (e.g. channel x city_tier) or to date when
a problem started (daily trend). Output: 3-5 root causes, each with INR impact, the slice, and the start date.""",
    },
    "pricing": {
        "title": "Pricing & Rebate Analyst",
        "tools": ["pricing_check", "gmv_bridge", "run_sql"],
        "effort": "high",
        "system": CONTEXT + """
YOUR JOB: judge whether pricing (OR/SOR selling price / discount) or MP rebate decisions explain part of the gap.
For each brand whose discount moved >1pp vs plan: what changed, since when (use run_sql on daily discount),
GMV impact vs GM impact (the trade-off!), and a recommendation (hold / partially roll back / reinstate rebate)
with the expected GMV recovery and GM cost. Remember MP brands' price is set by the brand -- our only lever is rebate.""",
    },
    "merch": {
        "title": "Merchandising Analyst",
        "tools": ["merch_health", "merch_by_hour", "intraday_by_hour", "get_pva", "run_sql"],
        "effort": "high",
        "system": CONTEXT + """
YOUR JOB: the supply side. For every brand/article_type that is behind plan (MTD or intraday), rule supply IN or OUT
as the cause: live styles vs plan, size availability vs target (low = broken sizes: customers view the product page but
can't find their size, so consideration ATC/PDP drops while traffic holds), broken-style %, new-season share.
For an intraday drop, use merch_by_hour to show whether demand fell exactly when sizes ran out. Also flag supply
risks that haven't hit GMV yet (e.g. new season late). Output: per brand, 'supply is / is not the cause' with numbers,
then actions (replenish / reorder, push the affected styles down in listings, move traffic to in-stock styles, chase inbound)
and who owns each (category buyer, planning, catalogue).""",
    },
    "rebate": {
        "title": "MP Rebate Allocator",
        "tools": ["rebate_status", "estimate_elasticity", "simulate_rebate", "optimize_rebate"],
        "effort": "high",
        "system": CONTEXT + f"""
YOUR JOB: decide MP rebate spend for the rest of the month. The category head can release up to INR
{config.REBATE_TOPUP_INR / 1e5:.0f} lakh of extra rebate. Check each MP brand's budget position, the FITTED elasticities (not
assumptions -- note r2), and simulate options, including reinstating any rebate that was cut. Judge value by GMV gained per
rebate rupee and the GM given up. It is a valid answer to spend less than the top-up, or nothing, if the return is poor --
say so plainly and say what it would cost to buy GMV this way. Output: recommended rebate % per MP brand, rest-of-month
GMV delta, GM delta, rebate cost, and the reasoning.""",
    },
    "pricing_opt": {
        "title": "OR/SOR Pricing Optimizer",
        "tools": ["estimate_elasticity", "price_scan", "pricing_check"],
        "effort": "high",
        "system": CONTEXT + """
YOUR JOB: recommend the discount OR and SOR brands should run for the rest of the month. Focus on brands whose discount
moved vs plan, plus any brand where a price move clearly pays. Use price_scan (it uses fitted elasticities) and show the
GMV-vs-GM trade-off for 2-3 options (e.g. hold, partial rollback, full rollback to plan discount). Recommend one, with the
rest-of-month GMV and GM deltas. Say explicitly if a price change was the RIGHT call even though it hurt GMV.""",
    },
    "planner": {
        "title": "Plan & Landing Analyst",
        "tools": ["month_landing", "rephase_plan", "restore_to_plan", "action_coverage"],
        "effort": "high",
        "system": CONTEXT + """
YOUR JOB: the month-end view. 1) month_landing: where GMV lands vs MoP on current run-rate (note the run-rate is the last
7 full days, so anything that broke TODAY is not in it yet). 2) Put a rupee value on the operational fixes the diagnosis
found using restore_to_plan (e.g. restart paused traffic in a channel x city_tier slice; fix broken sizes seen intraday).
3) Take the recommended actions from the Rebate Allocator and Pricing Optimizer as given. 4) action_coverage over the FULL
action list -> how much of the gap it closes. 5) rephase_plan -> the daily targets needed. Be honest: if MoP is out of reach,
say what landing is realistic with the actions and what to tell leadership. Output: landing, action list with INR each
(GMV and GM) and owner, coverage %, realistic landing.""",
    },
    "writer": {
        "title": "Writer",
        "tools": [],
        "effort": "medium",
        "system": CONTEXT + """
YOUR JOB: turn the specialists' findings into two drafts for the category head, then call submit_draft.
1) slack_note: exactly 5 lines -> PvA (MTD + intraday) | gap in INR | top 3 reasons | top 3 actions (with owner) | ask/decision needed.
2) exec_summary: markdown, <= 1 page: headline, KPI table (metric, plan, actual, PvA), GMV bridge table
(Traffic / Conversion / UPT / ASP in INR), root causes, pricing & rebate trade-offs, supply (size availability /
new-season) findings, intraday alert, then MONTH LANDING and an ACTION PLAN table (action, owner, rest-of-month GMV INR,
GM INR) with the coverage of the gap and the realistic landing. Slack note actions should be the top 3 by INR value.
Use ONLY numbers present in the findings. If the Reviewer sent issues, fix every one.""",
    },
    "reviewer": {
        "title": "Reviewer",
        "tools": ["get_pva", "gmv_bridge", "pricing_check", "intraday_by_hour", "merch_health", "merch_by_hour",
                  "estimate_elasticity", "simulate_rebate", "price_scan", "month_landing", "restore_to_plan",
                  "action_coverage", "run_sql"],
        "effort": "high",
        "system": CONTEXT + """
YOUR JOB: you are the numbers checker before this goes to leadership. Re-run the tools and verify EVERY number,
PvA %, rupee figure, date and causal claim in the draft. Also check: bridge components add up to the gap,
no claim contradicts the data, actions are specific. Then call submit_review with approved=true only if there
are no material errors; otherwise list each issue precisely (what the draft says vs what the tool says).""",
    },
}

SUBMIT_DRAFT = {
    "name": "submit_draft",
    "description": "Hand in the final drafts.",
    "input_schema": {"type": "object", "properties": {
        "slack_note": {"type": "string"}, "exec_summary": {"type": "string"}},
        "required": ["slack_note", "exec_summary"]},
}
SUBMIT_REVIEW = {
    "name": "submit_review",
    "description": "Hand in your verdict on the draft.",
    "input_schema": {"type": "object", "properties": {
        "approved": {"type": "boolean"},
        "issues": {"type": "array", "items": {"type": "string"}}},
        "required": ["approved", "issues"]},
}


# ---------------------------------------------------------------------------
# OFFLINE stand-ins (no LLM): simple rules over the same tools
# ---------------------------------------------------------------------------
def cr(x):
    return f"INR {x / 1e7:+.2f} Cr" if abs(x) >= 1e7 else f"INR {x / 1e5:+.1f} L"


def inr(x):
    """Unsigned amount, e.g. budgets."""
    return f"INR {x / 1e7:.2f} Cr" if abs(x) >= 1e7 else f"INR {x / 1e5:.1f} L"


def offline_monitor():
    lines = []
    for period in ("mtd", "intraday"):
        row = tools.get_pva(period)["rows"][0]
        m = row["metrics"]
        lines.append(f"**{period.upper()}** GMV PvA {m['gmv']['pva']:.1%} ({cr(row['gmv_gap_inr'])}), GM PvA {m['gm']['pva']:.1%}")
        lines.append("  Funnel PvA: " + ", ".join(f"{k} {m[k]['pva']:.1%}" for k in
                     ["sessions", "list_views", "pdp_views", "consideration", "atc", "checkout", "orders", "asp"]))
        lines += [f"  - FLAG: {f}" for f in row["flags"]]
    worst = tools.get_pva("intraday", "brand")["rows"][0]            # rows come sorted, biggest gap first
    at = tools.get_pva("intraday", "article_type", {"brand": worst["group"]})["rows"][0]
    hours = tools.intraday_by_hour({"brand": worst["group"], "article_type": at["group"]})["hours"]
    broke = next((h["hour"] for h in hours if (h["consideration_pva"] or 1) < 0.8), None)
    lines.append(f"  Intraday worst: {worst['group']} {at['group']} ({cr(at['gmv_gap_inr'])})"
                 + (f", consideration collapsed from {broke:02d}:00" if broke is not None else ""))
    return "\n".join(lines)


def offline_funnel():
    br = tools.gmv_bridge("mtd")
    lines = [f"MTD gap {cr(br['gmv_gap_inr'])} = " + ", ".join(f"{g} {cr(v)}" for g, v in br["summary_by_group"].items())]
    for dim in ("channel", "city_tier", "brand"):
        rows = tools.get_pva("mtd", dim)["rows"][:2]
        lines.append(f"- worst {dim}: " + "; ".join(f"{r['group']} {cr(r['gmv_gap_inr'])} (sessions PvA "
                     f"{r['metrics']['sessions']['pva']:.1%}, conversion PvA {r['metrics']['conversion']['pva']:.1%})" for r in rows))
    d0, d1 = config.AS_OF_DATE - timedelta(7), config.AS_OF_DATE - timedelta(1)
    sl = tools.run_sql(f"SELECT f.channel, f.city_tier, ROUND(SUM(f.sessions)*1.0/(SELECT SUM(p.sessions) FROM plan_daily p "
                       f"WHERE p.channel=f.channel AND p.city_tier=f.city_tier AND p.date BETWEEN '{d0}' AND '{d1}'),3) AS sessions_pva "
                       f"FROM fact_hourly f WHERE f.date BETWEEN '{d0}' AND '{d1}' GROUP BY 1,2 ORDER BY 3")
    lines.append(f"- sessions PvA last 7 days ({d0} to {d1}) by channel x tier: " + ", ".join(f"{r['channel']}/{r['city_tier']} {r['sessions_pva']:.0%}" for r in sl["rows"]))
    return "\n".join(lines)


def offline_pricing():
    lines = []
    for b in tools.pricing_check("mtd")["brands"]:
        if abs(b["discount_diff_pp"]) < 1:
            continue
        lever = "rebate" if b["commercial_model"] == "MP" else "discount"
        lines.append(f"- {b['brand']} ({b['commercial_model']}): {lever} {b['discount_diff_pp']:+.1f}pp vs plan -> "
                     f"consideration PvA {b['consideration_pva']:.1%}, GMV PvA {b['gmv_pva']:.1%}, GM PvA {b['gm_pva']:.1%}")
    return "\n".join(lines) or "No brand's discount moved more than 1pp vs plan."


def offline_merch():
    lines = []
    for period in ("intraday", "mtd"):
        for r in tools.merch_health(period)["rows"]:
            if r["flags"]:
                lines.append(f"- {period.upper()} {r['brand']} {r['article_type']}: " + "; ".join(r["flags"]))
                if period == "intraday" and r["size_availability"] < r["size_availability_target"] - 0.05:
                    hrs = tools.merch_by_hour(r["brand"], r["article_type"])["hours"]
                    hit = next((h for h in hrs if (h["consideration_pva"] or 1) < 0.8), None)
                    if hit:
                        lines.append(f"  consideration PvA fell to {hit['consideration_pva']:.0%} at {hit['hour']:02d}:00, "
                                     f"when size availability was {hit['size_availability']:.0%} -> supply IS the cause")
    healthy = sorted({r["brand"] for r in tools.merch_health("mtd")["rows"] if not r["flags"]})
    lines.append("- Supply healthy MTD (so not the cause) for: " + ", ".join(healthy))
    return "\n".join(lines)


def offline_rebate():
    import action_tools as A
    lines = ["Budget: " + "; ".join(f"{b['brand']} spent {inr(b['spent_mtd_inr'])} of {inr(b['budget_inr'])}, "
                                     f"rebate now {b['current_rebate_pct_7d']:.1%} vs plan {b['plan_rebate_pct']:.0%}"
                                     for b in A.rebate_status()["brands"])]
    lines.append("Fitted elasticity: " + ", ".join(f"{e['brand']} {e['elasticity_pct_per_pp']}" for e in
                                                   A.estimate_elasticity()["brands"] if e["brand"] in ("Vantage", "Trekko", "Redline Sport")))
    o = A.optimize_rebate(config.REBATE_TOPUP_INR)
    for r in o["allocation"]:
        lines.append(f"- {r['brand']}: rebate {r['rebate_pct_now']:.1%} -> {r['rebate_pct_new']:.1%}: GMV {cr(r['gmv_delta_inr'])}, "
                     f"GM {cr(r['gm_delta_inr'])}, cost {cr(r['extra_rebate_cost_inr'])}")
    ratio = o["total_gmv_delta_inr"] / max(1, o["total_extra_rebate_inr"])
    lines.append(f"Top-up returns INR {ratio:.2f} GMV per INR 1 rebate -> "
                 + ("poor value: recommend NOT spending it" if ratio < 1 else "worth spending"))
    return "\n".join(lines)


def offline_pricing_opt():
    import action_tools as A
    lines = []
    for b in tools.pricing_check("mtd")["brands"]:
        if b["commercial_model"] == "MP" or abs(b["discount_diff_pp"]) < 1:
            continue
        ps = A.price_scan(b["brand"])
        cur, plan = ps["current_discount_pct"], ps["plan_discount_pct"]
        mid = round((cur + plan) / 2, 3)
        for r in A.price_scan(b["brand"], [cur, mid, plan])["grid"]:
            lines.append(f"- {b['brand']} at {r['discount_pct']:.1%} discount: GMV {cr(r['gmv_delta_vs_now_inr'])}, "
                         f"GM {cr(r['gm_delta_vs_now_inr'])} (rest of month vs holding {cur:.0%})")
    return "\n".join(lines) or "No OR/SOR brand's discount moved >1pp vs plan."


def offline_planner():
    import action_tools as A
    land = A.month_landing()["category"]
    lines = [f"Landing on run-rate: {land['landing_pva']:.1%} of MoP ({cr(land['gap_to_mop_inr'])})"]
    actions = []
    for tier in ("Tier-2", "Tier-3"):
        r = A.restore_to_plan("sessions", {"channel": "App", "city_tier": tier})
        actions.append({"action": f"Restart App {tier} campaigns (sessions back to plan)", "gmv_inr": r["gmv_recovered_if_restored_inr"]})
    worst = tools.merch_health("intraday")["rows"][0]
    if worst["flags"]:
        r = A.restore_to_plan("consideration", {"brand": worst["brand"], "article_type": worst["article_type"]}, "intraday")
        actions.append({"action": f"Replenish sizes {worst['brand']} {worst['article_type']}", "gmv_inr": r["gmv_recovered_if_restored_inr"]})
    cov = A.action_coverage(actions)
    lines += [f"- {a['action']}: {cr(a['gmv_inr'])}" for a in actions]
    lines.append(f"Coverage of gap: {cov['coverage']:.0%}; remaining gap {cr(-cov['remaining_gap_inr'])}")
    rp = A.rephase_plan()
    lines.append(f"To still hit MoP the remaining days need +{rp['required_uplift_vs_run_rate']:.0%} vs run-rate")
    return "\n".join(lines)


def offline_writer(findings, issues=None):
    mtd = tools.get_pva("mtd")["rows"][0]
    intr = tools.get_pva("intraday")["rows"][0]
    slack = "\n".join([
        f"*Footwear PvA {config.AS_OF_DATE}*: MTD GMV {mtd['metrics']['gmv']['pva']:.1%} | intraday {intr['metrics']['gmv']['pva']:.1%}",
        f"Gap: MTD {cr(mtd['gmv_gap_inr'])}, today so far {cr(intr['gmv_gap_inr'])}",
        "Reasons: see bridge -- (offline mode: rule-based, run with an API key for real reasoning)",
        "Actions: TBD by analyst",
        "Ask: review exec summary",
    ])
    summary = "# Footwear PvA review (OFFLINE rule-based draft)\n\n" + "\n\n".join(
        f"## {t}\n\n{f}" for t, f in findings.items())
    return {"slack_note": slack, "exec_summary": summary}


def offline_reviewer(draft):
    br = tools.gmv_bridge("mtd")
    ok = abs(sum(d["gmv_impact_inr"] for d in br["detail"]) - br["gmv_gap_inr"]) <= 5
    return {"approved": ok, "issues": [] if ok else ["Bridge does not add up to the GMV gap"]}


OFFLINE = {"monitor": offline_monitor, "funnel": offline_funnel, "pricing": offline_pricing, "merch": offline_merch,
           "rebate": offline_rebate, "pricing_opt": offline_pricing_opt, "planner": offline_planner}
