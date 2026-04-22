# UI Queue And Thread Lifecycle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract a dedicated UI runtime module that owns queue commands, tray and hotkey wiring, queue dispatch, and runtime shutdown while preserving existing app behavior.

**Architecture:** Keep `src/cogstash/ui/app.py` focused on Tk UI behavior and startup flow, and introduce `src/cogstash/ui/app_runtime.py` as the single boundary for cross-thread command flow. The new module will define the command contract, expose queue dispatch helpers, and return handles for startup and shutdown so `main()` no longer open-codes lifecycle behavior.

**Tech Stack:** Python, Tkinter, `queue`, `threading`, `pynput`, `pystray`, `pytest`, `monkeypatch`

---

## File Map

- Create: `src/cogstash/ui/app_runtime.py`
  Purpose: own command definitions, queue drain/dispatch, tray startup, hotkey startup, and runtime cleanup handles.
- Modify: `src/cogstash/ui/app.py`
  Purpose: delegate queue polling and runtime startup/shutdown to `app_runtime.py`, keeping only UI behavior and startup warning UX.
- Create: `tests/ui/test_app_runtime.py`
  Purpose: focused contract tests for queue dispatch, tray/hotkey enqueue behavior, startup results, and safe cleanup.
- Modify: `tests/ui/test_app.py`
  Purpose: update startup tests to assert delegation into `app_runtime.py` and preserve current hotkey warning/startup behavior.

### Task 1: Add focused runtime-contract tests

**Files:**
- Create: `tests/ui/test_app_runtime.py`

- [ ] **Step 1: Write the failing queue-dispatch tests**

```python
from __future__ import annotations

import queue

import cogstash.ui.app_runtime as runtime


def test_drain_queue_dispatches_supported_commands():
    app_queue: queue.Queue[runtime.AppCommand] = queue.Queue()
    app_queue.put(runtime.AppCommand.SHOW)
    app_queue.put(runtime.AppCommand.BROWSE)
    app_queue.put(runtime.AppCommand.SETTINGS)
    app_queue.put(runtime.AppCommand.QUIT)

    events: list[str] = []

    should_continue = runtime.drain_app_queue(
        app_queue,
        on_show=lambda: events.append("show"),
        on_browse=lambda: events.append("browse"),
        on_settings=lambda: events.append("settings"),
        on_quit=lambda: events.append("quit"),
    )

    assert events == ["show", "browse", "settings", "quit"]
    assert should_continue is False


def test_drain_queue_ignores_unknown_commands():
    app_queue: queue.Queue[object] = queue.Queue()
    app_queue.put("UNKNOWN")

    events: list[str] = []

    should_continue = runtime.drain_app_queue(
        app_queue,
        on_show=lambda: events.append("show"),
        on_browse=lambda: events.append("browse"),
        on_settings=lambda: events.append("settings"),
        on_quit=lambda: events.append("quit"),
    )

    assert events == []
    assert should_continue is True


def test_drain_queue_handles_empty_queue():
    app_queue: queue.Queue[runtime.AppCommand] = queue.Queue()

    should_continue = runtime.drain_app_queue(
        app_queue,
        on_show=lambda: None,
        on_browse=lambda: None,
        on_settings=lambda: None,
        on_quit=lambda: None,
    )

    assert should_continue is True
```

- [ ] **Step 2: Run the runtime queue tests to verify they fail**

Run: `python -m pytest tests/ui/test_app_runtime.py -k "drain_queue" -q`
Expected: FAIL with `ModuleNotFoundError` for `cogstash.ui.app_runtime` or missing `AppCommand`/`drain_app_queue`.

- [ ] **Step 3: Write the failing startup and cleanup tests**

