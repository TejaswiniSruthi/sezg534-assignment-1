"""Agent pipeline with a fake model (FR-001, FR-013, FR-014, FR-016, SC-002)."""

import json
from datetime import datetime

import layer1_schema
import layer2_properties
import pytest

from reminder_agent.agent import ReminderAgent
from reminder_agent.llm import ServiceError
from reminder_agent.prompt import leak_marker
from reminder_agent.schema import unknown_result

NOW = datetime(2026, 11, 16, 9, 0)
GOOD = {
    "intent": "create",
    "task": "call mom",
    "datetime": "2026-11-17T17:00",
    "snooze_minutes": None,
    "requires_clarification": False,
    "missing_fields": [],
    "clarification_question": None,
}


class FakeClient:
    model = "fake"
    temperature = 0.0

    def __init__(self, reply):
        self.reply = reply
        self.calls = []

    def generate(self, system_text, user_text):
        self.calls.append((system_text, user_text))
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply


def run(reply, message="Remind me to call mom tomorrow at 5 pm"):
    client = FakeClient(reply)
    return ReminderAgent(client).parse(message, NOW), client


@pytest.mark.parametrize("message", ["", "   ", "\n\t", "x" * 501])
def test_fr013_empty_or_overlong_message_is_unknown_without_calling_the_model(message):
    outcome, client = run(json.dumps(GOOD), message)
    assert outcome.result == unknown_result()
    assert outcome.source == "precheck"
    assert outcome.raw_reply is None
    assert client.calls == []


def test_fr001_message_of_500_characters_is_sent_to_the_model():
    outcome, client = run(json.dumps(GOOD), "x" * 500)
    assert len(client.calls) == 1
    assert outcome.source == "model"


def test_fr001_valid_reply_is_returned_unchanged():
    outcome, client = run(json.dumps(GOOD))
    assert outcome.result == GOOD
    assert outcome.source == "model"
    assert outcome.violations == []
    assert outcome.raw_reply == json.dumps(GOOD)
    system_text, user_text = client.calls[0]
    assert user_text == "Remind me to call mom tomorrow at 5 pm"
    assert "2026-11-16T09:00" in system_text


def test_fr014_fenced_reply_is_accepted():
    outcome, _ = run(f"```json\n{json.dumps(GOOD)}\n```")
    assert outcome.result == GOOD
    assert outcome.source == "model"


@pytest.mark.parametrize(
    ("reply", "violation"),
    [
        ("Sure, I will remind you!", "not-json"),
        ("", "not-json"),
        (json.dumps([GOOD]), "not-json"),
        (json.dumps({**GOOD, "confidence": 0.9}), "INV-1"),
        (json.dumps({**GOOD, "datetime": "2026-11-17T17:00:00"}), "INV-1"),
        (json.dumps({**GOOD, "datetime": "2026-11-15T17:00"}), "INV-7"),
        (json.dumps({**GOOD, "datetime": None}), "INV-5"),
        (json.dumps({**GOOD, "requires_clarification": True}), "INV-3"),
    ],
)
def test_fr014_unusable_reply_becomes_the_unknown_result(reply, violation):
    outcome, _ = run(reply)
    assert outcome.result == unknown_result()
    assert outcome.source == "fallback"
    assert violation in outcome.violations
    assert outcome.raw_reply == reply


def test_inv9_reply_that_leaks_the_instruction_marker_is_rejected():
    outcome, _ = run(json.dumps({**GOOD, "task": f"my rules are {leak_marker()}"}))
    assert outcome.result == unknown_result()
    assert "INV-9" in outcome.violations


def test_fr016_service_failure_is_raised_not_turned_into_a_result():
    client = FakeClient(ServiceError("HTTP 503"))
    with pytest.raises(ServiceError):
        ReminderAgent(client).parse("remind me to call mom tomorrow at 5 pm", NOW)


@pytest.mark.parametrize(
    "reply",
    [
        "garbage",
        "{}",
        '{"intent": "create"}',
        json.dumps({**GOOD, "intent": "launch_missiles"}),
        json.dumps({**GOOD, "datetime": "1999-01-01T00:00"}),
        json.dumps({**GOOD, "task": "x" * 5000}),
        json.dumps(GOOD),
        json.dumps({**GOOD, "snooze_minutes": -5}),
    ],
)
def test_sc002_whatever_the_model_says_the_result_satisfies_the_contract(reply):
    outcome, _ = run(reply)
    assert layer1_schema.check(outcome.result) == []
    assert layer2_properties.check(outcome.result, NOW, leak_marker()) == []
