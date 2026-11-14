# Data Model: Smart Todo & Task CLI

## Task

| Field | Type | Rules | Source |
|-------|------|-------|--------|
| id | integer | ≥ 1, unique, assigned from `next_id`, never reused, immutable | FR-005 |
| title | string | trimmed; 1–100 characters after trimming | FR-002 |
| priority | string | one of `low`, `medium`, `high`; default `medium` | FR-003 |
| status | string | one of `todo`, `in_progress`, `done`; starts as `todo` | FR-006, FR-008 |
| tags | list of strings | 0–10 items; each 1–20 chars matching `[A-Za-z0-9-]+`; stored lower-case, unique, sorted ascending | FR-004 |

## Task Store

| Field | Type | Rules |
|-------|------|-------|
| next_id | integer | ≥ 1 and greater than every task id |
| tasks | list of Task | ids unique; stored in ascending id order |

A document that is not valid JSON, or that breaks any rule in the two tables above, is a corrupt
store (FR-014).

## Status transitions (FR-008)

| From \ To | todo | in_progress | done |
|-----------|------|-------------|------|
| todo | invalid | **allowed** | invalid |
| in_progress | **allowed** | invalid | **allowed** |
| done | invalid | invalid | invalid |

A target that is not one of the three status values is a validation error, not an invalid
transition.

## Ordering (FR-012)

- Default: ascending `id`.
- `priority`: rank high=0, medium=1, low=2; sort by (rank, id).

## Filtering (FR-011)

A task is returned when (no tag filter, or every filter tag, lower-cased, is in `tags`) and
(no status filter, or `status` equals the filter). Filter tags and the status filter are validated
with the same rules as stored values.
