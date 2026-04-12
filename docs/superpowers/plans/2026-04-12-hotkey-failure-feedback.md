# Hotkey Failure Feedback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add clear in-app feedback when global hotkey registration fails by showing a startup warning dialog and a persistent Settings warning for the current session.

**Architecture:** Keep this slice runtime-only. Detect the registration failure in `ui.app`, preserve the existing log/console output, and thread a small failure message through the live app/session state into `SettingsWindow` so the warning is visible without introducing new persisted config. Tests should lock both the startup modal behavior and the Settings warning copy.

**Tech Stack:** Python 3.9+, tkinter, pynput, pytest

---

## File Map

- Modify: `src/cogstash/ui/app.py`
  - capture hotkey registration failure details during startup
  - show a startup warning dialog
  - keep a runtime/session warning string on the app instance
  - pass the warning into Settings when opened
- Modify: `src/cogstash/ui/settings.py`
  - accept an optional hotkey failure warning input
  - render a visible warning block in General tab when present
- Modify: `tests/ui/test_app.py`
  - add focused startup-failure regression tests
- Modify: `tests/ui/test_settings.py`
  - add focused Settings warning tests

## Implementation notes

- This plan intentionally does **not** solve hotkey editing UX; that belongs to `#14`.
- The startup warning must be accurate with current behavior: users can inspect logs and adjust config, but not yet edit the hotkey directly in Settings.
- Keep the session state simple: one optional warning message string is enough.
- Do not persist this warning to config.

### Task 1: Lock startup failure UX with failing tests

**Files:**
- Modify: `tests/ui/test_app.py`
- Test: `tests/ui/test_app.py`

- [ ] **Step 1: Write a failing app test for startup warning on hotkey registration failure**

```python
def test_app_main_shows_warning_when_hotkey_registration_fails(monkeypatch, tmp_path):
    ...
    monkeypatch.setattr(app_mod.keyboard, "GlobalHotKeys", FailingListener)
    monkeypatch.setattr(app_mod.messagebox, "showwarning", lambda *a, **kw: warnings.append((a, kw)))
    ...
    app_mod.main()
    assert len(warnings) == 1
```

- [ ] **Step 2: Write a failing app test that startup still completes after the warning**

```python
def test_app_main_continues_startup_after_hotkey_registration_failure(monkeypatch, tmp_path):
    ...
    assert "CogStash is running." in output
    assert created_apps == [True]
```

- [ ] **Step 3: Write a failing app test that healthy startup does not show the warning**

```python
def test_app_main_does_not_show_hotkey_warning_when_registration_succeeds(monkeypatch, tmp_path):
    ...
    monkeypatch.setattr(app_mod.keyboard, "GlobalHotKeys", FakeListener)
    monkeypatch.setattr(app_mod.messagebox, "showwarning", lambda *a, **kw: warnings.append((a, kw)))
    ...
    app_mod.main()
    assert warnings == []
```

- [ ] **Step 4: Tighten the app warning assertions around real guidance copy**

The startup-warning test must verify the warning text includes:
- the configured hotkey
- that capture is unavailable for this session
- the log file path
- that another app may already be using the shortcut
- that platform permissions/accessibility hooks may be blocking registration
- that the user can change the hotkey in config for now, then restart CogStash

- [ ] **Step 5: Run the focused app tests to verify they fail**

Run: `uv run pytest tests\ui\test_app.py -k "hotkey_registration_failure or hotkey_warning" -v`
Expected: FAIL because no GUI warning or runtime warning state exists yet.

- [ ] **Step 6: Commit the red app tests**

```bash
git add tests/ui/test_app.py
git commit -m "test: cover hotkey registration failure feedback"
```

### Task 2: Lock Settings warning behavior with failing tests

**Files:**
- Modify: `tests/ui/test_settings.py`
- Modify: `tests/ui/test_app.py`
- Test: `tests/ui/test_settings.py`

- [ ] **Step 1: Write a failing Settings test for visible hotkey failure warning**

```python
@needs_display
def test_settings_shows_hotkey_registration_warning(tk_root, tmp_path):
    from cogstash.ui.app import CogStashConfig
    from cogstash.ui.settings import SettingsWindow

    sw = SettingsWindow(
        tk_root,
        CogStashConfig(),
        tmp_path / "test.json",
        hotkey_warning="Hotkey failed to register: <ctrl>+<shift>+<space>",
    )
    labels = [child.cget("text") for child in sw.tab_frames[0].winfo_children() if child.winfo_class() == "Label"]
    assert any("failed to register" in text for text in labels)
    sw.win.destroy()
```

- [ ] **Step 2: Write a failing Settings test that no warning is shown when there is no failure**

```python
@needs_display
def test_settings_hides_hotkey_warning_when_session_is_healthy(tk_root, tmp_path):
    ...
    assert not any("failed to register" in text for text in labels)
```

- [ ] **Step 3: Write a failing integration test in `tests/ui/test_app.py` that app state reaches Settings**

