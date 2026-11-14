# Data Model: Natural-Language Reminder Agent

## Result (Output Schema Contract)

Machine-readable form: [contracts/output-schema.json](./contracts/output-schema.json).

| Field | Type | Rules |
|-------|------|-------|
| intent | string | `create` \| `reschedule` \| `snooze` \| `unknown` |
| task | string \| null | 1–120 characters |
| datetime | string \| null | `YYYY-MM-DDTHH:MM`, a real date-time |
| snooze_minutes | integer \| null | 1–1440 (not a boolean) |
| requires_clarification | boolean | |
| missing_fields | array of string | items from `task`, `date`, `time`; unique |
| clarification_question | string \| null | 1–200 characters |

No other field is allowed.

## Unknown result (INV-2)

```json
{"intent": "unknown", "task": null, "datetime": null, "snooze_minutes": null,
 "requires_clarification": false, "missing_fields": [], "clarification_question": null}
```

## Result states

| State | intent | requires_clarification | task | datetime | snooze_minutes |
|-------|--------|------------------------|------|----------|----------------|
| Scheduled | create / reschedule | false | set | set, in (now, now + 366 days] | null |
| Snoozed | snooze | false | any | null | set |
| Needs clarification | create / reschedule / snooze | true | set or null | null | null |
| Unknown | unknown | false | null | null | null |

## Agent outcome (not part of the contract object)

| Field | Meaning |
|-------|---------|
| result | the contract object returned to the caller |
| source | `model` (reply accepted), `precheck` (decided without the model), `fallback` (reply rejected) |
| raw_reply | the model's text, or null |
| violations | list of rule ids that caused a fallback |

## Evaluation case

| Field | Meaning |
|-------|---------|
| id | `C01` … |
| category | `normal`, `boundary`, `ambiguous`, `missing`, `malformed`, `adversarial` |
| message | the user's sentence |
| cites | requirement / invariant / scenario ids exercised |
| expected.intent | expected intent |
| expected.datetime / snooze_minutes / missing_fields | exactly one slot expectation (none for unknown) |
| expected.task_keywords, task_forbidden | key words for BP-3 |
| expected.task | `"null"` when the task must be absent, `"any"` when it is not judged |
