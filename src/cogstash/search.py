"""Compatibility wrapper for shared note helpers."""

from __future__ import annotations

from cogstash.core.notes import *  # noqa: F403
from cogstash.core.notes import _atomic_write as _core_atomic_write
from cogstash.core.notes import _note_line_span as _core_note_line_span

_atomic_write = _core_atomic_write
_note_line_span = _core_note_line_span
