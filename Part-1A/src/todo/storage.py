"""Loading and atomic saving of the JSON data file (FR-013, FR-014, FR-016)."""

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from todo.errors import StorageError, ValidationError
from todo.models import PRIORITIES, STATUSES, Task, normalise_tags, validate_title

TASK_FIELDS = {"id", "title", "priority", "status", "tags"}


@dataclass
class Store:
    """All saved tasks plus the next id to assign."""

    next_id: int
    tasks: list[Task]


def _is_whole_number(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _parse_task(item: object) -> Task:
    if not isinstance(item, dict) or set(item) != TASK_FIELDS:
        raise StorageError("data file contains an invalid task")
    if not _is_whole_number(item["id"]) or item["id"] < 1:
        raise StorageError("data file contains an invalid task id")
    if item["priority"] not in PRIORITIES or item["status"] not in STATUSES:
        raise StorageError("data file contains an invalid priority or status")
    try:
        title_ok = validate_title(item["title"]) == item["title"]
        tags_ok = isinstance(item["tags"], list) and normalise_tags(item["tags"]) == item["tags"]
    except ValidationError as error:
        raise StorageError(f"data file contains an invalid task: {error}") from error
    if not title_ok or not tags_ok:
        raise StorageError("data file contains an invalid title or tags")
    return Task(item["id"], item["title"], item["priority"], item["status"], item["tags"])


def _parse_store(data: object) -> Store:
    if not isinstance(data, dict) or set(data) != {"next_id", "tasks"}:
        raise StorageError("data file is not a task store")
    if not _is_whole_number(data["next_id"]) or not isinstance(data["tasks"], list):
        raise StorageError("data file is not a task store")
    tasks = [_parse_task(item) for item in data["tasks"]]
    ids = [task.id for task in tasks]
    if ids != sorted(set(ids)):
        raise StorageError("data file has duplicate or unordered task ids")
    if data["next_id"] <= max(ids, default=0):
        raise StorageError("data file has an invalid next id")
    return Store(next_id=data["next_id"], tasks=tasks)


def load_store(path: Path) -> Store:
    """Load the store; a missing file is an empty store and is not created."""
    if not path.exists():
        return Store(next_id=1, tasks=[])
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise StorageError(f"data file cannot be read: {error}") from error
    return _parse_store(data)


def save_store(path: Path, store: Store) -> None:
    """Write the store to a temporary file, then replace the data file with it."""
    document = {"next_id": store.next_id, "tasks": [task.to_dict() for task in store.tasks]}
    text = json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", dir=path.parent, delete=False, encoding="utf-8", newline="\n", suffix=".tmp"
        ) as handle:
            temporary = handle.name
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except OSError as error:
        if temporary and os.path.exists(temporary):
            os.remove(temporary)
        raise StorageError(f"data file cannot be written: {error}") from error
