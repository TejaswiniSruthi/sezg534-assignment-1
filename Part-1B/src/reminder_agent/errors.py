"""Errors raised by the agent."""


class ServiceError(Exception):
    """The model service or its configuration failed; no result was produced (FR-016)."""

    def __init__(
        self, message: str, retry_after: float | None = None, quota_id: str | None = None
    ) -> None:
        """Keep the message plus any retry hint and quota name the service gave."""
        super().__init__(message)
        self.retry_after = retry_after
        self.quota_id = quota_id

    @property
    def daily_quota(self) -> bool:
        """True when a per-day quota is used up, so retrying today cannot succeed."""
        return bool(self.quota_id) and "PerDay" in self.quota_id
