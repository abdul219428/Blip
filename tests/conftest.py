"""Shared pytest fixtures for CogStash tests.

A single Tk instance is created once per session. Creating/destroying
multiple Tk() instances corrupts the Tcl interpreter on Windows
(Python 3.14+), causing sporadic 'tcl_findLibrary' errors.
"""

import tkinter as tk

import pytest


class CaptureStream:
    def __init__(self):
        self.parts = []

    def write(self, text):
        self.parts.append(text)
        return len(text)

    def flush(self):
        pass

    def getvalue(self):
        return "".join(self.parts)


class StrictEncodedStream(CaptureStream):
    def __init__(self, encoding: str):
        super().__init__()
        self.encoding = encoding

    def write(self, text):
        text.encode(self.encoding)
        return super().write(text)


try:
    _session_root = tk.Tk()
    _session_root.withdraw()
    HAS_DISPLAY = True
except tk.TclError:
    _session_root = None
    HAS_DISPLAY = False

needs_display = pytest.mark.skipif(not HAS_DISPLAY, reason="No display or Tcl unavailable")

# Defensive test-time stubs: prevent real OS/global listeners or tray icons from
# starting during tests which can hang CI (pynput, pystray create background
# threads that may not be stopped in test environments).
try:
    import pynput
except Exception:
    pynput = None

try:
    import pystray
except Exception:
    pystray = None


def pytest_sessionstart(session):
    """Session-level safety: replace GlobalHotKeys and Icon.run with no-op
    implementations so accidental starts don't spawn blocking threads during
    CI runs or in headless environments.
    """
    # Patch pynput.keyboard.GlobalHotKeys to a fake that does nothing
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
            # Best-effort; tests that explicitly patch GlobalHotKeys can override
            pass

    # Patch pystray.Icon.run to a no-op to avoid creating tray threads
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
    """Yield the shared Tk root, resetting state between tests."""
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
    """Destroy the shared Tk root at end of session."""
    global _session_root
    if _session_root is not None:
        try:
            _session_root.destroy()
        except tk.TclError:
            pass
        _session_root = None
