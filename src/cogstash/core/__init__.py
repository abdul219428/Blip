"""Shared CogStash core APIs."""

from __future__ import annotations

from .config import CogStashConfig, get_default_config_path, load_config, save_config
from .notes import (
    DEFAULT_SMART_TAGS,
    DEFAULT_TAG_COLORS,
    Note,
    append_note_to_file,
    compute_stats,
    delete_note,
    edit_note,
    filter_by_tag,
    mark_done,
    merge_tags,
    parse_notes,
    parse_smart_tags,
    search_notes,
)

__all__ = [
    "CogStashConfig",
    "DEFAULT_SMART_TAGS",
    "DEFAULT_TAG_COLORS",
    "Note",
    "append_note_to_file",
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
]
