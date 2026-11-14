# Implementation Plan: Smart Todo & Task CLI

**Branch**: `001-smart-todo-cli` | **Date**: 2026-11-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-smart-todo-cli/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

A single-user command-line task manager. Tasks (title, priority, tags, status) are created, read,
updated, deleted, filtered by tag/status and sorted by priority, and are saved in one local JSON
file. The design is a small layered Python package: pure validation and domain rules, a service
that applies operations to an in-memory store, a storage module that loads and atomically saves the
JSON file, and a thin CLI that maps arguments to service calls and service errors to exit codes.
All behaviour is deterministic so that every acceptance scenario becomes an exact assertion.

## Technical Context

**Language/Version**: Python 3.10+ (developed on 3.10, demonstrated on 3.12)

**Primary Dependencies**: None at runtime (standard library only: `argparse`, `json`, `os`,
`tempfile`, `dataclasses`, `re`)

**Storage**: One local JSON file (`--file PATH`, else `TODO_FILE`, else `./tasks.json`)

**Testing**: pytest (unit tests on the service/validation/storage; contract tests that run the CLI
as a subprocess and assert exit code, stdout and stderr)

**Target Platform**: Windows, Linux and macOS terminals

**Project Type**: cli

**Performance Goals**: Any command on a 1,000-task store completes in under 1 second

**Constraints**: Deterministic output; offline; no third-party runtime dependency; atomic writes;
cyclomatic complexity ≤ 10; line length ≤ 100

**Scale/Scope**: 1 user, up to 1,000 tasks, 6 commands, about 400 lines of production code

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | How the plan complies | Status |
|-----------|----------------------|--------|
| I. Specification is the source of truth | Every command and error in `contracts/cli-contract.md` cites its FR; no behaviour outside FR-001…FR-017 is planned | PASS |
| II. Deterministic behaviour | Sequential integer ids; no clock, randomness or network; total ordering defined for every list; JSON written with sorted keys | PASS |
| III. Tests derived from the specification | `tasks.md` schedules test tasks before implementation tasks; each test cites an AS/FR id | PASS |
| IV. Mandatory harness gates | `.harness/run_harness.py` runs Ruff (G1), Bandit (G2), pytest (G3); it does not import `src/` | PASS |
| V. Security and secrets | No `eval`/`exec`/`pickle`/`subprocess` in `src/`; one data file; validation before mutation; temp-file-then-replace writes | PASS |
| VI. Simplicity and maintainability | Standard library only; four small modules; complexity and line length enforced by Ruff | PASS |

Post-design re-check (after Phase 1): no violations; Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/001-smart-todo-cli/
├── plan.md              # This file
├── research.md          # Phase 0: decisions and alternatives
├── data-model.md        # Phase 1: Task, TaskStore, validation, state machine
├── quickstart.md        # Phase 1: how to run the tool and the harness
├── contracts/
│   └── cli-contract.md  # Phase 1: commands, output shapes, exit codes
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
Part-1A/
├── src/todo/
│   ├── __init__.py
│   ├── __main__.py      # python -m todo
│   ├── errors.py        # error categories and exit codes
│   ├── models.py        # Task, validation rules, status transitions
│   ├── service.py       # create / get / list / update / move / delete
│   ├── storage.py       # load, validate and atomically save the JSON file
│   └── cli.py           # argument parsing, JSON output, error → exit code
├── tests/
│   ├── unit/            # models, service, storage
│   └── contract/        # CLI contract (subprocess)
├── .harness/
│   ├── run_harness.py   # runs G1, G2, G3; writes results and feedback
│   ├── ruff.toml
│   └── bandit.yaml
├── evidence/
│   ├── initial-generation/
│   ├── final-generation/
│   ├── harness-results/
│   └── harness-log.md
├── requirements-dev.txt
└── pytest.ini
```

**Structure Decision**: Single project. Production code is one package under `src/todo/`; tests are
split into `tests/unit/` and `tests/contract/`; the harness is kept outside both, in `.harness/`,
so it stays independent of the implementation.

## Complexity Tracking

No constitution violations; nothing to justify.
