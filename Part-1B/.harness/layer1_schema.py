"""Layer 1: structural validation of one result (spec INV-1).

Independent of the application: this module does not import anything from src/.
"""

from __future__ import annotations

import re

FIELDS = (
    "intent",
    "task",
    "datetime",
    "snooze_minutes",
    "requires_clarification",
    "missing_fields",
    "clarification_question",
)
INTENTS = ("create", "reschedule", "snooze", "unknown")
MISSING = ("task", "date", "time")
DATETIME_SHAPE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}")


def _text_or_null(value, low, high):
    if value is None:
        return True
    return isinstance(value, str) and low <= len(value) <= high


def check(result) -> list[str]:
    """Return a list of structural errors; an empty list means L1 passes."""
    if not isinstance(result, dict):
        return ["result is not a JSON object"]
    errors = []
    missing = [name for name in FIELDS if name not in result]
    extra = sorted(name for name in result if name not in FIELDS)
    if missing:
        errors.append(f"missing field(s): {', '.join(missing)}")
    if extra:
        errors.append(f"unexpected field(s): {', '.join(extra)}")
    if missing:
        return errors

    if result["intent"] not in INTENTS:
        errors.append(f"intent {result['intent']!r} is not one of {', '.join(INTENTS)}")
    if not _text_or_null(result["task"], 1, 120):
        errors.append("task must be null or text of 1 to 120 characters")
    value = result["datetime"]
    if value is not None and not (isinstance(value, str) and DATETIME_SHAPE.fullmatch(value)):
        errors.append("datetime must be null or text shaped YYYY-MM-DDTHH:MM")
    value = result["snooze_minutes"]
    is_whole = isinstance(value, int) and not isinstance(value, bool)
    if value is not None and not (is_whole and 1 <= value <= 1440):
        errors.append("snooze_minutes must be null or a whole number from 1 to 1440")
    if not isinstance(result["requires_clarification"], bool):
        errors.append("requires_clarification must be true or false")
    value = result["missing_fields"]
    if not isinstance(value, list) or any(item not in MISSING for item in value):
        errors.append("missing_fields must be a list containing only task, date, time")
    elif len(set(value)) != len(value):
        errors.append("missing_fields must not repeat an item")
    if not _text_or_null(result["clarification_question"], 1, 200):
        errors.append("clarification_question must be null or text of 1 to 200 characters")
    return errors
