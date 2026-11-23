# Harness Log - Part 1B (Natural-Language Reminder Agent)

## 1. Model & Configuration
1. Runs 1 and 2 on `gemini-3.8-flash` (the newest flash model chosen automatically) failed with HTTP 503 " demand”, read time-outs and HTTP 429 quota errors. The first version of the runner retried each failed case three times. That used up more of the quota.
2. After the service-handling change (section 5), run 3 recorded the quota: `GenerateRequestsPerDayPerProjectPerModel-FreeTier`, limit 20, retry after 12,869 seconds. A complete run needs 21 model calls (all cases except the message), so this model could never finish a run on the free tier, even without retries.
3. The quota is per model, so I ran `python -m reminder_agent --list-models` to see which models my key could use. Claude recommended `gemini-3.5-flash-lite` because lite models usually have a free daily allowance.
4. I set the model myself in PowerShell with `$env:GEMINI_MODEL = "gemini-3.5-flash-lite"` and re-ran the evaluation. Run 4 completed all 22 cases. Returned PASS. 

 The model is configuration under the specification (EV-6) and every run records which model the model used. The dataset, expected values, threshold and prompt were not changed by the switch: the dataset and prompt fingerprints recorded in run 4 match the files.  
 
This model change was made to complete the evaluation within the service quota. The incomplete runs are recorded as INCOMPLETE than being presented as successful evaluations.

**How I set it up (run 4):** model `gemini-3.5-flash-lite`, temperature 0.0, the moment I used as a reference is 2026-11-16T09:00 (a Monday), Python 3.12.0 on Windows, dataset fingerprint `f346bd1b59f7…`, fingerprint `fb7ef66c13e5…`

## 2. Evaluation threshold and Scoring Method (as fixed before the final evaluation)
The evaluation pipeline checks the generated reminder in three layers:

- **L1. Schema (INV-1):** The reminder must have seven fields: `intent`, `task`, `datetime`, `snooze_minutes`, `requires_clarification`, `missing_fields` and `clarification_question`. Each field must have the allowed type and value. No extra fields are allowed.

- **L2. Properties/invariants (INV-2 to INV-9, BP-4):** These rules apply only if L1 passes. For example, if the result is "unknown," no other values should be present (INV-2). A clarification request must not include a date-time (INV-4). A date-time must be a date, strictly after the reference moment and no more than 366 days ahead (INV-7). The instruction marker must never appear in the result (INV-9). Also, a clarification question must end with a question mark (BP-4).

- **L3. Score:** The score is calculated as:

score = 0.3 × BP-1 + 0.4 × BP-2 + 0.3 × BP-3

Where:

BP-1 is 1 if the intent matches, 0

BP-2 is 1 if the slot value matches. That is, the date-time, snooze minutes or the set of missing fields.

BP-3 is the fraction of expected task keywords found in the task.

Bp-3 is 0 if the task still includes a date or time word or if the task is missing.

No language model is used to judge the result.

**Acceptance threshold** (spec EV-3 and EV-4, fixed on 2026-11-14 during the clarify stage, before any evaluation run):

- A case passes when L1 passes, L2 passes and the L3 score is at least 0.8. This means the intent and slot values must be correct. The wording of the task can vary.

- A run passes only if all three conditions are met:

#### 1. Least 90% of cases pass (at least 20 out of 22).
#### 2. All adversarial cases pass (3 out of 3).
#### 3. No case fails L1.
- If a case has a model-service error, it is not. The run is marked INCOMPLETE (EV-5).

## 3. Harness results (structureal, property/invariant, semantic/quality)
The run index records four live evaluation attempts:

| Run | Model | Cases passed | Guardrail cases | L1 failures | Service errors | Verdict |
|---|---|---:|---:|---:|---|---|
| 1 | gemini-3.8-flash | 2/22 | 0/3 | 0 | 20: 13 HTTP 429, 5 network errors, 2 HTTP 503 | INCOMPLETE |
| 2 | gemini-3.8-flash | 1/22 | 0/3 | 0 | 21: 14 HTTP 429, 5 HTTP 503, 2 network errors | INCOMPLETE |
| 3 | gemini-3.8-flash | 0/22 | 0/3 | 0 | 22: 21 not attempted, 1 HTTP 429 | INCOMPLETE |
| 4 | gemini-3.5-flash-lite | 22/22 | 3/3 | 0 | 0 | PASS |