```python
from __future__ import annotations

import queue
from types import SimpleNamespace

import cogstash.ui.app_runtime as runtime


def test_register_hotkey_listener_enqueues_show_command(monkeypatch):
    app_queue: queue.Queue[runtime.AppCommand] = queue.Queue()

    created_mappings: list[dict] = []

    class FakeListener:
        def __init__(self, mapping):
            created_mappings.append(mapping)
            self.started = False

        def start(self):
            self.started = True

    monkeypatch.setattr(runtime.keyboard, "GlobalHotKeys", FakeListener)

    listener = runtime.start_hotkey_listener(app_queue, "<ctrl>+<alt>+space")

    hotkey_callback = created_mappings[0]["<ctrl>+<alt>+space"]
    hotkey_callback()

    assert listener.started is True
    assert app_queue.get_nowait() is runtime.AppCommand.SHOW


def test_shutdown_runtime_stops_listener_and_tray():
    stopped: list[str] = []

    runtime.shutdown_runtime(
        runtime.AppRuntimeHandles(
            tray_icon=SimpleNamespace(stop=lambda: stopped.append("tray")),
            hotkey_listener=SimpleNamespace(stop=lambda: stopped.append("hotkey")),
        )
    )

    assert stopped == ["tray", "hotkey"]


def test_shutdown_runtime_tolerates_missing_handles():
    runtime.shutdown_runtime(runtime.AppRuntimeHandles())
```

- [ ] **Step 4: Run the startup and cleanup tests to verify they fail**

Run: `python -m pytest tests/ui/test_app_runtime.py -k "hotkey or shutdown_runtime" -q`
Expected: FAIL because `start_hotkey_listener`, `shutdown_runtime`, or `AppRuntimeHandles` are undefined.

- [ ] **Step 5: Commit the red tests checkpoint**

```bash
git add tests/ui/test_app_runtime.py
git commit -m "test: define app runtime contract"
```

### Task 2: Implement the runtime boundary module

**Files:**
- Create: `src/cogstash/ui/app_runtime.py`
- Test: `tests/ui/test_app_runtime.py`

- [ ] **Step 1: Create command types, handles, and queue drain implementation**

```python
from __future__ import annotations

import logging
import queue
from dataclasses import dataclass
from enum import Enum
from typing import Callable

from pynput import keyboard

logger = logging.getLogger("cogstash")


class AppCommand(str, Enum):
    SHOW = "SHOW"
    BROWSE = "BROWSE"
    SETTINGS = "SETTINGS"
    QUIT = "QUIT"


@dataclass
class AppRuntimeHandles:
    tray_icon: object | None = None
    hotkey_listener: object | None = None


def enqueue_command(app_queue: queue.Queue[AppCommand], command: AppCommand) -> None:
    app_queue.put(command)


def drain_app_queue(
    app_queue: queue.Queue[object],
    *,
    on_show: Callable[[], None],
    on_browse: Callable[[], None],
    on_settings: Callable[[], None],
    on_quit: Callable[[], None],
) -> bool:
    while True:
        try:
            command = app_queue.get_nowait()
        except queue.Empty:
            return True

        if command is AppCommand.SHOW:
            on_show()
        elif command is AppCommand.BROWSE:
            on_browse()
        elif command is AppCommand.SETTINGS:
            on_settings()
        elif command is AppCommand.QUIT:
            on_quit()
            return False
        else:
            logger.warning("Ignoring unknown app command: %r", command)
```

- [ ] **Step 2: Add tray and hotkey startup helpers plus cleanup**

```python
from pathlib import Path
import sys
import threading

from cogstash.core import CogStashConfig
from cogstash.ui import windows_runtime


def start_hotkey_listener(
    app_queue: queue.Queue[AppCommand],
    hotkey: str,
):
    listener = keyboard.GlobalHotKeys(
        {hotkey: lambda: enqueue_command(app_queue, AppCommand.SHOW)}
    )
    listener.start()
    return listener


def start_tray_icon(
    app_queue: queue.Queue[AppCommand],
    config: CogStashConfig,
    *,
    themes: dict[str, dict[str, str]],
):
    try:
        import pystray
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        logger.warning("pystray or Pillow not installed — skipping tray icon")
        return None

    theme = themes[config.theme]

    def open_notes():
        windows_runtime.open_target_in_shell(str(config.output_file))

    def browse_notes():
        enqueue_command(app_queue, AppCommand.BROWSE)

    def open_settings():
        enqueue_command(app_queue, AppCommand.SETTINGS)

    def quit_app(icon):
        icon.stop()
        enqueue_command(app_queue, AppCommand.QUIT)

    # keep existing icon-generation logic unchanged here
    icon = pystray.Icon("cogstash", img, "CogStash", menu)
    threading.Thread(target=icon.run, daemon=True).start()
    return icon


def start_runtime(
    app_queue: queue.Queue[AppCommand],
    config: CogStashConfig,
    *,
    themes: dict[str, dict[str, str]],
) -> AppRuntimeHandles:
    return AppRuntimeHandles(
        tray_icon=start_tray_icon(app_queue, config, themes=themes),
        hotkey_listener=None,
    )


def shutdown_runtime(handles: AppRuntimeHandles) -> None:
    if handles.tray_icon is not None:
        handles.tray_icon.stop()
    if handles.hotkey_listener is not None:
        handles.hotkey_listener.stop()
```

