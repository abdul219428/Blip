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


def test_note_line_span_single(tmp_path):
    """Single-line note spans exactly one line."""
    f = tmp_path / "cogstash.md"
    f.write_text(
        "- [2026-03-26 14:30] buy milk #todo\n"
        "- [2026-03-26 15:00] meeting\n",
        encoding="utf-8",
    )
    from cogstash_search import parse_notes, _note_line_span
    notes = parse_notes(f)
    lines = f.read_text(encoding="utf-8").splitlines(keepends=True)
    start, end = _note_line_span(lines, notes[0].line_number)
    assert (start, end) == (0, 1)


def test_note_line_span_multiline(tmp_path):
    """Multi-line note includes all continuation lines."""
    f = tmp_path / "cogstash.md"
    f.write_text(
        "- [2026-03-26 14:30] first line\n"
        "  second line\n"
        "  third line\n"
        "- [2026-03-26 15:00] next note\n",
        encoding="utf-8",
    )
    from cogstash_search import parse_notes, _note_line_span
    notes = parse_notes(f)
    lines = f.read_text(encoding="utf-8").splitlines(keepends=True)
    start, end = _note_line_span(lines, notes[0].line_number)
    assert (start, end) == (0, 3)


def test_edit_note_single_line(tmp_path):
    """Edit replaces text, preserves timestamp."""
    f = tmp_path / "cogstash.md"
    f.write_text(
        "- [2026-03-26 14:30] buy milk #todo\n"
        "- [2026-03-26 15:00] meeting\n",
        encoding="utf-8",
    )
    from cogstash_search import parse_notes, edit_note
    notes = parse_notes(f)
    result = edit_note(f, notes[0], "buy oat milk #todo")
    assert result is True
    content = f.read_text(encoding="utf-8")
    assert "- [2026-03-26 14:30] buy oat milk #todo\n" in content
    assert "buy milk" not in content
    assert "- [2026-03-26 15:00] meeting\n" in content


def test_edit_note_multiline(tmp_path):
    """Edit replaces multi-line note with new multi-line text."""
    f = tmp_path / "cogstash.md"
    f.write_text(
        "- [2026-03-26 14:30] old first\n"
        "  old second\n"
        "- [2026-03-26 15:00] keep this\n",
        encoding="utf-8",
    )
    from cogstash_search import parse_notes, edit_note
    notes = parse_notes(f)
    result = edit_note(f, notes[0], "new first\nnew second\nnew third")
    assert result is True
    content = f.read_text(encoding="utf-8")
    assert "- [2026-03-26 14:30] new first\n" in content
    assert "  new second\n" in content
    assert "  new third\n" in content
    assert "old" not in content
    assert "- [2026-03-26 15:00] keep this\n" in content


def test_edit_note_empty_rejected(tmp_path):
    """Empty new text returns False, file unchanged."""
    f = tmp_path / "cogstash.md"
    f.write_text("- [2026-03-26 14:30] original\n", encoding="utf-8")
    from cogstash_search import parse_notes, edit_note
    notes = parse_notes(f)
    result = edit_note(f, notes[0], "   ")
    assert result is False
    assert "original" in f.read_text(encoding="utf-8")


def test_delete_note(tmp_path):
    """Delete removes note and continuation lines, keeps others."""
    f = tmp_path / "cogstash.md"
    f.write_text(
        "- [2026-03-26 14:30] delete me\n"
        "  continuation\n"
        "- [2026-03-26 15:00] keep me\n",
        encoding="utf-8",
    )
    from cogstash_search import parse_notes, delete_note
    notes = parse_notes(f)
    result = delete_note(f, notes[0])
    assert result is True
    content = f.read_text(encoding="utf-8")
    assert "delete me" not in content
    assert "continuation" not in content
    assert "- [2026-03-26 15:00] keep me\n" in content


def test_compute_stats_basic(tmp_path):
    """Stats returns correct totals, done/pending, date range."""
    f = tmp_path / "cogstash.md"
    f.write_text(
        "- [2026-01-15 09:00] first note #todo\n"
        "- [2026-02-10 14:30] ☑ done item #todo\n"
        "- [2026-03-27 16:00] latest note #idea\n",
        encoding="utf-8",
    )
    from cogstash_search import parse_notes, compute_stats
    notes = parse_notes(f)
    stats = compute_stats(notes)

    assert stats["total"] == 3
    assert stats["done"] == 1
    assert stats["pending"] == 2
    assert stats["first_date"].year == 2026
    assert stats["first_date"].month == 1
    assert stats["last_date"].month == 3
    assert "todo" in stats["tag_counts"]
    assert stats["tag_counts"]["todo"] == 2
    assert stats["avg_length"] > 0
    assert stats["longest"] >= stats["avg_length"]


def test_compute_stats_empty():
    """Empty note list returns zeroed stats."""
    from cogstash_search import compute_stats
    stats = compute_stats([])

    assert stats["total"] == 0
    assert stats["done"] == 0
    assert stats["pending"] == 0
    assert stats["first_date"] is None
    assert stats["last_date"] is None
    assert stats["tag_counts"] == {}
    assert stats["avg_length"] == 0


def test_compute_stats_streaks(tmp_path):
    """Streak calculation finds consecutive days with notes."""
    from datetime import timedelta, date
    from cogstash_search import parse_notes, compute_stats

    today = date.today()
    dates = [today - timedelta(days=i) for i in range(3, -1, -1)]  # 4 consecutive days ending today
    lines = []
    for i, d in enumerate(dates):
        ts = d.strftime("%Y-%m-%d") + " 09:00"
        lines.append(f"- [{ts}] day {i + 1}\n")

    f = tmp_path / "cogstash.md"
    f.write_text("".join(lines), encoding="utf-8")
    notes = parse_notes(f)
    stats = compute_stats(notes)

    assert stats["current_streak"] == 4
    assert stats["longest_streak"] == 4
    assert stats["notes_this_week"] >= 1
