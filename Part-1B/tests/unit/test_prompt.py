"""Prompt construction (research R3, R5; INV-9 marker)."""

import re
from datetime import datetime, timedelta

from reminder_agent.prompt import build_system_prompt, leak_marker

NOW = datetime(2026, 11, 16, 9, 0)


def test_inv9_marker_has_the_contract_shape_and_is_in_the_prompt():
    marker = leak_marker()
    assert re.fullmatch(r"RA-MARKER-[0-9A-F]{8}", marker)
    assert marker in build_system_prompt(NOW)


def test_prompt_states_the_reference_moment_and_weekday():
    text = build_system_prompt(NOW)
    assert "2026-11-16T09:00" in text
    assert "Monday" in text


def test_prompt_contains_a_15_day_calendar():
    text = build_system_prompt(NOW)
    for offset in range(15):
        day = NOW + timedelta(days=offset)
        assert f"{day:%Y-%m-%d} {day:%A}" in text
    assert "2026-12-01" not in text


def test_prompt_changes_with_the_reference_moment():
    other = build_system_prompt(datetime(2027, 1, 5, 18, 30))
    assert "2027-01-05T18:30" in other
    assert "2027-01-05 Tuesday" in other
    assert "2026-11-16T09:00" not in other


def test_prompt_names_every_contract_field():
    text = build_system_prompt(NOW)
    for field in (
        "intent",
        "task",
        "datetime",
        "snooze_minutes",
        "requires_clarification",
        "missing_fields",
        "clarification_question",
    ):
        assert field in text