- [ ] **Step 3: Run the focused runtime tests and make them pass**

Run: `python -m pytest tests/ui/test_app_runtime.py -q`
Expected: PASS

- [ ] **Step 4: Commit the runtime boundary module**

```bash
git add src/cogstash/ui/app_runtime.py tests/ui/test_app_runtime.py
git commit -m "feat: extract app runtime lifecycle contract"
```

### Task 3: Refactor `app.py` to delegate queue and runtime lifecycle

**Files:**
- Modify: `src/cogstash/ui/app.py`
- Test: `tests/ui/test_app.py`

- [ ] **Step 1: Replace raw queue usage in `CogStash` with runtime delegation**

```python
from cogstash.ui import app_runtime, windows_runtime


class CogStash:
    def __init__(self, root: tk.Tk, config: CogStashConfig, config_path: Path | None = None):
        ...
        self.queue: queue.Queue[app_runtime.AppCommand] = queue.Queue()
        ...

    def poll_queue(self):
        should_continue = app_runtime.drain_app_queue(
            self.queue,
            on_show=self.show_window,
            on_browse=self._open_browse,
            on_settings=self._open_settings,
            on_quit=self.root.quit,
        )
        if should_continue:
            self.root.after(100, self.poll_queue)
```

- [ ] **Step 2: Move tray and hotkey startup/shutdown in `main()` behind runtime helpers**

```python
def main():
    ...
    app = CogStash(root, config)
    app.config_path = config_path

    runtime_handles = app_runtime.start_runtime(
        app.queue,
        config,
        themes=THEMES,
    )

    try:
        runtime_handles.hotkey_listener = app_runtime.start_hotkey_listener(
            app.queue,
            config.hotkey,
        )
    except Exception:
        app.hotkey_warning = _build_hotkey_failure_warning(config)
        logger.error("Failed to register global hotkey %s", config.hotkey, exc_info=True)
        ...

    try:
        root.mainloop()
    except KeyboardInterrupt:
        safe_print("\nCogStash stopped.")
    finally:
        app_runtime.shutdown_runtime(runtime_handles)
        instance_guard.close()
```

- [ ] **Step 3: Remove or collapse obsolete lifecycle helpers from `app.py`**

```python
# delete create_tray_icon() from app.py entirely after its tests move to app_runtime

def configure_dpi() -> None:
    """Compatibility forwarder for UI Windows runtime DPI setup."""
    windows_runtime.configure_dpi()
```

- [ ] **Step 4: Update startup tests to assert runtime delegation**

```python
def test_app_main_continues_startup_after_hotkey_registration_failure(monkeypatch, tmp_path):
    import cogstash.ui.app as app_mod
    import cogstash.ui.app_runtime as runtime_mod

    started_handles = runtime_mod.AppRuntimeHandles()

    monkeypatch.setattr(app_mod.app_runtime, "start_runtime", lambda *_a, **_k: started_handles)
    monkeypatch.setattr(
        app_mod.app_runtime,
        "start_hotkey_listener",
        lambda *_a, **_k: (_ for _ in ()).throw(OSError("hotkey already in use")),
    )
    monkeypatch.setattr(app_mod.app_runtime, "shutdown_runtime", lambda _handles: None)

    _config, output, warnings, created_apps = _run_main_startup(monkeypatch, tmp_path, listener_cls=None)

    assert len(warnings) == 1
    assert "CogStash is running." in output
    assert created_apps == [True]
```

