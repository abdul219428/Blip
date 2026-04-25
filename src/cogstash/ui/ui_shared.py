"""Shared UI theme and platform helpers.

These values are consumed by multiple UI modules and intentionally live outside
the app entrypoint so dialogs and browse views do not depend on ``ui.app``.
"""

from __future__ import annotations

import sys

THEMES = {
    "tokyo-night": {"bg": "#1a1b26", "fg": "#a9b1d6", "entry_bg": "#24283b", "accent": "#7aa2f7", "muted": "#565f89", "error": "#f7768e"},
    "light": {"bg": "#faf4ed", "fg": "#575279", "entry_bg": "#f2e9e1", "accent": "#d7827e", "muted": "#9893a5", "error": "#b4637a"},
    "dracula": {"bg": "#282a36", "fg": "#f8f8f2", "entry_bg": "#44475a", "accent": "#bd93f9", "muted": "#6272a4", "error": "#ff5555"},
    "gruvbox": {"bg": "#282828", "fg": "#ebdbb2", "entry_bg": "#3c3836", "accent": "#b8bb26", "muted": "#665c54", "error": "#fb4934"},
    "mono": {"bg": "#0a0a0a", "fg": "#d0d0d0", "entry_bg": "#1a1a1a", "accent": "#d0d0d0", "muted": "#4a4a4a", "error": "#ff3333"},
}

WINDOW_SIZES = {
    "compact": {"width": 320, "lines": 2, "max_lines": 5},
    "default": {"width": 400, "lines": 3, "max_lines": 8},
    "wide": {"width": 520, "lines": 4, "max_lines": 10},
}


def platform_font() -> str:
    """Return the native font family for the current OS."""
    fonts = {
        "win32": "Segoe UI",
        "darwin": "Helvetica Neue",
        "linux": "sans-serif",
    }
    return fonts.get(sys.platform, "TkDefaultFont")


__all__ = ["THEMES", "WINDOW_SIZES", "platform_font"]
