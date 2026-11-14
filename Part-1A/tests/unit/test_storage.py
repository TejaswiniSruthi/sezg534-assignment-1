"""JSON persistence (T008): FR-013, FR-014, FR-016."""

import json

import pytest

from todo.errors import StorageError
from todo.models import Task
from todo.storage import Store, load_store, save_store

TASK = {"id": 1, "priority": "medium", "status": "todo", "tags": [], "title": "Buy milk"}


def test_fr013_as17_missing_file_is_an_empty_store_and_is_not_created(tmp_path):
    path = tmp_path / "tasks.json"
    store = load_store(path)
    assert store.next_id == 1
    assert store.tasks == []
    assert not path.exists()


def test_fr013_as13_saved_store_is_loaded_back_identically(tmp_path):
    path = tmp_path / "tasks.json"
    tasks = [
        Task(id=1, title="Buy milk", priority="medium", status="todo", tags=[]),
        Task(id=3, title="Pay rent", priority="high", status="done", tags=["bills", "home"]),
    ]
    save_store(path, Store(next_id=4, tasks=tasks))
    loaded = load_store(path)
    assert loaded.next_id == 4
    assert [task.to_dict() for task in loaded.tasks] == [task.to_dict() for task in tasks]


def test_contract_file_format_is_sorted_two_space_json(tmp_path):
    path = tmp_path / "tasks.json"
    task = Task(id=1, title="Buy milk", priority="medium", status="todo", tags=[])
    save_store(path, Store(next_id=2, tasks=[task]))
    text = path.read_text(encoding="utf-8")
    expected = json.dumps({"next_id": 2, "tasks": [TASK]}, indent=2, sort_keys=True)
    assert text.rstrip("\n") == expected


def test_fr016_save_leaves_no_temporary_file(tmp_path):
    path = tmp_path / "tasks.json"
    save_store(path, Store(next_id=1, tasks=[]))
    save_store(path, Store(next_id=1, tasks=[]))
    assert [item.name for item in tmp_path.iterdir()] == ["tasks.json"]


def test_fr013_non_ascii_title_survives_a_round_trip(tmp_path):
    path = tmp_path / "tasks.json"
    task = Task(id=1, title="Café ☕ बैठक", priority="low", status="todo", tags=[])
    save_store(path, Store(next_id=2, tasks=[task]))
    assert load_store(path).tasks[0].title == "Café ☕ बैठक"


CORRUPT_DOCUMENTS = {
    "not_json": "this is not json",
    "empty_file": "",
    "top_level_list": "[]",
    "missing_next_id": json.dumps({"tasks": []}),
    "missing_tasks": json.dumps({"next_id": 1}),
    "tasks_not_a_list": json.dumps({"next_id": 1, "tasks": {}}),
    "next_id_not_integer": json.dumps({"next_id": "2", "tasks": [TASK]}),
    "next_id_not_above_ids": json.dumps({"next_id": 1, "tasks": [TASK]}),
    "duplicate_ids": json.dumps({"next_id": 5, "tasks": [TASK, TASK]}),
    "invalid_priority": json.dumps({"next_id": 2, "tasks": [{**TASK, "priority": "urgent"}]}),
    "invalid_status": json.dumps({"next_id": 2, "tasks": [{**TASK, "status": "started"}]}),
    "empty_title": json.dumps({"next_id": 2, "tasks": [{**TASK, "title": ""}]}),
    "tags_not_a_list": json.dumps({"next_id": 2, "tasks": [{**TASK, "tags": "home"}]}),
    "missing_field": json.dumps({"next_id": 2, "tasks": [{"id": 1, "title": "x"}]}),
    "task_not_an_object": json.dumps({"next_id": 2, "tasks": ["Buy milk"]}),
    "id_not_positive": json.dumps({"next_id": 2, "tasks": [{**TASK, "id": 0}]}),
}


@pytest.mark.parametrize("name", sorted(CORRUPT_DOCUMENTS))
def test_fr014_as16_corrupt_file_is_a_storage_error_and_is_untouched(tmp_path, name):
    path = tmp_path / "tasks.json"
    original = CORRUPT_DOCUMENTS[name].encode("utf-8")
    path.write_bytes(original)
    with pytest.raises(StorageError):
        load_store(path)
    assert path.read_bytes() == original


def test_fr014_invalid_utf8_is_a_storage_error(tmp_path):
    path = tmp_path / "tasks.json"
    path.write_bytes(b"\xff\xfe\x00broken")
    with pytest.raises(StorageError):
        load_store(path)
    assert path.read_bytes() == b"\xff\xfe\x00broken"


def test_fr014_path_that_is_a_directory_is_a_storage_error(tmp_path):
    with pytest.raises(StorageError):
        load_store(tmp_path)


def test_fr016_save_into_missing_folder_is_a_storage_error(tmp_path):
    path = tmp_path / "no-such-folder" / "tasks.json"
    with pytest.raises(StorageError):
        save_store(path, Store(next_id=1, tasks=[]))
    assert not path.exists()
