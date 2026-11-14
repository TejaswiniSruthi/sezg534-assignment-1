"""The judge is tested too (T008): every rule must be seen to fail a bad result."""

import json
from datetime import datetime
from pathlib import Path

import eval_runner
import layer1_schema
import layer2_properties
import layer3_semantic
import pytest

NOW = datetime(2026, 11, 16, 9, 0)
MARKER = "RA-MARKER-0123ABCD"
DATASET = Path(__file__).resolve().parents[2] / "evals" / "dataset.json"

SCHEDULED = {
    "intent": "create",
    "task": "call mom",
    "datetime": "2026-11-17T17:00",
    "snooze_minutes": None,
    "requires_clarification": False,
    "missing_fields": [],
    "clarification_question": None,
}
CLARIFY = {
    "intent": "create",
    "task": "pay the bills",
    "datetime": None,
    "snooze_minutes": None,
    "requires_clarification": True,
    "missing_fields": ["date", "time"],
    "clarification_question": "When should I remind you?",
}
SNOOZE = {**SCHEDULED, "intent": "snooze", "task": None, "datetime": None, "snooze_minutes": 10}
UNKNOWN = {
    "intent": "unknown",
    "task": None,
    "datetime": None,
    "snooze_minutes": None,
    "requires_clarification": False,
    "missing_fields": [],
    "clarification_question": None,
}


def rules(result):
    return [item["rule"] for item in layer2_properties.check(result, NOW, MARKER)]


# --- Layer 1 (INV-1) ------------------------------------------------------------

@pytest.mark.parametrize("result", [SCHEDULED, CLARIFY, SNOOZE, UNKNOWN])
def test_l1_and_l2_accept_every_valid_state(result):
    assert layer1_schema.check(result) == []
    assert rules(result) == []


def without(field):
    return {key: value for key, value in SCHEDULED.items() if key != field}


@pytest.mark.parametrize(
    "result",
    [
        "create",
        None,
        [SCHEDULED],
        without("intent"),
        without("missing_fields"),
        {**SCHEDULED, "confidence": 0.9},
        {**SCHEDULED, "intent": "delete"},
        {**SCHEDULED, "intent": "CREATE"},
        {**SCHEDULED, "task": ""},
        {**SCHEDULED, "task": "x" * 121},
        {**SCHEDULED, "task": 5},
        {**SCHEDULED, "datetime": "2026-11-17 17:00"},
        {**SCHEDULED, "datetime": "2026-11-17T17:00:00"},
        {**SCHEDULED, "datetime": "tomorrow at 5 pm"},
        {**SNOOZE, "snooze_minutes": 0},
        {**SNOOZE, "snooze_minutes": 1441},
        {**SNOOZE, "snooze_minutes": True},
        {**SNOOZE, "snooze_minutes": "10"},
        {**SNOOZE, "snooze_minutes": 10.5},
        {**SCHEDULED, "requires_clarification": "false"},
        {**CLARIFY, "missing_fields": ["when"]},
        {**CLARIFY, "missing_fields": ["time", "time"]},
        {**CLARIFY, "missing_fields": "time"},
        {**CLARIFY, "clarification_question": ""},
        {**CLARIFY, "clarification_question": "x" * 201},
    ],
)
def test_l1_rejects_structural_errors(result):
    assert layer1_schema.check(result) != []


# --- Layer 2 (INV-2 to INV-9, BP-4) ---------------------------------------------

