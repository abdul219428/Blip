"""Compatibility shim for the legacy ``cogstash._windows`` import surface.

The owning implementations live in ``cogstash.cli.windows`` and
``cogstash.ui.windows``. Keep this module as a narrow compatibility layer while
internal code imports the owning modules directly.
"""

from __future__ import annotations

from cogstash.cli.windows import prepare_windows_cli_console
from cogstash.ui.windows import WINDOWS_MUTEX_NAME, acquire_single_instance

__all__ = ["prepare_windows_cli_console", "WINDOWS_MUTEX_NAME", "acquire_single_instance"]
