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
import re
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
        "tools": ["month_landing", "rephase_plan", "restore_to_plan", "action_coverage", "merch_health"],
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
                  "action_coverage", "rebate_status", "weekly_trend", "brand_scorecard", "run_sql"],
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
        lever = "our rebate" if b["commercial_model"] == "MP" else "our price"
        lines.append(f"- {b['brand']} ({b['commercial_model']}, lever: {lever}): discount {b['discount_diff_pp']:+.1f}pp vs plan -> "
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
    """The Writer has NO tools: every number must come from the findings it was handed."""
    first = lambda title, pat="": next((l.strip("*- ").replace("**", "") for l in findings.get(title, "").splitlines()
                                        if pat in l), "")
    actions = [l.strip("- ") for l in findings.get("Plan & Landing Analyst", "").splitlines() if l.startswith("- ")]
    slack = "\n".join([
        f"*Footwear PvA {config.AS_OF_DATE}*: " + first("PvA Monitor", "**MTD**"),
        "Today: " + first("PvA Monitor", "**INTRADAY**"),
        "Reasons: " + first("Funnel Analyst", "MTD gap"),
        "Actions: " + "; ".join(actions[:3]),
        "Ask: " + first("MP Rebate Allocator", "Top-up") + " | " + first("Plan & Landing Analyst", "Landing"),
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


# ===========================================================================
# PERIODIC PACKS (run_packs.py): Brand Planner + Monthly Review Writer
# ===========================================================================
AGENTS["brand_planner"] = {
    "title": "Brand Planner",
    "tools": ["brand_scorecard", "weekly_trend", "get_pva", "gmv_bridge", "merch_health", "intraday_by_hour", "restore_to_plan"],
    "effort": "high",
    "system": CONTEXT + """
YOUR JOB: write the BRAND-PARTNER PACK for one brand -- a document we SHARE WITH THE BRAND -- plus a short internal cover note
for the category manager. Start with brand_scorecard. Always pass filters={"brand": <brand>} to other tools.
brand_pack (markdown, shareable): headline; scorecard table (plan, actual, PvA, share of category); weekly trend; funnel vs
category PvA (category-level benchmarks are fine); article-type view; availability & new season; what's working / not;
JOINT ACTION PLAN (asks of the brand + our commitments, each with expected rest-of-month GMV from restore_to_plan where possible);
next-month focus.
HARD RULE for brand_pack: use only the scorecard's 'shareable' data. NEVER mention GM, margin, commission, rebate budgets,
elasticity, or ANY other brand by name or number.
internal_note (markdown, for us only): GM view, rebate/price stance, negotiation points, risks.
Then call submit_brand_pack.""",
}
AGENTS["monthly"] = {
    "title": "Monthly Review Writer",
    "tools": ["weekly_trend", "gmv_bridge", "get_pva", "month_landing", "pricing_check", "merch_health",
              "rebate_status", "estimate_elasticity", "restore_to_plan"],
    "effort": "high",
    "system": CONTEXT + """
YOUR JOB: the monthly business review deck for leadership (month to date). Write it as slides in markdown:
'## Slide N: <title>' each with 3-5 bullets (so-what first) and, where useful, one small table, plus a
'> Speaker notes:' line. Slides: 1 headline & asks; 2 KPI scorecard (GMV, GM, sessions, conversion, ASP, discount vs plan);
3 weekly trend (what changed when); 4 GMV bridge; 5 brand performance (top/bottom by INR gap); 6 pricing & rebates (GMV vs GM);
7 supply & new season; 8 month landing & recovery actions (INR each); 9 next month: risks, decisions needed.
Then call submit_document.""",
}
SUBMIT_BRAND_PACK = {
    "name": "submit_brand_pack", "description": "Hand in the brand-partner pack and the internal cover note.",
    "input_schema": {"type": "object", "properties": {"brand_pack": {"type": "string"}, "internal_note": {"type": "string"}},
                     "required": ["brand_pack", "internal_note"]},
}
SUBMIT_DOCUMENT = {
    "name": "submit_document", "description": "Hand in the finished document.",
    "input_schema": {"type": "object", "properties": {"markdown": {"type": "string"}}, "required": ["markdown"]},
}

INTERNAL_TERMS = {"GM": r"\bgm\b", "margin": r"\bmargins?\b", "commission": r"\bcommission",
                  "rebate budget": r"\brebate budget", "elasticity": r"\belasticit", "COGS": r"\bcogs\b"}


def leak_check(text, brand):
    """Deterministic safety net for anything shared outside the company: no internal
    economics and no other brand's name. Runs on every brand pack, LLM or not."""
    low = text.lower()
    issues = [f"mentions internal term '{name}'" for name, rx in INTERNAL_TERMS.items() if re.search(rx, low)]
    others = [r["brand"] for r in tools._query("SELECT DISTINCT brand FROM dim_style") if r["brand"] != brand]
    issues += [f"mentions another brand: {b}" for b in others if re.search(r"\b" + re.escape(b.lower()) + r"\b", low)]
    return issues


def offline_brand_pack(brand):
    import action_tools as A
    import pack_tools
    sc = pack_tools.brand_scorecard(brand)
    s, i = sc["shareable"], sc["internal_only"]
    f = s["funnel_pva"]
    lines = [f"# {brand} x Footwear -- partner review ({config.AS_OF_DATE:%B %Y}, MTD) [offline rule-based draft]", "",
             "| | Plan | Actual | PvA | Share of category |", "|---|---|---|---|---|",
             f"| GMV | {inr(s['gmv']['plan'])} | {inr(s['gmv']['actual'])} | {s['gmv']['pva']:.1%} | {s['share_of_category_gmv']:.1%} |", "",
             "## Weekly trend", "", "| Week | GMV PvA | Sessions PvA | Conversion PvA | ASP PvA |", "|---|---|---|---|---|"]
    lines += [f"| {w['week']} | {w['gmv_pva']:.1%} | {w['sessions_pva']:.1%} | {w['conversion_pva']:.1%} | {w['asp_pva']:.1%} |" for w in s["weekly"]]
    lines += ["", "## Funnel vs plan", "", ", ".join(f"{k} {v:.1%}" for k, v in f.items()), "",
              "## Availability", ""]
    lines += [f"- {x['article_type']}: size availability {x['size_availability']:.0%}, new season {x['new_season_share']:.0%}"
              + (f" -- {'; '.join(x['flags'])}" if x["flags"] else "") for x in s["supply"]]
    lines += [f"- RIGHT NOW {x['article_type']}: size availability {x['size_availability']:.0%}" for x in s["supply_right_now"] if x["flags"]]
    lines += ["", "## Joint action plan", ""]
    for x in s["supply_right_now"]:
        if x["flags"]:
            r = A.restore_to_plan("consideration", {"brand": brand, "article_type": x["article_type"]}, "intraday")
            lines.append(f"- Brand: replenish sizes in {x['article_type']} -- worth ~{inr(r['gmv_recovered_if_restored_inr'])} GMV rest of month")
    lines.append("- Us: restore traffic in Tier-2/3 app campaigns")
    pack = "\n".join(lines)
    note = (f"# Internal note -- {brand}\n\n- GM PvA {i['gm_pva']:.1%} (GM% {i['gm_pct_actual']:.1%} vs plan {i['gm_pct_plan']:.1%})\n"
            f"- Fitted elasticity {i['elasticity_pct_per_pp']}%/pp (r2 {i['elasticity_r2']})\n"
            + (f"- Rebate: spent {inr(i['rebate']['spent_mtd_inr'])} of {inr(i['rebate']['budget_inr'])}\n" if i.get("rebate") else ""))
    return {"brand_pack": pack, "internal_note": note}


def offline_monthly():
    import action_tools as A
    import pack_tools
    mtd = tools.get_pva("mtd")["rows"][0]
    m = mtd["metrics"]
    br = tools.gmv_bridge("mtd")
    land = A.month_landing()["category"]
    brands = tools.get_pva("mtd", "brand")["rows"]
    out = [f"# Footwear monthly review -- {config.AS_OF_DATE:%B %Y} (MTD) [offline rule-based draft]", "",
           "## Slide 1: Headline", f"- GMV {m['gmv']['pva']:.1%} of plan MTD ({cr(mtd['gmv_gap_inr'])}); GM {m['gm']['pva']:.1%}",
           f"- Month lands ~{land['landing_pva']:.1%} of MoP on run-rate", "",
           "## Slide 2: KPI scorecard", "", "| Metric | PvA |", "|---|---|"]
    out += [f"| {k} | {m[k]['pva']:.1%} |" for k in ("gmv", "gm", "sessions", "conversion", "asp")]
    out += ["", "## Slide 3: Weekly trend", "", "| Week | GMV PvA | Sessions PvA | Conversion PvA |", "|---|---|---|---|"]
    out += [f"| {w['week']} | {w['gmv_pva']:.1%} | {w['sessions_pva']:.1%} | {w['conversion_pva']:.1%} |" for w in pack_tools.weekly_trend()["weeks"]]
    out += ["", "## Slide 4: GMV bridge", ""] + [f"- {g}: {cr(v)}" for g, v in br["summary_by_group"].items()]
    out += ["", "## Slide 5: Brands (by INR gap)", ""] + [f"- {r['group']}: {r['metrics']['gmv']['pva']:.1%} ({cr(r['gmv_gap_inr'])})" for r in brands]
    out += ["", "## Slide 6-9", "", "(Pricing, supply, landing and next-month slides need the LLM agent -- run without --offline.)"]
    return "\n".join(out)


# ===========================================================================
# TEAM COACH: turns today's action plan into your team's week
# ===========================================================================
AGENTS["coach"] = {
    "title": "Team Coach",
    "tools": ["team_roster", "check_workload"],
    "effort": "medium",
    "system": CONTEXT + """
YOUR JOB: you support the analytics manager in running their team. Turn today's findings and action plan into THIS WEEK's
analyst tasks. Business owners (performance marketing, buyers, brand managers) own the fixes; analysts own the analysis,
the tracking and the follow-through. For each task: owner, what exactly to deliver, due day, which INR impact it protects,
skill used and hours. Match skills; give each person one stretch task tied to their growth goal; never exceed free hours --
verify with check_workload and fix until it has no issues (a deliberate stretch skill mismatch is fine; say so).
Then write short 1:1 notes per person: recognition, this week's focus, one coaching tip. Call submit_team_plan.""",
}
SUBMIT_TEAM_PLAN = {
    "name": "submit_team_plan", "description": "Hand in the week's task board and 1:1 notes.",
    "input_schema": {"type": "object", "properties": {"task_board": {"type": "string"}, "one_on_ones": {"type": "string"}},
                     "required": ["task_board", "one_on_ones"]},
}


def offline_coach(findings):
    """Uses the action values the Plan & Landing Analyst already put on each fix (no re-computing)."""
    import team_tools
    acts = re.findall(r"^- (.+?): (INR [+-]?[\d.]+ (?:Cr|L))$", findings.get("Plan & Landing Analyst", ""), re.M)
    tasks = []
    for what, amount in acts:
        who, skill, hrs = ("Rohan", "traffic", 4) if "Tier" in what else ("Meera", "supply", 6)
        tasks.append({"owner": who, "task": f"Drive + track: {what}", "skill": skill, "hours": hrs, "due": "Mon",
                      "inr": amount.replace("+", "")})
    tasks += [
        {"owner": "Meera", "task": "Chase Formale new-season inbound; October risk note", "skill": "merchandising", "hours": 4, "due": "Wed", "inr": 0},
        {"owner": "Asha", "task": "Pricing & rebate decision memo (Stridex price, MP rebate top-up) for the category head",
         "skill": "pricing", "hours": 6, "due": "Tue", "inr": 0},
        {"owner": "Asha", "task": "Re-phase remaining days + landing note for leadership", "skill": "planning", "hours": 4, "due": "Tue", "inr": 0},
        {"owner": "Kabir", "task": "Refresh dashboard; draft UrbanKick and Vantage brand packs", "skill": "brand packs", "hours": 8, "due": "Thu", "inr": 0},
        {"owner": "Rohan", "task": "STRETCH: write the recommendation (not just the numbers) for the traffic fix", "skill": "funnel", "hours": 3, "due": "Wed", "inr": 0},
        {"owner": "Kabir", "task": "STRETCH: co-present the UrbanKick pack in the brand meeting with Asha", "skill": "brand packs", "hours": 3, "due": "Fri", "inr": 0},
    ]
    check = team_tools.check_workload(tasks)
    board = ["# This week's task board [offline rule-based draft]", "", "| Owner | Task | Due | Hours | INR at stake |", "|---|---|---|---|---|"]
    board += [f"| {t['owner']} | {t['task']} | {t['due']} | {t['hours']} | {t['inr'] or '-'} |" for t in tasks]
    board += ["", "Workload: " + ", ".join(f"{p['name']} {p['assigned_hrs']:.0f}/{p['free_hrs']}h" for p in check["people"])
              + ("" if check["ok"] else " -- ISSUES: " + "; ".join(check["issues"]))]
    ones = ["# 1:1 notes [offline rule-based draft]", ""]
    for m in team_tools.team_roster()["team"]:
        mine = [t["task"] for t in tasks if t["owner"] == m["name"]]
        ones += [f"## {m['name']} ({m['role']})", f"- Focus: {mine[0]}", f"- Growth goal: {m['growth_goal']}", ""]
    return {"task_board": "\n".join(board), "one_on_ones": "\n".join(ones)}


OFFLINE["coach"] = offline_coach