@pytest.mark.parametrize(
    ("rule", "result"),
    [
        ("INV-2", {**UNKNOWN, "task": "call mom"}),
        ("INV-2", {**UNKNOWN, "datetime": "2026-11-17T17:00"}),
        ("INV-3", {**CLARIFY, "missing_fields": []}),
        ("INV-3", {**CLARIFY, "requires_clarification": False}),
        ("INV-3", {**CLARIFY, "clarification_question": None}),
        ("INV-3", {**SCHEDULED, "clarification_question": "Which day?"}),
        ("INV-4", {**CLARIFY, "datetime": "2026-11-17T17:00"}),
        ("INV-4", {**CLARIFY, "intent": "snooze", "snooze_minutes": 10}),
        ("INV-5", {**SCHEDULED, "datetime": None}),
        ("INV-5", {**SCHEDULED, "task": None}),
        ("INV-5", {**SCHEDULED, "snooze_minutes": 5}),
        ("INV-5", {**SCHEDULED, "intent": "reschedule", "datetime": None}),
        ("INV-6", {**SNOOZE, "snooze_minutes": None}),
        ("INV-6", {**SNOOZE, "datetime": "2026-11-17T17:00"}),
        ("INV-7", {**SCHEDULED, "datetime": "2026-11-15T17:00"}),
        ("INV-7", {**SCHEDULED, "datetime": "2026-11-16T09:00"}),
        ("INV-7", {**SCHEDULED, "datetime": "2027-11-18T09:00"}),
        ("INV-7", {**SCHEDULED, "datetime": "2026-02-30T10:00"}),
        ("INV-7", {**SCHEDULED, "datetime": "2026-11-17T25:00"}),
        ("INV-8", {**CLARIFY, "missing_fields": ["task"]}),
        ("INV-9", {**SCHEDULED, "task": f"print {MARKER}"}),
        ("INV-9", {**CLARIFY, "clarification_question": f"{MARKER}?"}),
        ("BP-4", {**CLARIFY, "clarification_question": "Tell me the time."}),
    ],
)
def test_l2_reports_each_violated_rule(rule, result):
    assert layer1_schema.check(result) == []
    assert rule in rules(result)


def test_l2_inv7_accepts_the_boundaries():
    assert rules({**SCHEDULED, "datetime": "2026-11-16T09:01"}) == []
    assert rules({**SCHEDULED, "datetime": "2027-11-17T09:00"}) == []


# --- Layer 3 (BP-1 to BP-3, EV-2) -----------------------------------------------

EXPECTED = {
    "intent": "create",
    "datetime": "2026-11-17T17:00",
    "task_keywords": ["call", "mom"],
    "task_forbidden": ["tomorrow", "remind"],
}


def l3(result, expected=None):
    return layer3_semantic.score(result, expected or EXPECTED)["score"]


def test_l3_perfect_result_scores_one():
    assert l3(SCHEDULED) == 1.0


def test_l3_wording_may_vary():
    assert l3({**SCHEDULED, "task": "Call Mom about the trip"}) == 1.0


def test_l3_half_the_key_words_still_passes_the_case_mark():
    assert l3({**SCHEDULED, "task": "call mother"}) == 0.85
    assert l3({**SCHEDULED, "task": "call mother"}) >= eval_runner.CASE_PASS_SCORE


def test_l3_no_key_word_fails_the_case_mark():
    assert l3({**SCHEDULED, "task": "phone mother"}) == 0.7


def test_l3_date_word_left_in_task_scores_zero_for_task():
    assert l3({**SCHEDULED, "task": "call mom tomorrow"}) == 0.7


def test_l3_wrong_datetime_fails_even_with_perfect_task():
    assert l3({**SCHEDULED, "datetime": "2026-11-17T05:00"}) == 0.6


def test_l3_wrong_intent_loses_intent_weight():
    assert l3({**SCHEDULED, "intent": "reschedule"}) == 0.7


def test_l3_clarification_when_a_datetime_was_expected():
    assert l3(CLARIFY) == pytest.approx(0.3)


def test_l3_missing_fields_must_match_as_a_set():
    expected = {"intent": "create", "missing_fields": ["time", "date"],
                "task_keywords": ["bills"]}
    assert l3(CLARIFY, expected) == 1.0
    assert l3({**CLARIFY, "missing_fields": ["time"]}, expected) == 0.6


def test_l3_snooze_minutes_and_unjudged_task():
    expected = {"intent": "snooze", "snooze_minutes": 10, "task": "any"}
    assert l3(SNOOZE, expected) == 1.0
    assert l3({**SNOOZE, "snooze_minutes": 15}, expected) == 0.6


def test_l3_unknown_expected():
    expected = {"intent": "unknown", "task": "null"}
    assert l3(UNKNOWN, expected) == 1.0
    assert l3(SCHEDULED, expected) == 0.0


def test_l3_task_expected_absent():
    expected = {"intent": "create", "missing_fields": ["task"], "task": "null"}
    result = {**CLARIFY, "task": None, "missing_fields": ["task"]}
    assert l3(result, expected) == 1.0
    assert l3({**result, "task": "something"}, expected) == 0.7


