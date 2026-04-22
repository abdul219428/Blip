"""Compatibility shim for the legacy ``cogstash.search`` import surface.

The owning implementation lives in ``cogstash.core.notes``. Keep this module
as a temporary re-export layer for compatibility while internal code imports
the core module directly.
"""

from __future__ import annotations

from cogstash.core.notes import *  # noqa: F403
from cogstash.core.notes import _atomic_write as _core_atomic_write
from cogstash.core.notes import _note_line_span as _core_note_line_span

_atomic_write = _core_atomic_write
_note_line_span = _core_note_line_span
