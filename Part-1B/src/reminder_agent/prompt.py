"""Builds the model instructions: fixed rules plus the reference moment and a calendar."""

import re
from datetime import datetime, timedelta
from pathlib import Path

from reminder_agent import schema

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "system_prompt.md"
MARKER = re.compile(r"RA-MARKER-[0-9A-F]{8}")
CALENDAR_DAYS = 15


def _rules() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def leak_marker() -> str:
    """Return the unique marker embedded in the instructions (INV-9)."""
    match = MARKER.search(_rules())
    if match is None:
        raise ValueError("prompts/system_prompt.md has no RA-MARKER marker")
    return match.group(0)


def build_system_prompt(now: datetime) -> str:
    """Return the full instructions for one call, resolved against ``now``."""
    lines = [
        _rules().rstrip(),
        "",
        "## Current context",
        "",
        f"Reference moment (now): {now.strftime(schema.DATETIME_FORMAT)} ({now:%A})",
        "",
        "Calendar (use it to look up dates; do not calculate weekdays yourself):",
    ]
    for offset in range(CALENDAR_DAYS):
        day = now + timedelta(days=offset)
        label = " (today)" if offset == 0 else " (tomorrow)" if offset == 1 else ""
        lines.append(f"- {day:%Y-%m-%d} {day:%A}{label}")
    return "\n".join(lines) + "\n"
