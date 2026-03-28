"""Shared pytest fixtures for CogStash tests.

A single Tk instance is created once per session. Creating/destroying
multiple Tk() instances corrupts the Tcl interpreter on Windows
(Python 3.14+), causing sporadic 'tcl_findLibrary' errors.
"""

import tkinter as tk

import pytest

try:
    _session_root = tk.Tk()
    _session_root.withdraw()
    HAS_DISPLAY = True
except tk.TclError:
    _session_root = None
    HAS_DISPLAY = False

needs_display = pytest.mark.skipif(
    not HAS_DISPLAY, reason="No display or Tcl unavailable"
)


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
