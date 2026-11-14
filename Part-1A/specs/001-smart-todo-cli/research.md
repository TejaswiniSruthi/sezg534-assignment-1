# Research: Smart Todo & Task CLI

## R1. Interface: CLI rather than HTTP API

- **Decision**: Command-line interface run as `python -m todo`.
- **Rationale**: The problem statement allows "CLI/API". A CLI needs no server, port or framework,
  so it meets the "0 third-party runtime dependencies" constraint and each command is one
  deterministic process with an exit code that tests can assert exactly.
- **Alternatives considered**: HTTP API with `http.server` (more code, ports in tests, no added
  requirement coverage); FastAPI/Flask (violates Principle VI).

## R2. Persistence format and atomic writes

- **Decision**: One UTF-8 JSON document `{"next_id": N, "tasks": [...]}`, written with sorted keys
  and 2-space indent to a temporary file in the same directory, then `os.replace` onto the target.
- **Rationale**: `next_id` stored in the file guarantees ids are never reused after deletion
  (FR-005). Replace-after-write means a failed write cannot leave a half-written file (FR-016).
  Sorted keys make the file content deterministic (Principle II).
- **Alternatives considered**: SQLite (heavier than needed, not "JSON persistence"); deriving the
  next id from `max(id)+1` (would reuse the id of a deleted last task, breaking FR-005).

## R3. Corrupt data file

- **Decision**: On load, parse JSON and validate the whole document against the data model. Any
  failure raises a storage error; the file is never opened for writing in that run (FR-014).
- **Rationale**: Clarification answer of 2026-11-14: stop and leave the file untouched.
- **Alternatives considered**: Back up and start empty (rejected by the human owner).

## R4. Error reporting

- **Decision**: Four exception classes sharing one base, each carrying a category string and an exit
  code: validation=2, not_found=3, invalid_transition=4, storage=5. Errors go to stderr as one JSON
  line; stdout stays empty.
- **Rationale**: FR-015 needs categories a program can distinguish without reading message text;
  exit codes and a `category` field both satisfy that.
- **Alternatives considered**: A single exit code 1 with text messages (not machine-distinguishable).

## R5. Argument parsing

- **Decision**: `argparse` with a parser subclass whose `error()` raises the validation error, so
  usage mistakes follow the same JSON error contract. Field values (priority, status, tags, title)
  are validated in `models.py`, not with `argparse` `choices`.
- **Rationale**: Keeps one validation path for FR-002…FR-004 and one error format for FR-015.
- **Alternatives considered**: `argparse` defaults (prints usage text and exits 2 with a non-JSON
  message, which breaks the error contract).

## R6. Harness tools

- **Decision**: Ruff for syntax and lint (G1), Bandit for SAST (G2), pytest for tests (G3), all
  driven by `.harness/run_harness.py`, which records JSON results and captured output.
- **Rationale**: Named or implied by the assignment for Python; each has machine-readable output
  that gives an unambiguous pass/fail.
- **Alternatives considered**: flake8 + pylint (slower, two tools for one gate); Semgrep (needs
  network rule download).
