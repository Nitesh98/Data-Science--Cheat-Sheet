"""
Periodic packs: brand-partner packs and the monthly review. Same agents/tools/Reviewer
pattern as run_team.py, different jobs.

    python3 run_packs.py --brand Vantage        # one brand-partner pack (+ internal cover note)
    python3 run_packs.py --brand all            # every brand
    python3 run_packs.py --monthly              # monthly business review, slide by slide
    python3 run_packs.py --offline ...          # rule-based stand-ins, no API key
    python3 run_packs.py --approve              # after you've read out/<date>/packs/draft/

Flow for each document:

    Author agent ──> Reviewer agent ─┐
         ^           + leak_check()  ├─(issues?)──> back to Author ... ──> DRAFT ──> YOU approve
         └───────────────────────────┘

leak_check is plain code, not an LLM: brand packs go OUTSIDE the company, so a
deterministic check for internal economics and other brands' names runs every time,
whatever the Reviewer says.
"""
import os
import shutil
import sys
from datetime import datetime

import agents
import config
import tools

say = print


def author_with_review(key, task, submit, offline_fn, leak_brand=None):
    """Author -> Reviewer (+ leak check) loop. Returns (document_dict, issues_left)."""
    doc, issues = None, []
    for rnd in range(1, config.MAX_REVIEW_ROUNDS + 1):
        a = agents.AGENTS[key]
        say(f"\n>> {a['title']} drafting (round {rnd})...")
        if offline_fn:
            doc = offline_fn()
            issues = []
        else:
            import llm
            t = task
            if issues:
                t += "\n\nREVIEWER ISSUES TO FIX:\n- " + "\n- ".join(issues) + "\n\nYOUR PREVIOUS DRAFT:\n" + \
                     "\n\n".join(f"[{k}]\n{v}" for k, v in doc.items())
            _, doc = llm.run_agent(a["title"], a["system"], t, a["tools"], submit, a["effort"], say)
            if not doc:
                raise RuntimeError(f"{a['title']} finished without submitting")
            r = agents.AGENTS["reviewer"]
            say(f"\n>> Reviewer checking (round {rnd})...")
            note = ("This is a BRAND-PARTNER PACK that will be shared with the brand. Besides numbers, check that "
                    "brand_pack contains no GM/margin/rebate budget/elasticity and no other brand. internal_note may.\n\n"
                    if leak_brand else "This is the monthly leadership review deck.\n\n")
            _, review = llm.run_agent(r["title"], r["system"], note + "\n\n".join(f"[{k}]\n{v}" for k, v in doc.items()),
                                      r["tools"], agents.SUBMIT_REVIEW, r["effort"], say)
            issues = [] if (review and review["approved"]) else (review or {}).get("issues", ["no verdict"])
        if leak_brand:
            leaks = agents.leak_check(doc["brand_pack"], leak_brand)
            if leaks:
                say("   leak_check: " + "; ".join(leaks))
            issues = issues + [f"brand_pack {x} -- remove it (shared externally)" for x in leaks]
        say(f"   {'APPROVED' if not issues else 'CHANGES NEEDED'}")
        for i in issues:
            say(f"   - {i}")
        if not issues:
            break
    return doc, issues


def save(name, text, issues, offline):
    folder = config.OUT_DIR / config.AS_OF_DATE.isoformat() / "packs" / "draft"
    folder.mkdir(parents=True, exist_ok=True)
    banner = (f"<!-- DRAFT {'(offline rule-based) ' if offline else ''}generated {datetime.now():%Y-%m-%d %H:%M} -- "
              f"{'review passed' if not issues else 'OPEN ISSUES: ' + '; '.join(issues)} -- awaiting human approval -->\n\n")
    (folder / name).write_text(banner + text + "\n")
    say(f"   saved {folder / name}")


def approve():
    folder = config.OUT_DIR / config.AS_OF_DATE.isoformat() / "packs"
    if not (folder / "draft").exists():
        sys.exit("No packs to approve -- run one first.")
    final = folder / "approved"
    if final.exists():
        shutil.rmtree(final)
    shutil.copytree(folder / "draft", final)
    for p in final.glob("*.md"):
        body = p.read_text().split("-->\n\n", 1)[-1]
        p.write_text(f"<!-- APPROVED {datetime.now():%Y-%m-%d %H:%M} -->\n\n" + body)
    say(f"Approved -> {final}")


def main():
    args = sys.argv[1:]
    if "--approve" in args:
        return approve()
    offline = "--offline" in args
    if not config.DB_PATH.exists():
        import data
        data.build()
    if not offline and not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("Set ANTHROPIC_API_KEY first (or add --offline).")

    if "--brand" in args:
        which = args[args.index("--brand") + 1] if len(args) > args.index("--brand") + 1 else "all"
        brands = [r["brand"] for r in tools._query("SELECT DISTINCT brand FROM dim_style ORDER BY brand")]
        if which != "all":
            match = [b for b in brands if b.lower() == which.lower()]
            if not match:
                sys.exit(f"Unknown brand '{which}'. Choose from: {', '.join(brands)}")
            brands = match
        for b in brands:
            doc, issues = author_with_review(
                "brand_planner", f"Write the brand-partner pack for {b}.", agents.SUBMIT_BRAND_PACK,
                (lambda b=b: agents.offline_brand_pack(b)) if offline else None, leak_brand=b)
            slug = b.lower().replace(" ", "_")
            save(f"brand_{slug}.md", doc["brand_pack"], issues, offline)
            save(f"brand_{slug}_INTERNAL.md", doc["internal_note"], [], offline)
    elif "--monthly" in args:
        doc, issues = author_with_review(
            "monthly", "Write this month's business review deck.", agents.SUBMIT_DOCUMENT,
            (lambda: {"markdown": agents.offline_monthly()}) if offline else None)
        save("monthly_review.md", doc["markdown"], issues, offline)
    else:
        sys.exit(__doc__)
    say("\nRead the drafts, then:  python3 run_packs.py --approve")


if __name__ == "__main__":
    main()
