"""Shared UI test fixtures and desktop runtime stubs."""

from __future__ import annotations

import tkinter as tk

import pytest

try:
    _session_root = tk.Tk()
    _session_root.withdraw()
    HAS_DISPLAY = True
except tk.TclError:
    _session_root = None
    HAS_DISPLAY = False

needs_display = pytest.mark.skipif(not HAS_DISPLAY, reason="No display or Tcl unavailable")

try:
    import pynput
except Exception:
    pynput = None

try:
    import pystray
except Exception:
    pystray = None


def pytest_sessionstart(session):
    """Prevent real hotkey listeners and tray threads during UI tests."""
    if pynput is not None:
        try:

            class _FakeListener:
                def __init__(self, mapping=None):
                    self.started = False

                def start(self):
                    self.started = True

                def stop(self):
                    self.started = False

            pynput.keyboard.GlobalHotKeys = _FakeListener
        except Exception:
            pass

    if pystray is not None:
        try:

            class _FakeIcon:
                def __init__(self, *args, **kwargs):
                    pass

                def run(self):
                    return None

            pystray.Icon = _FakeIcon
        except Exception:
            pass


@pytest.fixture
def tk_root():
    """Yield a shared Tk root, resetting children between tests."""
    if not HAS_DISPLAY:
        pytest.skip("No display or Tcl unavailable")
    _session_root.overrideredirect(False)
    _session_root.withdraw()
    for child in _session_root.winfo_children():
        child.destroy()
    yield _session_root
    for child in _session_root.winfo_children():
        child.destroy()


def pytest_sessionfinish(session, exitstatus):
    """Destroy the shared Tk root at the end of the session."""
    global _session_root
    if _session_root is not None:
        try:
            _session_root.destroy()
        except tk.TclError:
            pass
        _session_root = None
