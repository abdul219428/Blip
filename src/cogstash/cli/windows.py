from __future__ import annotations

import sys
from typing import Any, TextIO, cast

_ATTACH_PARENT_PROCESS = -1
_ERROR_ACCESS_DENIED = 5


def _open_console_stream(name: str, mode: str) -> TextIO:
    return cast(TextIO, open(name, mode, encoding="utf-8", errors="replace", buffering=1))


def prepare_windows_cli_console() -> None:
    """Attach a Windows CLI process to the parent console when stdio is missing."""
    if sys.platform != "win32":
        return
    if sys.stdin is not None and sys.stdout is not None and sys.stderr is not None:
        return

    import ctypes

    kernel32: Any = cast(Any, ctypes).windll.kernel32
    attached = kernel32.AttachConsole(_ATTACH_PARENT_PROCESS)
    if not attached and kernel32.GetLastError() != _ERROR_ACCESS_DENIED:
        return

    if sys.stdin is None:
        sys.stdin = _open_console_stream("CONIN$", "r")
    if sys.stdout is None:
        sys.stdout = _open_console_stream("CONOUT$", "w")
    if sys.stderr is None:
        sys.stderr = _open_console_stream("CONOUT$", "w")


__all__ = ["prepare_windows_cli_console"]
