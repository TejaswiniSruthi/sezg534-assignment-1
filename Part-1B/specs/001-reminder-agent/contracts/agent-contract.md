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
- `validator.find_violations(result: object, now: datetime, marker: str) -> list[str]` — returns
  rule ids (`INV-1` … `INV-9`); empty list means valid. A non-object is `["INV-1"]`.
- `prompt.build_system_prompt(now: datetime) -> str` — contains the instructions, the leak marker,
  the reference moment with its weekday, and a 15-day calendar (the reference date and the next 14
  days, each as `YYYY-MM-DD Weekday`).
- `prompt.leak_marker() -> str` — the marker found in `prompts/system_prompt.md`, shaped
  `RA-MARKER-` followed by 8 upper-case hexadecimal characters.
- `schema.unknown_result() -> dict` — a fresh copy of the unknown result.
- `config.read_env_file(path: Path) -> dict[str, str]` — `KEY=value` lines; blank lines and `#`
  comments ignored; surrounding quotes removed.
- `config.load_settings(environ: Mapping[str, str], start: Path) -> Settings` — values from
  `environ` win over a `.env` file found in `start` or any parent folder. `Settings` has `api_key`,
  `model` (`None` when unset) and `temperature` (default `0.0`); its `repr` never shows the key.
  A missing key or a non-numeric temperature raises `ServiceError`.
- `llm.choose_model(names: list[str]) -> str` — from names such as `models/gemini-3.8-flash`, picks
  the highest-versioned plain `gemini-<version>-flash`; raises `ServiceError` when there is none.
- `llm.GeminiClient(settings, transport=None)` — `transport(method, path, headers, body) -> dict`
  performs one HTTPS call and returns the decoded JSON, or raises `ServiceError`. `generate`
  returns the reply text; a reply with no candidate text (for example a safety block) returns `""`,
  which the agent turns into the unknown result. `GeminiClient.from_config()` builds a client from
  the process environment. Attributes `model` and `temperature` report what was used.
- Fallback violation ids for an unusable reply: `"not-json"`.

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
