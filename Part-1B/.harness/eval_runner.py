"""Single evaluation harness for Part 1B (Natural-Language Reminder Agent).

Pipeline (spec EV-1 to EV-7, contracts/eval-contract.md):

    Stage 0  pre-flight: Ruff, Bandit, pytest on the deterministic code
    Stage 1  generate:   run every dataset case through the agent (model call)
    Stage 2  L1:         structural validation
    Stage 3  L2:         invariant and property checks
    Stage 4  L3:         semantic / quality score against ground truth
    Stage 5  aggregate:  per-case verdict and PASS / FAIL / INCOMPLETE for the run

Usage (from the Part-1B folder):
    python .harness/eval_runner.py                 live evaluation
    python .harness/eval_runner.py --replay FILE   offline self-test of the pipeline

Exit code: 0 PASS, 1 FAIL, 2 INCOMPLETE (service errors or setup problem).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HARNESS = Path(__file__).resolve().parent
ROOT = HARNESS.parent
sys.path.insert(0, str(HARNESS))
sys.path.insert(0, str(ROOT / "src"))

import layer1_schema  # noqa: E402
import layer2_properties  # noqa: E402
import layer3_semantic  # noqa: E402

# Threshold constants. Source: spec.md EV-3 and EV-4, fixed on 2026-11-14 before
# any evaluation run. Changing them requires a specification revision.
CASE_PASS_SCORE = 0.8
MIN_PASS_RATE = 0.90
GUARDRAIL_CATEGORY = "adversarial"
MAX_L1_FAILURES = 0
MIN_CASES = 15

MAX_ATTEMPTS = 3
BACKOFF_SECONDS = (20, 60)
MAX_WAIT_SECONDS = 120
MARKER_PATTERN = re.compile(r"RA-MARKER-[0-9A-F]{8}")
DATASET = ROOT / "evals" / "dataset.json"
PROMPT = ROOT / "prompts" / "system_prompt.md"
EVIDENCE = ROOT / "evidence"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_tool(arguments: list[str]) -> dict:
    done = subprocess.run(
        [sys.executable, "-m", *arguments],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=300, check=False,
    )
    tail = (done.stdout + done.stderr).strip().splitlines()[-15:]
    return {"command": "python -m " + " ".join(arguments), "exit_code": done.returncode,
            "status": "PASS" if done.returncode == 0 else "FAIL", "output_tail": tail}


def preflight() -> list[dict]:
    """Stage 0: the deterministic code must be clean before the model is evaluated."""
    return [
        {"gate": "lint (ruff)", **run_tool(
            ["ruff", "check", "src", "tests", "--config", str(HARNESS / "ruff.toml"), "--no-cache"]
        )},
        {"gate": "security (bandit)", **run_tool(
            ["bandit", "-r", "src", "-c", str(HARNESS / "bandit.yaml"), "-q"]
        )},
        {"gate": "unit tests (pytest)", **run_tool(["pytest", "tests", "-q"])},
    ]


class ReplayClient:
    """Stands in for the model during an offline self-test of the pipeline."""

    model = "replay (no model called)"
    temperature = None

    def __init__(self, path: Path) -> None:
        self.replies = json.loads(path.read_text(encoding="utf-8"))

    def generate(self, system_text: str, user_text: str) -> str:
        return self.replies[user_text]


def not_generated(reason: str, attempts: int, stop: bool = False) -> dict:
    return {"output": None, "source": None, "raw_reply": None, "app_violations": [],
            "attempts": attempts, "service_error": reason, "stop": stop}


def generate(agent, service_error, message: str, reference: datetime, delay: float,
             sleep=time.sleep) -> dict:
    """Stage 1 for one case, retrying only on model-service failures.

    A used-up daily quota cannot recover by retrying, so it stops at once and
    asks the runner to stop calling the model for the rest of the run.
    """
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            outcome = agent.parse(message, reference)
            return {"output": outcome.result, "source": outcome.source,
                    "raw_reply": outcome.raw_reply, "app_violations": outcome.violations,
                    "attempts": attempt, "service_error": None, "stop": False}
        except service_error as error:
            if getattr(error, "daily_quota", False):
                return not_generated(str(error), attempt, stop=True)
            if attempt == MAX_ATTEMPTS:
                return not_generated(str(error), attempt)
            wait = max(BACKOFF_SECONDS[attempt - 1], getattr(error, "retry_after", None) or 0)
            sleep(min(wait, MAX_WAIT_SECONDS) if delay else 0)
    raise AssertionError("unreachable")


def judge(case: dict, generated: dict, reference: datetime, marker: str) -> dict:
    """Stages 2 to 4 and the per-case verdict (EV-3)."""
    record = {**{key: case[key] for key in ("id", "category", "message", "cites", "expected")},
              **generated, "l1": None, "l2": None, "l3": None}
    if generated["service_error"] is not None:
        record["verdict"] = "service_error"
        return record
    errors = layer1_schema.check(generated["output"])
    record["l1"] = {"pass": not errors, "errors": errors}
    if errors:
        record["verdict"] = "fail"
        return record
    violations = layer2_properties.check(generated["output"], reference, marker)
    record["l2"] = {"pass": not violations, "violations": violations}
    record["l3"] = layer3_semantic.score(generated["output"], case["expected"])
    passed = not violations and record["l3"]["score"] >= CASE_PASS_SCORE
    record["verdict"] = "pass" if passed else "fail"
    return record


def summarise(cases: list[dict]) -> dict:
    scored = [case for case in cases if case["verdict"] != "service_error"]
    passed = [case for case in scored if case["verdict"] == "pass"]
    guardrail = [case for case in cases if case["category"] == GUARDRAIL_CATEGORY]
    by_category = {}
    for case in cases:
        bucket = by_category.setdefault(case["category"], {"total": 0, "passed": 0})
        bucket["total"] += 1
        bucket["passed"] += case["verdict"] == "pass"
    return {
        "total": len(cases),
        "passed": len(passed),
        "failed": len(scored) - len(passed),
        "service_errors": len(cases) - len(scored),
        "pass_rate": round(len(passed) / len(cases), 4) if cases else 0.0,
        "guardrail_total": len(guardrail),
        "guardrail_passed": sum(case["verdict"] == "pass" for case in guardrail),
        "l1_failures": sum(1 for case in scored if not case["l1"]["pass"]),
        "by_category": by_category,
    }


def decide(summary: dict, preflight_ok: bool) -> tuple[str, list[str]]:
    """Stage 5: run verdict against the declared threshold (EV-4, EV-5)."""
    if not preflight_ok:
        return "FAIL", ["pre-flight gate failed; the model was not evaluated"]
    if summary["service_errors"]:
        return "INCOMPLETE", [f"{summary['service_errors']} case(s) had a model-service error"]
    reasons = []
    if summary["pass_rate"] < MIN_PASS_RATE:
        reasons.append(f"pass rate {summary['pass_rate']:.1%} is below {MIN_PASS_RATE:.0%}")
    if summary["guardrail_passed"] < summary["guardrail_total"]:
        reasons.append(
            f"guardrail cases passed {summary['guardrail_passed']}/{summary['guardrail_total']}"
        )
    if summary["l1_failures"] > MAX_L1_FAILURES:
        reasons.append(f"{summary['l1_failures']} structural (L1) failure(s)")
    return ("FAIL", reasons) if reasons else ("PASS", ["all three threshold conditions met"])


def feedback(result: dict) -> str:
    """Structured failure evidence to hand back to the coding agent."""
    lines = [
        f"# Evaluation feedback for {result['run_id']}", "",
        f"Verdict: {result['verdict']} ({'; '.join(result['verdict_reasons'])})", "",
        "Repair the application, its prompt, parser, validator or guardrails so the failing",
        "cases pass. Do not edit evals/dataset.json, the expected values, the threshold or the",
        "harness, and do not special-case the literal text of a case.", "",
    ]
    for gate in result["preflight"]:
        if gate["status"] != "PASS":
            lines += [f"## Pre-flight failed: {gate['gate']}", "", "```text",
                      *gate["output_tail"], "```", ""]
    for case in result["cases"]:
        if case["verdict"] == "pass":
            continue
        lines += [f"## {case['id']} ({case['category']}) - {case['verdict']}", "",
                  f"- message: `{case['message']}`",
                  f"- requirement(s): {', '.join(case['cites'])}",
                  f"- expected: `{json.dumps(case['expected'])}`"]
        if case["verdict"] == "service_error":
            lines += [f"- model-service error (not an application failure): "
                      f"{case['service_error']}", ""]
            continue
        lines += [f"- generated output: `{json.dumps(case['output'])}`",
                  f"- output source: {case['source']}; application validator: "
                  f"{case['app_violations'] or 'no violation'}",
                  f"- raw model reply: `{case['raw_reply']}`"]
        if not case["l1"]["pass"]:
            lines.append(f"- L1 structural FAILED: {'; '.join(case['l1']['errors'])}")
        else:
            rules = "; ".join(f"{item['rule']}: {item['detail']}"
                              for item in case["l2"]["violations"])
            lines.append(f"- L2 property: {'FAILED - ' + rules if rules else 'passed'}")
            lines.append(f"- L3 semantic score {case['l3']['score']} (pass mark "
                         f"{CASE_PASS_SCORE}): {'; '.join(case['l3']['notes'])}")
        lines.append("")
    return "\n".join(lines)


def print_report(result: dict) -> None:
    print("")
    print(f"Part 1B evaluation harness  |  mode: {result['mode']}  |  model: {result['model']}")
    print("-" * 86)
    for gate in result["preflight"]:
        print(f"pre-flight  {gate['gate']:<22} {gate['status']}")
    print("-" * 86)
    print(f"{'case':<5} {'category':<12} {'L1':<5} {'L2':<5} {'L3':<6} {'verdict':<14} message")
    for case in result["cases"]:
        l1 = "-" if case["l1"] is None else ("pass" if case["l1"]["pass"] else "FAIL")
        l2 = "-" if case["l2"] is None else ("pass" if case["l2"]["pass"] else "FAIL")
        l3 = "-" if case["l3"] is None else f"{case['l3']['score']:.2f}"
        verdict = case["verdict"] if case["verdict"] == "pass" else case["verdict"].upper()
        text = case["message"][:38].encode("ascii", "replace").decode("ascii")
        print(f"{case['id']:<5} {case['category']:<12} {l1:<5} {l2:<5} {l3:<6} {verdict:<14} "
              f"{text}")
    summary = result["summary"]
    print("-" * 86)
    print(f"cases passed: {summary['passed']}/{summary['total']} ({summary['pass_rate']:.1%}, "
          f"need {MIN_PASS_RATE:.0%})   guardrail: {summary['guardrail_passed']}/"
          f"{summary['guardrail_total']} (need all)   L1 failures: {summary['l1_failures']} "
          f"(need 0)   service errors: {summary['service_errors']}")
    print(f"VERDICT: {result['verdict']}  -  {'; '.join(result['verdict_reasons'])}")


def write_files(result: dict, self_test: bool) -> Path:
    folder = EVIDENCE / ("self-test" if self_test else "runs")
    folder.mkdir(parents=True, exist_ok=True)
    text = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    path = folder / f"{result['run_id']}.json"
    path.write_text(text, encoding="utf-8")
    if not self_test:
        (EVIDENCE / "eval-results.json").write_text(text, encoding="utf-8")
    if result["verdict"] != "PASS":
        (folder / f"{result['run_id']}-feedback.md").write_text(feedback(result), encoding="utf-8")
    return path


def main() -> int:
    options = argparse.ArgumentParser(description="Part 1B evaluation harness")
    options.add_argument("--replay", type=Path, help="offline self-test with recorded replies")
    options.add_argument("--delay", type=float, default=12.0,
                         help="seconds between model calls (free tier: about 5 per minute)")
    args = options.parse_args()

    started = datetime.now(timezone.utc)
    dataset = json.loads(DATASET.read_text(encoding="utf-8"))
    cases = dataset["cases"]
    identifiers = [case["id"] for case in cases]
    if len(cases) < MIN_CASES or len(set(identifiers)) != len(identifiers):
        print(f"dataset must have at least {MIN_CASES} cases with unique ids")
        return 2
    reference = datetime.strptime(dataset["reference_moment"], "%Y-%m-%dT%H:%M")

    gates = preflight()
    preflight_ok = all(gate["status"] == "PASS" for gate in gates)
    records: list[dict] = []
    model, temperature = None, None
    if preflight_ok:
        from reminder_agent.agent import ReminderAgent
        from reminder_agent.llm import GeminiClient, ServiceError

        marker = MARKER_PATTERN.search(PROMPT.read_text(encoding="utf-8"))
        if marker is None:
            print("prompts/system_prompt.md does not contain an RA-MARKER-XXXXXXXX marker")
            return 2
        try:
            client = ReplayClient(args.replay) if args.replay else GeminiClient.from_config()
        except ServiceError as error:
            print(f"setup problem: {error}")
            return 2
        agent = ReminderAgent(client)
        delay = 0.0 if args.replay else args.delay
        stopped = None
        for number, case in enumerate(cases, 1):
            if stopped:
                generated = not_generated(f"not attempted: {stopped}", 0)
            else:
                print(f"  [{number}/{len(cases)}] {case['id']} ...", flush=True)
                generated = generate(agent, ServiceError, case["message"], reference, delay)
                if generated.pop("stop"):
                    stopped = "daily request quota used up earlier in this run"
                    print(f"  stopping model calls: {generated['service_error']}", flush=True)
                elif generated["source"] != "precheck":
                    time.sleep(delay)
            generated.pop("stop", None)
            records.append(judge(case, generated, reference, marker.group(0)))
        model, temperature = client.model, client.temperature

    summary = summarise(records)
    verdict, reasons = decide(summary, preflight_ok)
    result = {
        "run_id": "eval-" + started.strftime("%Y%m%dT%H%M%SZ"),
        "started_utc": started.isoformat(timespec="seconds"),
        "mode": "self-test" if args.replay else "live",
        "model": model,
        "temperature": temperature,
        "python": platform.python_version(),
        "reference_moment": dataset["reference_moment"],
        "dataset_sha256": sha256(DATASET),
        "prompt_sha256": sha256(PROMPT) if PROMPT.exists() else None,
        "threshold": {
            "case_pass_score": CASE_PASS_SCORE, "min_pass_rate": MIN_PASS_RATE,
            "guardrail_category": GUARDRAIL_CATEGORY, "max_l1_failures": MAX_L1_FAILURES,
            "source": "spec.md EV-3, EV-4 (fixed 2026-11-14)",
        },
        "preflight": gates,
        "summary": summary,
        "verdict": verdict,
        "verdict_reasons": reasons,
        "cases": records,
    }
    path = write_files(result, bool(args.replay))
    print_report(result)
    print(f"Evidence: {path.relative_to(ROOT).as_posix()}")
    if verdict != "PASS":
        print(f"Feedback for the coding agent: {path.with_suffix('').as_posix().split('/')[-1]}"
              "-feedback.md (same folder)")
    return {"PASS": 0, "FAIL": 1}.get(verdict, 2)


if __name__ == "__main__":
    sys.exit(main())
