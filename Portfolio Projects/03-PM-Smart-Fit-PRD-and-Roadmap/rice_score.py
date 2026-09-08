"""
Computes RICE scores (Reach x Impact x Confidence / Effort) from
initiatives.csv and writes a ranked roadmap table + chart. Scores are
computed here, not hand-typed in the write-up, for the same reason
Projects 01-02 compute rather than assert their numbers.

Impact scale used (a common RICE convention): 3 = massive, 2 = high,
1 = medium, 0.5 = low, 0.25 = minimal.
Confidence: 0-1 (e.g. 0.9 = high confidence, backed by real test/data;
0.5 = moderate; below that = mostly a guess -- worth naming as such).

Run:
    python3 rice_score.py
Produces:
    charts/rice_ranking.svg
    roadmap_prioritization.md
"""
import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from svg_charts import bar_chart  # noqa: E402


def main():
    with open("initiatives.csv") as f:
        rows = list(csv.DictReader(f))

    for r in rows:
        reach = float(r["reach_k_users_per_month"])
        impact = float(r["impact"])
        confidence = float(r["confidence"])
        effort = float(r["effort_person_months"])
        r["rice_score"] = round((reach * impact * confidence) / effort, 1) if effort else 0.0

    rows.sort(key=lambda r: -r["rice_score"])

    os.makedirs("charts", exist_ok=True)
    labels = [r["initiative"][:22] + ("…" if len(r["initiative"]) > 22 else "") for r in rows]
    scores = [r["rice_score"] for r in rows]
    bar_chart(labels, scores, "RICE Score by Initiative", subtitle="(Reach x Impact x Confidence) / Effort -- higher is higher priority",
              filename="charts/rice_ranking.svg")

    table_lines = [
        "| Rank | Initiative | Reach (k/mo) | Impact | Confidence | Effort (person-months) | RICE Score |",
        "|---|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(rows, 1):
        table_lines.append(
            f"| {i} | {r['initiative']} | {r['reach_k_users_per_month']} | {r['impact']} | "
            f"{r['confidence']} | {r['effort_person_months']} | **{r['rice_score']}** |"
        )

    notes = "\n".join(f"- **{r['initiative']}**: {r['source_note']}" for r in rows)

    md = f"""# Roadmap Prioritization — RICE Scoring

*(Scores computed by `rice_score.py` from `initiatives.csv` — rerun it and
this table regenerates; nothing below is hand-ranked.)*

## Ranked initiatives

{chr(10).join(table_lines)}

![RICE ranking](charts/rice_ranking.svg)

## Where each estimate comes from

{notes}

## Reading the ranking, not just the score

A RICE score is a prioritization *input*, not an output to follow blindly —
here's the judgment layer on top of the numbers:

- **Scoped scarcity messaging** ranks highly on RICE despite modest reach,
  because it's the only initiative backed by an actual completed experiment
  (Project 02) rather than an estimate — its Confidence score (0.8) reflects
  that, and it should realistically be sequenced first: it's nearly shipped
  already, pending the scoping described in that project's readout.
- **Smart Size & Fit Recommendation** scores well but has a real
  dependency (structured return-reason tagging) that isn't itself high-RICE
  in isolation — it's infrastructure. Sequencing the data-foundation
  initiative *before* or *alongside* the PRD, rather than after, avoids
  building the feature on top of unreliable inputs.
- **Discount calendar redesign** has high reach but was deliberately given
  **low confidence (0.2)**, because Project 01 explicitly flagged that its
  underlying elasticity estimate is confounded with seasonality. A naive
  RICE exercise that took the raw elasticity number at face value would
  over-rank this — the honest confidence score is doing real work here,
  and this is exactly the kind of thing a prioritization review should
  catch before committing a quarter to it. Recommended next step: a small,
  seasonality-controlled test, not a full rollout, to earn a higher
  confidence score before it's re-ranked.
- **Tier 3 fulfillment investment** has high potential impact but the
  highest effort by far (ops/infra-heavy, not a product build) — it's
  reasonable to flag as a candidate for next quarter's planning rather than
  this one, once a smaller scoping study confirms the return on that
  investment.
- **Return-reason structured tagging scores 0.0 and ranks last** — not
  because it doesn't matter, but because RICE divides by a "Reach" number
  that's undefined for pure infrastructure work with no direct end-user
  reach. This is a known blind spot in applying RICE mechanically: it will
  always bury foundational/enabling work at the bottom, even when (as here)
  it's a hard blocker for a higher-ranked item. The fix isn't to fudge the
  Reach number to make the score look better — it's to recognize RICE
  ranks *user-facing bets against each other* and treat sequencing
  dependencies as a separate, non-negotiable layer on top of the score,
  which is what the sequencing below does.

## Suggested quarter sequencing (not purely RICE-order)

1. Ship the scoped scarcity-messaging fix (nearly done, real data behind it).
2. Kick off return-reason structured tagging (unblocks the PRD; low user-facing
   risk; can run in parallel with #1).
3. Begin Smart Size & Fit MVP once tagging data reaches usable quality.
4. Design (don't yet run) the post-purchase retention campaign as an A/B
   test — the underlying insight is strong, but it hasn't been tested yet,
   and deserves the same experimental rigor as the other two.
"""
    with open("roadmap_prioritization.md", "w") as f:
        f.write(md)
    print(md)


if __name__ == "__main__":
    main()
