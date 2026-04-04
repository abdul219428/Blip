from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

from cogstash.core.config import CogStashConfig

_NOTE_RE = re.compile(r"^- \[(\d{4}-\d{2}-\d{2} \d{2}:\d{2})\] (.+)")
_TAG_RE = re.compile(r"(?:^|\s)#(\w+)")

DEFAULT_SMART_TAGS = {
    "todo": "☐",
    "urgent": "🔴",
    "important": "⭐",
    "idea": "💡",
}

DEFAULT_TAG_COLORS = {
    "urgent": "#f7768e",
    "important": "#e0af68",
    "idea": "#9ece6a",
    "todo": "#7aa2f7",
}

logger = logging.getLogger("cogstash")


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
    current_ts: datetime | None = None
    current_line = 0

    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
        match = _NOTE_RE.match(line)
        if match:
            if current_ts is not None:
                _flush_note(notes, current_ts, current_text_lines, current_line)
            current_ts = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M")
            current_text_lines = [match.group(2)]
            current_line = i
        elif line.startswith("  ") and current_ts is not None:
            current_text_lines.append(line[2:])

    if current_ts is not None:
        _flush_note(notes, current_ts, current_text_lines, current_line)

    return notes


def _flush_note(notes: list[Note], ts: datetime, text_lines: list[str], line_number: int) -> None:
    text = "\n".join(text_lines)
    seen: set[str] = set()
    unique_tags: list[str] = []
    for tag in _TAG_RE.findall(text):
        if tag not in seen:
            seen.add(tag)
            unique_tags.append(tag)

    notes.append(
        Note(
            index=len(notes) + 1,
            timestamp=ts,
            text=text,
            tags=unique_tags,
            is_done=text.startswith("☑"),
            line_number=line_number,
        )
    )


def search_notes(notes: list[Note], query: str) -> list[Note]:
    """Case-insensitive substring search. Multiple words are AND'd."""
    words = query.lower().split()
    if not words:
        return list(notes)
    return [note for note in notes if all(word in note.text.lower() for word in words)]


def filter_by_tag(notes: list[Note], tag: str) -> list[Note]:
    """Return only notes containing the given tag (without # prefix)."""
    return [note for note in notes if tag in note.tags]


def merge_tags(config: CogStashConfig) -> tuple[dict[str, str], dict[str, str]]:
    """Merge built-in tags with user-defined tags. Returns (smart_tags, tag_colors)."""
    smart_tags = dict(DEFAULT_SMART_TAGS)
    tag_colors = dict(DEFAULT_TAG_COLORS)
    if config.tags:
        for name, props in config.tags.items():
            smart_tags[name] = props["emoji"]
            tag_colors[name] = props["color"]
    return smart_tags, tag_colors


def parse_smart_tags(text: str, smart_tags: dict[str, str] | None = None) -> str:
    """Prepend smart-tag emojis to text. Tags stay inline for searchability."""
    tags_dict = smart_tags if smart_tags is not None else DEFAULT_SMART_TAGS
    seen: list[str] = []
    for tag in _TAG_RE.findall(text):
        tag_lower = tag.lower()
        if tag_lower in tags_dict and tag_lower not in seen:
            seen.append(tag_lower)
    if not seen:
        return text
    prefix = " ".join(tags_dict[tag] for tag in seen)
    return f"{prefix} {text}"


def append_note_to_file(text: str, output_file: Path, smart_tags: dict[str, str] | None = None) -> bool:
    """Append a timestamped note to the given file. Returns True on success."""
    text = text.strip()
    if not text:
        return False
    if len(text) > 10_000:
        text = text[:10_000]

    rendered = parse_smart_tags(text, smart_tags)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = rendered.split("\n")
    first = f"- [{timestamp}] {lines[0]}\n"
    rest = "".join(f"  {line}\n" for line in lines[1:])

    try:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with output_file.open("a", encoding="utf-8") as file:
            file.write(first + rest)
        return True
    except OSError:
        logger.error("Failed to write to %s", output_file, exc_info=True)
        return False


def _atomic_write(path: Path, content: str) -> None:
    """Write content to a file atomically via a temp file + rename."""
    tmp = path.with_suffix(".tmp")
    try:
        tmp.write_text(content, encoding="utf-8")
        os.replace(tmp, path)
    except OSError:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def _line_matches_note(lines: list[str], note: Note) -> bool:
    """Return True when the stored line still points at the expected note."""
    if note.line_number >= len(lines):
        return False
    timestamp = note.timestamp.strftime("%Y-%m-%d %H:%M")
    return lines[note.line_number].startswith(f"- [{timestamp}] ")


