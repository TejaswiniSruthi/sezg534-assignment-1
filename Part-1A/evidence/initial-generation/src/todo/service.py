"""Task operations: create, read, update, move, delete, filter and sort."""

from pathlib import Path
from typing import Iterable

from todo.errors import NotFoundError, ValidationError
from todo.models import (
    PRIORITIES,
    Task,
    check_transition,
    normalise_tags,
    validate_priority,
    validate_status,
    validate_title,
)
from todo.storage import Store, load_store, save_store

SORT_KEYS = ("id", "priority")


def _find(store: Store, task_id: int) -> Task:
    for task in store.tasks:
        if task.id == task_id:
            return task
    raise NotFoundError(f"no task with id {task_id}")


class TaskService:
    """Applies task operations to one data file."""

    def __init__(self, path: Path) -> None:
        """Remember which data file this service works on."""
        self.path = Path(path)

    def create_task(
        self, title: str, priority: str | None = None, tags: Iterable[str] = ()
    ) -> Task:
        """Create a task with the next id and status todo (FR-001, FR-005, FR-006)."""
        store = load_store(self.path)
        task = Task(
            id=store.next_id,
            title=validate_title(title),
            priority=validate_priority(priority),
            status="todo",
            tags=normalise_tags(tags),
        )
        store.tasks.append(task)
        store.next_id += 1
        save_store(self.path, store)
        return task

    def get_task(self, task_id: int) -> Task:
        """Return one task by id (FR-007)."""
        return _find(load_store(self.path), task_id)

    def list_tasks(
        self, tags: Iterable[str] = (), status: str | None = None, sort: str = "id"
    ) -> list[Task]:
        """Return tasks matching every filter, in the requested order (FR-011, FR-012)."""
        store = load_store(self.path)
        wanted = set(normalise_tags(tags))
        if status is not None:
            validate_status(status)
        if sort not in SORT_KEYS:
            raise ValidationError("sort must be one of id, priority")
        tasks = [
            task
            for task in store.tasks
            if wanted <= set(task.tags) and (status is None or task.status == status)
        ]
        if sort == "priority":
            tasks.sort(key=lambda task: (PRIORITIES.index(task.priority), task.id))
        return tasks

    def update_task(
        self,
        task_id: int,
        title: str | None = None,
        priority: str | None = None,
        tags: Iterable[str] | None = None,
    ) -> Task:
        """Change only the supplied fields of a task (FR-009)."""
        store = load_store(self.path)
        if title is None and priority is None and tags is None:
            raise ValidationError("nothing to update")
        new_title = validate_title(title) if title is not None else None
        new_priority = validate_priority(priority) if priority is not None else None
        new_tags = normalise_tags(tags) if tags is not None else None
        task = _find(store, task_id)
        if new_title is not None:
            task.title = new_title
        if new_priority is not None:
            task.priority = new_priority
        if new_tags is not None:
            task.tags = new_tags
        save_store(self.path, store)
        return task

    def move_task(self, task_id: int, status: str) -> Task:
        """Change a task's status along an allowed transition (FR-008)."""
        store = load_store(self.path)
        validate_status(status)
        task = _find(store, task_id)
        check_transition(task.status, status)
        task.status = status
        save_store(self.path, store)
        return task

    def delete_task(self, task_id: int) -> int:
        """Permanently remove a task and return its id (FR-010)."""
        store = load_store(self.path)
        task = _find(store, task_id)
        store.tasks.remove(task)
        save_store(self.path, store)
        return task.id
