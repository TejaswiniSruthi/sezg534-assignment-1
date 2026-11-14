# Implementation Plan: Natural-Language Reminder Agent

**Branch**: `001-reminder-agent` | **Date**: 2026-11-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-reminder-agent/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

A reminder agent that sends the user's sentence, a reference moment and a fixed set of instructions
to a Gemini model, then passes the model's reply through a deterministic parser and validator
before returning it. Anything that fails validation is replaced by the safe "unknown" result. A
separate evaluation harness runs a committed dataset through the agent and judges each result in
three layers (structural, property/invariant, semantic) against the threshold declared in the
specification.

## Technical Context

**Language/Version**: Python 3.10+ (developed on 3.10, demonstrated on 3.12)

**Primary Dependencies**: None at runtime (standard library only: `urllib.request`, `json`,
`datetime`, `re`, `dataclasses`). The Gemini API is called over HTTPS with `urllib`.

**Storage**: None (the agent is stateless). Evaluation results are written as JSON files.

**Testing**: pytest for the deterministic parts (pre-checks, parser, validator, prompt builder,
agent with a fake model client, and the harness evaluators themselves). No test needs the network.

**Target Platform**: Windows, Linux and macOS terminals

**Project Type**: cli + library

**Performance Goals**: One model call per message; full 22-case evaluation in under 5 minutes on the
free tier (bounded by rate limits, not by our code)

**Constraints**: Model output is untrusted data; API key only from environment or untracked `.env`;
no third-party runtime dependency; model name and temperature recorded per run

**Scale/Scope**: 1 user, 1 message per call, 22 evaluation cases, about 450 lines of production code

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | How the plan complies | Status |
|-----------|----------------------|--------|
| I. Specification is the source of truth | Schema, invariants, scoring and threshold are fixed in spec.md (EV-1…EV-7) before any evaluation; the harness reads the threshold values from one constants block that cites EV-4 | PASS |
| II. Contract over wording | `parser.py` + `validator.py` sit between the model and the caller; failures become the unknown result (FR-014) | PASS |
| III. Never guess, never obey embedded instructions | Rules stated in `prompts/system_prompt.md`; INV-4, INV-7 and INV-9 enforced in code regardless of what the model says | PASS |
| IV. One harness, three independent layers | `.harness/eval_runner.py` with `layer1_schema.py`, `layer2_properties.py`, `layer3_semantic.py`; none imports the application's validator | PASS |
| V. No gaming the benchmark | Dataset and threshold are committed before the first run; each run records a fingerprint of the dataset and prompt, so later changes are visible | PASS |
| VI. Security, secrets and simplicity | Key read by `config.py` from env/`.env`; never logged; standard library only; Ruff + Bandit + pytest run as a pre-flight stage of the harness | PASS |

Post-design re-check (after Phase 1): no violations; Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/001-reminder-agent/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── output-schema.json     # Output Schema Contract as JSON Schema
│   ├── agent-contract.md      # agent interface, CLI, error handling
│   └── eval-contract.md       # dataset format, layers, scoring, result file
├── checklists/requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
Part-1B/
├── src/reminder_agent/
│   ├── __init__.py
│   ├── __main__.py        # python -m reminder_agent "message"
│   ├── schema.py          # field names, allowed values, the unknown result
│   ├── config.py          # API key, model name, temperature from env / .env
│   ├── llm.py             # Gemini HTTPS client, ServiceError, retries
│   ├── prompt.py          # builds instructions + reference moment + calendar
│   ├── parser.py          # extracts one JSON object from the model's reply
│   ├── validator.py       # INV-1…INV-9 on the application side
│   └── agent.py           # pre-checks → model → parse → validate → result
├── prompts/system_prompt.md
├── tests/unit/            # deterministic parts and harness evaluators
├── evals/dataset.json     # 22 cases with ground truth and cited requirements
├── .harness/
│   ├── eval_runner.py     # the single evaluation pipeline
│   ├── layer1_schema.py   # L1 structural validation
│   ├── layer2_properties.py  # L2 invariants and properties
│   ├── layer3_semantic.py # L3 semantic scoring against ground truth
│   ├── ruff.toml
│   └── bandit.yaml
├── evidence/
│   ├── initial-generation/
│   ├── final-generation/
│   ├── runs/              # every evaluation run, never overwritten
│   ├── eval-results.json  # copy of the latest run
│   └── harness-log.md
├── requirements-dev.txt
└── pytest.ini
```

**Structure Decision**: Single project. The application (`src/`), its instructions (`prompts/`),
the benchmark (`evals/`) and the judge (`.harness/`) are separate folders so that a change to one
is visible in Git on its own.

## Complexity Tracking

No constitution violations; nothing to justify.
