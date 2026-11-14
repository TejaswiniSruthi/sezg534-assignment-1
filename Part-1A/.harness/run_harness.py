"""Deterministic harness for Part 1A.

Runs three independent gates against the generated implementation and records
the outcome as evidence:

    G1  Syntax & Lint Guard      Ruff
    G2  Security / SAST Guard    Bandit
    G3  Unit & Contract Tests    pytest

The harness never imports the application. It only runs external tools, reads
their machine-readable output, and writes a result file. Exit code 0 means
every gate passed; any other outcome exits with 1.

Usage (from the Part-1A folder):  python .harness/run_harness.py
"""

from __future__ import annotations

import json
import platform
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HARNESS = ROOT / ".harness"
RESULTS = ROOT / "evidence" / "harness-results"
SRC = ROOT / "src"
TESTS = ROOT / "tests"
TIMEOUT_SECONDS = 300

# Markers that would switch a check off. Their presence fails the gate they weaken.
LINT_SUPPRESSION = re.compile(r"#\s*(noqa|ruff:\s*noqa|type:\s*ignore)", re.IGNORECASE)
SAST_SUPPRESSION = re.compile(r"#\s*nosec", re.IGNORECASE)
TEST_SUPPRESSION = re.compile(r"pytest\.mark\.(skip|skipif|xfail)|pytest\.(skip|xfail)\(")


def run(command: list[str]) -> dict:
    """Run one tool and capture everything it prints."""
    try:
        done = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=TIMEOUT_SECONDS,
            check=False,
        )
        return {"exit_code": done.returncode, "stdout": done.stdout, "stderr": done.stderr}
    except subprocess.TimeoutExpired:
        return {"exit_code": None, "stdout": "", "stderr": f"timed out after {TIMEOUT_SECONDS}s"}


def tool_version(module: str) -> str:
    out = run([sys.executable, "-m", module, "--version"])
    text = (out["stdout"] or out["stderr"]).strip().splitlines()
    return text[0] if text else "unavailable"


def scan_for_markers(folders: list[Path], pattern: re.Pattern) -> list[dict]:
    hits = []
    for folder in folders:
        for path in sorted(folder.rglob("*.py")):
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if pattern.search(line):
                    hits.append(
                        {
                            "rule": "suppression-marker",
                            "location": f"{path.relative_to(ROOT).as_posix()}:{number}",
                            "expected": "no marker that disables a harness check",
                            "observed": line.strip(),
                        }
                    )
    return hits


def source_files() -> list[Path]:
    return sorted(SRC.rglob("*.py"))


def gate_lint() -> dict:
    command = [
        sys.executable, "-m", "ruff", "check", "src", "tests",
        "--config", str(HARNESS / "ruff.toml"), "--output-format", "json", "--no-cache",
    ]
    out = run(command)
    findings: list[dict] = []
    status = "PASS"
    try:
        for item in json.loads(out["stdout"] or "[]"):
            row = (item.get("location") or {}).get("row", "?")
            name = Path(item.get("filename", "?"))
            try:
                name = name.resolve().relative_to(ROOT)
            except ValueError:
                pass
            findings.append(
                {
                    "rule": item.get("code") or "syntax-error",
                    "location": f"{name.as_posix()}:{row}",
                    "expected": "no violation of the committed Ruff rule set",
                    "observed": item.get("message", ""),
                }
            )
    except json.JSONDecodeError:
        status = "ERROR"
    findings += scan_for_markers([SRC, TESTS], LINT_SUPPRESSION)
    if not source_files():
        findings.append(
            {
                "rule": "no-source",
                "location": "src/",
                "expected": "production code to check",
                "observed": "no .py file under src/",
            }
        )
    if status != "ERROR":
        status = "FAIL" if findings or out["exit_code"] != 0 else "PASS"
    return {
        "id": "G1", "name": "Syntax & Lint Guard", "tool": "ruff", "command": " ".join(command[1:]),
        "status": status, "exit_code": out["exit_code"],
        "summary": f"{len(findings)} violation(s)", "findings": findings, "raw": out,
    }


def gate_security() -> dict:
    command = [
        sys.executable, "-m", "bandit", "-r", "src",
        "-c", str(HARNESS / "bandit.yaml"), "-f", "json", "-q",
    ]
    out = run(command)
    findings: list[dict] = []
    status = "PASS"
    try:
        report = json.loads(out["stdout"])
        for item in report.get("results", []):
            name = Path(item.get("filename", "?")).as_posix()
            findings.append(
                {
                    "rule": f"{item.get('test_id')} {item.get('test_name')}",
                    "location": f"{name}:{item.get('line_number')}",
                    "expected": "no Bandit finding at any severity or confidence",
                    "observed": f"[{item.get('issue_severity')}/{item.get('issue_confidence')}] "
                    f"{item.get('issue_text')}",
                }
            )
        for item in report.get("errors", []):
            findings.append(
                {
                    "rule": "bandit-error",
                    "location": str(item.get("filename")),
                    "expected": "file can be analysed",
                    "observed": str(item.get("reason")),
                }
            )
    except (json.JSONDecodeError, TypeError):
        status = "ERROR"
    findings += scan_for_markers([SRC], SAST_SUPPRESSION)
    if not source_files():
        findings.append(
            {
                "rule": "no-source",
                "location": "src/",
                "expected": "production code to scan",
                "observed": "no .py file under src/",
            }
        )
    if status != "ERROR":
        status = "FAIL" if findings else "PASS"
    return {
        "id": "G2", "name": "Security / SAST Guard", "tool": "bandit",
        "command": " ".join(command[1:]), "status": status, "exit_code": out["exit_code"],
        "summary": f"{len(findings)} finding(s)", "findings": findings, "raw": out,
    }