def mark_done(path: Path, note: Note) -> bool:
    """Rewrite note's line in the file: ☐ → ☑. Returns True on success."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        if not _line_matches_note(lines, note):
            return False
        new_line = lines[note.line_number].replace("☐", "☑", 1)
        if new_line == lines[note.line_number]:
            return False
        lines[note.line_number] = new_line
        _atomic_write(path, "".join(lines))
        return True
    except OSError:
        return False


def _note_line_span(lines: list[str], line_number: int) -> tuple[int, int]:
    """Return (start, end) line range for a note including continuation lines."""
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
        if not _line_matches_note(lines, note):
            return False
        start, end = _note_line_span(lines, note.line_number)
        timestamp = note.timestamp.strftime("%Y-%m-%d %H:%M")
        text_lines = new_text.split("\n")
        replacement = [f"- [{timestamp}] {text_lines[0]}\n"]
        replacement.extend(f"  {line}\n" for line in text_lines[1:])
        lines[start:end] = replacement
        _atomic_write(path, "".join(lines))
        return True
    except OSError:
        return False


def delete_note(path: Path, note: Note) -> bool:
    """Remove a note and its continuation lines from the file. Returns True on success."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        if not _line_matches_note(lines, note):
            return False
        start, end = _note_line_span(lines, note.line_number)
        del lines[start:end]
        _atomic_write(path, "".join(lines))
        return True
    except OSError:
        return False


def compute_stats(notes: list[Note]) -> dict:
    """Compute extended statistics from a list of notes."""
    if not notes:
        return {
            "total": 0,
            "done": 0,
            "pending": 0,
            "first_date": None,
            "last_date": None,
            "tag_counts": {},
            "avg_length": 0,
            "longest": 0,
            "notes_this_week": 0,
            "notes_last_week": 0,
            "busiest_day": None,
            "avg_per_week": 0.0,
            "current_streak": 0,
            "longest_streak": 0,
        }

    from collections import Counter

    total = len(notes)
    done = sum(1 for note in notes if note.is_done)
    pending = total - done

    timestamps = sorted(note.timestamp for note in notes)
    first_date = timestamps[0]
    last_date = timestamps[-1]

    tag_counter: Counter[str] = Counter()
    for note in notes:
        for tag in note.tags:
            tag_counter[tag] += 1

    lengths = [len(note.text) for note in notes]
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    last_week_start = week_start - timedelta(days=7)
    notes_this_week = sum(1 for note in notes if note.timestamp.date() >= week_start)
    notes_last_week = sum(1 for note in notes if last_week_start <= note.timestamp.date() < week_start)

    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    day_counts = Counter(note.timestamp.weekday() for note in notes)
    busiest_day = day_names[day_counts.most_common(1)[0][0]]

    span_days = (last_date.date() - first_date.date()).days + 1
    avg_per_week = round(total / max(span_days / 7, 1), 1)

    note_dates_set = set(note.timestamp.date() for note in notes)
    note_dates = sorted(note_dates_set)
    current_streak = 0
    cursor = today
    while cursor in note_dates_set:
        current_streak += 1
        cursor -= timedelta(days=1)

    longest_streak = 1
    running_streak = 1
    for previous, current in zip(note_dates, note_dates[1:]):
        if current == previous + timedelta(days=1):
            running_streak += 1
            longest_streak = max(longest_streak, running_streak)
        else:
            running_streak = 1

    return {
        "total": total,
        "done": done,
        "pending": pending,
        "first_date": first_date,
        "last_date": last_date,
        "tag_counts": dict(tag_counter.most_common()),
        "avg_length": sum(lengths) // total,
        "longest": max(lengths),
        "notes_this_week": notes_this_week,
        "notes_last_week": notes_last_week,
        "busiest_day": busiest_day,
        "avg_per_week": avg_per_week,
        "current_streak": current_streak,
        "longest_streak": longest_streak,
    }


__all__ = [
    "DEFAULT_SMART_TAGS",
    "DEFAULT_TAG_COLORS",
    "Note",
    "append_note_to_file",
    "compute_stats",
    "delete_note",
    "edit_note",
    "filter_by_tag",
    "mark_done",
    "merge_tags",
    "parse_notes",
    "parse_smart_tags",
    "search_notes",
]
