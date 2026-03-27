"""Tests for cogstash_cli.py — CLI command handlers and output formatting."""

from datetime import datetime


def _make_notes_file(tmp_path):
    """Create a test cogstash.md with 5 notes spanning various states."""
    f = tmp_path / "cogstash.md"
    f.write_text(
        "- [2026-03-25 09:00] ☐ old note\n"
        "- [2026-03-26 11:20] meeting notes\n"
        "- [2026-03-26 14:30] ☐ buy milk #todo\n"
        "- [2026-03-27 09:00] ☑ fix login bug #urgent\n"
        "- [2026-03-27 16:00] ⭐ redesign dashboard #important\n",
        encoding="utf-8",
    )
    return f


def test_format_note_color():
    """ANSI escape codes present when use_color=True."""
    from cogstash_cli import format_note
    from cogstash_search import Note

    note = Note(
        index=1,
        timestamp=datetime(2026, 3, 27, 14, 30),
        text="☐ buy milk #todo",
        tags=["todo"],
    )
    result = format_note(note, use_color=True)
    assert "\033[" in result
    assert "buy milk" in result
    assert "#todo" in result


def test_format_note_plain():
    """No ANSI codes when use_color=False."""
    from cogstash_cli import format_note
    from cogstash_search import Note

    note = Note(
        index=1,
        timestamp=datetime(2026, 3, 27, 14, 30),
        text="☐ buy milk #todo",
        tags=["todo"],
    )
    result = format_note(note, use_color=False)
    assert "\033[" not in result
    assert "[2026-03-27 14:30]" in result
    assert "buy milk" in result


def test_format_done_note():
    """Done notes get strikethrough + dimmed styling."""
    from cogstash_cli import format_note
    from cogstash_search import Note

    note = Note(
        index=1,
        timestamp=datetime(2026, 3, 26, 9, 0),
        text="☑ fix login bug #urgent",
        tags=["urgent"],
        is_done=True,
    )
    result = format_note(note, use_color=True)
    assert "\033[9" in result
    assert "fix login bug" in result