- [ ] **Step 5: Run the app startup tests for delegation behavior**

Run: `python -m pytest tests/ui/test_app.py -k "startup or hotkey_warning or duplicate_instance" -q`
Expected: PASS

- [ ] **Step 6: Commit the app delegation refactor**

```bash
git add src/cogstash/ui/app.py tests/ui/test_app.py
git commit -m "refactor: delegate ui runtime lifecycle"
```

### Task 4: Verify queue behavior at the app seam

**Files:**
- Modify: `tests/ui/test_app.py`
- Modify: `tests/ui/test_settings_extended.py`

- [ ] **Step 1: Add a focused app poll test that proves the runtime dispatcher is used**

```python
@needs_display
def test_poll_queue_delegates_to_app_runtime(monkeypatch, tk_root):
    import cogstash.ui.app as app_mod

    app = app_mod.CogStash(tk_root, app_mod.CogStashConfig())
    called: list[object] = []

    def fake_drain(app_queue, **callbacks):
        called.append(app_queue)
        callbacks["on_show"]()
        return False

    monkeypatch.setattr(app_mod.app_runtime, "drain_app_queue", fake_drain)
    app.show_window = lambda: called.append("show")

    app.poll_queue()

    assert called[0] is app.queue
    assert called[1] == "show"
```

- [ ] **Step 2: Update any queue message tests to use `AppCommand` instead of raw strings where appropriate**

```python
@needs_display
def test_settings_queue_message(tk_root):
    from cogstash.app import CogStash, CogStashConfig
    from cogstash.ui.app_runtime import AppCommand

    app = CogStash(tk_root, CogStashConfig())
    app.queue.put(AppCommand.SETTINGS)
    opened = []
    app._open_settings = lambda: opened.append(True)

    app.poll_queue()

    assert opened == [True]
```

- [ ] **Step 3: Run the queue-behavior seam tests**

Run: `python -m pytest tests/ui/test_app.py tests/ui/test_settings_extended.py -k "poll_queue or settings_queue_message" -q`
Expected: PASS

- [ ] **Step 4: Commit the seam-level queue test updates**

```bash
git add tests/ui/test_app.py tests/ui/test_settings_extended.py
git commit -m "test: cover runtime queue delegation"
```

### Task 5: Full verification and finish

**Files:**
- Verify: `src/cogstash/ui/app_runtime.py`
- Verify: `src/cogstash/ui/app.py`
- Verify: `tests/ui/test_app_runtime.py`
- Verify: `tests/ui/test_app.py`
- Verify: `tests/ui/test_settings_extended.py`

- [ ] **Step 1: Run lint on changed source and tests**

Run: `python -m ruff check src/cogstash/ui/app.py src/cogstash/ui/app_runtime.py tests/ui/test_app.py tests/ui/test_app_runtime.py tests/ui/test_settings_extended.py`
Expected: PASS with no diagnostics.

- [ ] **Step 2: Run the focused verification suite**

Run: `python -m pytest tests/ui/test_app_runtime.py tests/ui/test_app.py tests/ui/test_settings_extended.py tests/ui/test_app_compat.py tests/cli/test_main.py tests/test_build_installer.py -q`
Expected: PASS

- [ ] **Step 3: Inspect diff before final commit**

Run: `git diff -- src/cogstash/ui/app.py src/cogstash/ui/app_runtime.py tests/ui/test_app.py tests/ui/test_app_runtime.py tests/ui/test_settings_extended.py`
Expected: only the planned runtime-boundary and test changes.

- [ ] **Step 4: Commit the verified slice if any verification fixes were needed**

```bash
git add src/cogstash/ui/app.py src/cogstash/ui/app_runtime.py tests/ui/test_app.py tests/ui/test_app_runtime.py tests/ui/test_settings_extended.py
git commit -m "test: finalize ui runtime lifecycle coverage"
```

- [ ] **Step 5: Prepare handoff notes**

```text
Summarize:
- new runtime contract module added
- app.py now delegates queue drain and lifecycle startup/shutdown
- tray and hotkey wiring use the shared command contract
- verification commands and results
```
