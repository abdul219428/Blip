# Wrapper Boundaries and Direct Imports Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make root-level wrapper modules explicitly compatibility-only while migrating internal code and non-compatibility tests to direct owning-layer imports.

**Architecture:** Keep the external wrapper files in place, but stop relying on them for normal internal behavior. The implementation should move note/config imports toward `cogstash.core` and UI implementation imports toward `cogstash.ui.*`, while preserving wrapper coverage in dedicated compatibility tests such as `tests/ui/test_app_compat.py`.

**Tech Stack:** Python 3.9+, tkinter, pytest, ruff

---

## File / Artifact Map

- Modify: `src/cogstash/ui/browse.py`
  - replace `cogstash.search` imports with owning `cogstash.core` / `cogstash.core.notes` imports
  - keep true UI-owned imports in `cogstash.ui.app`
- Modify: `src/cogstash/ui/settings.py`
  - move clearly core-owned imports off `cogstash.ui.app`
  - keep true UI-owned imports in `cogstash.ui.app`
- Modify: `src/cogstash/app.py`
  - add compatibility-shim module docstring
- Modify: `src/cogstash/browse.py`
  - add compatibility-shim module docstring
- Modify: `src/cogstash/settings.py`
  - add compatibility-shim module docstring
- Modify: `src/cogstash/search.py`
  - add compatibility-shim module docstring
- Modify: `src/cogstash/_windows.py`
  - add compatibility-shim module docstring
- Modify: `tests/core/test_search.py`
  - migrate implementation tests to `cogstash.core.notes`
  - keep wrapper-compatibility assertions only where compatibility is the point
- Modify: `tests/cli/test_cli.py`
  - migrate `Note` imports to `cogstash.core`
- Modify: `tests/ui/test_browse_extended.py`
  - migrate implementation tests to `cogstash.ui.app` and `cogstash.ui.browse`
- Modify: `tests/ui/test_settings_extended.py`
  - migrate implementation tests to `cogstash.ui.app` and `cogstash.ui.settings`
- Reference: `docs/superpowers/specs/2026-04-22-wrapper-policy-and-direct-imports-design.md`
  - approved scope for issues `#21` and `#22`

## Baseline Verification

Before implementation starts, run:

```bash
python -m pytest tests/core/test_search.py tests/ui/test_browse_extended.py tests/ui/test_settings_extended.py tests/cli/test_cli.py -q
```

Expected: PASS on the current branch before new tests or import-path edits.

## Task 1: Lock the new import policy with failing tests

**Files:**
- Modify: `tests/core/test_search.py`
- Modify: `tests/ui/test_browse_extended.py`
- Modify: `tests/ui/test_settings_extended.py`
- Modify: `tests/cli/test_cli.py`

- [ ] **Step 1: Add a core-ownership regression test for note helpers**

Add a focused test in `tests/core/test_search.py` that imports from `cogstash.core.notes` and asserts the core API remains directly usable for parse/search/edit flows.

- [ ] **Step 2: Migrate one Browse test to owning-layer imports**

Change one representative Browse test to import `CogStashConfig` from `cogstash.ui.app` or `cogstash.core` and `BrowseWindow` from `cogstash.ui.browse`.

- [ ] **Step 3: Migrate one Settings test to owning-layer imports**

Change one representative Settings test to import `CogStashConfig` from `cogstash.ui.app` or `cogstash.core` and `SettingsWindow` from `cogstash.ui.settings`.

- [ ] **Step 4: Migrate one CLI test to `cogstash.core.Note`**

Replace a representative `from cogstash.search import Note` import with `from cogstash.core import Note`.

- [ ] **Step 5: Run focused tests to verify they fail only because production imports are not fully migrated yet**

Run:

```bash
python -m pytest tests/core/test_search.py tests/ui/test_browse_extended.py tests/ui/test_settings_extended.py tests/cli/test_cli.py -q
```

Expected: at least one failure or import mismatch caused by the new owning-layer expectations.

- [ ] **Step 6: Commit the red tests**

