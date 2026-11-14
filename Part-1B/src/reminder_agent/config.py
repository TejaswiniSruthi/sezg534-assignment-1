"""Settings from the environment or a local .env file. The key is never displayed."""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from reminder_agent.errors import ServiceError

ENV_FILE = ".env"


@dataclass(frozen=True, repr=False)
class Settings:
    """Model access settings."""

    api_key: str
    model: str | None
    temperature: float

    def __repr__(self) -> str:
        """Describe the settings without revealing the API key."""
        return f"Settings(api_key=<hidden>, model={self.model!r}, temperature={self.temperature})"


def read_env_file(path: Path) -> dict[str, str]:
    """Read KEY=value lines, ignoring blank lines and comments."""
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#") or "=" not in text:
            continue
        key, value = text.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key.strip()] = value
    return values


def find_env_file(start: Path) -> Path | None:
    """Return the nearest .env file in ``start`` or one of its parent folders."""
    folder = start.resolve()
    for candidate in (folder, *folder.parents):
        path = candidate / ENV_FILE
        if path.is_file():
            return path
    return None


def load_settings(environ: Mapping[str, str], start: Path) -> Settings:
    """Build settings; values in ``environ`` win over the .env file."""
    path = find_env_file(start)
    values = read_env_file(path) if path else {}
    values.update(environ)
    api_key = values.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ServiceError("GEMINI_API_KEY is not set (environment variable or .env file)")
    try:
        temperature = float(values.get("GEMINI_TEMPERATURE", "0"))
    except ValueError as error:
        raise ServiceError("GEMINI_TEMPERATURE must be a number") from error
    model = values.get("GEMINI_MODEL", "").strip() or None
    return Settings(api_key=api_key, model=model, temperature=temperature)
