"""Shared CogStash core APIs."""

from __future__ import annotations

from .config import (
    VALID_THEMES,
    VALID_WINDOW_SIZES,
    CogStashConfig,
    get_default_config_path,
    load_config,
    save_config,
)
from .notes import (
    DEFAULT_SMART_TAGS,
    DEFAULT_TAG_COLORS,
    Note,
    append_note_to_file,
    compute_stats,
    count_tags,
    delete_note,
    edit_note,
    filter_by_tag,
    mark_done,
    merge_tags,
    parse_notes,
    parse_smart_tags,
    search_notes,
)
from .output import safe_print

__all__ = [
    "CogStashConfig",
    "DEFAULT_SMART_TAGS",
    "DEFAULT_TAG_COLORS",
    "Note",
    "VALID_THEMES",
    "VALID_WINDOW_SIZES",
    "append_note_to_file",
    "count_tags",
    "compute_stats",
    "delete_note",
    "edit_note",
    "filter_by_tag",
    "get_default_config_path",
    "load_config",
    "mark_done",
    "merge_tags",
    "parse_notes",
    "parse_smart_tags",
    "save_config",
    "search_notes",
    "safe_print",
]