def gate_tests() -> dict:
    with tempfile.TemporaryDirectory() as folder:
        report = Path(folder) / "junit.xml"
        command = [sys.executable, "-m", "pytest", "tests", "-q", f"--junitxml={report}"]
        out = run(command)
        findings: list[dict] = []
        counts = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
        status = "PASS"
        if report.exists():
            root = ET.parse(report).getroot()
            suite = root if root.tag == "testsuite" else root.find("testsuite")
            for key in counts:
                counts[key] = int(suite.get(key, 0))
            for case in suite.iter("testcase"):
                test_id = f"{case.get('classname')}::{case.get('name')}"
                for kind in ("failure", "error", "skipped"):
                    node = case.find(kind)
                    if node is None:
                        continue
                    detail = (node.text or "").strip().splitlines()
                    findings.append(
                        {
                            "rule": f"test-{kind}",
                            "location": test_id,
                            "expected": "test passes (assertion derived from the specification)",
                            "observed": (node.get("message") or "").strip()[:400],
                            "detail": "\n".join(detail[-12:]),
                        }
                    )
        else:
            status = "ERROR"
    findings += scan_for_markers([TESTS], TEST_SUPPRESSION)
    passed = counts["tests"] - counts["failures"] - counts["errors"] - counts["skipped"]
    if status != "ERROR":
        ok = out["exit_code"] == 0 and counts["tests"] > 0 and not findings
        status = "PASS" if ok else "FAIL"
    command_text = "-m pytest tests -q --junitxml=<temp>"
    return {
        "id": "G3", "name": "Unit & Contract Tests", "tool": "pytest", "command": command_text,
        "status": status, "exit_code": out["exit_code"],
        "summary": f"{passed} passed, {counts['failures']} failed, {counts['errors']} errors, "
        f"{counts['skipped']} skipped of {counts['tests']}",
        "counts": counts, "findings": findings, "raw": out,
    }


def write_evidence(result: dict, gates: list[dict]) -> Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    run_id = result["run_id"]
    log_lines = []
    for gate in gates:
        raw = gate.pop("raw")
        log_lines += [
            "=" * 78, f"{gate['id']} {gate['name']} ({gate['tool']})  ->  {gate['status']}",
            f"command: python {gate['command']}", f"exit code: {raw['exit_code']}",
            "--- stdout ---", raw["stdout"].rstrip(), "--- stderr ---", raw["stderr"].rstrip(), "",
        ]
    (RESULTS / f"{run_id}.log").write_text("\n".join(log_lines), encoding="utf-8")
    text = json.dumps(result, indent=2)
    (RESULTS / f"{run_id}.json").write_text(text + "\n", encoding="utf-8")
    (RESULTS / "latest.json").write_text(text + "\n", encoding="utf-8")
    if result["overall"] != "PASS":
        write_feedback(result)
    return RESULTS / f"{run_id}.json"


def write_feedback(result: dict) -> None:
    """Structured failure evidence to hand back to the coding agent."""
    lines = [
        f"# Harness feedback for run {result['run_id']}", "",
        "Repair the implementation so that the failed checks below pass.",
        "Do not edit tests, harness configuration or the specification.", "",
    ]
    for gate in result["gates"]:
        if gate["status"] == "PASS":
            continue
        lines += [f"## {gate['id']} {gate['name']}: {gate['status']} ({gate['summary']})", ""]
        for number, item in enumerate(gate["findings"], 1):
            lines += [
                f"{number}. **{item['rule']}** at `{item['location']}`",
                f"   - expected: {item['expected']}",
                f"   - observed: {item['observed']}",
            ]
            if item.get("detail"):
                lines += ["", "   ```text"]
                lines += [f"   {row}" for row in item["detail"].splitlines()]
                lines += ["   ```"]
        lines.append("")
    (RESULTS / f"{result['run_id']}-feedback.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    started = datetime.now(timezone.utc)
    gates = [gate_lint(), gate_security(), gate_tests()]
    overall = "PASS" if all(gate["status"] == "PASS" for gate in gates) else "FAIL"
    result = {
        "run_id": "run-" + started.strftime("%Y%m%dT%H%M%SZ"),
        "started_utc": started.isoformat(timespec="seconds"),
        "python": platform.python_version(),
        "platform": platform.system(),
        "tools": {name: tool_version(name) for name in ("ruff", "bandit", "pytest")},
        "source_files": [path.relative_to(ROOT).as_posix() for path in source_files()],
        "gates": gates,
        "overall": overall,
    }
    path = write_evidence(result, gates)
    print("")
    print("Part 1A deterministic harness")
    print("-" * 78)
    for gate in gates:
        print(f"{gate['id']}  {gate['name']:<24} {gate['tool']:<7} {gate['status']:<5}  "
              f"{gate['summary']}")
    print("-" * 78)
    print(f"OVERALL: {overall}")
    print(f"Evidence: {path.relative_to(ROOT).as_posix()}")
    if overall != "PASS":
        print(f"Feedback for the coding agent: "
              f"evidence/harness-results/{result['run_id']}-feedback.md")
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
