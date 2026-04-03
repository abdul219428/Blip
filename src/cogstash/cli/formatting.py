from __future__ import annotations

from cogstash.core import Note


def stream_supports_color(stream: object | None) -> bool:
    """Return True when a stream safely reports interactive TTY support."""
    if stream is None:
        return False
    isatty = getattr(stream, "isatty", None)
    if not callable(isatty):
        return False
    try:
        return bool(isatty())
    except Exception:
        return False


def stream_is_interactive(stream: object | None) -> bool:
    """Return True when stdin-like streams can be treated as interactive."""
    return stream_supports_color(stream)

ANSI_RESET = "\033[0m"
ANSI_BOLD = "\033[1m"
ANSI_DIM = "\033[90m"
ANSI_STRIKE_DIM = "\033[9;90m"

DEFAULT_ANSI_TAG = {
    "urgent": "\033[31m",
    "important": "\033[33m",
    "idea": "\033[32m",
    "todo": "\033[36m",
}


def hex_to_ansi(hex_color: str) -> str:
    """Map a hex color to the nearest 8-color ANSI escape code."""
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    ansi_map = [
        (0, 0, 0, "\033[30m"),
        (255, 0, 0, "\033[31m"),
        (0, 255, 0, "\033[32m"),
        (255, 255, 0, "\033[33m"),
        (0, 0, 255, "\033[34m"),
        (255, 0, 255, "\033[35m"),
        (0, 255, 255, "\033[36m"),
        (255, 255, 255, "\033[37m"),
    ]
    best = min(ansi_map, key=lambda c: (c[0] - r) ** 2 + (c[1] - g) ** 2 + (c[2] - b) ** 2)
    return best[3]


def build_ansi_tag_map(tag_colors: dict[str, str]) -> dict[str, str]:
    """Build ANSI color map from hex tag colors."""
    return {tag: hex_to_ansi(color) for tag, color in tag_colors.items()}


def format_note(note: Note, use_color: bool = True, ansi_tag: dict[str, str] | None = None) -> str:
    """Format a single note as one line of CLI output."""
    tag_map = ansi_tag if ansi_tag is not None else DEFAULT_ANSI_TAG
    ts = note.timestamp.strftime("[%Y-%m-%d %H:%M]")
    text = note.text

    if not use_color:
        return f"{ts} {text}"

    if note.is_done:
        return f"{ANSI_STRIKE_DIM}{ts} {text}{ANSI_RESET}"

    colored = text
    for tag in note.tags:
        color = tag_map.get(tag)
        if color:
            colored = colored.replace(f"#{tag}", f"{color}#{tag}{ANSI_RESET}")

    return f"{ANSI_DIM}{ts}{ANSI_RESET} {colored}"


__all__ = [
    "ANSI_BOLD",
    "ANSI_DIM",
    "ANSI_RESET",
    "ANSI_STRIKE_DIM",
    "DEFAULT_ANSI_TAG",
    "build_ansi_tag_map",
    "format_note",
    "hex_to_ansi",
    "stream_is_interactive",
    "stream_supports_color",
]
