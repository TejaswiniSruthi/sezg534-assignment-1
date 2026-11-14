"""Write evidence/harness-results/run-index.md from the recorded run files.

This only tabulates what the harness already recorded; it does not judge or
edit any result. Usage:  python .harness/summarise_runs.py
"""

from __future__ import annotations

import json
from pathlib import Path

RESULTS = Path(__file__).resolve().parent.parent / "evidence" / "harness-results"


def main() -> None:
    rows = [
        "# Harness run index (generated from the run-*.json files)", "",
        "| # | Run id | Source files | G1 Ruff | G2 Bandit | G3 pytest | Overall |",
        "|---|--------|--------------|---------|-----------|-----------|---------|",
    ]
    for number, path in enumerate(sorted(RESULTS.glob("run-*.json")), 1):
        run = json.loads(path.read_text(encoding="utf-8"))
        cells = [f"{gate['status']} ({gate['summary']})" for gate in run["gates"]]
        rows.append(
            f"| {number} | {run['run_id']} | {len(run['source_files'])} | "
            f"{cells[0]} | {cells[1]} | {cells[2]} | **{run['overall']}** |"
        )
    (RESULTS / "run-index.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
    print("\n".join(rows))


if __name__ == "__main__":
    main()
