# Specification Analysis Report (/speckit-analyze)

**Date**: 2026-11-14 | **Artifacts**: constitution v1.0.0, spec.md, plan.md, data-model.md,
contracts/, tasks.md | **Mode**: read-only

## Findings

| ID | Category | Severity | Location | Summary | Recommendation |
|----|----------|----------|----------|---------|----------------|
| B1 | Inconsistency | HIGH (fixed before this report) | spec.md EV-2/EV-3 | With BP-3 scored 0 or 1, the 0.8 pass mark needed a perfect score, contradicting "exact wording is not required". | Fixed in the clarification commit: BP-3 is a fraction. No open action. |
| B2 | Coverage | MEDIUM | spec.md FR-002…FR-010, FR-015 | These requirements describe model behaviour and have no unit test; they are covered only by evaluation cases. | Expected for a non-deterministic component. Accept; recorded in the traceability table. |
| B3 | Underspecification | MEDIUM | spec.md FR-012 | "An instruction aimed at the agent itself" is judged by the model; there is no deterministic definition. | Accept for this version; INV-9 gives one deterministic leak check. Record as residual risk. |
| B4 | Coverage | LOW | spec.md Edge Cases | "More than 366 days ahead" has a validator test (INV-7) but no evaluation case. | Accept; covered by unit test T009. |
| B5 | Ambiguity | LOW | spec.md FR-009 | Snooze clarification uses "time" in missing_fields to mean a duration. | Accept; stated explicitly in FR-009 and AS-3.4. |
| B6 | Consistency | LOW | plan.md vs earlier estimate | The dataset has 22 cases, not the 20 mentioned when the threshold was chosen. The threshold is a percentage (90%), so it now means at least 20 of 22. | Confirm with the human owner at approval. |
| B7 | Risk | LOW | research.md R2 | Automatic model selection means two runs could use different models. | The model name is recorded per run (EV-6); set `GEMINI_MODEL` to pin it. |

## Coverage Summary

| Item | Covered by |
|------|-----------|
| FR-001 … FR-016 | 16 of 16 have a task; 11 have evaluation cases, 5 have unit tests, FR-016 has both a unit test and the run-level rule |
| INV-1 … INV-9 | application validator (T014) + independent harness check (T004, T005) + unit tests for both |
| EV-1 … EV-7 | T003, T007, T008 |
| SC-001 … SC-005 | SC-001 run verdict; SC-002 T009; SC-003/SC-004 L2 + categories; SC-005 dataset integrity test |

## Constitution Alignment

No conflicts. Principle IV: harness evaluators do not import `src/reminder_agent/validator.py`
(two independent implementations of the invariants). Principle V: dataset and threshold are
committed in Phase 2, before T022.

## Metrics

- Functional requirements: 16 | Invariants: 9 | Tasks: 25 | Evaluation cases: 22
- CRITICAL issues: 0 | HIGH: 1 (already fixed) | Open items needing the owner: B6

## Next Actions

Implementation may proceed after human approval. B3 and B7 go to the known-limitations list.
