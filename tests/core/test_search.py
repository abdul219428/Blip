"""Tests for cogstash_search.py — note parsing and search logic."""

import builtins
from datetime import datetime


def test_parse_notes_basic(tmp_path):
    """Single note parsed correctly: timestamp, text, tags, line_number."""
    f = tmp_path / "cogstash.md"
    f.write_text("- [2026-03-26 14:30] ☐ buy milk #todo\n", encoding="utf-8")

    from cogstash.search import parse_notes
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

    from cogstash.search import parse_notes
    notes = parse_notes(f)

    assert len(notes) == 1
    assert notes[0].text == "first line\nsecond line\nthird line"


def test_parse_notes_missing_file(tmp_path):
    """Missing file returns empty list."""
    from cogstash.search import parse_notes
    notes = parse_notes(tmp_path / "nonexistent.md")
    assert notes == []


def test_parse_notes_no_prefix(tmp_path):
    """Note without smart-tag emoji → is_done=False."""
    f = tmp_path / "cogstash.md"
    f.write_text("- [2026-03-26 14:30] plain note\n", encoding="utf-8")

    from cogstash.search import parse_notes
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
    from cogstash.search import parse_notes, search_notes
    notes = parse_notes(_make_notes_file(tmp_path))
    results = search_notes(notes, "buy")
    assert len(results) == 2


def test_search_case_insensitive(tmp_path):
    """Search is case-insensitive."""
    from cogstash.search import parse_notes, search_notes
    notes = parse_notes(_make_notes_file(tmp_path))
    results = search_notes(notes, "MILK")
    assert len(results) == 1
    assert "milk" in results[0].text


def test_search_multi_word(tmp_path):
    """Multiple words are AND'd."""
    from cogstash.search import parse_notes, search_notes
    notes = parse_notes(_make_notes_file(tmp_path))
    results = search_notes(notes, "buy eggs")
    assert len(results) == 1
    assert "eggs" in results[0].text


def test_filter_by_tag(tmp_path):
    """Filters to only notes with given tag."""
    from cogstash.search import filter_by_tag, parse_notes
    notes = parse_notes(_make_notes_file(tmp_path))
    results = filter_by_tag(notes, "todo")
    assert len(results) == 2
    assert all("todo" in n.tags for n in results)


def test_mark_done(tmp_path):
    """☐ flipped to ☑ in file, returns True."""
    f = tmp_path / "cogstash.md"
    f.write_text("- [2026-03-26 14:30] ☐ buy milk #todo\n", encoding="utf-8")

    from cogstash.search import MutationStatus, mark_done, parse_notes
    notes = parse_notes(f)
    result = mark_done(f, notes[0])

    assert result is MutationStatus.SUCCESS
    content = f.read_text(encoding="utf-8")
    assert "☑" in content
    assert "☐" not in content


def test_note_line_span_single(tmp_path):
    """Single-line note spans exactly one line."""
    f = tmp_path / "cogstash.md"
    f.write_text(
        "- [2026-03-26 14:30] buy milk #todo\n"
        "- [2026-03-26 15:00] meeting\n",
        encoding="utf-8",
    )
    from cogstash.search import _note_line_span, parse_notes
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
    from cogstash.search import _note_line_span, parse_notes
    notes = parse_notes(f)
    lines = f.read_text(encoding="utf-8").splitlines(keepends=True)
    start, end = _note_line_span(lines, notes[0].line_number)
    assert (start, end) == (0, 3)


def test_edit_note_multiline(tmp_path):
    """Edit replaces multi-line note with new multi-line text."""
    f = tmp_path / "cogstash.md"
    f.write_text(
        "- [2026-03-26 14:30] old first\n"
        "  old second\n"
        "- [2026-03-26 15:00] keep this\n",
        encoding="utf-8",
    )
    from cogstash.search import MutationStatus, edit_note, parse_notes
    notes = parse_notes(f)
    result = edit_note(f, notes[0], "new first\nnew second\nnew third")
    assert result is MutationStatus.SUCCESS
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
    from cogstash.search import MutationStatus, edit_note, parse_notes
    notes = parse_notes(f)
    result = edit_note(f, notes[0], "   ")
    assert result is MutationStatus.INVALID_INPUT
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
    from cogstash.search import MutationStatus, delete_note, parse_notes
    notes = parse_notes(f)
    result = delete_note(f, notes[0])
    assert result is MutationStatus.SUCCESS
    content = f.read_text(encoding="utf-8")
    assert "delete me" not in content
    assert "continuation" not in content
    assert "- [2026-03-26 15:00] keep me\n" in content


