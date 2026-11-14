# CLI Contract: Smart Todo & Task CLI

Invocation: `python -m todo [--file PATH] <command> [arguments]`

Data file resolution: `--file PATH`, else environment variable `TODO_FILE`, else `./tasks.json`.

## Output rules (FR-015, FR-017)

- **Success**: exit code 0; stdout is exactly one line of JSON followed by a newline, keys sorted
  alphabetically; stderr is empty.
- **Failure**: exit code from the table below; stdout is empty; stderr is exactly one line of JSON
  `{"error": {"category": "<category>", "message": "<text>"}}` followed by a newline.
- A Task is rendered as `{"id": 1, "priority": "medium", "status": "todo", "tags": [], "title": "Buy milk"}`.

| Category | Exit code | When |
|----------|-----------|------|
| (success) | 0 | operation completed |
| `validation` | 2 | bad or missing argument, invalid title/priority/tag/status/id |
| `not_found` | 3 | no task with the given id |
| `invalid_transition` | 4 | status change not allowed by FR-008 |
| `storage` | 5 | data file corrupt or cannot be read or written |

## Error precedence

When more than one problem applies, exactly one error is reported, in this order:
1. usage (unknown command, missing argument, id not a positive integer) → `validation`
2. data file cannot be loaded → `storage`
3. invalid field value → `validation`
4. task id does not exist → `not_found`
5. status change not allowed → `invalid_transition`

## Commands

| Command | Arguments | Success stdout | FR |
|---------|-----------|----------------|----|
| `add` | `TITLE [--priority P] [--tag TAG]...` | the created Task | FR-001…FR-006 |
| `show` | `ID` | the Task | FR-007 |
| `list` | `[--tag TAG]... [--status S] [--sort id\|priority]` | JSON array of Tasks | FR-007, FR-011, FR-012 |
| `update` | `ID [--title T] [--priority P] [--tag TAG]... [--clear-tags]` | the updated Task | FR-009 |
| `move` | `ID STATUS` | the updated Task | FR-008 |
| `delete` | `ID` | `{"deleted": ID}` | FR-010 |

Notes:
- `update`: `--tag` replaces the whole tag set; `--clear-tags` sets it to empty; using both, or
  supplying no field at all, is a `validation` error.
- `list --sort`: any value other than `id` or `priority` is a `validation` error; default is `id`.
- A failed command never changes the data file (FR-016). A missing data file is an empty store and
  is created by the first successful write (FR-013).

## Data file format

UTF-8 JSON, 2-space indent, sorted keys:

```json
{
  "next_id": 2,
  "tasks": [
    {"id": 1, "priority": "medium", "status": "todo", "tags": [], "title": "Buy milk"}
  ]
}
```
