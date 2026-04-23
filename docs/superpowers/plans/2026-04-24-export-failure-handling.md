# Export Failure Handling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden CLI export failure behavior so JSON, CSV, and Markdown export write failures produce a clear user-facing error and stable exit semantics instead of surfacing raw I/O exceptions.

**Architecture:** Keep the change local to `src/cogstash/cli/main.py`. Add one small private export-write boundary or local helper that centralizes final write execution and `OSError` handling, then add focused CLI tests for failure paths. Do not introduce a new module or widen the refactor into a general export redesign.

**Tech Stack:** Python 3.9+, pytest

---

## File / Artifact Map

- Modify: `src/cogstash/cli/main.py`
  - add export-local failure handling
  - keep success behavior unchanged
- Modify: `tests/cli/test_cli.py`
  - add failure-path regression tests for export
- Reference: `docs/superpowers/specs/2026-04-24-export-failure-handling-design.md`
  - scope and behavior contract for issue `#28`

## Baseline Verification

Before implementation starts, run:

```bash
uv run pytest tests/cli/test_cli.py -k "cmd_export" -q
```

Expected: current export success-path tests should pass before new failure tests are added.

## Task 1: Lock failure behavior with focused tests

**Files:**
- Modify: `tests/cli/test_cli.py`

- [ ] **Step 1: Add failing JSON export failure test**

Add a test that forces the JSON write path to raise `OSError` and verifies:

- `cmd_export()` exits with code `1`
- stderr contains `Error: failed to export notes to`
- stdout does not contain the success message

- [ ] **Step 2: Add failing CSV export failure test**

Add a test that forces the CSV file open or write path to raise `OSError` and verifies the same error contract.

- [ ] **Step 3: Add failing Markdown export failure test**

Add a test that forces the Markdown write path to raise `OSError` and verifies the same error contract.

- [ ] **Step 4: Run focused export tests to confirm red state**

Run only the new export-failure tests plus nearby export coverage.

Expected: FAIL before implementation because current code does not convert these failures into the target user-facing behavior.

## Task 2: Implement export-local failure handling

**Files:**
- Modify: `src/cogstash/cli/main.py`

- [ ] **Step 1: Add a small private export-write boundary**

Introduce a private helper or tightly scoped local boundary that:

- performs the format-specific write
- catches `OSError`
- prints a clear error to `stderr`
- exits with status `1`

Keep it private to export and avoid turning this into a shared generic I/O abstraction.

- [ ] **Step 2: Route JSON, CSV, and Markdown writes through the new boundary**

Apply the same failure semantics to all three export formats.

- [ ] **Step 3: Preserve success-path behavior**

Do not change:

- export payload content
- file naming behavior
- success message wording
- no-notes early return behavior

- [ ] **Step 4: Re-run focused export tests**

Expected: PASS.

- [ ] **Step 5: Commit the export hardening change**

Expected commit:

```bash
git add src/cogstash/cli/main.py tests/cli/test_cli.py
git commit -m "fix: harden export failure handling"
```

## Task 3: Run verification and prepare for review

**Files:**
- Verify: `src/cogstash/cli/main.py`
- Verify: `tests/cli/test_cli.py`

- [ ] **Step 1: Run targeted CLI verification**

Run:

```bash
uv run pytest tests/cli/test_cli.py -k "cmd_export" -q
```

Expected: PASS.

- [ ] **Step 2: Run quality checks for the modified scope**

Run the relevant linter/type-check commands for touched files.

Expected: PASS.

- [ ] **Step 3: Review the diff for scope control**

Confirm the change remains limited to:

- export-local error handling
- failure-path regression tests

- [ ] **Step 4: Summarize the branch outcome for issue `#28`**

Final review summary should call out:

1. export write failures now produce a clear error and exit code `1`
2. JSON, CSV, and Markdown paths share the same failure contract
3. failure-path tests now protect the user-facing behavior
