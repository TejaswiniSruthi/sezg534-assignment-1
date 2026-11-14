"""Task model, validation rules and status transitions (FR-002 to FR-008)."""

import re
from collections.abc import Iterable
from dataclasses import dataclass

from todo.errors import InvalidTransitionError, ValidationError

PRIORITIES = ("high", "medium", "low")
STATUSES = ("todo", "in_progress", "done")
TRANSITIONS = {
    "todo": {"in_progress"},
    "in_progress": {"todo", "done"},
    "done": set(),
}
MAX_TITLE_LENGTH = 100
MAX_TAGS = 10
MAX_TAG_LENGTH = 20
TAG_PATTERN = re.compile(r"[A-Za-z0-9-]+")


@dataclass
class Task:
    """One unit of work."""

    id: int
    title: str
    priority: str
    status: str
    tags: list[str]

    def to_dict(self) -> dict:
        """Return the task as a plain dictionary with the contract fields."""
        return {
            "id": self.id,
            "title": self.title,
            "priority": self.priority,
            "status": self.status,
            "tags": list(self.tags),
        }


def validate_title(title: str) -> str:
    """Return the trimmed title, or raise if it is not 1 to 100 characters."""
    if not isinstance(title, str):
        raise ValidationError("title must be text")
    trimmed = title.strip()
    if not trimmed:
        raise ValidationError("title must not be empty")
    if len(trimmed) > MAX_TITLE_LENGTH:
        raise ValidationError(f"title must be at most {MAX_TITLE_LENGTH} characters")
    return trimmed


def validate_priority(priority: str | None) -> str:
    """Return the priority, defaulting to medium when it is omitted."""
    if priority is None:
        return "medium"
    if priority not in PRIORITIES:
        raise ValidationError("priority must be one of low, medium, high")
    return priority


def normalise_tags(tags: Iterable[str]) -> list[str]:
    """Return the tags lower-cased, without duplicates, in alphabetical order."""
    result = set()
    for tag in tags:
        if not isinstance(tag, str) or not TAG_PATTERN.fullmatch(tag):
            raise ValidationError("a tag may contain only letters, digits and hyphens")
        if len(tag) > MAX_TAG_LENGTH:
            raise ValidationError(f"a tag must be at most {MAX_TAG_LENGTH} characters")
        result.add(tag.lower())
    if len(result) > MAX_TAGS:
        raise ValidationError(f"a task may have at most {MAX_TAGS} tags")
    return sorted(result)


def validate_status(status: str) -> str:
    """Return the status, or raise if it is not a known status value."""
    if status not in STATUSES:
        raise ValidationError("status must be one of todo, in_progress, done")
    return status


def validate_id(value: str | int) -> int:
    """Return the task id as a positive whole number written with the digits 0-9."""
    text = str(value)
    if not (text.isascii() and text.isdigit()) or int(text) < 1:
        raise ValidationError("task id must be a positive whole number")
    return int(text)


def check_transition(current: str, target: str) -> None:
    """Raise unless a task may move from ``current`` to ``target`` (FR-008)."""
    if target not in TRANSITIONS[current]:
        raise InvalidTransitionError(f"a task cannot move from {current} to {target}")
