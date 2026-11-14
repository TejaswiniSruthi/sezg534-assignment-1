# Feature Specification: Smart Todo & Task CLI

**Feature Branch**: `001-smart-todo-cli`

**Created**: 2026-11-14

**Status**: Approved by the human owner on 2026-11-14 (spec, plan, contracts and tasks reviewed)

**Input**: User description: "Build a Smart Todo & Task command-line tool for a single user. The user can create, view, update and delete tasks; give each task a priority and tags; filter tasks by tag; sort tasks by priority; and move a task through its statuses. Tasks are saved to a local file and are still there the next time the tool runs. Behaviour must be fully deterministic so that every acceptance criterion can be checked with an exact pass/fail test. Exclude due dates, reminders, multiple users, authentication and any network feature."

## Clarifications

### Session 2026-11-14

- Q: Which status changes are allowed between todo, in_progress and done? → A: todo→in_progress, in_progress→done, and in_progress→todo (pause). "done" is final. todo→done is rejected.
- Q: When several tags are given in a filter, must a task have all of them or any of them? → A: All of them (AND).
- Q: What happens when the data file exists but cannot be understood? → A: Stop with a "storage" error and leave the file untouched.
- Q: What is the default list order? → A: Creation order (ascending id). Priority order only when requested.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Capture and review tasks (Priority: P1)

A user records a task with a title, an optional priority and optional tags, and can later see that
task again, either on its own or in the full list, even after closing and reopening the tool.

**Why this priority**: Without creating, saving and reading tasks nothing else has value. This slice
alone is a usable task list.

**Independent Test**: Create two tasks, restart the tool, list tasks, and confirm both are returned
with the exact field values that were entered.

**Acceptance Scenarios**:

1. **AS-1.1** **Given** an empty task store, **When** the user creates a task with title
   "Buy milk", **Then** the result is a task with id 1, title "Buy milk", priority "medium",
   status "todo" and no tags.
2. **AS-1.2** **Given** a store containing task 1, **When** the user creates a task with title
   "Pay rent", priority "high" and tags "Home" and "bills", **Then** the result is a task with id 2,
   priority "high" and tags exactly ["bills", "home"].
3. **AS-1.3** **Given** two tasks were created in an earlier run, **When** the tool is started
   again and the user lists tasks, **Then** both tasks are returned with unchanged field values.
4. **AS-1.4** **Given** a store containing task 1, **When** the user views task 1, **Then** exactly
   that task is returned; **When** the user views task 99, **Then** a "not found" error is reported
   and nothing is changed.
5. **AS-1.5** **Given** any store, **When** the user creates a task with an empty title, a title
   longer than 100 characters, a priority other than low/medium/high, or an invalid tag, **Then** a
   "validation" error is reported and the store is unchanged.
6. **AS-1.6** **Given** the data file contains text that is not a valid task store, **When** the
   user runs any operation, **Then** a "storage" error is reported and the file is unchanged.
7. **AS-1.7** **Given** no data file exists, **When** the user lists tasks, **Then** an empty list
   is returned and no error is reported.

---

### User Story 2 - Progress, edit and remove tasks (Priority: P2)

A user moves a task through its statuses as work proceeds, corrects its details, and removes tasks
that are no longer needed.

**Why this priority**: Tracking progress is the main purpose of a task tool, but it depends on tasks
existing first.

**Independent Test**: Create a task, move it through each allowed status, attempt a disallowed
move, edit its title, delete it, and confirm each outcome exactly.

**Acceptance Scenarios**:

1. **AS-2.1** **Given** task 1 has status "todo", **When** the user starts it, **Then** its status
   is "in_progress"; **When** the user then completes it, **Then** its status is "done".
2. **AS-2.2** **Given** a task with status "todo", **When** the user requests "done", **Then** an
   "invalid transition" error is reported and the task is unchanged. The same holds for every
   change from "done" (to todo or in_progress) and for a change to the status the task already has.
6. **AS-2.6** **Given** task 1 has status "in_progress", **When** the user moves it back to "todo",
   **Then** its status is "todo".
7. **AS-2.7** **Given** task 1 exists, **When** the user requests a status that is not todo,
   in_progress or done, **Then** a "validation" error is reported and the task is unchanged.
3. **AS-2.3** **Given** task 1 exists, **When** the user updates its title, priority or tags with
   valid values, **Then** only the supplied fields change and its id and status are unchanged.
4. **AS-2.4** **Given** tasks 1 and 2 exist, **When** the user deletes task 1 and then creates a new
   task, **Then** task 1 can no longer be viewed and the new task has id 3 (ids are never reused).
5. **AS-2.5** **Given** task 1 exists, **When** the user updates it with an invalid value, **Then**
   a "validation" error is reported and the task is unchanged.

---

### User Story 3 - Find the right task (Priority: P3)

A user narrows the list to tasks with a given tag or status and orders it so the most important
tasks come first.

**Why this priority**: Filtering and sorting only matter once there are several tasks to manage.

**Independent Test**: Create several tasks with mixed tags and priorities, then filter and sort and
compare the returned ids with the exact expected sequence.

**Acceptance Scenarios**:

1. **AS-3.1** **Given** tasks 1 (tags: home), 2 (tags: work) and 3 (tags: home, urgent), **When**
   the user filters by tag "home", **Then** exactly tasks 1 and 3 are returned.
