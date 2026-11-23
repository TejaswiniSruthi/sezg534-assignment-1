# SEZG534 AI-Augmented SDLC — Assignment 1: Spec-Driven Development & Harness Engineering

Student: Tejaswini Thambabathula

Two small applications built with the GitHub Spec Kit workflow
(constitution → specify → clarify → plan → tasks → analyze → implement), each validated by a harness
that is independent of the generated code. The coding agent was Claude (Anthropic), working from the
approved Spec Kit artifacts; every stage is a separate commit in the Git history.

| Part | Application | Behaviour | Harness |
|------|-------------|-----------|---------|
| [Part-1A](Part-1A/) | Smart Todo & Task CLI (Python) | deterministic | Ruff lint, Bandit SAST, pytest unit + contract tests |
| [Part-1B](Part-1B/) | Natural-Language Reminder Agent (Python + Google Gemini) | non-deterministic | one evaluation pipeline: schema → invariants → semantic score → threshold |

## Requirements

- Python 3.10 or newer, Git
- Part 1B only: a Google Gemini API key

## Part 1A — run the harness

```powershell
cd Part-1A
pip install -r requirements-dev.txt
python .harness/run_harness.py
```

Prints PASS/FAIL for G1 (Ruff), G2 (Bandit) and G3 (pytest, 197 tests) and writes evidence to
`Part-1A/evidence/harness-results/`. Exit code 0 only when all three gates pass.

Try the tool:

```powershell
$env:PYTHONPATH = "src"
python -m todo --file demo.json add "Buy milk" --priority high --tag home
python -m todo --file demo.json list --sort priority
```

## Part 1B — run the evaluation

1. Create a file named `.env` in this top folder (it is git-ignored) containing
   `GEMINI_API_KEY=your-key`.
2. Run:

```powershell
cd Part-1B
pip install -r requirements-dev.txt
$env:GEMINI_MODEL = "gemini-3.5-flash-lite"
python .harness/eval_runner.py
```

The runner checks the deterministic code (Ruff, Bandit, pytest), sends the 22 cases in
`evals/dataset.json` to the model, judges each result in three layers and prints
PASS / FAIL / INCOMPLETE against the threshold declared in the spec (EV-4). Results:
`Part-1B/evidence/eval-results.json`. Takes about 5 minutes (12 s pause between calls).

`GEMINI_MODEL` is needed on the free tier: `gemini-3.8-flash` allows only 20 requests per day and a
run needs 21. `python -m reminder_agent --list-models` (with `$env:PYTHONPATH = "src"`) lists the
models your key can use.

Offline check of the pipeline without a key or network (labelled self-test, never an evaluation
result): `python .harness/eval_runner.py --replay tests/fixtures/replay_flawed_model.json`.

## Where to find things

| | Part 1A | Part 1B |
|-|---------|---------|
| Constitution | `.specify/memory/constitution.md` | `.specify/memory/constitution.md` |
| Spec, clarifications, plan, contracts, tasks, analysis | `specs/001-smart-todo-cli/` | `specs/001-reminder-agent/` |
| Source / prompt | `src/todo/` | `src/reminder_agent/`, `prompts/system_prompt.md` |
| Tests / dataset | `tests/` | `tests/`, `evals/dataset.json` |
| Harness | `.harness/run_harness.py` | `.harness/eval_runner.py`, `layer1_schema.py`, `layer2_properties.py`, `layer3_semantic.py` |
| Evidence | `evidence/` (`harness-results/run-index.md`, `harness-log.md`) | `evidence/` (`runs/run-index.md`, `eval-results.json`, `harness-log.md`) |

No API keys, credentials or `.env` files are committed.
