"""Compatibility shim for the legacy ``cogstash.browse`` import surface.

The owning implementation lives in ``cogstash.ui.browse``. Keep this module as
a temporary re-export layer for compatibility while internal code imports the
UI module directly.
"""

from __future__ import annotations

from cogstash.ui.browse import *  # noqa: F401,F403
