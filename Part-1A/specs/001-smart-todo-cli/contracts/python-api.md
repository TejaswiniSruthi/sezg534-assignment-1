# Internal Interface Contract (Python)

Added during planning so that unit tests (T005, T008, T009, T014, T018) can be written from the
design before any implementation exists (Constitution III).

## `todo.errors`

| Class | `category` | `exit_code` |
|-------|-----------|-------------|
| `TodoError(Exception)` | base class | — |
| `ValidationError(TodoError)` | `"validation"` | 2 |
| `NotFoundError(TodoError)` | `"not_found"` | 3 |
| `InvalidTransitionError(TodoError)` | `"invalid_transition"` | 4 |
| `StorageError(TodoError)` | `"storage"` | 5 |

`category` and `exit_code` are class attributes. `str(error)` is the human-readable message.

## `todo.models`

- `Task(id: int, title: str, priority: str, status: str, tags: list[str])` — dataclass;
  `to_dict()` returns a dict with exactly the keys `id`, `title`, `priority`, `status`, `tags`.
- `validate_title(title: str) -> str` — returns the trimmed title (FR-002).
- `validate_priority(priority: str | None) -> str` — `None` becomes `"medium"` (FR-003).
- `normalise_tags(tags: Iterable[str]) -> list[str]` — lower-case, unique, sorted (FR-004).
- `validate_status(status: str) -> str` (FR-008).
- `validate_id(value: str | int) -> int` — positive whole number.
- `check_transition(current: str, target: str) -> None` — raises `InvalidTransitionError` unless the
  move is allowed by the transition table in data-model.md.

All validators raise `ValidationError` on bad input.

## `todo.storage`

- `Store(next_id: int, tasks: list[Task])` — dataclass.
- `load_store(path: Path) -> Store` — missing file returns `Store(1, [])` and does not create the
  file; an unreadable or invalid file raises `StorageError`.
- `save_store(path: Path, store: Store) -> None` — atomic; raises `StorageError` on failure; leaves
  no temporary file behind.

## `todo.service`

`TaskService(path: Path)`; every method loads the store, applies the operation and, for a change,
saves it.

- `create_task(title: str, priority: str | None = None, tags: Iterable[str] = ()) -> Task`
- `get_task(task_id: int) -> Task`
- `list_tasks(tags: Iterable[str] = (), status: str | None = None, sort: str = "id") -> list[Task]`
- `update_task(task_id: int, title: str | None = None, priority: str | None = None, tags: Iterable[str] | None = None) -> Task`
  (`tags=None` means "leave unchanged"; an empty iterable clears the tags; all three `None` is a
  `ValidationError`)
- `move_task(task_id: int, status: str) -> Task`
- `delete_task(task_id: int) -> int` — returns the deleted id.
