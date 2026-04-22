# Windows Responsibility Boundaries Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Consolidate UI-only Windows runtime helpers into a dedicated owner while preserving the existing split between CLI Windows helpers, UI mutex/process helpers, installer-state readers, and installer-time side effects.

**Architecture:** Keep `cogstash.cli.windows` focused on CLI console attach, keep `cogstash.ui.windows` focused on single-instance primitives, keep `cogstash.ui.install_state` focused on installer-derived runtime state, and introduce `cogstash.ui.windows_runtime` for GUI-runtime Windows actions currently embedded in `ui.app` and `ui.settings`. Preserve behavior and compatibility while moving the implementation seams to clearer owners.

**Tech Stack:** Python 3.9+, tkinter, pytest, ruff

---

## File / Artifact Map

- Create: `src/cogstash/ui/windows_runtime.py`
  - own GUI-runtime Windows helpers such as DPI setup, shell/open-target behavior, and startup-script mutation
- Modify: `src/cogstash/ui/app.py`
  - delegate Windows runtime actions through `ui.windows_runtime`
- Modify: `src/cogstash/ui/settings.py`
  - delegate startup-script mutation and shell opening through `ui.windows_runtime`
- Modify: `tests/ui/test_app.py`
  - lock DPI delegation to `ui.windows_runtime`
- Modify: `tests/ui/test_settings.py`
  - lock startup-toggle and link-opening delegation to `ui.windows_runtime`
- Verify: `tests/ui/test_app_compat.py`
  - existing compatibility coverage remains valid
- Verify: `tests/cli/test_main.py`
  - CLI Windows bootstrap remains unchanged
- Verify: `tests/test_build_installer.py`
  - installer ownership contract remains unchanged
- Reference: `docs/superpowers/specs/2026-04-22-windows-responsibility-boundaries-design.md`
  - approved scope for issue `#23`

## Baseline Verification

Before implementation starts, run:

```bash
python -m pytest tests/ui/test_app.py tests/ui/test_settings.py -q
```

Expected: PASS on the current branch before adding new ownership tests.

## Task 1: Lock the new Windows-runtime ownership with failing tests

**Files:**
- Modify: `tests/ui/test_app.py`
- Modify: `tests/ui/test_settings.py`

- [ ] **Step 1: Add a failing app startup delegation test**

Add a test proving `app.main()` uses `cogstash.ui.windows_runtime.configure_dpi()` rather than owning the DPI implementation inline.

- [ ] **Step 2: Add a failing settings startup-toggle delegation test**

Add a test proving `SettingsWindow._save_general()` delegates startup mutation to `cogstash.ui.windows_runtime.set_launch_at_startup()`.

- [ ] **Step 3: Add a failing settings shell-open delegation test**

Add a test proving `SettingsWindow._open_link()` delegates to `cogstash.ui.windows_runtime.open_target_in_shell()`.

- [ ] **Step 4: Run the focused red tests**

Run:

```bash
python -m pytest tests/ui/test_app.py -k windows_runtime -q
python -m pytest tests/ui/test_settings.py -k windows_runtime -q
```

Expected: FAIL because `cogstash.ui.windows_runtime` does not exist yet.

## Task 2: Introduce `ui.windows_runtime` and wire app/settings through it

**Files:**
- Create: `src/cogstash/ui/windows_runtime.py`
- Modify: `src/cogstash/ui/app.py`
- Modify: `src/cogstash/ui/settings.py`

- [ ] **Step 1: Add the new owner module**

Create `src/cogstash/ui/windows_runtime.py` with these helpers:

- `configure_dpi()`
- `open_target_in_shell(target: str)`
- `set_launch_at_startup(enable: bool)`

- [ ] **Step 2: Delegate app Windows runtime behavior**

Update `src/cogstash/ui/app.py` so:

- DPI setup goes through `ui.windows_runtime`
- tray “Open notes” behavior uses `open_target_in_shell()`
- any retained local helper is only a thin forwarder, not the real owner

- [ ] **Step 3: Delegate settings Windows runtime behavior**

Update `src/cogstash/ui/settings.py` so:

- startup toggle writes/removes the script through `ui.windows_runtime.set_launch_at_startup()`
- About/settings link opening goes through `ui.windows_runtime.open_target_in_shell()`

- [ ] **Step 4: Run the focused ownership tests**

Run:

```bash
python -m pytest tests/ui/test_app.py -k windows_runtime -q
python -m pytest tests/ui/test_settings.py -k windows_runtime -q
```

Expected: PASS.

## Task 3: Verify the full Windows-responsibility surface

**Files:**
- Verify: `tests/ui/test_app.py`
- Verify: `tests/ui/test_settings.py`
- Verify: `tests/ui/test_app_compat.py`
- Verify: `tests/cli/test_main.py`
- Verify: `tests/test_build_installer.py`

- [ ] **Step 1: Run the broader regression set**

Run:

```bash
python -m pytest tests/ui/test_app.py tests/ui/test_settings.py tests/ui/test_app_compat.py tests/cli/test_main.py tests/test_build_installer.py -q
```

Expected: PASS.

- [ ] **Step 2: Run lint**

Run:

```bash
python -m ruff check src/ tests/
```

Expected: PASS.

- [ ] **Step 3: Review the diff for boundary correctness**

Confirm the branch now reflects:

- `cli.windows` for CLI console attach
- `ui.windows` for GUI mutex/process primitives
- `ui.install_state` for installer-derived runtime state
- `ui.windows_runtime` for GUI-runtime Windows actions
- installer-side artifact writes still owned by `installer/windows/CogStash.iss`
