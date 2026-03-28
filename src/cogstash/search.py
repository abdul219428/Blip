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


def compute_stats(notes: list[Note]) -> dict:
    """Compute extended statistics from a list of notes.

    Returns a dict with keys: total, done, pending, first_date, last_date,
    tag_counts, avg_length, longest, notes_this_week, notes_last_week,
    busiest_day, avg_per_week, current_streak, longest_streak.
    """
    if not notes:
        return {
            "total": 0, "done": 0, "pending": 0,
            "first_date": None, "last_date": None,
            "tag_counts": {}, "avg_length": 0, "longest": 0,
            "notes_this_week": 0, "notes_last_week": 0,
            "busiest_day": None, "avg_per_week": 0.0,
            "current_streak": 0, "longest_streak": 0,
        }

    from collections import Counter
    from datetime import timedelta, date

    total = len(notes)
    done = sum(1 for n in notes if n.is_done)
    pending = total - done

    timestamps = sorted(n.timestamp for n in notes)
    first_date = timestamps[0]
    last_date = timestamps[-1]

    # Tag counts
    tag_counter: Counter[str] = Counter()
    for n in notes:
        for tag in n.tags:
            tag_counter[tag] += 1
    tag_counts = dict(tag_counter.most_common())

    # Note lengths
    lengths = [len(n.text) for n in notes]
    avg_length = sum(lengths) // total
    longest = max(lengths)

    # Weekly activity
    today = date.today()
    week_start = today - timedelta(days=today.weekday())  # Monday
    last_week_start = week_start - timedelta(days=7)
    notes_this_week = sum(1 for n in notes if n.timestamp.date() >= week_start)
    notes_last_week = sum(
        1 for n in notes
        if last_week_start <= n.timestamp.date() < week_start
    )

    # Busiest day of week (0=Monday, 6=Sunday)
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    day_counts = Counter(n.timestamp.weekday() for n in notes)
    busiest_idx = day_counts.most_common(1)[0][0]
    busiest_day = day_names[busiest_idx]

    # Average per week
    span_days = (last_date.date() - first_date.date()).days + 1
    span_weeks = max(span_days / 7, 1)
    avg_per_week = round(total / span_weeks, 1)

    # Streaks — consecutive days with at least one note
    note_dates = sorted(set(n.timestamp.date() for n in notes))
    current_streak = 0
    longest_streak = 0
    streak = 1

    for i in range(1, len(note_dates)):
        if (note_dates[i] - note_dates[i - 1]).days == 1:
            streak += 1
        else:
            longest_streak = max(longest_streak, streak)
            streak = 1
    longest_streak = max(longest_streak, streak)

    # Current streak: count backwards from today
    if today in note_dates:
        current_streak = 1
        check = today - timedelta(days=1)
        while check in set(note_dates):
            current_streak += 1
            check -= timedelta(days=1)
    else:
        current_streak = 0

    return {
        "total": total, "done": done, "pending": pending,
        "first_date": first_date, "last_date": last_date,
        "tag_counts": tag_counts, "avg_length": avg_length, "longest": longest,
        "notes_this_week": notes_this_week, "notes_last_week": notes_last_week,
        "busiest_day": busiest_day, "avg_per_week": avg_per_week,
        "current_streak": current_streak, "longest_streak": longest_streak,
    }