def test_mark_done_stale_line_number_rejected(tmp_path):
    """mark_done rejects stale line numbers after external file changes."""
    f = tmp_path / "cogstash.md"
    f.write_text(
        "- [2026-03-26 14:00] first\n"
        "- [2026-03-26 15:00] ☐ target #todo\n"
        "- [2026-03-26 16:00] ☐ last #todo\n",
        encoding="utf-8",
    )

    from cogstash.search import MutationStatus, mark_done, parse_notes

    note = parse_notes(f)[1]
    f.write_text(
        "- [2026-03-26 15:00] ☐ target #todo\n"
        "- [2026-03-26 16:00] ☐ last #todo\n",
        encoding="utf-8",
    )

    assert mark_done(f, note) is MutationStatus.STALE_NOTE
    assert f.read_text(encoding="utf-8") == (
        "- [2026-03-26 15:00] ☐ target #todo\n"
        "- [2026-03-26 16:00] ☐ last #todo\n"
    )


def test_edit_note_stale_line_number_rejected(tmp_path):
    """edit_note rejects stale line numbers after external file changes."""
    f = tmp_path / "cogstash.md"
    f.write_text(
        "- [2026-03-26 14:00] first\n"
        "- [2026-03-26 15:00] target #todo\n"
        "- [2026-03-26 16:00] last\n",
        encoding="utf-8",
    )

    from cogstash.search import MutationStatus, edit_note, parse_notes

    note = parse_notes(f)[1]
    current = (
        "- [2026-03-26 15:00] target #todo\n"
        "- [2026-03-26 16:00] last\n"
    )
    f.write_text(current, encoding="utf-8")

    assert edit_note(f, note, "updated #todo") is MutationStatus.STALE_NOTE
    assert f.read_text(encoding="utf-8") == current


def test_delete_note_stale_line_number_rejected(tmp_path):
    """delete_note rejects stale line numbers after external file changes."""
    f = tmp_path / "cogstash.md"
    f.write_text(
        "- [2026-03-26 14:00] first\n"
        "- [2026-03-26 15:00] target #todo\n"
        "- [2026-03-26 16:00] last\n",
        encoding="utf-8",
    )

    from cogstash.search import MutationStatus, delete_note, parse_notes

    note = parse_notes(f)[1]
    current = (
        "- [2026-03-26 15:00] target #todo\n"
        "- [2026-03-26 16:00] last\n"
    )
    f.write_text(current, encoding="utf-8")

    assert delete_note(f, note) is MutationStatus.STALE_NOTE
    assert f.read_text(encoding="utf-8") == current


def test_compute_stats_current_streak_reuses_date_set(tmp_path, monkeypatch):
    from cogstash.search import compute_stats, parse_notes

    f = tmp_path / "cogstash.md"
    f.write_text(
        "- [2026-03-24 09:00] day 1\n"
        "- [2026-03-25 09:00] day 2\n"
        "- [2026-03-26 09:00] day 3\n"
        "- [2026-03-27 09:00] day 4\n",
        encoding="utf-8",
    )
    notes = parse_notes(f)

    real_set = builtins.set
    set_calls = 0

    def counting_set(*args, **kwargs):
        nonlocal set_calls
        set_calls += 1
        return real_set(*args, **kwargs)

    monkeypatch.setattr(builtins, "set", counting_set)

    compute_stats(notes)

    assert set_calls == 1


def test_search_reexports_core_helpers():
    import cogstash.core.notes as core_notes
    import cogstash.search as search_mod

    assert search_mod.MutationStatus is core_notes.MutationStatus
    assert search_mod.Note is core_notes.Note
    assert search_mod.parse_notes is core_notes.parse_notes
    assert search_mod.search_notes is core_notes.search_notes
    assert search_mod.filter_by_tag is core_notes.filter_by_tag
    assert search_mod.mark_done is core_notes.mark_done
    assert search_mod.edit_note is core_notes.edit_note
    assert search_mod.delete_note is core_notes.delete_note
    assert search_mod.compute_stats is core_notes.compute_stats
    assert search_mod.DEFAULT_TAG_COLORS is core_notes.DEFAULT_TAG_COLORS


def test_search_reexports_private_helpers():
    import cogstash.core.notes as core_notes
    import cogstash.search as search_mod

    assert search_mod._atomic_write is core_notes._atomic_write
    assert search_mod._note_line_span is core_notes._note_line_span
