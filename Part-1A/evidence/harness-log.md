# Harness Log - Part 1A (Smart ToDo & Task CLI)

## 1. Initial coding-agent generation and its specification context
I used Claude as the coding agent to build the Smart Todo & Task CLI in Python. The Smart Todo & Task CLI was built from the approved Spec Kit artifacts, such as the constitution, feature specification, clarifications, technical plan and task list. The initial source code was kept in evidence/initial-generation/ so that the Smart Todo & Task CLI could be compared with the repaired version. The harness was kept separate from the Smart Todo & Task CLI. Used Ruff, Bandit and pytest as its three validation gates.

## 2. Harness executions and outcomes
The run index records ten harness executions:

| Run | Ruff (G1) | Bandit (G2) | pytest (G3) | Overall |
|---|---|---|---|---|
| 1 | FAIL: 5 violations | FAIL: 1 finding | 3 collection/runtime errors; 0 tests passed | FAIL |
| 2 | FAIL: 4 violations | FAIL: 1 finding | 3 collection/runtime errors; 0 tests passed | FAIL |
| 3 | FAIL: 5 violations | PASS | 191 passed | FAIL |
| 4 | FAIL: 2 violations | PASS | 191 passed | FAIL |
| 5 | PASS | PASS | 191 passed | PASS |
| 6 | PASS | PASS | 191 passed, 6 failed (197 total) | FAIL |
| 7 | PASS | PASS | 197 passed | PASS |
| 8 | Ruff reported FAIL despite 0 violations; Bandit ERROR; 197 tests passed | ERROR | 197 passed | FAIL |
| 9 | PASS | PASS | 197 passed | PASS |
| 10 | PASS | PASS | 197 passed | PASS |

Runs 1 and 2 were the starting point. We did them once the tests and the harness were in place,. Before any app code was written. G1 and G2 failed with a `no-source` finding, because there was no `.py` file under `src/`. Ruff also raised a formatting complaint about the test files and pytest could not import the missing `todo` modules. These runs show the tests came before the implementation. In between, one test line that was long got wrapped and Ruff was told where the app package lives. That was just. Configuration. No assertion changed.

Run 3 was the one on generated code. Runs 3 and 4 showed the tests could pass while Ruff still found style issues,. The whole harness rightly stayed at FAIL. Run 5 was the full PASS, with 191 tests. Run 6 turned up six failing tests after the suite grew to 197 tests. Run 7 passed all 197 tests. Run 8 was my run on my own Windows laptop. Ruff and Bandit were not installed there. See " missing-tool issue" below. Run 9 was Claudes re-check, in its Linux environment, of the harness change made after run 8. Run 10 was my run on Windows, after I installed the tools and it passed all three gates. Claude ran runs 1 to 7 and 9 in a Linux environment. I ran runs 8 and 10 on Windows with Python 3.12.
## 3. Failures and repair cycles
### Cycle 1 - Ruff Findings
On the generated implementation (run 3), all 191 tests passed.. Ruff found 5 violations. Two were `UP035` in `src/todo/models.py` and `src/todo/service.py`. These flagged that `Iterable` should come from `collections.abc`, not `typing`. There was also an `I001` violation (import block not formatted) in three test files: `tests/unit/test_models.py`, `test_service.py` and `test_storage.py`. The first repair fixed the two imports in `src/`. Added blank lines after the import blocks in the tests. No assertion was changed.

Run 4 still failed. It had two `I001` violations in `models.py` and `service.py`. The first repair had put the import outside the alphabetical order. The second repair sorted those import blocks. After that, run 5 passed all three gates.

I did not consider a passing pytest result if the lint gate was failing. I waited for all checks to pass.

### Cycle 2 - Task ID / Unicode edge case (`show ²`)

After run 5 passed, Claude reviewed the code. It found that running `python -m todo show ²` caused a crash. The error was a ValueError` with a traceback. The exit code was 1. The expected behavior was a validation error. This broke FR-015.

The harness had not caught this because no test used such a character. The rule for task ID needed to be clear: ASCII digits `0` through `9` were allowed. Not any Unicode character that Python sees as a digit.

The rule was made explicit in the specification’s edge cases first. Then new unit and contract tests were added for `²`, `٣`, `１`. 1²`. No existing test was changed. The new tests failed on the code. That failure helped guide the repair.

