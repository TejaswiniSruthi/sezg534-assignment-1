<!--
Sync Impact Report
- Version change: (template) → 1.0.0
- Modified principles: none (initial ratification)
- Added sections: Core Principles I–VI, Engineering Constraints, Development Workflow & Quality Gates, Governance
- Removed sections: none
- Follow-up TODOs: none
-->

# Smart Todo & Task CLI Constitution

## Core Principles

### I. Specification Is the Source of Truth (NON-NEGOTIABLE)

- No production code MUST be written before `spec.md`, `plan.md` and `tasks.md` exist for the
  feature and have been reviewed by the human owner.
- Every functional requirement (FR-xxx) MUST have at least one acceptance scenario that can be
  decided as pass or fail without human judgement.
- If an ambiguity is found during or after implementation, the upstream artifact (spec, plan or
  tasks) MUST be amended first and the change committed; code MUST NOT silently choose a behaviour.
- The coding agent MUST NOT weaken, reword or remove an acceptance criterion to make an
  implementation pass.

Rationale: the specification, not the generated code, is what the human approved.

### II. Deterministic Behaviour

- For the same stored state and the same input, every command MUST produce byte-identical output
  and the same exit code.
- Production code MUST NOT use randomness, network access, or wall-clock time in any decision that
  affects output ordering or content. Identifiers MUST be sequential integers.
- Every list output MUST have a total, documented ordering (no reliance on dictionary or file-system
  order).

Rationale: exact assertions are only possible when behaviour is fully determined by input and state.

### III. Tests Are Derived From the Specification

- Every FR MUST be covered by at least one automated test whose name or docstring cites the FR or
  acceptance-scenario identifier.
- Tests MUST assert exact values (exit codes, JSON fields, ordering), not "truthy" results.
- Tests MUST be written from the specification and contracts, not from the implementation, and MUST
  exist before the implementation task they cover is started.
- The coding agent MUST NOT delete, skip, `xfail` or loosen a failing test. A test may change only
  when the specification changes, and that change MUST be documented in the harness log.

Rationale: a test written to match the code proves nothing about the requirement.

### IV. Mandatory Harness Gates

All of the following gates MUST report PASS, in one harness run, before the work can be offered for
human acceptance:

| Gate | Tool | PASS means |
|------|------|-----------|
| G1 Syntax & Lint | Ruff | 0 violations with the committed rule set |
| G2 Security (SAST) | Bandit | 0 findings at any severity or confidence |
| G3 Unit & Contract Tests | pytest | 100% of collected tests pass, 0 skipped, 0 xfailed |

- The harness MUST be independent of the implementation: it lives in `.harness/` and MUST NOT import
  production code.
- The coding agent MUST NOT disable a gate, add blanket ignore rules (`# noqa`, `# nosec`,
  per-file ignores) or edit a recorded harness result. Any suppression requires a written
  justification approved by the human owner.
- Every harness run MUST write a machine-readable result file and capture stdout/stderr of each gate.

Rationale: the agent's own claim that the code "works" is not evidence.

### V. Security and Secrets

- No secret, credential, token or `.env` file MUST ever be committed.
- Production code MUST NOT use `eval`, `exec`, `pickle`, `subprocess`, `os.system` or shell
  invocation.
- The application MUST read and write only the single data file it is configured with.
- All user input MUST be validated before it changes stored state; invalid input MUST leave stored
  state unchanged.
- Writes to the data file MUST be atomic (write to a temporary file, then replace).

Rationale: these are the realistic risks for a local file-based tool, and each is checkable.

### VI. Simplicity and Maintainability

- Production code MUST use the Python standard library only (0 third-party runtime dependencies).
- Cyclomatic complexity MUST be 10 or less per function; line length MUST be 100 characters or less.
- Every public function MUST have type hints and a docstring.
- Features not present in the approved specification MUST NOT be implemented.

Rationale: a small scope lets the full specify → implement → validate cycle be completed and
inspected.

## Engineering Constraints

- Language: Python 3.10 or newer.
- Interface: command-line; results on stdout as JSON, error messages on stderr.
- Storage: one local JSON file.
- Development-only tools: Ruff, Bandit, pytest (pinned in `requirements-dev.txt`).
- Exit codes are part of the contract and MUST be documented in `contracts/`.

## Development Workflow & Quality Gates

1. Follow the Spec Kit order: constitution → specify → clarify → plan → tasks → analyze → implement.
2. Commit each approved artifact before starting the next stage, so change history is preserved.
3. Preserve the first generated implementation in `evidence/initial-generation/` before any
   harness-driven correction.
4. On a harness FAIL: record the failing gate, rule or test, expected and observed behaviour; supply
   that evidence to the coding agent; repair the implementation; re-run the same unchanged gates.
5. After an automated PASS, the human owner records a final ACCEPT or REJECT decision with known
   limitations in `evidence/harness-log.md`.

## Governance

- This constitution overrides any conflicting instruction given to the coding agent.
- Amendments require: a written reason, a version bump (semantic versioning: MAJOR for removed or
  redefined principles, MINOR for added principles, PATCH for clarifications) and a commit.
- Compliance is checked at the Constitution Check in `plan.md`, by `/speckit-analyze` before
  implementation, and by the harness after implementation.
- The human owner (Tejaswini Thambabathula) is accountable for the submitted software and makes the
  final acceptance decision.

**Version**: 1.0.0 | **Ratified**: 2026-11-14 | **Last Amended**: 2026-11-14
