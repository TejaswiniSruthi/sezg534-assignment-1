"""CLI contract tests (T010, T015, T019).

Each test runs the tool as a separate process, exactly as a user would, and
asserts the exit code, stdout and stderr defined in contracts/cli-contract.md.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "src"


def run_cli(*arguments, file=None, cwd=None, extra_env=None):
    env = {key: value for key, value in os.environ.items() if key != "TODO_FILE"}
    env["PYTHONPATH"] = str(SRC)
    env["PYTHONIOENCODING"] = "utf-8"
    env.update(extra_env or {})
    command = [sys.executable, "-m", "todo"]
    if file is not None:
        command += ["--file", str(file)]
    command += list(arguments)
    return subprocess.run(
        command, capture_output=True, text=True, encoding="utf-8", env=env, cwd=cwd, timeout=60
    )


def assert_success(result):
    """Contract: exit 0, one line of sorted-key JSON on stdout, empty stderr."""
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    assert result.stdout.endswith("\n")
    assert result.stdout.count("\n") == 1
    return json.loads(result.stdout)


def assert_failure(result, category, exit_code):
    """Contract: exit code, empty stdout, one line of error JSON on stderr."""
    assert result.returncode == exit_code, result.stderr
    assert result.stdout == ""
    assert result.stderr.endswith("\n")
    assert result.stderr.count("\n") == 1
    payload = json.loads(result.stderr)
    assert list(payload) == ["error"]
    assert sorted(payload["error"]) == ["category", "message"]
    assert payload["error"]["category"] == category
    assert isinstance(payload["error"]["message"], str)
    assert payload["error"]["message"] != ""


@pytest.fixture
def file(tmp_path):
    return tmp_path / "tasks.json"


def snapshot(path):
    return path.read_bytes() if path.exists() else None


def ids(tasks):
    return [task["id"] for task in tasks]


# --- User Story 1: add, show, list --------------------------------------------

def test_as11_add_prints_the_created_task(file):
    task = assert_success(run_cli("add", "Buy milk", file=file))
    assert task == {
        "id": 1,
        "priority": "medium",
        "status": "todo",
        "tags": [],
        "title": "Buy milk",
    }


def test_fr017_keys_are_sorted_on_stdout(file):
    result = run_cli("add", "Buy milk", file=file)
    pairs = json.loads(result.stdout, object_pairs_hook=list)
    assert [key for key, _ in pairs] == ["id", "priority", "status", "tags", "title"]


def test_as12_add_with_priority_and_tags(file):
    assert_success(run_cli("add", "Buy milk", file=file))
    task = assert_success(
        run_cli("add", "Pay rent", "--priority", "high", "--tag", "Home", "--tag", "bills",
                file=file)
    )
    assert task == {
        "id": 2,
        "priority": "high",
        "status": "todo",
        "tags": ["bills", "home"],
        "title": "Pay rent",
    }


def test_as13_tasks_persist_between_processes(file):
    first = assert_success(run_cli("add", "Buy milk", file=file))
    second = assert_success(run_cli("add", "Pay rent", "--priority", "high", file=file))
    assert assert_success(run_cli("list", file=file)) == [first, second]


def test_as14_show_existing_and_missing_task(file):
    created = assert_success(run_cli("add", "Buy milk", file=file))
    assert assert_success(run_cli("show", "1", file=file)) == created
    before = snapshot(file)
    assert_failure(run_cli("show", "99", file=file), "not_found", 3)
    assert snapshot(file) == before


@pytest.mark.parametrize(
    "arguments",
    [
        ["add", ""],
        ["add", "   "],
        ["add", "x" * 101],
        ["add", "ok", "--priority", "urgent"],
        ["add", "ok", "--priority", "HIGH"],
        ["add", "ok", "--tag", "bad tag"],
    ],
)
def test_as15_invalid_add_is_a_validation_error_and_changes_nothing(file, arguments):
    assert_success(run_cli("add", "Existing", file=file))
    before = snapshot(file)
    assert_failure(run_cli(*arguments, file=file), "validation", 2)
    assert snapshot(file) == before


def test_as17_list_with_no_data_file_is_empty_and_creates_nothing(file):
    assert assert_success(run_cli("list", file=file)) == []
    assert not file.exists()


@pytest.mark.parametrize(
    "arguments",
    [
        ["list"],
        ["add", "Buy milk"],
        ["show", "1"],
        ["update", "1", "--title", "x"],
        ["move", "1", "in_progress"],
        ["delete", "1"],
    ],
)
def test_as16_corrupt_file_is_a_storage_error_for_every_command(file, arguments):
    file.write_bytes(b"{ this is not a task store")
    assert_failure(run_cli(*arguments, file=file), "storage", 5)
    assert file.read_bytes() == b"{ this is not a task store"


@pytest.mark.parametrize(
    "arguments",
    [
        [],
        ["frobnicate"],
        ["add"],
        ["show"],
        ["show", "abc"],
        ["show", "0"],
        ["show", "1.5"],
        ["move", "1"],
        ["delete", "abc"],
        ["list", "--sort", "title"],
        ["list", "--unknown-option"],
    ],
)
def test_fr015_usage_errors_follow_the_validation_error_contract(file, arguments):
    assert_failure(run_cli(*arguments, file=file), "validation", 2)
    assert not file.exists()


@pytest.mark.parametrize("value", ["²", "٣"])
def test_fr015_non_ascii_digit_id_is_a_validation_error_not_a_crash(file, value):
    assert_success(run_cli("add", "Buy milk", file=file))
    before = snapshot(file)
    assert_failure(run_cli("show", value, file=file), "validation", 2)
    assert snapshot(file) == before


def test_contract_data_file_from_environment_variable(tmp_path):
    target = tmp_path / "from-env.json"
    assert_success(run_cli("add", "Buy milk", cwd=tmp_path, extra_env={"TODO_FILE": str(target)}))
    assert target.exists()
    assert not (tmp_path / "tasks.json").exists()


def test_contract_default_data_file_is_tasks_json_in_current_folder(tmp_path):
    assert_success(run_cli("add", "Buy milk", cwd=tmp_path))
    assert (tmp_path / "tasks.json").exists()


def test_contract_file_option_wins_over_environment_variable(tmp_path, file):
    other = tmp_path / "other.json"
    assert_success(run_cli("add", "Buy milk", file=file, extra_env={"TODO_FILE": str(other)}))
    assert file.exists()
    assert not other.exists()


def test_sc004_create_and_see_a_task_in_two_commands(file):
    assert_success(run_cli("add", "Buy milk", file=file))
    assert [task["title"] for task in assert_success(run_cli("list", file=file))] == ["Buy milk"]


# --- User Story 2: move, update, delete ---------------------------------------

def test_as21_move_through_allowed_statuses(file):
    assert_success(run_cli("add", "Buy milk", file=file))
    assert assert_success(run_cli("move", "1", "in_progress", file=file))["status"] == "in_progress"
    assert assert_success(run_cli("move", "1", "done", file=file))["status"] == "done"
    assert assert_success(run_cli("show", "1", file=file))["status"] == "done"


def test_as22_disallowed_move_is_an_invalid_transition(file):
    assert_success(run_cli("add", "Buy milk", file=file))
    before = snapshot(file)
    assert_failure(run_cli("move", "1", "done", file=file), "invalid_transition", 4)
    assert_failure(run_cli("move", "1", "todo", file=file), "invalid_transition", 4)
    assert snapshot(file) == before


def test_as22_done_is_final(file):
    assert_success(run_cli("add", "Buy milk", file=file))
    assert_success(run_cli("move", "1", "in_progress", file=file))
    assert_success(run_cli("move", "1", "done", file=file))
    before = snapshot(file)
    for target in ("todo", "in_progress", "done"):
        assert_failure(run_cli("move", "1", target, file=file), "invalid_transition", 4)
    assert snapshot(file) == before


def test_as26_move_back_to_todo(file):
    assert_success(run_cli("add", "Buy milk", file=file))
    assert_success(run_cli("move", "1", "in_progress", file=file))
    assert assert_success(run_cli("move", "1", "todo", file=file))["status"] == "todo"


def test_as27_unknown_status_is_a_validation_error(file):
    assert_success(run_cli("add", "Buy milk", file=file))
    before = snapshot(file)
    assert_failure(run_cli("move", "1", "started", file=file), "validation", 2)
    assert snapshot(file) == before


def test_as23_update_changes_only_supplied_fields(file):
    assert_success(run_cli("add", "Buy milk", "--priority", "low", "--tag", "home", file=file))
    updated = assert_success(run_cli("update", "1", "--title", "Buy oat milk", file=file))
    assert updated == {
        "id": 1,
        "priority": "low",
        "status": "todo",
        "tags": ["home"],
        "title": "Buy oat milk",
    }
    updated = assert_success(run_cli("update", "1", "--priority", "high", file=file))
    assert (updated["priority"], updated["tags"], updated["title"]) == (
        "high",
        ["home"],
        "Buy oat milk",
    )


def test_contract_update_tag_replaces_and_clear_tags_empties(file):
    assert_success(run_cli("add", "Buy milk", "--tag", "home", file=file))
    updated = assert_success(run_cli("update", "1", "--tag", "Shop", "--tag", "urgent", file=file))
    assert updated["tags"] == ["shop", "urgent"]
    assert assert_success(run_cli("update", "1", "--clear-tags", file=file))["tags"] == []


@pytest.mark.parametrize(
    "arguments",
    [
        ["update", "1"],
        ["update", "1", "--tag", "a", "--clear-tags"],
        ["update", "1", "--title", ""],
        ["update", "1", "--priority", "urgent"],
        ["update", "1", "--tag", "bad tag"],
    ],
)
def test_as25_invalid_update_is_a_validation_error_and_changes_nothing(file, arguments):
    assert_success(run_cli("add", "Buy milk", "--tag", "home", file=file))
    before = snapshot(file)
    assert_failure(run_cli(*arguments, file=file), "validation", 2)
    assert snapshot(file) == before


def test_as24_delete_prints_deleted_id_and_id_is_not_reused(file):
    assert_success(run_cli("add", "One", file=file))
    assert_success(run_cli("add", "Two", file=file))
    assert assert_success(run_cli("delete", "1", file=file)) == {"deleted": 1}
    assert_failure(run_cli("show", "1", file=file), "not_found", 3)
    assert assert_success(run_cli("add", "Three", file=file))["id"] == 3
    assert ids(assert_success(run_cli("list", file=file))) == [2, 3]


@pytest.mark.parametrize(
    "arguments",
    [["update", "99", "--title", "x"], ["move", "99", "in_progress"], ["delete", "99"]],
)
def test_edge_changing_a_missing_task_is_not_found(file, arguments):
    assert_success(run_cli("add", "Buy milk", file=file))
    before = snapshot(file)
    assert_failure(run_cli(*arguments, file=file), "not_found", 3)
    assert snapshot(file) == before


def test_contract_error_precedence(file):
    assert_success(run_cli("add", "Buy milk", file=file))
    # rule 3 before rule 4: invalid value is reported even though the task is missing
    assert_failure(run_cli("move", "99", "started", file=file), "validation", 2)
    # rule 4 before rule 5: missing task is reported before the transition is checked
    assert_failure(run_cli("move", "99", "done", file=file), "not_found", 3)
    file.write_bytes(b"corrupt")
    # rule 1 before rule 2: usage error is reported without reading the file
    assert_failure(run_cli("show", "abc", file=file), "validation", 2)
    # rule 2 before rule 3: the file is loaded before field values are validated
    assert_failure(run_cli("add", "", file=file), "storage", 5)
    assert file.read_bytes() == b"corrupt"


# --- User Story 3: filter and sort --------------------------------------------

@pytest.fixture
def mixed(file):
    assert_success(run_cli("add", "One", "--priority", "low", "--tag", "home", file=file))
    assert_success(run_cli("add", "Two", "--priority", "high", "--tag", "work", file=file))
    assert_success(
        run_cli("add", "Three", "--priority", "medium", "--tag", "home", "--tag", "urgent",
                file=file)
    )
    assert_success(run_cli("add", "Four", "--priority", "high", file=file))
    return file


def test_as31_as32_filter_by_tag_ignores_case(mixed):
    assert ids(assert_success(run_cli("list", "--tag", "home", file=mixed))) == [1, 3]
    assert ids(assert_success(run_cli("list", "--tag", "HOME", file=mixed))) == [1, 3]


def test_as36_several_tags_must_all_match(mixed):
    result = run_cli("list", "--tag", "home", "--tag", "urgent", file=mixed)
    assert ids(assert_success(result)) == [3]


def test_as33_as37_sort_order(mixed):
    assert ids(assert_success(run_cli("list", file=mixed))) == [1, 2, 3, 4]
    assert ids(assert_success(run_cli("list", "--sort", "id", file=mixed))) == [1, 2, 3, 4]
    assert ids(assert_success(run_cli("list", "--sort", "priority", file=mixed))) == [2, 4, 3, 1]


def test_as34_filter_by_status(mixed):
    assert_success(run_cli("move", "2", "in_progress", file=mixed))
    assert_success(run_cli("move", "2", "done", file=mixed))
    assert ids(assert_success(run_cli("list", "--status", "done", file=mixed))) == [2]
    assert ids(assert_success(run_cli("list", "--status", "todo", file=mixed))) == [1, 3, 4]


def test_as35_no_match_is_an_empty_list(mixed):
    assert assert_success(run_cli("list", "--tag", "nothing", file=mixed)) == []
    assert assert_success(run_cli("list", "--status", "done", file=mixed)) == []


def test_fr011_invalid_filter_values_are_validation_errors(mixed):
    assert_failure(run_cli("list", "--status", "started", file=mixed), "validation", 2)
    assert_failure(run_cli("list", "--tag", "bad tag", file=mixed), "validation", 2)


def test_list_does_not_modify_the_data_file(mixed):
    before = snapshot(mixed)
    assert_success(run_cli("list", "--sort", "priority", "--tag", "home", file=mixed))
    assert snapshot(mixed) == before


# --- SC-002: determinism ------------------------------------------------------

SEQUENCE = [
    ["add", "Buy milk", "--priority", "high", "--tag", "Home"],
    ["add", "Write report", "--tag", "work", "--tag", "Q4-2026"],
    ["add", "Café ☕"],
    ["move", "1", "in_progress"],
    ["move", "1", "done"],
    ["move", "2", "done"],
    ["update", "2", "--title", "Write the report", "--priority", "low"],
    ["delete", "3"],
    ["show", "3"],
    ["add", "Call bank"],
    ["list"],
    ["list", "--sort", "priority"],
    ["list", "--tag", "work", "--status", "todo"],
]


def test_sc002_same_commands_give_identical_output_and_file(tmp_path):
    transcripts = []
    files = []
    for name in ("first.json", "second.json"):
        target = tmp_path / name
        transcript = []
        for arguments in SEQUENCE:
            result = run_cli(*arguments, file=target)
            transcript.append((result.returncode, result.stdout, result.stderr))
        transcripts.append(transcript)
        files.append(target.read_bytes())
    assert transcripts[0] == transcripts[1]
    assert files[0] == files[1]
    assert [code for code, _, _ in transcripts[0]] == [0, 0, 0, 0, 0, 4, 0, 0, 3, 0, 0, 0, 0]