Run 6 had six failing tests out of 197. After fixing the issue, run 7 passed all 197 tests.

The final diff shows that `validate_id` now checks both `text.isascii()` and `text.isdigit()` before converting the value.

### Cycle 3 - Local missing-tool issue

Run 8 was my first harness run on my Windows laptop (Python 3.12.0). I ran `pip install -r requirements-dev.txt` from the top-level assignment folder.. That file does not exist there. So Ruff and Bandit were never installed.

The run log (`run-20261114T182647Z.log`) showed `No module named ruff` and `No module named bandit`. Pytest 9.1.1 was installed. All 197 tests passed. The harness showed G1 as "FAIL, 0 violation(s)". G2 as "ERROR". That was misleading because no code had been checked by either tool.

I pasted the output into Claude. It read the run record and log. That led to two changes.

1. **Environment fix (by me):** I ran `pip install -r requirements-dev.txt` from inside `Part-1A`, then re-ran the harness. Run 10 passed all three gates on Windows.

2. **Harness fix (by Claude):** The harness now reports a missing tool as `ERROR` with the message "ruff is not installed: run pip install -r requirements-dev.txt". It does not show a FAIL. No gate or rule was relaxed. Run 9 was Claude’s re-check of this change.


## 4. Failure evidence supplied back to the coding agent
Every failed run wrote a feedback file to `evidence/harness-results/`. Each lists the failing gate, the rule or test, its location, the expected behaviour and the observed behaviour, and tells the agent not to edit tests, harness configuration or the specification. Claude read each run's findings from the feedback file or from the matching `run-*.json`, which records the same findings.

| Run | Feedback file | Content | Used for |
|---|---|---|---|
| 1 | `run-20261114T123159Z-feedback.md` | baseline: no source code, test-file formatting, import errors | no repair (expected before implementation) |
| 2 | `run-20261114T123224Z-feedback.md` | baseline after the formatting change | no repair (expected before implementation) |
| 3 | `run-20261114T124615Z-feedback.md` | 5 Ruff findings (2 × UP035, 3 × I001) | first lint repair |
| 4 | `run-20261114T124748Z-feedback.md` | 2 Ruff I001 findings in `models.py`, `service.py` | second lint repair |
| 6 | `run-20261114T125024Z-feedback.md` | 6 failing tests, with the `ValueError: invalid literal for int()` traceback from `validate_id` | task-ID repair |
| 8 | `run-20261114T182647Z-feedback.md` (and `run-20261114T182647Z.log`) | "No module named ruff" / "No module named bandit" | tool installation and harness message change |

Runs 5, 7, 9 and 10 passed, so no feedback file was written for them.

## 5. What changed after repair, and re-execution result
The `evidence/initial-to-final.diff` records these source changes:

- `Iterable` was imported from `collections.abc` instead of `typing` in the task model and service modules.
- Task ID validation was tightened. The final implementation requires the text to contain ASCII digits and to represent a positive integer.
- The validation docstring was updated to state the ASCII-digit requirement.

These changes are consistent with the final implementation being more explicit about the accepted task-ID format. The diff covers application code only; the harness message change from run 8 is in `.harness/run_harness.py` and its own commit. The final harness runs then reported Ruff PASS, Bandit PASS, and 197 pytest tests passing.

## 6. Final human decision (ACCEPT / REJECT), known limitations and justification
**Decision: ACCEPT** for the assignment's stated scope, subject to the limitations below.

I would accept this version because the final recorded runs (9 and 10) passed all three harness gates: Ruff, Bandit, and pytest. The final test run covered 197 tests, and the original generated implementation and the repair diff were preserved for review.

This is not a claim that the application is production-ready. Known limitations:

- **Performance not tested:** the plan's goal of under 1 second for 1,000 tasks has no test (analysis finding A4).
- **Single user only:** two processes writing the same data file at the same time are not protected against; this was out of scope in the specification.
- **Delete is immediate:** there is no confirmation step or undo (a specification assumption).
- **Edge case found by review, not by the harness:** the `²` crash was missed by all three gates until a test was added, so other unusual inputs may still be untested.
- **Static checks have limits:** Ruff and Bandit find known patterns only; they do not prove the absence of bugs or security issues.

Before production use, I would add performance tests with large task stores, file locking or a database for concurrent use, property-based tests for unusual input, and a review of persistence and recovery behaviour.
