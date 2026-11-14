---

description: "Task list for Natural-Language Reminder Agent"
---

# Tasks: Natural-Language Reminder Agent

**Input**: Design documents from `/specs/001-reminder-agent/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Required (Constitution IV and VI). The evaluation dataset, the three evaluators and the
unit tests for deterministic code are written before the application and its prompt.

**Organization**: Benchmark and judge first, then the application by user story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- All paths are relative to `Part-1B/`

---

## Phase 1: Setup (Shared Infrastructure)

- [ ] T001 Create folders `src/reminder_agent/`, `prompts/`, `tests/unit/`, `evals/`, `.harness/`, `evidence/runs/`
- [ ] T002 [P] Create `requirements-dev.txt`, `pytest.ini`, `.harness/ruff.toml`, `.harness/bandit.yaml`

---

## Phase 2: Foundational — benchmark and judge (Blocking Prerequisites)

**Purpose**: Fix what "acceptable" means before any application code or prompt exists

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T003 Create `evals/dataset.json` with 22 cases across normal, boundary, ambiguous, missing, malformed and adversarial categories; every case cites FR/INV/AS ids and carries ground truth (EV-1, SC-005)
- [ ] T004 [P] Create `.harness/layer1_schema.py`: structural check of INV-1 (EV-2 L1)
- [ ] T005 [P] Create `.harness/layer2_properties.py`: INV-2…INV-9 and BP-4 (EV-2 L2)
- [ ] T006 [P] Create `.harness/layer3_semantic.py`: BP-1…BP-3 scoring against ground truth (EV-2 L3)
- [ ] T007 Create `.harness/eval_runner.py`: pre-flight gates, generation with retry, L1→L2→L3, per-case verdict (EV-3), run verdict (EV-4, EV-5), run metadata (EV-6, EV-7), result and feedback files, `--replay` self-test mode
- [ ] T008 [P] Unit tests for the three evaluators in `tests/unit/test_harness_layers.py`: each invariant has a result that must fail it; scoring arithmetic; dataset integrity (ids unique, ≥ 15 cases, every category present, every case cites a requirement)
- [ ] T009 [P] Unit tests for the deterministic application code in `tests/unit/test_parser.py`, `test_validator.py`, `test_agent.py`, `test_prompt.py` (FR-013, FR-014, FR-016, INV-1…INV-9), using a fake model client

**Checkpoint**: Harness and tests exist and fail only because the application does not exist yet

---

## Phase 3: User Story 1 - Turn a sentence into a reminder (Priority: P1) 🎯 MVP

**Goal**: A complete reminder sentence becomes a valid "create" result

**Independent Test**: Dataset cases C01–C07 pass all three layers

- [ ] T010 [P] [US1] Create `src/reminder_agent/schema.py`: field names, allowed values, `unknown_result()` (INV-1, INV-2)
- [ ] T011 [P] [US1] Create `src/reminder_agent/config.py`: key/model/temperature from environment or `.env`; key never logged (Constitution VI)
- [ ] T012 [US1] Create `src/reminder_agent/llm.py`: Gemini HTTPS client, model selection, `ServiceError` (FR-016)
- [ ] T013 [US1] Create `src/reminder_agent/parser.py`: `extract_json` (FR-014)
- [ ] T014 [US1] Create `src/reminder_agent/validator.py`: `find_violations` for INV-1…INV-9 (FR-014, SC-002)
- [ ] T015 [US1] Create `prompts/system_prompt.md` and `src/reminder_agent/prompt.py`: instructions for FR-002…FR-005, FR-015, output contract, leak marker, reference moment and calendar
- [ ] T016 [US1] Create `src/reminder_agent/agent.py`: pre-check → model → parse → validate → result/fallback (FR-001, FR-013, FR-014)
- [ ] T017 [US1] Create `src/reminder_agent/__main__.py`: CLI per agent-contract.md

---

## Phase 4: User Story 2 - Ask instead of guessing (Priority: P2)

**Goal**: Missing or ambiguous information produces a clarification, never a guess

**Independent Test**: Dataset cases C08–C13 pass all three layers

- [ ] T018 [US2] Add clarification rules to `prompts/system_prompt.md` (FR-006, FR-007, FR-010, FR-011, INV-3, INV-4, INV-8)

---

## Phase 5: User Story 3 - Reschedule and snooze (Priority: P3)

**Independent Test**: Dataset cases C14–C17 pass all three layers

- [ ] T019 [US3] Add reschedule and snooze rules to `prompts/system_prompt.md` (FR-008, FR-009, INV-6)

---

## Phase 6: User Story 4 - Stay safe on bad input (Priority: P4)

**Independent Test**: Dataset cases C18–C22 pass all three layers

- [ ] T020 [US4] Add guardrail rules to `prompts/system_prompt.md` (FR-012, FR-013, INV-2, INV-9)

---

## Phase 7: Evaluation, repair and evidence

- [ ] T021 Copy the first complete implementation and prompt to `evidence/initial-generation/` before any evaluation run
- [ ] T022 Run `.harness/eval_runner.py` against the live model; keep every run file in `evidence/runs/`
- [ ] T023 For each FAIL: give the feedback file to the coding agent, repair the cause (prompt / parser / validator / guardrail), re-run the unchanged dataset and threshold
- [ ] T024 Copy the accepted implementation and prompt to `evidence/final-generation/`
- [ ] T025 Human owner records model/configuration, threshold, results, failures, repairs, ACCEPT/REJECT, limitations and residual risks in `evidence/harness-log.md`

---

## Dependencies & Execution Order

- Phase 1 → Phase 2 → Phases 3–6 → Phase 7.
- Phases 4–6 extend the same prompt file created in Phase 3 and are done in order.
- T022 needs network access to the model and the API key; it is run on the owner's machine.

## Requirement → Task → Check Traceability

| Requirement | Implementation task(s) | Unit test | Evaluation cases |
|-------------|------------------------|-----------|------------------|
| FR-001 | T016, T017 | T009 | all |
| FR-002, FR-003, FR-004 | T015 | — (model behaviour) | C01–C04, C06, C07 |
| FR-005 | T015 | — | C05 |
| FR-006 | T018 | — | C08 |
| FR-007 | T018 | — | C09, C10 |
| FR-008 | T019 | — | C14 |
| FR-009 | T019 | — | C15, C16, C17 |
| FR-010 | T018 | — | C08–C12 |
| FR-011 | T018 | T009 (INV-7) | C13 |
| FR-012 | T020 | T009 (INV-9) | C20, C21, C22 |
| FR-013 | T016, T020 | T009 | C18, C19 |
| FR-014 | T013, T014, T016 | T009 | all (L1) |
| FR-015 | T015 | — | all cases with task key words (BP-3) |
| FR-016 | T012, T016 | T009 | run-level (EV-5) |
| INV-1 | T014, T004 | T008, T009 | all (L1) |
| INV-2…INV-9, BP-4 | T014, T005 | T008, T009 | all (L2) |
| EV-1…EV-7 | T003, T007 | T008 | — |

## Notes

- The dataset, expected values and threshold are frozen once Phase 2 is committed (Constitution V).
- A failing case is evidence. Repairs change the application or its prompt, never the benchmark.
