from __future__ import annotations

import logging
import os
import subprocess
import sys

from cogstash.ui.install_state import get_startup_shortcut_path

logger = logging.getLogger("cogstash")


def configure_dpi() -> None:
    """Enable DPI awareness on Windows so the UI renders crisply on HiDPI displays."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        pass


def open_target_in_shell(target: str) -> None:
    """Open a URL or file path via the native platform shell."""
    if target.startswith("http"):
        import webbrowser

        webbrowser.open(target)
        return

    if sys.platform == "win32":
        os.startfile(target)
        return
    if sys.platform == "darwin":
        subprocess.run(["open", target], check=False)
        return
    subprocess.run(["xdg-open", target], check=False)


def set_launch_at_startup(enable: bool) -> None:
    """Enable or disable launch at system startup (Windows only)."""
    if sys.platform != "win32":
        return

    shortcut_path = get_startup_shortcut_path()
    if enable:
        exe = sys.executable
        if getattr(sys, "frozen", False):
            exe = sys.argv[0]
            content = f'@echo off\nstart "" "{exe}"\n'
        else:
            content = f'@echo off\nstart "" "{exe}" -m cogstash.ui\n'
        try:
            shortcut_path.parent.mkdir(parents=True, exist_ok=True)
            shortcut_path.write_text(content, encoding="utf-8")
        except OSError:
            logger.error("Failed to create startup shortcut", exc_info=True)
        return

    try:
        if shortcut_path.exists():
            shortcut_path.unlink()
    except OSError:
        logger.error("Failed to remove startup shortcut", exc_info=True)


__all__ = ["configure_dpi", "open_target_in_shell", "set_launch_at_startup"]
