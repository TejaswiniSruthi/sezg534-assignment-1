"""Validation and domain rules (T005). Each test cites the requirement it checks."""

import pytest
from todo.errors import (
    InvalidTransitionError,
    NotFoundError,
    StorageError,
    TodoError,
    ValidationError,
)
from todo.models import (
    Task,
    check_transition,
    normalise_tags,
    validate_id,
    validate_priority,
    validate_status,
    validate_title,
)

# --- FR-015: error categories -------------------------------------------------

@pytest.mark.parametrize(
    ("error_class", "category", "exit_code"),
    [
        (ValidationError, "validation", 2),
        (NotFoundError, "not_found", 3),
        (InvalidTransitionError, "invalid_transition", 4),
        (StorageError, "storage", 5),
    ],
)
def test_fr015_error_categories_and_exit_codes(error_class, category, exit_code):
    assert issubclass(error_class, TodoError)
    assert error_class.category == category
    assert error_class.exit_code == exit_code
    assert str(error_class("some message")) == "some message"


# --- FR-002: title ------------------------------------------------------------

def test_fr002_title_is_returned_unchanged_when_valid():
    assert validate_title("Buy milk") == "Buy milk"


def test_fr002_title_is_trimmed():
    assert validate_title("   Buy milk  ") == "Buy milk"


def test_fr002_title_of_100_characters_is_accepted():
    assert validate_title("x" * 100) == "x" * 100


def test_fr002_length_is_checked_after_trimming():
    assert validate_title("  " + "x" * 100 + "  ") == "x" * 100


@pytest.mark.parametrize("title", ["", "   ", "\t", "x" * 101])
def test_fr002_invalid_title_is_rejected(title):
    with pytest.raises(ValidationError):
        validate_title(title)


# --- FR-003: priority ---------------------------------------------------------

def test_fr003_priority_defaults_to_medium():
    assert validate_priority(None) == "medium"


@pytest.mark.parametrize("priority", ["low", "medium", "high"])
def test_fr003_valid_priority_is_accepted(priority):
    assert validate_priority(priority) == priority


@pytest.mark.parametrize("priority", ["urgent", "HIGH", "", " high", "1"])
def test_fr003_invalid_priority_is_rejected(priority):
    with pytest.raises(ValidationError):
        validate_priority(priority)


# --- FR-004: tags -------------------------------------------------------------

def test_fr004_tags_are_lowercased_and_sorted():
    assert normalise_tags(["Home", "bills"]) == ["bills", "home"]


def test_fr004_duplicate_tags_are_stored_once():
    assert normalise_tags(["a", "A", "a", "b"]) == ["a", "b"]


def test_fr004_no_tags_gives_empty_list():
    assert normalise_tags([]) == []


def test_fr004_letters_digits_and_hyphen_are_allowed():
    assert normalise_tags(["q4-2026", "a" * 20]) == ["a" * 20, "q4-2026"]


def test_fr004_ten_tags_are_accepted():
    tags = [f"t{number:02d}" for number in range(10)]
    assert normalise_tags(tags) == tags


def test_fr004_eleven_tags_are_rejected():
    with pytest.raises(ValidationError):
        normalise_tags([f"t{number:02d}" for number in range(11)])


@pytest.mark.parametrize("tag", ["", "a" * 21, "has space", "tag!", "under_score", "é"])
def test_fr004_invalid_tag_is_rejected(tag):
    with pytest.raises(ValidationError):
        normalise_tags(["ok", tag])


# --- FR-008: status values and transitions ------------------------------------

@pytest.mark.parametrize("status", ["todo", "in_progress", "done"])
def test_fr008_valid_status_is_accepted(status):
    assert validate_status(status) == status


@pytest.mark.parametrize("status", ["started", "DONE", "", "in progress"])
def test_fr008_unknown_status_is_a_validation_error(status):
    with pytest.raises(ValidationError):
        validate_status(status)


@pytest.mark.parametrize(
    ("current", "target"),
    [("todo", "in_progress"), ("in_progress", "done"), ("in_progress", "todo")],
)
def test_fr008_allowed_transitions(current, target):
    assert check_transition(current, target) is None


@pytest.mark.parametrize(
    ("current", "target"),
    [
        ("todo", "todo"),
        ("todo", "done"),
        ("in_progress", "in_progress"),
        ("done", "todo"),
        ("done", "in_progress"),
        ("done", "done"),
    ],
)
def test_fr008_every_other_transition_is_rejected(current, target):
    with pytest.raises(InvalidTransitionError):
        check_transition(current, target)


# --- Edge case: task id -------------------------------------------------------

@pytest.mark.parametrize(("value", "expected"), [("1", 1), (5, 5), ("42", 42)])
def test_edge_valid_id_is_returned_as_integer(value, expected):
    assert validate_id(value) == expected


@pytest.mark.parametrize("value", ["0", "-1", "abc", "1.5", "", 0, -3])
def test_edge_id_must_be_a_positive_whole_number(value):
    with pytest.raises(ValidationError):
        validate_id(value)


@pytest.mark.parametrize("value", ["²", "٣", "１", "1²"])
def test_edge_id_must_use_the_digits_0_to_9(value):
    with pytest.raises(ValidationError):
        validate_id(value)


# --- FR-017: task shape -------------------------------------------------------

def test_fr017_task_to_dict_has_exactly_the_contract_fields():
    task = Task(id=1, title="Buy milk", priority="medium", status="todo", tags=[])
    assert task.to_dict() == {
        "id": 1,
        "title": "Buy milk",
        "priority": "medium",
        "status": "todo",
        "tags": [],
    }
