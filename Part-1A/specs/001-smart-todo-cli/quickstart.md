# Quickstart: Smart Todo & Task CLI

All commands are run from the `Part-1A/` folder.

## Setup (once)

```powershell
pip install -r requirements-dev.txt
```

## Use the tool (PowerShell)

```powershell
$env:PYTHONPATH = "src"
python -m todo --file demo.json add "Buy milk" --priority high --tag home
python -m todo --file demo.json add "Write report" --tag work
python -m todo --file demo.json list --sort priority
python -m todo --file demo.json move 1 in_progress
python -m todo --file demo.json move 1 done
python -m todo --file demo.json list --status done
```

On Linux/macOS use `export PYTHONPATH=src` instead of the first line.

## Run the harness

```powershell
python .harness/run_harness.py
```

The harness runs G1 Ruff, G2 Bandit and G3 pytest, prints a PASS/FAIL table, and writes the result
to `evidence/harness-results/`. It exits with code 0 only when all three gates pass.
