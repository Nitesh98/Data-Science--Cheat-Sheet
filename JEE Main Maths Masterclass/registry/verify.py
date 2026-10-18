"""Run every registry check and write verify/REPORT.md. Exit code 1 on any failure."""
import datetime, os, sys, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from registry import ENTRIES

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "verify", "REPORT.md")
rows, bad = [], 0
for e in ENTRIES:
    try:
        ok = bool(e["check"]())
        err = ""
    except Exception as ex:  # a crashing check is a failure, never a pass
        ok, err = False, f"{type(ex).__name__}: {ex}"
        traceback.print_exc()
    bad += not ok
    rows.append((e, ok, err))
    print(("PASS " if ok else "FAIL ") + e["id"], err)

with open(out, "w") as f:
    f.write(f"# Formula / example verification report\n\nGenerated {datetime.datetime.now():%Y-%m-%d %H:%M} by `registry/verify.py` "
            f"(sympy). {len(rows) - bad}/{len(rows)} checks pass.\n\n"
            "`numeric` checks are supporting evidence only — not proofs.\n\n")
    f.write("| ID | Expression | Section | Domain / assumptions | Exceptions | Derivation / reference | Method | Result |\n|---|---|---|---|---|---|---|---|\n")
    for e, ok, err in rows:
        cells = [e["id"], e["expr"], e["section"], e["domain"], e["exceptions"], e["reference"], e["kind"],
                 "PASS" if ok else f"**FAIL** {err}"]
        f.write("| " + " | ".join(c.replace("|", "\\|") for c in cells) + " |\n")
sys.exit(1 if bad else 0)
