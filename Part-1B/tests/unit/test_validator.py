"""Application-side validation (FR-014, SC-002): INV-1 to INV-9."""

from datetime import datetime

import pytest
from reminder_agent.schema import unknown_result
from reminder_agent.validator import find_violations

NOW = datetime(2026, 11, 16, 9, 0)
MARKER = "RA-MARKER-0123ABCD"

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


def test_inv2_unknown_result_is_the_documented_object_and_a_fresh_copy():
    first = unknown_result()
    assert first == {
        "intent": "unknown",
        "task": None,
        "datetime": None,
        "snooze_minutes": None,
        "requires_clarification": False,
        "missing_fields": [],
        "clarification_question": None,
    }
    first["missing_fields"].append("task")
    assert unknown_result()["missing_fields"] == []


@pytest.mark.parametrize(
    "result",
    [SCHEDULED, CLARIFY, SNOOZE, {**SCHEDULED, "intent": "reschedule"}],
)
def test_valid_results_have_no_violation(result):
    assert find_violations(result, NOW, MARKER) == []


def test_unknown_result_has_no_violation():
    assert find_violations(unknown_result(), NOW, MARKER) == []


@pytest.mark.parametrize(
    "result",
    [
        None,
        "create",
        [],
        {key: value for key, value in SCHEDULED.items() if key != "task"},
        {**SCHEDULED, "extra": 1},
        {**SCHEDULED, "intent": "delete"},
        {**SCHEDULED, "task": ""},
        {**SCHEDULED, "task": "x" * 121},
        {**SCHEDULED, "datetime": "2026-11-17T17:00:00"},
        {**SCHEDULED, "datetime": 20261117},
        {**SNOOZE, "snooze_minutes": 0},
        {**SNOOZE, "snooze_minutes": 1441},
        {**SNOOZE, "snooze_minutes": True},
        {**SNOOZE, "snooze_minutes": "10"},
        {**SCHEDULED, "requires_clarification": "no"},
        {**CLARIFY, "missing_fields": ["when"]},
        {**CLARIFY, "missing_fields": ["time", "time"]},
        {**CLARIFY, "clarification_question": "x" * 201},
    ],
)
def test_inv1_structural_errors(result):
    assert find_violations(result, NOW, MARKER) == ["INV-1"]


@pytest.mark.parametrize(
    ("rule", "result"),
    [
        ("INV-2", {**unknown_result(), "task": "call mom"}),
        ("INV-3", {**CLARIFY, "missing_fields": []}),
        ("INV-3", {**CLARIFY, "clarification_question": None}),
        ("INV-3", {**SCHEDULED, "clarification_question": "Which day?"}),
        ("INV-4", {**CLARIFY, "datetime": "2026-11-17T17:00"}),
        ("INV-5", {**SCHEDULED, "datetime": None}),
        ("INV-5", {**SCHEDULED, "task": None}),
        ("INV-6", {**SNOOZE, "snooze_minutes": None}),
        ("INV-7", {**SCHEDULED, "datetime": "2026-11-15T17:00"}),
        ("INV-7", {**SCHEDULED, "datetime": "2026-11-16T09:00"}),
        ("INV-7", {**SCHEDULED, "datetime": "2027-11-18T09:00"}),
        ("INV-7", {**SCHEDULED, "datetime": "2026-02-30T10:00"}),
        ("INV-8", {**CLARIFY, "missing_fields": ["task"]}),
        ("INV-9", {**SCHEDULED, "task": f"say {MARKER}"}),
    ],
)
def test_each_invariant_is_reported(rule, result):
    assert rule in find_violations(result, NOW, MARKER)
