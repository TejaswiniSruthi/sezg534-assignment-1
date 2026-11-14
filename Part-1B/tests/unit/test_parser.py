"""Reply parsing (FR-014): exactly one JSON object, optionally in a code fence."""

import pytest
from reminder_agent.parser import extract_json

OBJECT = '{"intent": "unknown", "task": null}'
PARSED = {"intent": "unknown", "task": None}


@pytest.mark.parametrize(
    "text",
    [
        OBJECT,
        f"  \n{OBJECT}\n  ",
        f"```json\n{OBJECT}\n```",
        f"```\n{OBJECT}\n```",
        f"```JSON\n{OBJECT}\n```\n",
    ],
)
def test_fr014_accepts_a_bare_or_fenced_object(text):
    assert extract_json(text) == PARSED


@pytest.mark.parametrize(
    "text",
    [
        "",
        "   ",
        "Sure! Here is your reminder.",
        f"Here you go: {OBJECT}",
        f"{OBJECT} Hope that helps!",
        f"{OBJECT}\n{OBJECT}",
        "[1, 2, 3]",
        '"just text"',
        "42",
        "null",
        '{"intent": "create",',
        f"```json\n{OBJECT}\n``` and some more text",
    ],
)
def test_fr014_rejects_anything_else(text):
    with pytest.raises(ValueError):
        extract_json(text)
