# Agent Contract

## Library

`ReminderAgent(client)` where `client.generate(system_text: str, user_text: str) -> str` returns the
model's reply text or raises `ServiceError`.

`ReminderAgent.parse(message: str, now: datetime) -> Outcome`

- `Outcome.result`: dict satisfying the Output Schema Contract (always).
- `Outcome.source`: `"model"`, `"precheck"` or `"fallback"`.
- `Outcome.raw_reply`: model text or `None`.
- `Outcome.violations`: list of strings such as `"INV-7"`, `"not-json"`.
- Raises `ServiceError` when the model service fails (FR-016). It never returns a made-up result.

Order of processing:
1. Pre-check (FR-013): empty, white-space only, or longer than 500 characters → unknown result,
   `source="precheck"`, no model call.
2. Build instructions (`prompts/system_prompt.md` + reference moment + calendar) and call the model.
3. Parse the reply (`parser.extract_json`). Failure → fallback.
4. Validate (`validator.find_violations(result, now)`). Any violation → fallback.
5. Return the accepted result, `source="model"`.

## Deterministic functions (unit-tested)

- `parser.extract_json(text: str) -> dict` — raises `ValueError` unless the text is exactly one JSON
  object, optionally wrapped in a Markdown code fence.
- `validator.find_violations(result: object, now: datetime) -> list[str]` — returns rule ids
  (`INV-1` … `INV-9`); empty list means valid.
- `prompt.build_system_prompt(now: datetime) -> str` — contains the instructions, the leak marker,
  the reference moment and a 15-day calendar.
- `schema.unknown_result() -> dict` — a fresh copy of the unknown result.

## CLI

`python -m reminder_agent "MESSAGE" [--now YYYY-MM-DDTHH:MM]`

| Outcome | stdout | stderr | exit code |
|---------|--------|--------|-----------|
| result (any intent) | one line of JSON, the contract object | empty | 0 |
| service failure | empty | `{"error": {"category": "service", "message": "..."}}` | 3 |
| bad usage / configuration (no key, bad `--now`) | empty | `{"error": {"category": "usage", ...}}` | 2 |

## Configuration

| Name | Meaning | Default |
|------|---------|---------|
| `GEMINI_API_KEY` | API key (environment, or a `.env` file in this folder or a parent) | required |
| `GEMINI_MODEL` | model name | newest general-purpose flash model reported by the API |
| `GEMINI_TEMPERATURE` | sampling temperature | `0` |

The key is never written to stdout, stderr, logs or result files.
