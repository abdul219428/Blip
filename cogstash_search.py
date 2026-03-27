"""cogstash_search.py — Note parsing, search, and filtering logic.

Pure functions with no tkinter dependency. Used by cogstash_browse.py
for the Browse Window and potentially CLI tools in the future.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

_NOTE_RE = re.compile(r"^- \[(\d{4}-\d{2}-\d{2} \d{2}:\d{2})\] (.+)")
_TAG_RE = re.compile(r"(?:^|\s)#(\w+)")

DEFAULT_TAG_COLORS = {
    "urgent": "#f7768e",
    "important": "#e0af68",
    "idea": "#9ece6a",
    "todo": "#7aa2f7",
}


@dataclass
class Note:
    index: int
    timestamp: datetime
    text: str
    tags: list[str] = field(default_factory=list)
    is_done: bool = False
    line_number: int = 0


def parse_notes(path: Path) -> list[Note]:
    """Parse cogstash.md into a list of Note objects."""
    if not path.exists():
        return []

    notes: list[Note] = []
    current_text_lines: list[str] = []
    current_ts = None
    current_line = 0

    lines = path.read_text(encoding="utf-8").splitlines()

    for i, line in enumerate(lines):
        m = _NOTE_RE.match(line)
        if m:
            # Flush previous note
            if current_ts is not None:
                _flush_note(notes, current_ts, current_text_lines, current_line)

            current_ts = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M")
            current_text_lines = [m.group(2)]
            current_line = i
        elif line.startswith("  ") and current_ts is not None:
            current_text_lines.append(line[2:])

    # Flush last note
    if current_ts is not None:
        _flush_note(notes, current_ts, current_text_lines, current_line)

    return notes


def _flush_note(
    notes: list[Note], ts: datetime, text_lines: list[str], line_number: int
) -> None:
    """Build a Note from accumulated lines and append to notes list."""
    text = "\n".join(text_lines)
    tags = _TAG_RE.findall(text)
    # Deduplicate while preserving order
    seen = set()
    unique_tags = []
    for t in tags:
        if t not in seen:
            seen.add(t)
            unique_tags.append(t)

    is_done = text.startswith("☑")

    notes.append(
        Note(
            index=len(notes) + 1,
            timestamp=ts,
            text=text,
            tags=unique_tags,
            is_done=is_done,
            line_number=line_number,
        )
    )


def search_notes(notes: list[Note], query: str) -> list[Note]:
    """Case-insensitive substring search. Multiple words are AND'd."""
    words = query.lower().split()
    if not words:
        return list(notes)
    return [n for n in notes if all(w in n.text.lower() for w in words)]


def filter_by_tag(notes: list[Note], tag: str) -> list[Note]:
    """Return only notes containing the given tag (without # prefix)."""
    return [n for n in notes if tag in n.tags]


def mark_done(path: Path, note: Note) -> bool:
    """Rewrite note's line in the file: ☐ → ☑. Returns True on success."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        if note.line_number >= len(lines):
            return False
        lines[note.line_number] = lines[note.line_number].replace("☐", "☑", 1)
        path.write_text("".join(lines), encoding="utf-8")
        return True
    except OSError:
        return False


def _note_line_span(lines: list[str], line_number: int) -> tuple[int, int]:
    """Return (start, end) line range for a note including continuation lines.

    start is inclusive, end is exclusive. Continuation lines start with 2 spaces.
    """
    end = line_number + 1
    while end < len(lines) and lines[end].startswith("  "):
        end += 1
    return (line_number, end)


def edit_note(path: Path, note: Note, new_text: str) -> bool:
    """Replace a note's text, preserving its timestamp. Returns True on success."""
    new_text = new_text.strip()
    if not new_text:
        return False
    try:
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        start, end = _note_line_span(lines, note.line_number)
        if start >= len(lines):
            return False

        ts = note.timestamp.strftime("%Y-%m-%d %H:%M")
        text_lines = new_text.split("\n")
        replacement = [f"- [{ts}] {text_lines[0]}\n"]
        replacement.extend(f"  {line}\n" for line in text_lines[1:])

        lines[start:end] = replacement
        path.write_text("".join(lines), encoding="utf-8")
        return True
    except OSError:
        return False


def delete_note(path: Path, note: Note) -> bool:
    """Remove a note and its continuation lines from the file. Returns True on success."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        start, end = _note_line_span(lines, note.line_number)
        if start >= len(lines):
            return False

        del lines[start:end]
        path.write_text("".join(lines), encoding="utf-8")
        return True
    except OSError:
        return False

