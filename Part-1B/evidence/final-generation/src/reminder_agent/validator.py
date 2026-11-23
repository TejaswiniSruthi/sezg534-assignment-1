"""Application-side checks of INV-1 to INV-9 before a result is returned (FR-014)."""

import json
from datetime import datetime, timedelta

from reminder_agent import schema


def _is_text(value: object, limit: int) -> bool:
    return value is None or (isinstance(value, str) and 1 <= len(value) <= limit)


def _is_datetime_text(value: object) -> bool:
    if value is None:
        return True
    return isinstance(value, str) and len(value) == 16 and value[10] == "T"


def _is_snooze(value: object) -> bool:
    if value is None:
        return True
    whole = isinstance(value, int) and not isinstance(value, bool)
    return whole and 1 <= value <= schema.MAX_SNOOZE_MINUTES


def _is_missing_list(value: object) -> bool:
    if not isinstance(value, list) or len(set(map(str, value))) != len(value):
        return False
    return all(item in schema.MISSING_FIELDS for item in value)


def _structure_ok(result: object) -> bool:
    if not isinstance(result, dict) or set(result) != set(schema.FIELDS):
        return False
    return (
        result["intent"] in schema.INTENTS
        and _is_text(result["task"], schema.MAX_TASK_LENGTH)
        and _is_datetime_text(result["datetime"])
        and _is_snooze(result["snooze_minutes"])
        and isinstance(result["requires_clarification"], bool)
        and _is_missing_list(result["missing_fields"])
        and _is_text(result["clarification_question"], schema.MAX_QUESTION_LENGTH)
    )


def _datetime_ok(text: str | None, now: datetime) -> bool:
    if text is None:
        return True
    try:
        moment = datetime.strptime(text, schema.DATETIME_FORMAT)
    except ValueError:
        return False
    return now < moment <= now + timedelta(days=schema.MAX_DAYS_AHEAD)


def _clarification_rules(result: dict) -> list[str]:
    found = []
    asks = result["requires_clarification"]
    has_missing = bool(result["missing_fields"])
    has_question = result["clarification_question"] is not None
    if not (asks == has_missing == has_question):
        found.append("INV-3")
    if asks and (result["datetime"] is not None or result["snooze_minutes"] is not None):
        found.append("INV-4")
    if "task" in result["missing_fields"] and result["task"] is not None:
        found.append("INV-8")
    return found


def _completeness_rules(result: dict) -> list[str]:
    if result["requires_clarification"]:
        return []
    intent = result["intent"]
    scheduled = result["task"] is not None and result["datetime"] is not None
    if intent in ("create", "reschedule") and not (scheduled and result["snooze_minutes"] is None):
        return ["INV-5"]
    snoozed = result["snooze_minutes"] is not None and result["datetime"] is None
    if intent == "snooze" and not snoozed:
        return ["INV-6"]
    return []


def find_violations(result: object, now: datetime, marker: str) -> list[str]:
    """Return the ids of the violated invariants; an empty list means valid."""
    if not _structure_ok(result):
        return ["INV-1"]
    found = []
    if result["intent"] == "unknown" and result != schema.unknown_result():
        found.append("INV-2")
    found += _clarification_rules(result)
    found += _completeness_rules(result)
    if not _datetime_ok(result["datetime"], now):
        found.append("INV-7")
    if marker in json.dumps(result, ensure_ascii=False):
        found.append("INV-9")
    return found