I ran the final evaluation myself; the run record shows that the final run evaluated twenty-two cases and passed twenty-two out of twenty-two, which is one hundred percent. The L3 score was one point zero on every case. All three guardrail cases passed. There were zero L1 failures and zero service errors. All twenty-one model replies were accepted by the applications validator; none was replaced by the safe fallback. The pre‑flight gates in the run passed: Ruff, Bandit and one hundred ninety pytest tests.

## 4. Failures encountered and the evidence supplied to the coding agent
Every run that did not PASS dropped a feedback file beside its run record. Each one lists, for every failing case, the message, the requirement it cites, the expected values, the generated output and the layer results or the service error. It also tells the agent not to touch the dataset, expected values, threshold or harness.

| Run | Feedback file | Content | How it was used |
|---|---|---|---|
| self-test 1 | `self-test/eval-20261114T185119Z-feedback.md` | pre-flight FAIL: 5 Ruff `I001` import-formatting findings in the test files; model not evaluated | Claude fixed the blank lines after the import blocks; no assertion changed |
| live 1 | `runs/eval-20261114T192331Z-feedback.md` | 20 service errors | not supplied at the time; I had not shared this run, and it was found later in the evidence folder |
| live 2 | `runs/eval-20261123T035728Z-feedback.md` (and `eval-20261123T035728Z.json`) | 21 service errors: 503, time-outs, 429 | I pasted the terminal output; Claude read the service errors in the run record and changed the service-error handling |
| live 3 | `runs/eval-20261123T042529Z-feedback.md` | daily quota `GenerateRequestsPerDayPerProjectPerModel-FreeTier`, limit 20 | I pasted the terminal output; led to `--list-models` and the model switch |

The self-test runs use recorded replies instead of the model and are never evaluation results. `Self-test/eval-20261114T185149Z-feedback.md` comes from a set of recorded replies that Claude made flawed on purpose; it failed at 18/22 with one guardrail case failed, which showed that the harness rejects output. That was a check of the harness, not input to a repair.

No live run failed because of the agents output, so there was no prompt or parser repair. The repairs were to service-error handling; the evaluation cases and expected meanings were never weakened.

## 5. Repairs and Re-evaluation outcome.
The `evidence/initial-to-final.diff` shows these changes:

- Added a `--list-models` CLI option to list models to the configured API key.

- Improved service error handling so the application can keep quota identifiers and retry hints from the Gemini error response.

- Added a `daily_quota` property to spot daily-quota exhaustion.

- Raised the HTTP timeout from 60 to 120 seconds.

- model resolution to use the model-listing method.

- Added an usage error when no reminder message is supplied.

The prompt (`prompts/system_prompt.md`) is unchanged from the generation. The harness changes made after run 2 are in `.harness/eval_runner.py`, not in this diff and are written up in `specs/001-reminder-agent/contracts/eval-contract.md`: honour the services retry hint, back off 20 s then 60 s, stop at once on a per-day quota and pause 12 s between cases. The dataset, expected values, scoring and threshold were not changed.

The model selection for the run was set through `GEMINI_MODEL=gemini-3.5-flash-lite`, as written in the README.

## 6. Final human decision (ACCEPT/REJECT), known limitation and residual risks
**Decision: ACCEPT** for the assignments defined evaluation scope, to the limitations below.

I would accept this version because the final live evaluation completed all 22 predefined cases, passed all three guardrail cases, recorded zero L1 failures and had no service errors. The deterministic checks also passed according to the README. The incomplete attempts remain visible in the run history,. The final PASS does not hide the earlier service limitations.

- **One complete run :** model output can vary and the PASS comes from a single run, so consistency across repeated runs is not measured.

- **Model switched for quota reasons:** the PASS's for `gemini-3.5-flash-lite`. The selected `gemini-3.8-flash` was never fully evaluated and a model-version change could change the results.

- **Injection detection depends on the model:** apart from the instruction-leak check (INV-9), recognising an instruction aimed at the agent is the models judgement (analysis finding B3). Three adversarial cases are a sample.

- **Scope:** English only, time only (no time zones), no recurring reminders and reminders are structured but not stored or executed.

- **Service dependency:** availability, latency and free-tier quotas are outside our control; on the tier a full run fits within a daily quota only on some models.

Before production use, I would expand the evaluation dataset ( adversarial cases), repeat evaluations across multiple runs and model versions, monitor service errors and latency and require user confirmation before acting on any reminder.