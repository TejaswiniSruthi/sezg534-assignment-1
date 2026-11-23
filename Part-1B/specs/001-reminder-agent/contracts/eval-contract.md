# Evaluation Contract

## Dataset: `evals/dataset.json`

```json
{
  "reference_moment": "2026-11-16T09:00",
  "cases": [
    {
      "id": "C01",
      "category": "normal",
      "message": "…",
      "cites": ["FR-002", "AS-1.1"],
      "expected": {
        "intent": "create",
        "datetime": "2026-11-17T17:00",
        "task_keywords": ["call", "mom"],
        "task_forbidden": ["tomorrow", "remind"]
      }
    }
  ]
}
```

Exactly one slot expectation per case: `datetime`, `snooze_minutes` or `missing_fields`
(none when `intent` is `unknown`). Task expectation: `task_keywords` (+ optional `task_forbidden`),
or `"task": "null"`, or `"task": "any"`.

## Pipeline: `python .harness/eval_runner.py`

```text
Stage 0  pre-flight   Ruff, Bandit, pytest on the deterministic code      FAIL → stop, run FAIL
Stage 1  generate     for each case: agent.parse(message, reference)      service error → retry ×3
Stage 2  L1           layer1_schema.check(result)                         INV-1
Stage 3  L2           layer2_properties.check(result, reference, marker)  INV-2…INV-9, BP-4
Stage 4  L3           layer3_semantic.score(result, expected)             0.3·BP-1 + 0.4·BP-2 + 0.3·BP-3
Stage 5  aggregate    EV-3 per case, EV-4 for the run
```

- L2 runs only when L1 passed; L3 is computed whenever L1 passed (so partial credit is visible).
- Case verdict: `pass`, `fail` or `service_error`.
- Run verdict: `PASS`, `FAIL` or `INCOMPLETE` (any `service_error`), per EV-4 and EV-5.

## Threshold constants (from spec EV-3, EV-4; fixed 2026-11-14)

| Constant | Value |
|----------|-------|
| `CASE_PASS_SCORE` | 0.8 |
| `MIN_PASS_RATE` | 0.90 |
| `GUARDRAIL_CATEGORY` | `adversarial` (must be 100%) |
| `MAX_L1_FAILURES` | 0 |

## Result file: `evidence/eval-results.json` (and `evidence/runs/<run_id>.json`)

Top level: `run_id`, `started_utc`, `mode` (`live` or `self-test`), `model`, `temperature`,
`reference_moment`, `dataset_sha256`, `prompt_sha256`, `threshold`, `preflight`, `summary`
(`total`, `passed`, `failed`, `service_errors`, `pass_rate`, `guardrail_passed`, `l1_failures`,
`by_category`), `verdict`, `cases`.

Each case: `id`, `category`, `message`, `cites`, `expected`, `output`, `source`, `raw_reply`,
`app_violations`, `l1` (`pass`, `errors`), `l2` (`pass`, `violations`), `l3` (`score`, `bp1`,
`bp2`, `bp3`, `notes`), `verdict`, `attempts`, `service_error`.

On FAIL the runner also writes `evidence/runs/<run_id>-feedback.md`: for each failing case the
message, generated output, failed requirement or property, and layer results, ready to hand to the
coding agent.

## Retry policy for model-service errors (revised 2026-11-23 after live run 1)

Live run 1 was INCOMPLETE: 21 of 22 cases hit HTTP 503, read time-outs or HTTP 429 quota errors,
and the fixed retries spent more of the free quota. Revised policy (no change to the dataset,
expected values, scoring or threshold):

- Up to 3 attempts per case; wait 20 s, then 60 s, or the service's own retry hint if longer
  (capped at 120 s). Default pause between cases: 12 s (about 5 requests per minute).
- A per-day quota error stops model calls for the rest of the run; remaining cases are recorded as
  `service_error` ("not attempted") and the run is INCOMPLETE, as EV-5 already requires.
- Service-error messages keep the quota name and limit, so the evidence shows which quota was hit.
- Read time-out raised from 60 s to 120 s.

## Options

- `--replay FILE`: take model replies from a JSON file `{message: reply_text}` instead of calling
  the model. The run is labelled `self-test`, is written to `evidence/self-test/`, and never updates
  `eval-results.json`.
- `--delay SECONDS`: pause between model calls (default 4) to respect free-tier rate limits.
