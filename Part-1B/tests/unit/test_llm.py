"""Gemini client (FR-016) with a fake transport; no network is used."""

import pytest
from reminder_agent.config import Settings
from reminder_agent.llm import GeminiClient, ServiceError, choose_model

SECRET = "test-key-not-real-123"


class FakeTransport:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, method, path, headers, body):
        self.calls.append({"method": method, "path": path, "headers": headers, "body": body})
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def reply(text):
    return {"candidates": [{"content": {"parts": [{"text": text}]}}]}


def test_generate_sends_one_request_and_returns_the_text():
    transport = FakeTransport(reply('{"intent": "unknown"}'))
    client = GeminiClient(Settings(SECRET, "gemini-test-flash", 0.0), transport)
    assert client.generate("SYSTEM RULES", "remind me") == '{"intent": "unknown"}'
    call = transport.calls[0]
    assert call["method"] == "POST"
    assert call["path"] == "/v1beta/models/gemini-test-flash:generateContent"
    assert call["headers"]["x-goog-api-key"] == SECRET
    assert SECRET not in call["path"]
    body = call["body"]
    assert body["systemInstruction"]["parts"][0]["text"] == "SYSTEM RULES"
    assert body["contents"] == [{"role": "user", "parts": [{"text": "remind me"}]}]
    assert body["generationConfig"]["temperature"] == 0.0
    assert body["generationConfig"]["responseMimeType"] == "application/json"
    assert client.model == "gemini-test-flash"
    assert client.temperature == 0.0


def test_text_parts_are_joined_and_thought_parts_are_ignored():
    response = {
        "candidates": [
            {"content": {"parts": [{"text": "thinking...", "thought": True}, {"text": "{"},
                                   {"text": "}"}]}}
        ]
    }
    client = GeminiClient(Settings(SECRET, "m", 0.0), FakeTransport(response))
    assert client.generate("s", "u") == "{}"


@pytest.mark.parametrize(
    "response",
    [
        {},
        {"candidates": []},
        {"promptFeedback": {"blockReason": "SAFETY"}},
        {"candidates": [{"finishReason": "SAFETY"}]},
        {"candidates": [{"content": {"parts": []}}]},
    ],
)
def test_reply_without_text_is_an_empty_string(response):
    client = GeminiClient(Settings(SECRET, "m", 0.0), FakeTransport(response))
    assert client.generate("s", "u") == ""


def test_fr016_transport_failure_is_a_service_error():
    transport = FakeTransport(ServiceError("HTTP 429: quota exceeded"))
    client = GeminiClient(Settings(SECRET, "m", 0.0), transport)
    with pytest.raises(ServiceError):
        client.generate("s", "u")


def test_model_is_chosen_from_the_api_when_not_configured():
    listing = {"models": [{"name": "models/gemini-3.6-flash"}, {"name": "models/gemini-3.8-flash"},
                          {"name": "models/gemini-3.8-flash-lite"}]}
    transport = FakeTransport(listing, reply("{}"))
    client = GeminiClient(Settings(SECRET, None, 0.0), transport)
    client.generate("s", "u")
    assert transport.calls[0]["method"] == "GET"
    assert transport.calls[0]["path"].startswith("/v1beta/models")
    assert transport.calls[1]["path"] == "/v1beta/models/gemini-3.8-flash:generateContent"
    assert client.model == "gemini-3.8-flash"


def test_choose_model_prefers_the_highest_plain_flash_version():
    names = [
        "models/gemini-2.5-flash",
        "models/gemini-3.8-flash-lite",
        "models/gemini-3.8-flash-tts",
        "models/gemini-10.0-flash",
        "models/gemini-3.8-pro",
        "models/gemini-3.8-flash",
        "models/embedding-001",
    ]
    assert choose_model(names) == "gemini-10.0-flash"


def test_choose_model_without_a_flash_model_is_a_service_error():
    with pytest.raises(ServiceError):
        choose_model(["models/embedding-001", "models/gemini-3.8-pro"])
