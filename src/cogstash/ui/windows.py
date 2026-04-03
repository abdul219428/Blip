from __future__ import annotations

import sys
from typing import Any, cast

WINDOWS_MUTEX_NAME = r"Local\CogStash.SingleInstance"
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

            kernel32: Any = cast(Any, ctypes).windll.kernel32
            kernel32.CloseHandle(self.handle)
            self.handle = 0


def acquire_single_instance(name: str = WINDOWS_MUTEX_NAME):
    """Return a GUI instance guard, or None when another CogStash UI owns the mutex."""
    if sys.platform != "win32":
        return _NullInstanceGuard()

    import ctypes

    kernel32: Any = cast(Any, ctypes).windll.kernel32
    handle = kernel32.CreateMutexW(None, False, name)
    if not handle:
        raise OSError("Could not create CogStash single-instance mutex.")
    if kernel32.GetLastError() == _ERROR_ALREADY_EXISTS:
        kernel32.CloseHandle(handle)
        return None
    return _WindowsMutexGuard(handle)
