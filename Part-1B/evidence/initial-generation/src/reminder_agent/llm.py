"""Gemini client over HTTPS using only the standard library (FR-016)."""

import http.client
import json
import os
import re
from collections.abc import Callable
from pathlib import Path

from reminder_agent.config import Settings, load_settings
from reminder_agent.errors import ServiceError

HOST = "generativelanguage.googleapis.com"
TIMEOUT_SECONDS = 60
FLASH_MODEL = re.compile(r"models/(gemini-(\d+)\.(\d+)-flash)")
SAFE_MODEL_NAME = re.compile(r"[A-Za-z0-9._-]+")

Transport = Callable[[str, str, dict, dict | None], dict]

__all__ = ["GeminiClient", "ServiceError", "choose_model"]


def https_transport(method: str, path: str, headers: dict, body: dict | None) -> dict:
    """Perform one HTTPS call to the Gemini API and return the decoded JSON."""
    payload = json.dumps(body).encode("utf-8") if body is not None else None
    connection = http.client.HTTPSConnection(HOST, timeout=TIMEOUT_SECONDS)
    try:
        connection.request(method, path, body=payload, headers=headers)
        response = connection.getresponse()
        text = response.read().decode("utf-8", errors="replace")
    except (OSError, http.client.HTTPException) as error:
        raise ServiceError(f"network error: {type(error).__name__}: {error}") from error
    finally:
        connection.close()
    if response.status >= 400:
        raise ServiceError(f"HTTP {response.status}: {_error_message(text)}")
    try:
        return json.loads(text)
    except ValueError as error:
        raise ServiceError("the model service returned a reply that is not JSON") from error


def _error_message(text: str) -> str:
    try:
        return str(json.loads(text)["error"]["message"])[:300]
    except (ValueError, KeyError, TypeError):
        return text[:300]


def choose_model(names: list[str]) -> str:
    """Pick the highest-versioned plain ``gemini-<version>-flash`` model."""
    best = None
    for name in names:
        match = FLASH_MODEL.fullmatch(name)
        if match is None:
            continue
        version = (int(match.group(2)), int(match.group(3)))
        if best is None or version > best[0]:
            best = (version, match.group(1))
    if best is None:
        raise ServiceError("no general-purpose flash model is available; set GEMINI_MODEL")
    return best[1]


def _reply_text(response: dict) -> str:
    candidates = response.get("candidates") or [{}]
    parts = (candidates[0].get("content") or {}).get("parts") or []
    return "".join(part.get("text", "") for part in parts if not part.get("thought"))


class GeminiClient:
    """Sends the instructions and the user's message to a Gemini model."""

    def __init__(self, settings: Settings, transport: Transport | None = None) -> None:
        """Keep the settings; ``transport`` can be replaced in tests."""
        self._settings = settings
        self._transport = transport or https_transport
        self.model = settings.model
        self.temperature = settings.temperature

    @classmethod
    def from_config(cls) -> "GeminiClient":
        """Build a client from the process environment and the nearest .env file."""
        return cls(load_settings(os.environ, Path.cwd()))

    def _headers(self) -> dict:
        return {"Content-Type": "application/json", "x-goog-api-key": self._settings.api_key}

    def _resolve_model(self) -> str:
        if self.model is None:
            listing = self._transport("GET", "/v1beta/models?pageSize=1000", self._headers(), None)
            names = [item.get("name", "") for item in listing.get("models", [])]
            self.model = choose_model(names)
        if not SAFE_MODEL_NAME.fullmatch(self.model):
            raise ServiceError("GEMINI_MODEL contains characters that are not allowed")
        return self.model

    def generate(self, system_text: str, user_text: str) -> str:
        """Return the model's reply text; an empty string when it gave no text."""
        model = self._resolve_model()
        body = {
            "systemInstruction": {"parts": [{"text": system_text}]},
            "contents": [{"role": "user", "parts": [{"text": user_text}]}],
            "generationConfig": {
                "temperature": self.temperature,
                "responseMimeType": "application/json",
            },
        }
        path = f"/v1beta/models/{model}:generateContent"
        return _reply_text(self._transport("POST", path, self._headers(), body))
