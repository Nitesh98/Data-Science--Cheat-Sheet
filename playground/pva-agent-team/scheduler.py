"""
SCHEDULER: the daily review on autopilot, with you still in charge.

    python3 scheduler.py run [--offline]   # run team + audit, send the DRAFT to you only
    python3 scheduler.py status            # where is today's review?
    python3 scheduler.py approve           # you've read it -> post the Slack note to the team
    python3 scheduler.py install           # print the cron line for weekday mornings

Every morning (cron):

    run team ──> audit every agent ──┬─ all passed ──> DM you "draft ready"   ──> you: approve ──> team channel
                                     └─ any failed ──> DM you "BLOCKED + why"      (approve refuses, unless --force)

Slack is via incoming webhooks (no Slack SDK needed). Two env vars:

    SLACK_PRIVATE_WEBHOOK_URL   a webhook that posts to YOU (a DM or private channel) -- drafts go here
    SLACK_TEAM_WEBHOOK_URL      the team channel -- only APPROVED notes go here

If a webhook isn't set, messages are written to out/<date>/outbox/ instead (dry run),
so you can try the whole flow with no Slack at all.
"""
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime

import config

STATUS_FILE = config.OUT_DIR / config.AS_OF_DATE.isoformat() / "status.json"


def webhook(channel):
    """The channel's webhook URL ('' = dry run). Refuses anything that isn't a Slack webhook."""
    url = os.environ.get(f"SLACK_{channel.upper()}_WEBHOOK_URL", "")
    if url and not url.startswith("https://hooks.slack.com/"):
        sys.exit(f"SLACK_{channel.upper()}_WEBHOOK_URL is not a Slack webhook URL -- refusing to send data there.")
    return url


def post(channel, text):
    """channel: 'private' or 'team'. Falls back to a dry-run outbox file."""
    url = webhook(channel)
    if not url:
        box = config.OUT_DIR / config.AS_OF_DATE.isoformat() / "outbox"
        box.mkdir(parents=True, exist_ok=True)
        path = box / f"{datetime.now():%H%M%S}_{channel}.json"
        path.write_text(json.dumps({"channel": channel, "text": text}, indent=1, ensure_ascii=False))
        print(f"   [dry run] no SLACK_{channel.upper()}_WEBHOOK_URL set -> saved {path}")
        return
    req = urllib.request.Request(url, data=json.dumps({"text": text}).encode(), method="POST",
                                 headers={"content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            r.read()
        print(f"   posted to Slack ({channel})")
    except urllib.error.URLError as e:
        sys.exit(f"Slack post failed ({channel}): {e}")


def load_status():
    return json.loads(STATUS_FILE.read_text()) if STATUS_FILE.exists() else None


def save_status(st):
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text(json.dumps(st, indent=1))


def cmd_run(offline, sabotage=False):
    import audit
    import run_team
    if not offline and not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("Set ANTHROPIC_API_KEY first (or add --offline).")
    webhook("private")                                  # fail fast on a bad URL, before a long run
    st = load_status()
    if st and st["status"] == "posted":
        sys.exit(f"Today's review was already posted at {st['posted_at']}. Nothing to do.")

    print(f"[{datetime.now():%H:%M}] running the team + audit ({'offline' if offline else config.MODEL})...")
    run = audit.run_and_grade(offline, sabotage_on=sabotage, with_packs=False)
    folder = run_team.save(run["findings"], run["draft"], run["review"], offline)
    (folder / "team_plan.md").write_text(run["team"]["task_board"] + "\n")
    (folder / "one_on_ones.md").write_text(run["team"]["one_on_ones"] + "\n")
    report_path, _ = audit.save_report(run, offline)

    failed = [r for r in run["results"] if r["verdict"] != "PASS"]
    problems = [f"{r['agent']}: {p}" for r in failed for p in r["problems"]]
    status = "ready" if not failed else "blocked"
    save_status({"date": str(config.AS_OF_DATE), "status": status, "generated_at": f"{datetime.now():%Y-%m-%d %H:%M}",
                 "reviewer_approved": bool(run["review"].get("approved")), "audit_failed_agents": [r["agent"] for r in failed],
                 "problems": problems, "draft_folder": str(folder), "audit_report": str(report_path)})

    passed = len(run["results"]) - len(failed)
    if status == "ready":
        msg = (f":white_check_mark: *PvA review draft ready* ({config.AS_OF_DATE}) -- audit {passed}/{len(run['results'])} agents passed.\n\n"
               f"{run['draft']['slack_note']}\n\n"
               f"Full draft: `{folder}`\nTo send to the team: `python3 scheduler.py approve`")
    else:
        msg = (f":no_entry: *PvA review BLOCKED* ({config.AS_OF_DATE}) -- {len(failed)} agent(s) failed the audit, "
               f"so this draft will not be posted:\n" + "\n".join(f"• {p}" for p in problems[:8])
               + f"\n\nAudit: `{report_path}`\nRe-run: `python3 scheduler.py run`  (or override: `python3 scheduler.py approve --force`)")
    post("private", msg)
    print(f"   status: {status.upper()}")


def cmd_approve(force=False):
    import run_team
    st = load_status()
    if not st:
        sys.exit("No review has run today -- `python3 scheduler.py run` first.")
    if st["status"] == "posted":
        sys.exit(f"Already posted at {st['posted_at']}.")
    webhook("team")                                     # validate BEFORE marking anything approved
    if st["status"] == "blocked" and not force:
        sys.exit("Today's draft is BLOCKED by the audit:\n  - " + "\n  - ".join(st["problems"])
                 + "\nFix and re-run, or `approve --force` if you've checked it yourself.")
    run_team.approve()
    note = (config.OUT_DIR / config.AS_OF_DATE.isoformat() / "approved" / "slack_note.md").read_text()
    body = note.split("-->\n\n", 1)[-1].strip()
    post("team", body)
    st.update(status="posted", posted_at=f"{datetime.now():%Y-%m-%d %H:%M}", forced=bool(force and st["status"] == "blocked"))
    save_status(st)


def cmd_status():
    st = load_status()
    print(json.dumps(st, indent=1) if st else "No review has run today.")


def cmd_install():
    here = config.HERE.resolve()
    print("Add this line with `crontab -e` (runs 08:47 Mon-Fri; set your machine's timezone, e.g. Asia/Kolkata):\n")
    print(f"47 8 * * 1-5  cd {here} && mkdir -p out && . ./.env && /usr/bin/env python3 scheduler.py run >> out/scheduler.log 2>&1\n")
    print("Put your secrets in ./.env (it is git-ignored), e.g.:\n"
          "  export ANTHROPIC_API_KEY=sk-ant-...\n"
          "  export SLACK_PRIVATE_WEBHOOK_URL=https://hooks.slack.com/services/...\n"
          "  export SLACK_TEAM_WEBHOOK_URL=https://hooks.slack.com/services/...\n")
    print("Note: config.AS_OF_DATE is fixed to the demo date. For real use, point data.py/tools.py at your "
          "warehouse and set AS_OF_DATE = date.today() and AS_OF_HOUR = datetime.now().hour.")


def main():
    args = sys.argv[1:]
    cmd = args[0] if args else ""
    if cmd == "run":
        cmd_run("--offline" in args, "--sabotage" in args)
    elif cmd == "approve":
        cmd_approve("--force" in args)
    elif cmd == "status":
        cmd_status()
    elif cmd == "install":
        cmd_install()
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