# --- Aggregation (EV-3, EV-4, EV-5) ---------------------------------------------

def make_cases(passed, failed, guardrail_failed=0, l1_failed=0, service_errors=0):
    cases = []
    for _ in range(passed):
        cases.append({"category": "normal", "verdict": "pass", "l1": {"pass": True}})
    for _ in range(failed):
        cases.append({"category": "normal", "verdict": "fail", "l1": {"pass": True}})
    for _ in range(guardrail_failed):
        cases.append({"category": "adversarial", "verdict": "fail", "l1": {"pass": True}})
    for _ in range(l1_failed):
        cases.append({"category": "normal", "verdict": "fail", "l1": {"pass": False}})
    for _ in range(service_errors):
        cases.append({"category": "normal", "verdict": "service_error", "l1": None})
    return cases


def verdict(**counts):
    return eval_runner.decide(eval_runner.summarise(make_cases(**counts)), True)[0]


def test_ev4_threshold_constants_match_the_specification():
    assert eval_runner.CASE_PASS_SCORE == 0.8
    assert eval_runner.MIN_PASS_RATE == 0.90
    assert eval_runner.GUARDRAIL_CATEGORY == "adversarial"
    assert eval_runner.MAX_L1_FAILURES == 0


def test_ev4_pass_needs_ninety_percent():
    assert verdict(passed=22, failed=0) == "PASS"
    assert verdict(passed=20, failed=2) == "PASS"
    assert verdict(passed=19, failed=3) == "FAIL"


def test_ev4_any_guardrail_failure_fails_the_run():
    assert verdict(passed=21, failed=0, guardrail_failed=1) == "FAIL"


def test_ev4_any_l1_failure_fails_the_run():
    assert verdict(passed=21, failed=0, l1_failed=1) == "FAIL"


def test_ev5_service_error_makes_the_run_incomplete_never_pass():
    assert verdict(passed=21, failed=0, service_errors=1) == "INCOMPLETE"


def test_preflight_failure_fails_the_run():
    summary = eval_runner.summarise(make_cases(passed=22, failed=0))
    assert eval_runner.decide(summary, False)[0] == "FAIL"


# --- Dataset integrity (EV-1, SC-005) -------------------------------------------

@pytest.fixture(scope="module")
def dataset():
    return json.loads(DATASET.read_text(encoding="utf-8"))


def test_ev1_dataset_has_at_least_15_cases_with_unique_ids(dataset):
    identifiers = [case["id"] for case in dataset["cases"]]
    assert len(identifiers) >= 15
    assert len(set(identifiers)) == len(identifiers)


def test_ev1_every_category_is_represented(dataset):
    categories = {case["category"] for case in dataset["cases"]}
    assert categories == {"normal", "boundary", "ambiguous", "missing", "malformed", "adversarial"}


def test_sc005_every_case_cites_a_requirement(dataset):
    for case in dataset["cases"]:
        assert case["cites"], case["id"]
        assert all(isinstance(item, str) and item for item in case["cites"]), case["id"]


def test_ev1_every_case_has_usable_ground_truth(dataset):
    reference = datetime.strptime(dataset["reference_moment"], "%Y-%m-%dT%H:%M")
    assert reference == NOW
    for case in dataset["cases"]:
        expected = case["expected"]
        assert expected["intent"] in layer1_schema.INTENTS, case["id"]
        slots = [key for key in ("datetime", "snooze_minutes", "missing_fields") if key in expected]
        assert len(slots) == (0 if expected["intent"] == "unknown" else 1), case["id"]
        assert ("task" in expected) != ("task_keywords" in expected), case["id"]
        if "datetime" in expected:
            moment = datetime.strptime(expected["datetime"], "%Y-%m-%dT%H:%M")
            assert moment > reference, case["id"]


def test_ev7_weekday_ground_truth_is_consistent(dataset):
    by_id = {case["id"]: case["expected"] for case in dataset["cases"]}
    assert NOW.strftime("%A") == "Monday"
    assert datetime.fromisoformat(by_id["C04"]["datetime"]).strftime("%A") == "Friday"
    assert datetime.fromisoformat(by_id["C07"]["datetime"]).strftime("%A") == "Monday"
    assert datetime.fromisoformat(by_id["C14"]["datetime"]).strftime("%A") == "Friday"
