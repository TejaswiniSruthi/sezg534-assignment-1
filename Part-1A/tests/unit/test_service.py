"""Task operations (T009, T014, T018). Each test cites its acceptance scenario."""

import pytest
from todo.errors import (
    InvalidTransitionError,
    NotFoundError,
    StorageError,
    ValidationError,
)
from todo.service import TaskService


@pytest.fixture
def path(tmp_path):
    return tmp_path / "tasks.json"


@pytest.fixture
def service(path):
    return TaskService(path)


def snapshot(path):
    return path.read_bytes() if path.exists() else None


def ids(tasks):
    return [task.id for task in tasks]


# --- User Story 1 -------------------------------------------------------------

def test_as11_first_task_gets_id_1_and_defaults(service):
    task = service.create_task("Buy milk")
    assert task.to_dict() == {
        "id": 1,
        "title": "Buy milk",
        "priority": "medium",
        "status": "todo",
        "tags": [],
    }


def test_as12_second_task_gets_id_2_with_normalised_tags(service):
    service.create_task("Buy milk")
    task = service.create_task("Pay rent", priority="high", tags=["Home", "bills"])
    assert task.to_dict() == {
        "id": 2,
        "title": "Pay rent",
        "priority": "high",
        "status": "todo",
        "tags": ["bills", "home"],
    }


def test_as13_tasks_are_still_there_in_a_new_service(service, path):
    first = service.create_task("Buy milk")
    second = service.create_task("Pay rent", priority="high", tags=["home"])
    reopened = TaskService(path)
    assert [task.to_dict() for task in reopened.list_tasks()] == [
        first.to_dict(),
        second.to_dict(),
    ]


def test_as14_view_returns_exactly_that_task(service):
    service.create_task("Buy milk")
    service.create_task("Pay rent")
    assert service.get_task(2).title == "Pay rent"


def test_as14_view_of_missing_task_is_not_found_and_changes_nothing(service, path):
    service.create_task("Buy milk")
    before = snapshot(path)
    with pytest.raises(NotFoundError):
        service.get_task(99)
    assert snapshot(path) == before


@pytest.mark.parametrize(
    "arguments",
    [
        {"title": ""},
        {"title": "   "},
        {"title": "x" * 101},
        {"title": "ok", "priority": "urgent"},
        {"title": "ok", "tags": ["bad tag"]},
        {"title": "ok", "tags": [f"t{number}" for number in range(11)]},
    ],
)
def test_as15_invalid_create_is_rejected_and_store_is_unchanged(service, path, arguments):
    service.create_task("Existing")
    before = snapshot(path)
    with pytest.raises(ValidationError):
        service.create_task(**arguments)
    assert snapshot(path) == before
    assert ids(service.list_tasks()) == [1]


def test_as15_invalid_create_on_empty_store_does_not_create_the_file(service, path):
    with pytest.raises(ValidationError):
        service.create_task("")
    assert not path.exists()


def test_as17_listing_with_no_file_returns_empty_list(service):
    assert service.list_tasks() == []


def test_as16_every_operation_on_a_corrupt_file_is_a_storage_error(service, path):
    path.write_text("corrupt", encoding="utf-8")
    operations = [
        lambda: service.create_task("Buy milk"),
        lambda: service.get_task(1),
        lambda: service.list_tasks(),
        lambda: service.update_task(1, title="x"),
        lambda: service.move_task(1, "in_progress"),
        lambda: service.delete_task(1),
    ]
    for operation in operations:
        with pytest.raises(StorageError):
            operation()
        assert path.read_text(encoding="utf-8") == "corrupt"


# --- User Story 2 -------------------------------------------------------------

def test_as21_task_moves_todo_to_in_progress_to_done(service, path):
    service.create_task("Buy milk")
    assert service.move_task(1, "in_progress").status == "in_progress"
    assert service.move_task(1, "done").status == "done"
    assert TaskService(path).get_task(1).status == "done"


@pytest.mark.parametrize(
    ("moves_to_reach_state", "target"),
    [
        ([], "todo"),
        ([], "done"),
        (["in_progress"], "in_progress"),
        (["in_progress", "done"], "todo"),
        (["in_progress", "done"], "in_progress"),
        (["in_progress", "done"], "done"),
    ],
)
def test_as22_disallowed_transition_is_rejected_and_task_unchanged(
    service, path, moves_to_reach_state, target
):
    service.create_task("Buy milk")
    for status in moves_to_reach_state:
        service.move_task(1, status)
    before = snapshot(path)
    status_before = service.get_task(1).status
    with pytest.raises(InvalidTransitionError):
        service.move_task(1, target)
    assert snapshot(path) == before
    assert service.get_task(1).status == status_before


def test_as26_in_progress_task_can_be_moved_back_to_todo(service):
    service.create_task("Buy milk")
    service.move_task(1, "in_progress")
    assert service.move_task(1, "todo").status == "todo"


def test_as27_unknown_status_is_a_validation_error_and_task_unchanged(service, path):
    service.create_task("Buy milk")
    before = snapshot(path)
    with pytest.raises(ValidationError):
        service.move_task(1, "started")
    assert snapshot(path) == before


