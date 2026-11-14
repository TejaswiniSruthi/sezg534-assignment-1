---

description: "Task list for Smart Todo & Task CLI"
---

# Tasks: Smart Todo & Task CLI

**Input**: Design documents from `/specs/001-smart-todo-cli/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cli-contract.md

**Tests**: Required. Constitution Principle III: tests are derived from the specification and are
written before the implementation task they cover.

**Organization**: Tasks are grouped by user story so each story can be implemented and tested
independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- All paths are relative to `Part-1A/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project skeleton and the independent harness

- [x] T001 Create folders `src/todo/`, `tests/unit/`, `tests/contract/`, `.harness/`, `evidence/`
- [x] T002 [P] Create `requirements-dev.txt` (ruff, bandit, pytest, pinned) and `pytest.ini` (pythonpath = src)
- [x] T003 [P] Create `.harness/ruff.toml` (line length 100, complexity ≤ 10, docstrings, type hints) and `.harness/bandit.yaml`
- [x] T004 Create `.harness/run_harness.py`: run G1 Ruff, G2 Bandit, G3 pytest; write JSON result and captured output to `evidence/harness-results/`; exit 0 only if all gates pass (Constitution IV)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Error categories and the Task model that every story uses

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T005 [P] Write validation tests in `tests/unit/test_models.py` for title, priority, tags, status, id (FR-002, FR-003, FR-004, AS-1.5)
- [x] T006 [P] Create `src/todo/errors.py`: base error plus validation (2), not_found (3), invalid_transition (4), storage (5) (FR-015)
- [x] T007 Create `src/todo/models.py`: `Task` dataclass, `validate_title`, `validate_priority`, `normalise_tags`, `validate_status`, transition table (FR-002…FR-004, FR-008; depends on T006)

**Checkpoint**: `tests/unit/test_models.py` passes

---

## Phase 3: User Story 1 - Capture and review tasks (Priority: P1) 🎯 MVP

**Goal**: Create, view and list tasks that persist between runs

**Independent Test**: Create two tasks, start a new process, list, and compare exact field values

### Tests for User Story 1

- [x] T008 [P] [US1] Storage tests in `tests/unit/test_storage.py`: missing file is empty, round trip, corrupt file raises storage error and is unchanged, file format (FR-013, FR-014, AS-1.3, AS-1.6, AS-1.7)
- [x] T009 [P] [US1] Service tests in `tests/unit/test_service.py` for create/get/list (FR-001, FR-005, FR-006, FR-007, AS-1.1, AS-1.2, AS-1.4, AS-1.5)
- [x] T010 [P] [US1] CLI contract tests in `tests/contract/test_cli_contract.py` for `add`, `show`, `list`: exit codes, stdout JSON shape, stderr error shape, persistence across processes (FR-015, FR-017, AS-1.1…AS-1.7)

### Implementation for User Story 1

- [x] T011 [US1] Create `src/todo/storage.py`: load + validate store, atomic save (FR-013, FR-014, FR-016; depends on T007)
- [x] T012 [US1] Create `src/todo/service.py` with `create_task`, `get_task`, `list_tasks` (FR-001, FR-005, FR-006, FR-007; depends on T011)
- [x] T013 [US1] Create `src/todo/cli.py` and `src/todo/__main__.py` with `add`, `show`, `list`, JSON output and error-to-exit-code mapping (FR-015, FR-017; depends on T012)

**Checkpoint**: User Story 1 works and its tests pass

---

## Phase 4: User Story 2 - Progress, edit and remove tasks (Priority: P2)

**Goal**: Status transitions, update and delete

**Independent Test**: Walk one task through every allowed and disallowed transition, edit it, delete it

### Tests for User Story 2

- [x] T014 [P] [US2] Service tests in `tests/unit/test_service.py` for every cell of the transition table, update, delete, id non-reuse, unchanged state after failure (FR-008, FR-009, FR-010, FR-016, AS-2.1…AS-2.7)
- [x] T015 [P] [US2] CLI contract tests in `tests/contract/test_cli_contract.py` for `move`, `update`, `delete` and error precedence (FR-008…FR-010, FR-015, FR-016)

### Implementation for User Story 2

- [x] T016 [US2] Add `move_task`, `update_task`, `delete_task` to `src/todo/service.py` (FR-008, FR-009, FR-010, FR-016)
- [x] T017 [US2] Add `move`, `update`, `delete` commands to `src/todo/cli.py` (FR-008…FR-010)

**Checkpoint**: User Stories 1 and 2 work and their tests pass

---

## Phase 5: User Story 3 - Find the right task (Priority: P3)

**Goal**: Filter by tag and status, sort by priority

**Independent Test**: Build a mixed store and compare returned id sequences with exact expectations

### Tests for User Story 3

- [x] T018 [P] [US3] Service tests in `tests/unit/test_service.py` for tag filter (single, case-insensitive, multi-tag AND), status filter, combined filter, empty result, default and priority ordering (FR-011, FR-012, AS-3.1…AS-3.7)
- [x] T019 [P] [US3] CLI contract tests in `tests/contract/test_cli_contract.py` for `list --tag/--status/--sort` and the determinism check (SC-002)

### Implementation for User Story 3

- [x] T020 [US3] Add filtering and sorting to `list_tasks` in `src/todo/service.py` (FR-011, FR-012)
- [x] T021 [US3] Add `--tag`, `--status`, `--sort` to `list` in `src/todo/cli.py` (FR-011, FR-012)

**Checkpoint**: All user stories work and all tests pass

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T022 Copy the first complete implementation to `evidence/initial-generation/` before any harness-driven change
- [x] T023 Run `.harness/run_harness.py`; for each FAIL, record gate, rule/test, expected and observed in `evidence/harness-log.md`, repair, re-run the same gates
- [x] T024 Copy the accepted implementation to `evidence/final-generation/`
- [x] T025 Validate `quickstart.md` commands by running them
- [ ] T026 Human owner records ACCEPT/REJECT, limitations and justification in `evidence/harness-log.md`

---

## Dependencies & Execution Order

- Phase 1 → Phase 2 → Phase 3 (US1) → Phase 4 (US2) → Phase 5 (US3) → Phase 6
- US2 and US3 both extend `service.py` and `cli.py` created in US1, so they follow US1.
- Within each story: test tasks first, then storage/model, then service, then CLI.
- [P] tasks within a phase touch different files and can be done together.

## Requirement → Task → Test Traceability

| Requirement | Implementation task(s) | Test task(s) |
|-------------|------------------------|--------------|
| FR-001 | T012, T013 | T009, T010 |
| FR-002, FR-003, FR-004 | T007 | T005, T009 |
| FR-005, FR-006 | T012 | T009, T014 |
| FR-007 | T012, T013 | T009, T010 |
| FR-008 | T007, T016, T017 | T014, T015 |
| FR-009 | T016, T017 | T014, T015 |
| FR-010 | T016, T017 | T014, T015 |
| FR-011 | T020, T021 | T018, T019 |
| FR-012 | T020, T021 | T018, T019 |
| FR-013 | T011 | T008, T010 |
| FR-014 | T011 | T008, T010 |
| FR-015 | T006, T013 | T010, T015 |
| FR-016 | T011, T016 | T008, T014, T015 |
| FR-017 | T013 | T010 |
| SC-002 | — | T019 |

## Notes

- A failing test is evidence, not an obstacle: tests and gates are never edited to obtain PASS
  (Constitution III and IV).
- Commit after each phase.
