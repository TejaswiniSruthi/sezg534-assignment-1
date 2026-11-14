"""Errors raised by the agent."""


class ServiceError(Exception):
    """The model service or its configuration failed; no result was produced (FR-016)."""
