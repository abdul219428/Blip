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


def test_cmd_recent_default(tmp_path, capsys):
    """Shows notes newest-first, up to 20 by default."""
    f = _make_notes_file(tmp_path)
    from cogstash_cli import cmd_recent
    from cogstash import CogStashConfig
    from types import SimpleNamespace

    cmd_recent(SimpleNamespace(limit=20), CogStashConfig(output_file=f))
    output = capsys.readouterr().out
    lines = [l for l in output.strip().split("\n") if l.strip()]

    assert len(lines) == 5
    assert "redesign dashboard" in lines[0]  # newest first
    assert "old note" in lines[4]  # oldest last


def test_cmd_recent_limit(tmp_path, capsys):
    """--limit restricts number of notes shown."""
    f = _make_notes_file(tmp_path)
    from cogstash_cli import cmd_recent
    from cogstash import CogStashConfig
    from types import SimpleNamespace

    cmd_recent(SimpleNamespace(limit=2), CogStashConfig(output_file=f))
    output = capsys.readouterr().out
    lines = [l for l in output.strip().split("\n") if l.strip()]

    assert len(lines) == 2
    assert "redesign dashboard" in lines[0]
    assert "fix login bug" in lines[1]


def test_cmd_recent_empty(tmp_path, capsys):
    """Empty/missing file shows 'No notes found.' message."""
    f = tmp_path / "cogstash.md"  # does not exist
    from cogstash_cli import cmd_recent
    from cogstash import CogStashConfig
    from types import SimpleNamespace

    cmd_recent(SimpleNamespace(limit=20), CogStashConfig(output_file=f))
    output = capsys.readouterr().out
    assert "No notes found." in output


def test_cmd_search_match(tmp_path, capsys):
    """Finds notes matching the query, newest first."""
    f = _make_notes_file(tmp_path)
    from cogstash_cli import cmd_search
    from cogstash import CogStashConfig
    from types import SimpleNamespace

    cmd_search(SimpleNamespace(query="milk", limit=20), CogStashConfig(output_file=f))
    output = capsys.readouterr().out
    lines = [l for l in output.strip().split("\n") if l.strip()]

    assert len(lines) == 1
    assert "buy milk" in lines[0]


def test_cmd_search_no_match(tmp_path, capsys):
    """No matches shows 'No matching notes.' message."""
    f = _make_notes_file(tmp_path)
    from cogstash_cli import cmd_search
    from cogstash import CogStashConfig
    from types import SimpleNamespace

    cmd_search(SimpleNamespace(query="nonexistent xyz", limit=20), CogStashConfig(output_file=f))
    output = capsys.readouterr().out
    assert "No matching notes." in output


def test_cmd_tags_counts(tmp_path, capsys):
    """Tags listed with correct counts, sorted by count descending."""
    f = _make_notes_file(tmp_path)
    from cogstash_cli import cmd_tags
    from cogstash import CogStashConfig
    from types import SimpleNamespace

    cmd_tags(SimpleNamespace(), CogStashConfig(output_file=f))
    output = capsys.readouterr().out
    lines = [l for l in output.strip().split("\n") if l.strip()]

    # 3 tags in fixture: #todo (1), #urgent (1), #important (1)
    assert len(lines) == 3
    # All have count 1, sorted alphabetically as tiebreaker
    assert "#important" in lines[0]
    assert "#todo" in lines[1]
    assert "#urgent" in lines[2]
    assert "1 note" in lines[0]


def test_cmd_tags_empty(tmp_path, capsys):
    """Empty file shows 'No tags found.' message."""
    f = tmp_path / "cogstash.md"
    f.write_text("", encoding="utf-8")
    from cogstash_cli import cmd_tags
    from cogstash import CogStashConfig
    from types import SimpleNamespace

    cmd_tags(SimpleNamespace(), CogStashConfig(output_file=f))
    output = capsys.readouterr().out
    assert "No tags found." in output
