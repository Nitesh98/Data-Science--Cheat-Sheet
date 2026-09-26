"""
Team tools for the Team Coach: who is on the team, what they're good at, how much
time they have -- and a workload check so the plan never silently overloads anyone.
"""
import config


def team_roster():
    return {"team": [{**m, "free_hrs": m["capacity_hrs"] - m["committed_hrs"]} for m in config.TEAM],
            "note": "free_hrs = capacity minus BAU commitments this week."}


def check_workload(assignments):
    """assignments: [{"owner", "task", "skill", "hours"}] -> load per person, over-capacity and skill-mismatch flags."""
    people = {m["name"]: m for m in config.TEAM}
    load, issues = {n: 0.0 for n in people}, []
    for a in assignments:
        who = a.get("owner")
        if who not in people:
            issues.append(f"'{a.get('task')}' has unknown owner '{who}'")
            continue
        load[who] += float(a.get("hours", 0))
        if a.get("skill") and a["skill"] not in people[who]["skills"]:
            issues.append(f"{who} is not skilled in '{a['skill']}' ('{a.get('task')}') -- OK only if it's a deliberate stretch")
    summary = []
    for n, m in people.items():
        free = m["capacity_hrs"] - m["committed_hrs"]
        summary.append({"name": n, "assigned_hrs": load[n], "free_hrs": free, "utilisation_of_free": round(load[n] / free, 2) if free else None})
        if load[n] > free:
            issues.append(f"{n} over capacity: {load[n]:.0f}h assigned vs {free}h free")
        if load[n] == 0:
            issues.append(f"{n} has no tasks this week")
    return {"people": summary, "issues": issues, "ok": not issues}


SPECS = {
    "team_roster": {"description": "The analytics team: role, skills, capacity, BAU commitments, free hours this week, growth goal.",
                    "input_schema": {"type": "object", "properties": {}}},
    "check_workload": {
        "description": "Check a proposed task assignment: hours per person vs free hours, skill mismatches, people with no tasks.",
        "input_schema": {"type": "object", "properties": {"assignments": {"type": "array", "items": {"type": "object", "properties": {
            "owner": {"type": "string"}, "task": {"type": "string"}, "skill": {"type": "string"}, "hours": {"type": "number"}},
            "required": ["owner", "task", "hours"]}}}, "required": ["assignments"]}},
}
FUNCS = {"team_roster": team_roster, "check_workload": check_workload}
