"""Compatibility shim for the legacy ``cogstash.app`` import surface.

The owning implementation lives in ``cogstash.ui.app``. Keep this module as a
temporary re-export layer for compatibility while internal code imports the UI
module directly.
"""

from __future__ import annotations

from cogstash.ui.app import *  # noqa: F401,F403