2. **AS-3.2** **Given** the same tasks, **When** the user filters by tag "HOME", **Then** the result
   is identical to filtering by "home".
3. **AS-3.3** **Given** tasks 1 (low), 2 (high), 3 (medium) and 4 (high), **When** the user asks for
   the list sorted by priority, **Then** the order of ids is exactly 2, 4, 3, 1.
4. **AS-3.4** **Given** tasks in different statuses, **When** the user filters by status "done",
   **Then** exactly the tasks with status "done" are returned.
5. **AS-3.5** **Given** any store, **When** a filter matches no task, **Then** an empty list is
   returned and no error is reported.
6. **AS-3.6** **Given** tasks 1 (tags: home), 2 (tags: work) and 3 (tags: home, urgent), **When**
   the user filters by tags "home" and "urgent" together, **Then** exactly task 3 is returned.
7. **AS-3.7** **Given** tasks 1 (low) and 2 (high) and no sort request, **When** the user lists
   tasks, **Then** the order of ids is exactly 1, 2.

---

### Edge Cases

- A title that contains only spaces is treated as empty and rejected.
- Leading and trailing spaces in a title are removed before the length is checked and stored.
- The same tag supplied twice, or in different letter case, is stored once.
- The data file does not exist yet: the store is treated as empty.
- The data file exists but cannot be understood: a storage error, file untouched (FR-014).
- Deleting or changing a task id that does not exist reports "not found" and changes nothing.
- A task id that is not a positive whole number written with the digits 0-9 is a validation
  error. This includes other digit characters such as "²" or "٣" (added 2026-11-14 after review of
  the first passing harness run found that "²" crashed the tool instead of reporting an error).
- Priority and status values are matched exactly: "HIGH" or "Done" is a validation error. Only tags
  are case-insensitive.
- Filtering by more than one tag at once returns only tasks with all of the tags (FR-011).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST let the user create a task with a title (required), a priority
  (optional) and tags (optional).
- **FR-002**: A title MUST be 1 to 100 characters after leading and trailing spaces are removed.
- **FR-003**: A priority MUST be one of "low", "medium" or "high"; when omitted it MUST be "medium".
- **FR-004**: A task MUST have 0 to 10 tags. Each tag MUST be 1 to 20 characters using only letters,
  digits and hyphens. Tags MUST be stored in lower case, without duplicates, in alphabetical order.
- **FR-005**: Each new task MUST receive the next whole-number id, starting at 1. An id MUST never
  be reused, even after its task is deleted.
- **FR-006**: Each new task MUST start with status "todo".
- **FR-007**: The system MUST let the user view one task by id and list all tasks.
- **FR-008**: The system MUST let the user change a task's status only along these transitions:
  todo→in_progress, in_progress→done and in_progress→todo. Every other requested change, including
  todo→done, any change from "done", and a change to the status the task already has, MUST be
  rejected as an "invalid transition". A status value other than todo, in_progress or done MUST be
  rejected as a "validation" error.
- **FR-009**: The system MUST let the user update the title, priority and tags of a task under the
  same validation rules as creation; fields that are not supplied MUST stay unchanged.
- **FR-010**: The system MUST let the user permanently delete a task by id.
- **FR-011**: The system MUST let the user filter the list by tag (case-insensitive) and by status.
  When several tags are given, only tasks that have all of them MUST be returned. When a tag filter
  and a status filter are both given, a task MUST satisfy both.
- **FR-012**: The list MUST be returned in ascending id order by default. When sorting by priority
  is requested, the order MUST be high, then medium, then low, with ties in ascending id order.
- **FR-013**: Every successful create, update, status change and delete MUST be saved so that it is
  present the next time the tool runs. A missing data file MUST be treated as an empty store.
- **FR-014**: When the data file exists but cannot be understood, the system MUST report a
  "storage" error for every operation and MUST leave the file byte-for-byte unchanged.
- **FR-015**: Every failure MUST be reported as exactly one of four categories: "validation",
  "not found", "invalid transition" or "storage". Each category MUST be distinguishable by a program
  without reading the message text.
- **FR-016**: A failed operation MUST leave the stored tasks exactly as they were before it.
- **FR-017**: Successful results MUST be produced in a structured, machine-readable form with the
  fields id, title, priority, status and tags.

### Key Entities

- **Task**: one unit of work. Attributes: id (whole number, unique, never reused), title, priority
  (low | medium | high), status (todo | in_progress | done), tags (set of lower-case labels).
- **Task Store**: the saved collection of all tasks plus the next id to assign.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of the acceptance scenarios AS-1.1 to AS-3.7 are verified by automated checks
  that give the same result on every run.
- **SC-002**: Running the same sequence of commands twice from an empty store produces identical
  output both times.
- **SC-003**: After any rejected operation, the saved data is identical to the saved data before it,
  in 100% of tested cases.
- **SC-004**: A user can create a task and see it in the list in two commands, with no setup other
  than choosing where tasks are saved.
- **SC-005**: Every functional requirement FR-001 to FR-017 is traceable to at least one automated
  check.

## Assumptions

- One user works with one task store at a time; simultaneous use by several processes is out of
  scope.
- Due dates, reminders, timestamps, recurring tasks, sub-tasks, authentication and any network
  feature are out of scope.
- Task descriptions (long free text) are out of scope; the title is the only text field.
- Deleting is immediate and permanent; there is no confirmation step and no undo.
- A store of up to 1,000 tasks is sufficient for this version.
