from __future__ import annotations

import sys
from typing import Any, TextIO, cast

WINDOWS_MUTEX_NAME = r"Local\CogStash.SingleInstance"
_ATTACH_PARENT_PROCESS = -1
_ERROR_ACCESS_DENIED = 5
_ERROR_ALREADY_EXISTS = 183


class _NullInstanceGuard:
    def close(self) -> None:
        return None


class _WindowsMutexGuard:
    def __init__(self, handle: int):
        self.handle = handle

    def close(self) -> None:
        if self.handle:
            import ctypes

            kernel32: Any = ctypes.windll.kernel32
            kernel32.CloseHandle(self.handle)
            self.handle = 0


def _open_console_stream(name: str, mode: str) -> TextIO:
    return cast(TextIO, open(name, mode, encoding="utf-8", errors="replace", buffering=1))


def prepare_windows_cli_console() -> None:
    """Attach a GUI-subsystem Windows process to the parent console for CLI mode."""
    if sys.platform != "win32":
        return
    if sys.stdin is not None and sys.stdout is not None and sys.stderr is not None:
        return

    import ctypes

    kernel32: Any = ctypes.windll.kernel32
    attached = kernel32.AttachConsole(_ATTACH_PARENT_PROCESS)
    if not attached and kernel32.GetLastError() != _ERROR_ACCESS_DENIED:
        return

    if sys.stdin is None:
        sys.stdin = _open_console_stream("CONIN$", "r")
    if sys.stdout is None:
        sys.stdout = _open_console_stream("CONOUT$", "w")
    if sys.stderr is None:
        sys.stderr = _open_console_stream("CONOUT$", "w")


def acquire_single_instance(name: str = WINDOWS_MUTEX_NAME):
    """Return a guard for the current GUI instance, or None if one already exists."""
    if sys.platform != "win32":
        return _NullInstanceGuard()

    import ctypes

    kernel32: Any = ctypes.windll.kernel32
    handle = kernel32.CreateMutexW(None, False, name)
    if not handle:
        raise OSError("Could not create CogStash single-instance mutex.")
    if kernel32.GetLastError() == _ERROR_ALREADY_EXISTS:
        kernel32.CloseHandle(handle)
        return None
    return _WindowsMutexGuard(handle)
