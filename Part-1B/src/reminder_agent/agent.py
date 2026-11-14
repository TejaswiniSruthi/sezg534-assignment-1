"""The agent: pre-check, model call, parse, validate, then result or safe fallback."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from reminder_agent import schema
from reminder_agent.parser import extract_json
from reminder_agent.prompt import build_system_prompt, leak_marker
from reminder_agent.validator import find_violations


class ModelClient(Protocol):
    """Anything that can turn instructions and a message into reply text."""

    def generate(self, system_text: str, user_text: str) -> str:
        """Return the model's reply text or raise ServiceError."""


@dataclass
class Outcome:
    """A contract-valid result plus diagnostics that are not part of the contract."""

    result: dict
    source: str
    raw_reply: str | None = None
    violations: list[str] = field(default_factory=list)


class ReminderAgent:
    """Turns one message into one result that always satisfies the output contract."""

    def __init__(self, client: ModelClient) -> None:
        """Remember the model client to use."""
        self._client = client

    def parse(self, message: str, now: datetime) -> Outcome:
        """Interpret ``message`` relative to ``now`` (FR-001, FR-013, FR-014)."""
        if not message.strip() or len(message) > schema.MAX_MESSAGE_LENGTH:
            return Outcome(schema.unknown_result(), "precheck")
        reply = self._client.generate(build_system_prompt(now), message)
        try:
            result = extract_json(reply)
        except ValueError:
            return Outcome(schema.unknown_result(), "fallback", reply, ["not-json"])
        violations = find_violations(result, now, leak_marker())
        if violations:
            return Outcome(schema.unknown_result(), "fallback", reply, violations)
        return Outcome(result, "model", reply)
