"""Installer-aware onboarding helpers for CogStash.

Centralises detection of installed-Windows-run vs source/portable, and
keeps startup-script state accessible without polluting app.py or settings.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

from cogstash.core.config import CogStashConfig

INSTALL_MARKER_NAME = ".cogstash-installed"


def _install_marker_path() -> Path:
    """Return the installer marker path next to the running executable."""
    return Path(sys.executable).resolve().parent / INSTALL_MARKER_NAME


def is_installed_windows_run() -> bool:
    """Return True when running as a frozen (PyInstaller) Windows installed build."""
    return sys.platform == "win32" and bool(getattr(sys, "frozen", False)) and _install_marker_path().exists()


def should_show_installer_welcome(config: CogStashConfig, version: str) -> bool:
    """Return True when we should show the installer-welcome dialog.

    Conditions:
    - Running as the installed Windows app (frozen exe).
    - An existing config exists, i.e. ``last_seen_version`` is non-empty
      (new users with no config see the full first-run wizard instead).
    - The installer-specific recorded version differs from *version* (covers
      both upgrades and a first installed launch over an existing config from
      a previous portable/source run).
    """
    if not is_installed_windows_run():
        return False
    if config.last_seen_version == "":
        return False
    return config.last_seen_installer_version != version


def startup_script_exists() -> bool:
    """Return True if the installer-managed startup batch script is present on disk."""
    if sys.platform != "win32":
        return False
    from cogstash.ui.settings import get_startup_shortcut_path  # lazy — avoids circular import

    return get_startup_shortcut_path().exists()


__all__ = [
    "is_installed_windows_run",
    "should_show_installer_welcome",
    "startup_script_exists",
]