def test_as23_update_changes_only_the_supplied_fields(service, path):
    service.create_task("Buy milk", priority="low", tags=["home"])
    service.move_task(1, "in_progress")
    updated = service.update_task(1, title="  Buy oat milk ")
    assert updated.to_dict() == {
        "id": 1,
        "title": "Buy oat milk",
        "priority": "low",
        "status": "in_progress",
        "tags": ["home"],
    }
    updated = service.update_task(1, priority="high")
    assert (updated.title, updated.priority, updated.tags) == ("Buy oat milk", "high", ["home"])
    updated = service.update_task(1, tags=["Shop", "urgent"])
    assert (updated.title, updated.priority, updated.tags) == (
        "Buy oat milk",
        "high",
        ["shop", "urgent"],
    )
    assert TaskService(path).get_task(1).to_dict() == updated.to_dict()


def test_as23_update_with_empty_tags_clears_them(service):
    service.create_task("Buy milk", tags=["home"])
    assert service.update_task(1, tags=[]).tags == []


def test_fr009_update_with_no_field_is_a_validation_error(service, path):
    service.create_task("Buy milk")
    before = snapshot(path)
    with pytest.raises(ValidationError):
        service.update_task(1)
    assert snapshot(path) == before


@pytest.mark.parametrize(
    "changes",
    [{"title": ""}, {"title": "x" * 101}, {"priority": "urgent"}, {"tags": ["bad tag"]}],
)
def test_as25_invalid_update_is_rejected_and_task_unchanged(service, path, changes):
    service.create_task("Buy milk", priority="low", tags=["home"])
    before = snapshot(path)
    with pytest.raises(ValidationError):
        service.update_task(1, **changes)
    assert snapshot(path) == before


def test_as24_deleted_task_is_gone_and_its_id_is_never_reused(service, path):
    service.create_task("One")
    service.create_task("Two")
    assert service.delete_task(1) == 1
    with pytest.raises(NotFoundError):
        service.get_task(1)
    assert service.create_task("Three").id == 3
    assert ids(TaskService(path).list_tasks()) == [2, 3]


def test_fr005_id_is_not_reused_after_deleting_the_newest_task(service):
    service.create_task("One")
    service.create_task("Two")
    service.delete_task(2)
    assert service.create_task("Three").id == 3


@pytest.mark.parametrize("operation", ["update", "move", "delete"])
def test_edge_changing_a_missing_task_is_not_found_and_changes_nothing(service, path, operation):
    service.create_task("Buy milk")
    before = snapshot(path)
    with pytest.raises(NotFoundError):
        if operation == "update":
            service.update_task(99, title="x")
        elif operation == "move":
            service.move_task(99, "in_progress")
        else:
            service.delete_task(99)
    assert snapshot(path) == before


def test_contract_precedence_invalid_value_is_reported_before_not_found(service):
    service.create_task("Buy milk")
    with pytest.raises(ValidationError):
        service.move_task(99, "started")
    with pytest.raises(ValidationError):
        service.update_task(99, priority="urgent")


# --- User Story 3 -------------------------------------------------------------

@pytest.fixture
def tagged(service):
    service.create_task("One", tags=["home"])
    service.create_task("Two", tags=["work"])
    service.create_task("Three", tags=["home", "urgent"])
    return service


def test_as31_filter_by_one_tag(tagged):
    assert ids(tagged.list_tasks(tags=["home"])) == [1, 3]


def test_as32_tag_filter_is_case_insensitive(tagged):
    assert ids(tagged.list_tasks(tags=["HOME"])) == [1, 3]


def test_as36_several_tags_must_all_be_present(tagged):
    assert ids(tagged.list_tasks(tags=["home", "urgent"])) == [3]
    assert ids(tagged.list_tasks(tags=["home", "work"])) == []


def test_as33_priority_sort_is_high_medium_low_then_id(service):
    service.create_task("One", priority="low")
    service.create_task("Two", priority="high")
    service.create_task("Three", priority="medium")
    service.create_task("Four", priority="high")
    assert ids(service.list_tasks(sort="priority")) == [2, 4, 3, 1]


def test_as37_default_order_is_ascending_id(service):
    service.create_task("One", priority="low")
    service.create_task("Two", priority="high")
    assert ids(service.list_tasks()) == [1, 2]
    assert ids(service.list_tasks(sort="id")) == [1, 2]


def test_as34_filter_by_status(service):
    service.create_task("One")
    service.create_task("Two")
    service.create_task("Three")
    service.move_task(2, "in_progress")
    service.move_task(2, "done")
    service.move_task(3, "in_progress")
    assert ids(service.list_tasks(status="done")) == [2]
    assert ids(service.list_tasks(status="in_progress")) == [3]
    assert ids(service.list_tasks(status="todo")) == [1]


def test_fr011_tag_and_status_filters_must_both_match(tagged):
    tagged.move_task(3, "in_progress")
    assert ids(tagged.list_tasks(tags=["home"], status="in_progress")) == [3]
    assert ids(tagged.list_tasks(tags=["work"], status="in_progress")) == []


def test_fr011_fr012_filter_and_priority_sort_combine(service):
    service.create_task("One", priority="low", tags=["home"])
    service.create_task("Two", priority="high", tags=["work"])
    service.create_task("Three", priority="high", tags=["home"])
    assert ids(service.list_tasks(tags=["home"], sort="priority")) == [3, 1]


def test_as35_filter_with_no_match_returns_empty_list(tagged):
    assert tagged.list_tasks(tags=["nothing"]) == []
    assert tagged.list_tasks(status="done") == []


@pytest.mark.parametrize(
    "arguments",
    [{"tags": ["bad tag"]}, {"status": "started"}, {"sort": "title"}, {"sort": "PRIORITY"}],
)
def test_fr011_invalid_filter_or_sort_is_a_validation_error(tagged, arguments):
    with pytest.raises(ValidationError):
        tagged.list_tasks(**arguments)
