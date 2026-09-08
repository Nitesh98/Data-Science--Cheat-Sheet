"""
Simulates session-level data for the scarcity-messaging A/B test described
in experiment_design.md, with a built-in true effect so the subsequent
analysis has something real to detect.

True effects baked in (for grading your own analysis against ground truth):
  - Conversion: control 12.0% -> treatment 12.9% (~+7.5% relative, close to
    the +8% MDE the experiment was powered for)
  - AOV: no true effect (small noise only) -- should NOT be significant
  - Return rate: a small adverse nudge in treatment (10.0% -> 10.6%) --
    small enough that it may or may not reach significance at this sample
    size; that ambiguity is realistic and worth discussing in the readout.

Run:
    python3 simulate_experiment.py
Produces:
    experiment_data.csv
"""
import csv
import random

random.seed(7)

DAYS = 21
SESSIONS_PER_ARM_PER_DAY = 1250

CONTROL_CONVERSION = 0.120
TREATMENT_CONVERSION = 0.129

CONTROL_RETURN_RATE = 0.100
TREATMENT_RETURN_RATE = 0.106

AOV_MEAN, AOV_SD = 2900, 650


def gen_order_value():
    v = random.gauss(AOV_MEAN, AOV_SD)
    return max(499, round(v))


def main():
    rows = []
    session_id = 1
    for day in range(1, DAYS + 1):
        for arm, conv_rate, return_rate in (
            ("control", CONTROL_CONVERSION, CONTROL_RETURN_RATE),
            ("treatment", TREATMENT_CONVERSION, TREATMENT_RETURN_RATE),
        ):
            for _ in range(SESSIONS_PER_ARM_PER_DAY):
                converted = random.random() < conv_rate
                order_value = gen_order_value() if converted else ""
                returned = int(random.random() < return_rate) if converted else ""
                rows.append({
                    "session_id": session_id, "day": day, "arm": arm,
                    "converted": int(converted), "order_value": order_value, "returned": returned,
                })
                session_id += 1

    with open("experiment_data.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} sessions ({DAYS} days x {SESSIONS_PER_ARM_PER_DAY}/arm/day x 2 arms)")


if __name__ == "__main__":
    main()
