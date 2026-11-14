"""Output Schema Contract constants and the unknown result (INV-1, INV-2)."""

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
MISSING_FIELDS = ("task", "date", "time")
MAX_MESSAGE_LENGTH = 500
MAX_TASK_LENGTH = 120
MAX_QUESTION_LENGTH = 200
MAX_SNOOZE_MINUTES = 1440
MAX_DAYS_AHEAD = 366
DATETIME_FORMAT = "%Y-%m-%dT%H:%M"


def unknown_result() -> dict:
    """Return a fresh copy of the safe unknown result."""
    return {
        "intent": "unknown",
        "task": None,
        "datetime": None,
        "snooze_minutes": None,
        "requires_clarification": False,
        "missing_fields": [],
        "clarification_question": None,
    }
