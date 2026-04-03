"""CogStash CLI package."""

from __future__ import annotations

from .formatting import (
    ANSI_BOLD,
    ANSI_DIM,
    ANSI_RESET,
    ANSI_STRIKE_DIM,
    DEFAULT_ANSI_TAG,
    build_ansi_tag_map,
    format_note,
    hex_to_ansi,
    stream_is_interactive,
    stream_supports_color,
)
from .main import (
    VALID_CONFIG_KEYS,
    build_parser,
    cli_main,
    cmd_add,
    cmd_config,
    cmd_delete,
    cmd_edit,
    cmd_export,
    cmd_recent,
    cmd_search,
    cmd_stats,
    cmd_tags,
)

__all__ = [
    "ANSI_BOLD",
    "ANSI_DIM",
    "ANSI_RESET",
    "ANSI_STRIKE_DIM",
    "DEFAULT_ANSI_TAG",
    "VALID_CONFIG_KEYS",
    "build_ansi_tag_map",
    "build_parser",
    "cli_main",
    "cmd_add",
    "cmd_config",
    "cmd_delete",
    "cmd_edit",
    "cmd_export",
    "cmd_recent",
    "cmd_search",
    "cmd_stats",
    "cmd_tags",
    "format_note",
    "hex_to_ansi",
    "stream_is_interactive",
    "stream_supports_color",
]
