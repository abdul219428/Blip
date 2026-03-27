"""cogstash_cli.py — CLI subcommands for querying CogStash notes.

Provides `recent`, `search`, and `tags` commands with ANSI-colored output.
All data operations delegate to cogstash_search.py.
"""

from __future__ import annotations

from cogstash_search import Note

# ANSI escape codes — approximations of TAG_COLORS hex values
ANSI_RESET = "\033[0m"
ANSI_BOLD = "\033[1m"
ANSI_DIM = "\033[90m"
ANSI_STRIKE_DIM = "\033[9;90m"

ANSI_TAG = {
    "urgent": "\033[31m",
    "important": "\033[33m",
    "idea": "\033[32m",
    "todo": "\033[36m",
}


def format_note(note: Note, use_color: bool = True) -> str:
    """Format a single note as one line of CLI output."""
    ts = note.timestamp.strftime("[%Y-%m-%d %H:%M]")
    text = note.text

    if not use_color:
        return f"{ts} {text}"

    if note.is_done:
        return f"{ANSI_STRIKE_DIM}{ts} {text}{ANSI_RESET}"

    # Dim timestamp, color tags in text
    colored = text
    for tag in note.tags:
        color = ANSI_TAG.get(tag)
        if color:
            colored = colored.replace(f"#{tag}", f"{color}#{tag}{ANSI_RESET}")

    return f"{ANSI_DIM}{ts}{ANSI_RESET} {colored}"
