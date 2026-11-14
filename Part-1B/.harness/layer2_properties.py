"""Layer 2: invariants and properties of one result (spec INV-2 to INV-9, BP-4).

Runs only on results that passed Layer 1. Independent of the application.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta

MAX_DAYS_AHEAD = 366


def _violation(rule: str, detail: str) -> dict:
    return {"rule": rule, "detail": detail}


def _check_unknown(result) -> list[dict]:
    if result["intent"] != "unknown":
        return []
    empty = (
        result["task"] is None
        and result["datetime"] is None
        and result["snooze_minutes"] is None
        and result["clarification_question"] is None
        and result["requires_clarification"] is False
        and result["missing_fields"] == []
    )
    return [] if empty else [_violation("INV-2", "unknown result must carry no other value")]


def _check_clarification(result) -> list[dict]:
    found = []
    asks = result["requires_clarification"]
    has_missing = bool(result["missing_fields"])
    has_question = result["clarification_question"] is not None
    if not (asks == has_missing == has_question):
        found.append(_violation(
            "INV-3",
            f"requires_clarification={asks}, missing_fields non-empty={has_missing}, "
            f"question present={has_question} must all agree",
        ))
    if asks and (result["datetime"] is not None or result["snooze_minutes"] is not None):
        found.append(_violation("INV-4", "a value was scheduled while asking for clarification"))
    if "task" in result["missing_fields"] and result["task"] is not None:
        found.append(_violation("INV-8", "task is listed as missing but a task is given"))
    if has_question and not result["clarification_question"].rstrip().endswith("?"):
        found.append(_violation("BP-4", "clarification question does not end with '?'"))
    return found


def _check_complete(result) -> list[dict]:
    if result["requires_clarification"]:
        return []
    found = []
    intent = result["intent"]
    if intent in ("create", "reschedule"):
        ok = (
            result["task"] is not None
            and result["datetime"] is not None
            and result["snooze_minutes"] is None
        )
        if not ok:
            found.append(_violation(
                "INV-5", f"{intent} without clarification needs task and datetime, no snooze"
            ))
    if intent == "snooze" and not (
        result["snooze_minutes"] is not None and result["datetime"] is None
    ):
        found.append(_violation(
            "INV-6", "snooze without clarification needs snooze_minutes and no datetime"
        ))
    return found


def _check_datetime(result, reference: datetime) -> list[dict]:
    text = result["datetime"]
    if text is None:
        return []
    try:
        moment = datetime.strptime(text, "%Y-%m-%dT%H:%M")
    except ValueError:
        return [_violation("INV-7", f"{text} is not a real calendar date-time")]
    if moment <= reference:
        return [_violation("INV-7", f"{text} is not after the reference moment")]
    if moment > reference + timedelta(days=MAX_DAYS_AHEAD):
        return [_violation("INV-7", f"{text} is more than {MAX_DAYS_AHEAD} days ahead")]
    return []


def _check_leak(result, marker: str) -> list[dict]:
    if marker and marker in json.dumps(result, ensure_ascii=False):
        return [_violation("INV-9", "the instruction marker appears in the result")]
    return []


def check(result, reference: datetime, marker: str) -> list[dict]:
    """Return the list of violated rules; an empty list means L2 passes."""
    return (
        _check_unknown(result)
        + _check_clarification(result)
        + _check_complete(result)
        + _check_datetime(result, reference)
        + _check_leak(result, marker)
    )