```bash
git add tests/core/test_search.py tests/ui/test_browse_extended.py tests/ui/test_settings_extended.py tests/cli/test_cli.py
git commit -m "test: lock direct import ownership"
```

## Task 2: Move production imports to owning layers

**Files:**
- Modify: `src/cogstash/ui/browse.py`
- Modify: `src/cogstash/ui/settings.py`

- [ ] **Step 1: Update Browse imports**

In `src/cogstash/ui/browse.py`, replace `cogstash.search` imports with direct owning-layer imports:

- `DEFAULT_TAG_COLORS`, `Note`, `delete_note`, `edit_note`, `filter_by_tag`, `mark_done`, `parse_notes`, `search_notes` from `cogstash.core`
- `_atomic_write` from `cogstash.core.notes`

Keep `THEMES` and `platform_font` from `cogstash.ui.app` because they are UI-owned.

- [ ] **Step 2: Update Settings imports**

In `src/cogstash/ui/settings.py`, move clearly core-owned imports off `cogstash.ui.app`:

- `DEFAULT_SMART_TAGS`, `CogStashConfig`, `merge_tags`, `save_config` from `cogstash.core`

Keep `THEMES`, `WINDOW_SIZES`, `logger`, and `platform_font` from `cogstash.ui.app` because they remain UI-owned in this slice.

- [ ] **Step 3: Run focused tests to verify green**

Run:

```bash
python -m pytest tests/core/test_search.py tests/ui/test_browse_extended.py tests/ui/test_settings_extended.py tests/cli/test_cli.py -q
```

Expected: PASS.

- [ ] **Step 4: Commit the direct-import implementation**

```bash
git add src/cogstash/ui/browse.py src/cogstash/ui/settings.py tests/core/test_search.py tests/ui/test_browse_extended.py tests/ui/test_settings_extended.py tests/cli/test_cli.py
git commit -m "refactor: use owning layer imports"
```

## Task 3: Make wrapper intent explicit without changing behavior

**Files:**
- Modify: `src/cogstash/app.py`
- Modify: `src/cogstash/browse.py`
- Modify: `src/cogstash/settings.py`
- Modify: `src/cogstash/search.py`
- Modify: `src/cogstash/_windows.py`
- Verify: `tests/ui/test_app_compat.py`
- Verify: `tests/core/test_search.py`

- [ ] **Step 1: Add compatibility-shim docstrings**

Add short module docstrings describing each root-level wrapper as a temporary compatibility shim and naming the real owning module.

- [ ] **Step 2: Keep existing re-export behavior unchanged**

Do not remove star imports, helper aliases, or `__all__` in this task. The purpose is policy clarity, not API removal.

- [ ] **Step 3: Run wrapper-focused compatibility tests**

Run:

```bash
python -m pytest tests/ui/test_app_compat.py tests/core/test_search.py -q
```

Expected: PASS, including wrapper re-export assertions.

- [ ] **Step 4: Commit the wrapper-policy clarification**

```bash
git add src/cogstash/app.py src/cogstash/browse.py src/cogstash/settings.py src/cogstash/search.py src/cogstash/_windows.py
git commit -m "docs: mark root wrappers as compatibility shims"
```

## Task 4: Full verification and issue update preparation

**Files:**
- Verify: touched source files and tests for this slice

- [ ] **Step 1: Run the full targeted regression set**

Run:

```bash
python -m pytest tests/core/test_search.py tests/ui/test_app_compat.py tests/ui/test_browse_extended.py tests/ui/test_settings_extended.py tests/cli/test_cli.py tests/cli/test_main.py -q
```

Expected: PASS.

- [ ] **Step 2: Run repo lint for touched files**

Run:

```bash
python -m ruff check src/ tests/
```

Expected: PASS.

- [ ] **Step 3: Review the diff for scope**

Confirm the branch only covers:

- wrapper intent documentation
- direct import migration
- test migration away from wrappers where compatibility is not the subject

- [ ] **Step 4: Prepare issue and PR notes**

Record that this slice covers:

- issue `#21` wrapper role definition
- issue `#22` direct owning-layer import migration
- no changes yet for issues `#23`, `#24`, or `#25`
