"""Tests for cogstash_search.py — note parsing and search logic."""

from pathlib import Path
from datetime import datetime


def test_parse_notes_basic(tmp_path):
    """Single note parsed correctly: timestamp, text, tags, line_number."""
    f = tmp_path / "cogstash.md"
    f.write_text("- [2026-03-26 14:30] ☐ buy milk #todo\n", encoding="utf-8")

    from cogstash_search import parse_notes
    notes = parse_notes(f)

    assert len(notes) == 1
    n = notes[0]
    assert n.index == 1
    assert n.timestamp == datetime(2026, 3, 26, 14, 30)
    assert n.text == "☐ buy milk #todo"
    assert n.tags == ["todo"]
    assert n.is_done is False
    assert n.line_number == 0


def test_parse_notes_multiline(tmp_path):
    """Continuation lines joined to parent note."""
    f = tmp_path / "cogstash.md"
    f.write_text(
        "- [2026-03-26 14:30] first line\n"
        "  second line\n"
        "  third line\n",
        encoding="utf-8",
    )

    from cogstash_search import parse_notes
    notes = parse_notes(f)

    assert len(notes) == 1
    assert notes[0].text == "first line\nsecond line\nthird line"


def test_parse_notes_empty_file(tmp_path):
    """Empty file returns empty list."""
    f = tmp_path / "cogstash.md"
    f.write_text("", encoding="utf-8")

    from cogstash_search import parse_notes
    notes = parse_notes(f)
    assert notes == []


def test_parse_notes_missing_file(tmp_path):
    """Missing file returns empty list."""
    from cogstash_search import parse_notes
    notes = parse_notes(tmp_path / "nonexistent.md")
    assert notes == []


def test_parse_notes_done_status(tmp_path):
    """☐ → is_done=False, ☑ → is_done=True."""
    f = tmp_path / "cogstash.md"
    f.write_text(
        "- [2026-03-26 14:30] ☐ open item #todo\n"
        "- [2026-03-26 15:00] ☑ done item #todo\n",
        encoding="utf-8",
    )

    from cogstash_search import parse_notes
    notes = parse_notes(f)

    assert notes[0].is_done is False
    assert notes[1].is_done is True


def test_parse_notes_no_prefix(tmp_path):
    """Note without smart-tag emoji → is_done=False."""
    f = tmp_path / "cogstash.md"
    f.write_text("- [2026-03-26 14:30] plain note\n", encoding="utf-8")

    from cogstash_search import parse_notes
    notes = parse_notes(f)

    assert notes[0].is_done is False
    assert notes[0].tags == []


def _make_notes_file(tmp_path):
    """Helper: create a cogstash.md with several notes for search tests."""
    f = tmp_path / "cogstash.md"
    f.write_text(
        "- [2026-03-26 14:30] ☐ buy milk and eggs #todo\n"
        "- [2026-03-26 11:20] ⭐ team lunch next Tuesday #important\n"
        "- [2026-03-25 09:15] 💡 voice capture idea #idea\n"
        "- [2026-03-24 18:42] ☑ buy bread #todo\n",
        encoding="utf-8",
    )
    return f


def test_search_keyword(tmp_path):
    """Substring match finds correct notes."""
    from cogstash_search import parse_notes, search_notes
    notes = parse_notes(_make_notes_file(tmp_path))
    results = search_notes(notes, "buy")
    assert len(results) == 2


def test_search_case_insensitive(tmp_path):
    """Search is case-insensitive."""
    from cogstash_search import parse_notes, search_notes
    notes = parse_notes(_make_notes_file(tmp_path))
    results = search_notes(notes, "MILK")
    assert len(results) == 1
    assert "milk" in results[0].text


def test_search_multi_word(tmp_path):
    """Multiple words are AND'd."""
    from cogstash_search import parse_notes, search_notes
    notes = parse_notes(_make_notes_file(tmp_path))
    results = search_notes(notes, "buy eggs")
    assert len(results) == 1
    assert "eggs" in results[0].text


def test_filter_by_tag(tmp_path):
    """Filters to only notes with given tag."""
    from cogstash_search import parse_notes, filter_by_tag
    notes = parse_notes(_make_notes_file(tmp_path))
    results = filter_by_tag(notes, "todo")
    assert len(results) == 2
    assert all("todo" in n.tags for n in results)


def test_mark_done(tmp_path):
    """☐ flipped to ☑ in file, returns True."""
    f = tmp_path / "cogstash.md"
    f.write_text("- [2026-03-26 14:30] ☐ buy milk #todo\n", encoding="utf-8")

    from cogstash_search import parse_notes, mark_done
    notes = parse_notes(f)
    result = mark_done(f, notes[0])

    assert result is True
    content = f.read_text(encoding="utf-8")
    assert "☑" in content
    assert "☐" not in content


def test_mark_done_already_done(tmp_path):
    """Already ☑ → no change, returns True."""
    f = tmp_path / "cogstash.md"
    f.write_text("- [2026-03-26 14:30] ☑ already done #todo\n", encoding="utf-8")

    from cogstash_search import parse_notes, mark_done
    notes = parse_notes(f)
    result = mark_done(f, notes[0])

    assert result is True
    content = f.read_text(encoding="utf-8")
    assert content.count("☑") == 1
