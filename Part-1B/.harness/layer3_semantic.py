"""Layer 3: semantic / quality score of one result against ground truth.

score = 0.3 * BP-1 (intent) + 0.4 * BP-2 (slot value) + 0.3 * BP-3 (task fidelity)
(spec EV-2). Rule-based; no model is used as a judge. Independent of the application.
"""

from __future__ import annotations

WEIGHT_INTENT = 0.3
WEIGHT_SLOT = 0.4
WEIGHT_TASK = 0.3


def _slot(result, expected) -> tuple[float, str]:
    if "datetime" in expected:
        ok = result["datetime"] == expected["datetime"] and not result["requires_clarification"]
        return float(ok), f"datetime expected {expected['datetime']}, got {result['datetime']}"
    if "snooze_minutes" in expected:
        ok = result["snooze_minutes"] == expected["snooze_minutes"]
        return float(ok), (
            f"snooze_minutes expected {expected['snooze_minutes']}, "
            f"got {result['snooze_minutes']}"
        )
    if "missing_fields" in expected:
        ok = result["requires_clarification"] and sorted(result["missing_fields"]) == sorted(
            expected["missing_fields"]
        )
        return float(ok), (
            f"missing_fields expected {sorted(expected['missing_fields'])}, "
            f"got {sorted(result['missing_fields'])} "
            f"(requires_clarification={result['requires_clarification']})"
        )
    ok = (
        result["datetime"] is None
        and result["snooze_minutes"] is None
        and not result["requires_clarification"]
    )
    return float(ok), "no slot value expected"


def _task(result, expected) -> tuple[float, str]:
    task = result["task"]
    rule = expected.get("task")
    if rule == "any":
        return 1.0, "task not judged for this case"
    if rule == "null":
        return float(task is None), f"task expected to be absent, got {task!r}"
    keywords = expected.get("task_keywords", [])
    if task is None:
        return 0.0, "task is missing"
    lowered = task.lower()
    present = [word for word in expected.get("task_forbidden", []) if word.lower() in lowered]
    if present:
        return 0.0, f"task contains date/time or filler word(s): {', '.join(present)}"
    found = [word for word in keywords if word.lower() in lowered]
    fraction = len(found) / len(keywords) if keywords else 1.0
    return fraction, f"key words found {len(found)}/{len(keywords)} in task {task!r}"


def score(result, expected) -> dict:
    """Return the L3 score with its three components and explanatory notes."""
    bp1 = float(result["intent"] == expected["intent"])
    bp2, slot_note = _slot(result, expected)
    bp3, task_note = _task(result, expected)
    total = WEIGHT_INTENT * bp1 + WEIGHT_SLOT * bp2 + WEIGHT_TASK * bp3
    return {
        "score": round(total, 3),
        "bp1_intent": bp1,
        "bp2_slot": bp2,
        "bp3_task": round(bp3, 3),
        "notes": [
            f"intent expected {expected['intent']}, got {result['intent']}",
            slot_note,
            task_note,
        ],
    }