Add an app-level test that:
- simulates hotkey registration failure in `main()` / app startup flow
- opens Settings through `CogStash._open_settings()` or equivalent wiring point
- verifies the Settings warning receives the runtime failure state

- [ ] **Step 4: Tighten the Settings warning assertions around real guidance copy**

The Settings warning test must verify:
- it says the hotkey failed to register
- it says capture is unavailable until the issue is fixed/restarted
- it points to the log file
- it does **not** claim hotkey can already be edited in Settings

- [ ] **Step 5: Run the focused Settings tests to verify they fail**

Run: `uv run pytest tests\ui\test_settings.py -k "hotkey_warning" -v`
Expected: FAIL because `SettingsWindow` has no such parameter or warning block yet.

- [ ] **Step 6: Commit the red Settings tests**

```bash
git add tests/ui/test_settings.py
git commit -m "test: lock settings hotkey warning UX"
```

### Task 3: Implement runtime hotkey failure state and startup modal

**Files:**
- Modify: `src/cogstash/ui/app.py`
- Test: `tests/ui/test_app.py`

- [ ] **Step 1: Add a small runtime/session field for hotkey warning state**

Implementation shape:

```python
class CogStash:
    def __init__(...):
        ...
        self.hotkey_warning: str | None = None
```

- [ ] **Step 2: Pass the warning state into `SettingsWindow`**

Update `_open_settings()`:

```python
self._settings_win = SettingsWindow(
    self.root,
    self.config,
    self.config_path,
    on_config_changed=self._on_config_changed,
    hotkey_warning=self.hotkey_warning,
)
```

- [ ] **Step 3: On hotkey registration failure, build a user-facing warning string**

Implementation should include:
- configured hotkey
- log file path
- plain next-step guidance

- [ ] **Step 4: Show `messagebox.showwarning(...)` once during startup**

This must happen only on the failure path and must not prevent startup from completing.

- [ ] **Step 5: Keep existing logger + console output intact**

Do not remove:
- `logger.error(...)`
- `safe_print(...)`

- [ ] **Step 6: Re-run focused app tests until they pass**

Run: `uv run pytest tests\ui\test_app.py -k "hotkey_registration_failure or hotkey_warning" -v`
Expected: PASS

- [ ] **Step 7: Commit the app implementation**

```bash
git add src/cogstash/ui/app.py tests/ui/test_app.py
git commit -m "fix: surface hotkey registration failures"
```

### Task 4: Implement persistent Settings warning

**Files:**
- Modify: `src/cogstash/ui/settings.py`
- Test: `tests/ui/test_settings.py`

- [ ] **Step 1: Extend `SettingsWindow` to accept an optional `hotkey_warning`**

Implementation shape:

```python
def __init__(..., hotkey_warning: str | None = None):
    self.hotkey_warning = hotkey_warning
```

- [ ] **Step 2: Render a warning block near the General tab hotkey section**

The warning block should:
- be visually distinct
- state that the current hotkey failed to register
- explain that global capture is unavailable until restart/fix
- point to the log file / config path accurately

- [ ] **Step 3: Keep copy accurate with current product behavior**

Do **not** claim:
- hotkey can already be changed directly in Settings
- the warning persists across restarts

- [ ] **Step 4: Re-run focused Settings tests until they pass**

Run: `uv run pytest tests\ui\test_settings.py -k "hotkey_warning" -v`
Expected: PASS

- [ ] **Step 5: Commit the Settings implementation**

```bash
git add src/cogstash/ui/settings.py tests/ui/test_settings.py
git commit -m "feat: show persistent hotkey failure warning"
```

### Task 5: Full verification and issue tracking

**Files:**
- Modify: `docs/superpowers/specs/2026-04-12-hotkey-failure-feedback.md` only if review reveals spec drift
- Modify: `docs/superpowers/plans/2026-04-12-hotkey-failure-feedback.md` only if review reveals plan drift
- GitHub issue: `#15`

- [ ] **Step 1: Run the focused UX regression suite**

Run:

```bash
uv run pytest tests\ui\test_app.py -v
uv run pytest tests\ui\test_settings.py -v
```

Expected: PASS

- [ ] **Step 2: Run repository quality checks**

Run:

```bash
uv run ruff check src\ tests\
uv run mypy src\cogstash\
uv run pytest tests\ -q
```

Expected: PASS

- [ ] **Step 3: Update the child issue with spec/plan + execution status**

At minimum:
- link or reference the spec document
- link or reference the implementation plan
- note that implementation has started on the feature branch

- [ ] **Step 4: Request review before closing the child**

Review must confirm:
- startup modal appears only on failure
- startup still completes
- Settings warning is present only in the failed session
- runtime failure state is actually threaded from app startup into Settings
- copy is accurate and does not overpromise hotkey editing

- [ ] **Step 5: After review + push/PR, update and close the child issue**

At minimum:
- comment with what shipped
- link the PR
- close `#15`
