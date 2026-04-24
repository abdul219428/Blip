# UI App Decomposition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Decompose the broad startup and tray functions in `src/cogstash/ui/app.py` and trim a small amount of low-value indirection, while preserving current GUI/tray/hotkey behavior.

**Architecture:** Keep the work centered on `src/cogstash/ui/app.py`. Extract focused private helpers for tray image/menu startup and for main startup/bootstrap branches, then remove only the clearly low-value wrappers that directly support readability in the touched flow. Do not broaden this into a repo-wide cleanup.

**Tech Stack:** Python 3.9+, tkinter, threading, pytest

---

## File / Artifact Map

- Modify: `src/cogstash/ui/app.py`
  - decompose `create_tray_icon()`
  - decompose `main()`
  - trim local low-value indirection tied to the touched flow
- Modify: targeted UI tests
  - add or update regression coverage around startup/tray helpers where decomposition makes behavior easier to test
- Reference: `docs/superpowers/specs/2026-04-25-ui-app-decomposition-design.md`
  - scope and acceptance boundaries for issue `#30`

## Baseline Verification

Before implementation starts, run:

```bash
uv run pytest tests/ui -k "app or settings or tray or hotkey" -q
```

Expected: current UI/runtime-adjacent tests should pass before any refactor-driven edits begin.

## Task 1: Lock the behavior that decomposition must preserve

**Files:**
- Modify: existing UI tests only if focused behavior coverage is missing

- [ ] **Step 1: Identify behavior-sensitive flows owned by `ui/app.py`**

Target the flows most likely to regress when `main()` and `create_tray_icon()` are split:

- tray icon startup behavior
- hotkey registration failure warning behavior
- first-run / update dialog branching
- logger/config bootstrap ordering where already tested

- [ ] **Step 2: Add failing regression tests only where current coverage is too weak**

Prefer small behavior-level tests over implementation-detail tests. Add coverage only if existing tests do not already pin the critical ordering/branching.

- [ ] **Step 3: Run focused tests to confirm red state if new tests were added**

Expected: any new tests should fail before the refactor, or existing tests should already define enough protection to proceed without adding more.

## Task 2: Decompose `create_tray_icon()` into focused helpers

**Files:**
- Modify: `src/cogstash/ui/app.py`

- [ ] **Step 1: Extract tray image loading/generation helper(s)**

Split resource/icon logic into focused private helpers, for example:

- bundled icon load
- fallback icon generation

Keep behavior unchanged.

- [ ] **Step 2: Extract tray action/menu wiring helper(s)**

Split:

- platform-specific note opening
- menu item wiring
- tray thread startup

Avoid creating a new module; keep helpers private to `ui/app.py`.

- [ ] **Step 3: Re-run focused tray/UI tests**

Expected: PASS.

## Task 3: Decompose `main()` into startup helpers

**Files:**
- Modify: `src/cogstash/ui/app.py`

- [ ] **Step 1: Extract config/logger bootstrap helper(s)**

Move the startup config and logger setup into a focused private helper without changing behavior.

- [ ] **Step 2: Extract onboarding/update dialog flow helper(s)**

Move first-run / installer welcome / what’s-new branching into a focused helper that returns the updated config state needed by `main()`.

- [ ] **Step 3: Extract hotkey registration helper**

Move global hotkey registration and warning construction into a helper that clearly returns the listener (or `None`) and preserves current warning behavior.

- [ ] **Step 4: Keep `main()` as orchestration**

After extraction, `main()` should primarily:

- bootstrap
- instantiate app/root
- run tray + hotkey startup
- enter mainloop
- perform final cleanup

- [ ] **Step 5: Re-run focused UI tests**

Expected: PASS.

## Task 4: Trim low-value indirection in the touched flow

**Files:**
- Modify: `src/cogstash/ui/app.py`
- Optionally modify: one directly related caller file if the cleanup clearly supports the same readability goal

- [ ] **Step 1: Remove the clearest no-value alias/wrapper in the touched area**

Candidates include:

- alias-only re-export patterns inside `ui/app.py`
- tiny wrappers whose only job is `sorted(...)` or similar and which add no domain meaning

- [ ] **Step 2: Verify no external behavior depends on the removed indirection**

If a wrapper is externally imported or part of a compatibility story, leave it alone for this issue.

- [ ] **Step 3: Re-run tests covering the touched path**

Expected: PASS.

## Task 5: Run verification and prepare for review

**Files:**
- Verify: `src/cogstash/ui/app.py`
- Verify: touched tests

- [ ] **Step 1: Run targeted verification**

Run:

```bash
uv run pytest tests/ui -k "app or settings or tray or hotkey" -q
```

Expected: PASS.

- [ ] **Step 2: Run linter/type checks for the modified scope**

Run the relevant quality checks for touched files.

Expected: PASS.

- [ ] **Step 3: Review diff for scope control**

Confirm the change remains limited to:

- decomposing `create_tray_icon()`
- decomposing `main()`
- a very small amount of low-value indirection trimming

- [ ] **Step 4: Summarize the branch outcome for issue `#30`**

Final review summary should call out:

1. `ui/app.py` startup/tray flow is easier to read
2. behavior remains unchanged
3. only clearly low-value indirection was removed
