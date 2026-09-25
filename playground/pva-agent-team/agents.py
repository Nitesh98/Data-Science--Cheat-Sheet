"""
The team. Each agent = a job description (system prompt) + the tools it may use.

    Monitor         -> "Where are we vs plan, MTD and right now? What's flagged?"
    Funnel Analyst  -> "Which funnel step and which slice explains the rupees?"
    Pricing Analyst -> "Did our price (OR/SOR) or rebate (MP) decisions cause it?"
    Merch Analyst   -> "Is it supply? Live styles, broken sizes, new-season share"
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
    "writer": {
        "title": "Writer",
        "tools": [],
        "effort": "medium",
        "system": CONTEXT + """
YOUR JOB: turn the specialists' findings into two drafts for the category head, then call submit_draft.
1) slack_note: exactly 5 lines -> PvA (MTD + intraday) | gap in INR | top 3 reasons | top 3 actions (with owner) | ask/decision needed.
2) exec_summary: markdown, <= 1 page: headline, KPI table (metric, plan, actual, PvA), GMV bridge table
(Traffic / Conversion / UPT / ASP in INR), root causes, pricing & rebate trade-offs, supply (size availability /
new-season) findings, intraday alert, actions with owners.
Use ONLY numbers present in the findings. If the Reviewer sent issues, fix every one.""",
    },
    "reviewer": {
        "title": "Reviewer",
        "tools": ["get_pva", "gmv_bridge", "pricing_check", "intraday_by_hour", "merch_health", "merch_by_hour", "run_sql"],
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


OFFLINE = {"monitor": offline_monitor, "funnel": offline_funnel, "pricing": offline_pricing, "merch": offline_merch}
