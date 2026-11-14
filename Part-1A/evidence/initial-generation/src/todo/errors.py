"""Error categories and exit codes (FR-015)."""


class TodoError(Exception):
    """Base class for every error the tool reports."""

    category = "error"
    exit_code = 1


class ValidationError(TodoError):
    """Input does not satisfy a validation rule."""

    category = "validation"
    exit_code = 2


class NotFoundError(TodoError):
    """No task has the requested id."""

    category = "not_found"
    exit_code = 3


class InvalidTransitionError(TodoError):
    """The requested status change is not allowed."""

    category = "invalid_transition"
    exit_code = 4


class StorageError(TodoError):
    """The data file is corrupt or cannot be read or written."""

    category = "storage"
    exit_code = 5
