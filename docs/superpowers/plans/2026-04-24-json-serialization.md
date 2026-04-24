# JSON Serialization Helper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove repeated JSON serialization behavior by defining one shared serializer contract in `src/cogstash/core/config.py` and reusing it from the config and CLI flows that currently hand-roll pretty JSON output.

**Architecture:** Keep JSON parsing local to each caller. Add one small shared helper boundary in `src/cogstash/core/config.py` for pretty JSON string generation and UTF-8 file writes, then reuse it from config creation/saving and CLI JSON-producing paths. Do not introduce a new helper module or expand this change into broader I/O refactors.

**Tech Stack:** Python 3.9+, stdlib `json`, pytest

---

## File / Artifact Map

- Modify: `src/cogstash/core/config.py`
  - add shared JSON serialization helpers
  - reuse them in default config creation and `save_config()`
- Modify: `src/cogstash/core/__init__.py`
  - export helpers only if needed by CLI imports
- Modify: `src/cogstash/cli/main.py`
  - replace repeated pretty JSON serialization and file writes with shared helpers
- Modify: targeted tests under `tests/core/` and `tests/cli/`
  - add regression coverage for formatting policy reuse
- Reference: `docs/superpowers/specs/2026-04-24-json-serialization-design.md`
  - scope and behavior contract for issue `#27`

## Baseline Verification

Before implementation starts, run:

```bash
uv run pytest tests/core/test_config.py tests/cli/test_cli.py -k "config or export" -q
```

Expected: current config and CLI export coverage should pass before new tests are added.

## Task 1: Lock the serialization contract with focused tests

**Files:**
- Modify: `tests/core/test_config.py`
- Modify: `tests/cli/test_cli.py`

- [ ] **Step 1: Add failing core-config tests for shared JSON policy**

Add focused tests that verify:

- saved config preserves Unicode characters
- saved config uses readable multi-line pretty JSON
- default config creation follows the same serialization contract

Prefer asserting both parsed JSON content and at least one formatting property so the test can catch policy drift.

- [ ] **Step 2: Add failing CLI tests for shared JSON policy**

Add or extend tests to verify:

- JSON export preserves Unicode and remains pretty-printed
- `config set` writes valid pretty JSON
- dictionary-valued `config get` output remains formatted consistently

- [ ] **Step 3: Run focused tests to confirm red state**

Run only the new or adjacent config/export tests.

Expected: FAIL before implementation because the shared helpers do not exist yet and the repeated call sites are still inline.

## Task 2: Implement shared helpers in `core.config`

**Files:**
- Modify: `src/cogstash/core/config.py`
- Modify: `src/cogstash/core/__init__.py` if needed

- [ ] **Step 1: Add the shared serializer helpers**

Implement a minimal helper boundary such as:

```python
def to_pretty_json(data: object) -> str:
    ...


def write_json_file(path: Path, data: object) -> None:
    ...
```

Contract:

- `indent=2`
- `ensure_ascii=False`
- UTF-8 file writes

- [ ] **Step 2: Reuse the helpers in config save paths**

Replace inline JSON serialization in:

- default config creation inside `load_config()`
- `save_config()`

Keep current directory-creation behavior and error handling semantics intact.

- [ ] **Step 3: Export intentionally**

If CLI imports the helpers through `cogstash.core`, export only the names that are actually needed. Avoid widening the public surface beyond this issue’s scope.

- [ ] **Step 4: Run focused core-config tests**

Expected: PASS.

- [ ] **Step 5: Commit the config-layer refactor**

Expected commit:

```bash
git add src/cogstash/core/config.py src/cogstash/core/__init__.py tests/core/test_config.py
git commit -m "refactor: share json serialization helpers"
```

## Task 3: Replace CLI duplication with the shared contract

**Files:**
- Modify: `src/cogstash/cli/main.py`
- Modify: `tests/cli/test_cli.py`

- [ ] **Step 1: Reuse the helpers in CLI JSON-producing paths**

Replace inline pretty-JSON serialization in:

- `cmd_export()` JSON branch
- `_config_wizard()` write path
- `cmd_config()` set write path
- dictionary-valued `cmd_config(get ...)` pretty-print path where appropriate

Leave JSON parsing local to the CLI functions.

- [ ] **Step 2: Preserve behavior outside serialization**

Do not change:

- export payload shape
- config key validation
- parse error fallback behavior
- non-JSON export paths

- [ ] **Step 3: Run focused CLI tests**

Run config/export coverage after the CLI reuse change.

Expected: PASS.

- [ ] **Step 4: Commit the CLI reuse change if separate from Task 2**

Expected commit:

```bash
git add src/cogstash/cli/main.py tests/cli/test_cli.py
git commit -m "refactor: reuse json serialization contract in cli"
```

## Task 4: Run verification and prepare for review

**Files:**
- Verify: `src/cogstash/core/config.py`
- Verify: `src/cogstash/cli/main.py`
- Verify: touched tests

- [ ] **Step 1: Run targeted verification**

Run:

```bash
uv run pytest tests/core/test_config.py tests/cli/test_cli.py -k "config or export" -q
```

Expected: PASS.

- [ ] **Step 2: Run linter/type checks for the modified scope**

Run the relevant checks for touched files.

Expected: PASS.

- [ ] **Step 3: Review the diff for scope control**

Confirm the change stays limited to:

- shared JSON serialization helpers
- config write-path reuse
- CLI JSON-producing reuse
- focused regression coverage

- [ ] **Step 4: Summarize the branch outcome for issue `#27`**

Final review summary should call out:

1. one shared pretty JSON serialization contract
2. config and CLI reuse it
3. Unicode/indent/UTF-8 behavior is now tested and explicit
