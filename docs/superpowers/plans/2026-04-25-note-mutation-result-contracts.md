# Note Mutation Result Contracts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace coarse boolean note mutation results with a small explicit status contract so CLI and UI callers can distinguish stale-note conflicts, invalid input, already-done cases, and real I/O failures.

**Architecture:** Keep the result contract in `src/cogstash/core/notes.py` with the mutation helpers. Update direct callers in `src/cogstash/cli/main.py` and `src/cogstash/ui/browse.py` to map statuses to clearer behavior. Keep the contract lightweight; do not introduce a large result-object hierarchy.

**Tech Stack:** Python 3.9+, `Enum` or equivalent typed statuses, pytest

---

## File / Artifact Map

- Modify: `src/cogstash/core/notes.py`
  - add the shared mutation status contract
  - update `mark_done()`, `edit_note()`, and `delete_note()` to return statuses
- Modify: `src/cogstash/core/__init__.py`
  - export the status type if callers import through `cogstash.core`
- Modify: `src/cogstash/cli/main.py`
  - map mutation statuses to clearer CLI behavior/messages
- Modify: `src/cogstash/ui/browse.py`
  - map mutation statuses to clearer UI behavior/messages
- Modify: tests under `tests/core/`, `tests/cli/`, and `tests/ui/`
  - add status-level coverage and caller behavior coverage
- Reference: `docs/superpowers/specs/2026-04-25-note-mutation-result-contracts-design.md`
  - scope and contract for issue `#29`

## Baseline Verification

Before implementation starts, run:

```bash
uv run pytest tests/core/test_notes.py tests/cli/test_cli.py tests/ui/test_browse_extended.py -k "mark_done or edit_note or delete_note" -q
```

Expected: current mutation-path coverage should pass before new result-contract tests are added.

## Task 1: Lock the new status contract with focused tests

**Files:**
- Modify: `tests/core/test_notes.py`
- Modify: any duplicated mutation-path tests under `tests/core/test_search.py` if needed

- [ ] **Step 1: Add failing core tests for status-returning helpers**

Add focused tests that verify:

- `mark_done()` returns `SUCCESS` on mutation
- `mark_done()` returns `STALE_NOTE` for mismatched/stale notes
- `mark_done()` returns `ALREADY_DONE` when no checkbox transition is available
- `edit_note()` returns `INVALID_INPUT` for blank replacement text
- `edit_note()` / `delete_note()` return `STALE_NOTE` for mismatched notes
- write failures return `IO_ERROR`

- [ ] **Step 2: Keep the status set intentionally small**

Make sure tests only lock statuses that are genuinely useful to callers. Avoid speculative extra statuses.

- [ ] **Step 3: Run focused core tests to confirm red state**

Expected: FAIL before implementation because the helpers still return booleans.

## Task 2: Implement the mutation status contract in `core.notes`

**Files:**
- Modify: `src/cogstash/core/notes.py`
- Modify: `src/cogstash/core/__init__.py` if needed

- [ ] **Step 1: Add the shared mutation status type**

Implement a small status contract, preferably an `Enum`, with the approved statuses:

- `SUCCESS`
- `STALE_NOTE`
- `INVALID_INPUT`
- `ALREADY_DONE`
- `IO_ERROR`

- [ ] **Step 2: Update mutation helpers to return statuses**

Apply the contract to:

- `mark_done()`
- `edit_note()`
- `delete_note()`

Map outcomes carefully:

- note mismatch / moved line → `STALE_NOTE`
- blank edit text → `INVALID_INPUT`
- mark-done on already complete note → `ALREADY_DONE`
- write/read `OSError` → `IO_ERROR`
- successful mutation → `SUCCESS`

- [ ] **Step 3: Export the contract intentionally**

If callers need the status type through `cogstash.core`, export only what is needed.

- [ ] **Step 4: Run focused core verification**

Expected: PASS.

- [ ] **Step 5: Commit the notes-layer contract change**

Expected commit:

```bash
git add src/cogstash/core/notes.py src/cogstash/core/__init__.py tests/core/test_notes.py
git commit -m "refactor: define note mutation result statuses"
```

## Task 3: Update CLI callers to consume statuses

**Files:**
- Modify: `src/cogstash/cli/main.py`
- Modify: `tests/cli/test_cli.py`

- [ ] **Step 1: Update CLI mutation commands**

Update `cmd_edit()` and `cmd_delete()` to branch on returned statuses instead of treating all failures as identical.

Caller expectations:

- `SUCCESS` keeps current success path
- `STALE_NOTE` produces a clearer “note changed or no longer matches” style message
- `INVALID_INPUT` remains a validation-style message where relevant
- `IO_ERROR` remains a real failure message

- [ ] **Step 2: Add/adjust focused CLI tests**

Add tests that prove the CLI surfaces different messages for stale-note conflicts versus real write failures where applicable.

- [ ] **Step 3: Re-run focused CLI tests**

Expected: PASS.

## Task 4: Update browse UI callers to consume statuses

**Files:**
- Modify: `src/cogstash/ui/browse.py`
- Modify: `tests/ui/test_browse_extended.py`

- [ ] **Step 1: Update browse mutation handlers**

Update:

- `_on_mark_done()`
- edit flow handler
- delete flow handler

to respond to the new statuses with clearer notices instead of generic failure handling.

- [ ] **Step 2: Add/adjust focused UI tests**

Cover at least the most important user-visible branches:

- stale-note path
- already-done path
- I/O failure path

- [ ] **Step 3: Re-run focused UI tests**

Expected: PASS.

## Task 5: Run verification and prepare for review

**Files:**
- Verify: `src/cogstash/core/notes.py`
- Verify: `src/cogstash/cli/main.py`
- Verify: `src/cogstash/ui/browse.py`
- Verify: touched tests

- [ ] **Step 1: Run targeted mutation-path verification**

Run:

```bash
uv run pytest tests/core/test_notes.py tests/cli/test_cli.py tests/ui/test_browse_extended.py -k "mark_done or edit_note or delete_note" -q
```

Expected: PASS.

- [ ] **Step 2: Run linter/type checks for modified scope**

Run the relevant quality checks for touched files.

Expected: PASS.

- [ ] **Step 3: Review diff for scope control**

Confirm the change stays limited to:

- the note mutation status contract
- direct caller adoption in CLI/UI
- focused regression tests

- [ ] **Step 4: Summarize the branch outcome for issue `#29`**

Final review summary should call out:

1. note mutations now return explicit statuses instead of booleans
2. CLI and UI distinguish expected conflicts from real failures
3. the contract stays lightweight and is protected by focused tests
