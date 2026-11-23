"""Write evidence/runs/run-index.md from the recorded live run files.

Only tabulates what the harness recorded; it does not judge or edit any result.
Usage:  python .harness/summarise_runs.py
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

RUNS = Path(__file__).resolve().parent.parent / "evidence" / "runs"


def main() -> None:
    rows = [
        "# Live evaluation run index (generated from evidence/runs/eval-*.json)", "",
        "| # | Run id | Model | Passed | Guardrail | L1 fails | Service errors | Verdict |",
        "|---|--------|-------|--------|-----------|----------|----------------|---------|",
    ]
    for number, path in enumerate(sorted(RUNS.glob("eval-*.json")), 1):
        run = json.loads(path.read_text(encoding="utf-8"))
        s = run["summary"]
        kinds = Counter(
            (case["service_error"] or "").split(":")[0] for case in run["cases"]
            if case["service_error"]
        )
        detail = ", ".join(f"{count} x {kind}" for kind, count in kinds.most_common())
        rows.append(
            f"| {number} | {run['run_id']} | {run['model']} | {s['passed']}/{s['total']} | "
            f"{s['guardrail_passed']}/{s['guardrail_total']} | {s['l1_failures']} | "
            f"{s['service_errors']}{' (' + detail + ')' if detail else ''} | **{run['verdict']}** |"
        )
    (RUNS / "run-index.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
    print("\n".join(rows))


if __name__ == "__main__":
    main()
