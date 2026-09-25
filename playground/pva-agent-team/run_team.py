"""
Orchestrator: runs the agent team end-to-end and leaves a DRAFT for you to approve.

    python3 run_team.py              # real agents (needs ANTHROPIC_API_KEY)
    python3 run_team.py --offline    # rule-based stand-ins, no API key, same outputs
    python3 run_team.py --approve    # mark the latest draft as approved (after you've read it)

Pipeline (plain Python decides the order -- a "workflow", not an LLM boss):

    STAGE 1: diagnose        STAGE 2: act (sees stage 1)
    Monitor ─┐               Rebate Allocator ─┐
    Funnel  ─┤               Pricing Optimizer ┼─> Plan & Landing ─> Writer ─> Reviewer ─(issues?)─> Writer ...
    Pricing ─┼──────────────>                  ┘   (sees everything)                      ─> DRAFT ─> YOU approve
    Merch   ─┘

Outputs in out/<date>/: slack_note.md, exec_summary.md, brand_table.csv, queries.sql, transcript.md
"""
import csv
import os
import shutil
import sys
from datetime import datetime

import agents
import config
import tools


def say(msg):
    print(msg, flush=True)


DIAGNOSE = ("monitor", "funnel", "pricing", "merch")
ACT = ("rebate", "pricing_opt", "planner")     # planner last: it adds up everyone's actions


def run_specialists(offline):
    findings = {}
    for stage, keys in (("STAGE 1 -- diagnose", DIAGNOSE), ("STAGE 2 -- act", ACT)):
        say(f"\n========== {stage} ==========")
        for key in keys:
            a = agents.AGENTS[key]
            say(f"\n>> {a['title']} working...")
            if offline:
                findings[a["title"]] = agents.OFFLINE[key]()
            else:
                import llm
                task = "Do your job for today's PvA review."
                if findings:        # stage-2 agents build on what's been found so far
                    task += "\n\nFINDINGS SO FAR:\n\n" + "\n\n".join(f"## {t}\n{f}" for t, f in findings.items())
                text, _ = llm.run_agent(a["title"], a["system"], task, a["tools"], effort=a["effort"], log=say)
                findings[a["title"]] = text
            say(findings[a["title"]])
    return findings


def write_and_review(findings, offline):
    issues, draft, review = None, None, None
    for rnd in range(1, config.MAX_REVIEW_ROUNDS + 1):
        say(f"\n>> Writer drafting (round {rnd})...")
        if offline:
            draft = agents.offline_writer(findings, issues)
            say(f"\n>> Reviewer checking (round {rnd})...")
            review = agents.offline_reviewer(draft)
        else:
            import llm
            w, r = agents.AGENTS["writer"], agents.AGENTS["reviewer"]
            task = "Specialist findings:\n\n" + "\n\n".join(f"## {t}\n{f}" for t, f in findings.items())
            if issues:
                task += "\n\nREVIEWER ISSUES TO FIX:\n- " + "\n- ".join(issues) + \
                        "\n\nYOUR PREVIOUS DRAFT:\n" + draft["exec_summary"] + "\n\n" + draft["slack_note"]
            _, draft = llm.run_agent(w["title"], w["system"], task, w["tools"], agents.SUBMIT_DRAFT, w["effort"], say)
            if not draft:
                raise RuntimeError("Writer finished without calling submit_draft")
            say(f"\n>> Reviewer checking (round {rnd})...")
            _, review = llm.run_agent(r["title"], r["system"],
                                      "DRAFT SLACK NOTE:\n" + draft["slack_note"] + "\n\nDRAFT EXEC SUMMARY:\n" + draft["exec_summary"],
                                      r["tools"], agents.SUBMIT_REVIEW, r["effort"], say)
            review = review or {"approved": False, "issues": ["Reviewer did not submit a verdict"]}
        say(f"   Reviewer: {'APPROVED' if review['approved'] else 'CHANGES NEEDED'}")
        for i in review["issues"]:
            say(f"   - {i}")
        if review["approved"]:
            break
        issues = review["issues"]
    return draft, review


def save(findings, draft, review, offline):
    folder = config.OUT_DIR / config.AS_OF_DATE.isoformat() / "draft"
    folder.mkdir(parents=True, exist_ok=True)
    banner = (f"<!-- DRAFT {'(offline rule-based)' if offline else ''} generated {datetime.now():%Y-%m-%d %H:%M} -- "
              f"reviewer: {'approved' if review['approved'] else 'NOT approved: ' + '; '.join(review['issues'])} -- "
              f"awaiting human approval -->\n\n")
    (folder / "slack_note.md").write_text(banner + draft["slack_note"] + "\n")
    (folder / "exec_summary.md").write_text(banner + draft["exec_summary"] + "\n")
    rows = tools.brand_table("mtd")
    with open(folder / "brand_table.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    (folder / "queries.sql").write_text(
        "-- Every query the agents ran (SQLite dialect; port table names to your warehouse)\n\n"
        + "\n\n".join(q + ";" for q in tools.SQL_LOG) + "\n")
    (folder / "transcript.md").write_text("# Specialist findings\n\n" + "\n\n".join(
        f"## {t}\n\n{f}" for t, f in findings.items()) + "\n")
    return folder


def approve():
    folder = config.OUT_DIR / config.AS_OF_DATE.isoformat()
    if not (folder / "draft").exists():
        sys.exit("No draft to approve -- run the team first.")
    final = folder / "approved"
    if final.exists():
        shutil.rmtree(final)
    shutil.copytree(folder / "draft", final)
    for name in ("slack_note.md", "exec_summary.md"):
        p = final / name
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
    if not offline:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            sys.exit("Set ANTHROPIC_API_KEY first (or try `python3 run_team.py --offline`).")
        import llm
        say(f"Using {config.MODEL} via {llm.BACKEND}")

    findings = run_specialists(offline)
    draft, review = write_and_review(findings, offline)
    folder = save(findings, draft, review, offline)

    say(f"\n=== DRAFT SLACK NOTE ===\n{draft['slack_note']}\n")
    say(f"Draft saved in {folder}\nRead exec_summary.md and brand_table.csv, then run:  python3 run_team.py --approve")


if __name__ == "__main__":
    main()
