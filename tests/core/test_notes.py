from __future__ import annotations

import builtins
from datetime import date, datetime, timedelta


def test_parse_notes_basic(tmp_path):
    from cogstash.core import parse_notes

    notes_file = tmp_path / "cogstash.md"
    notes_file.write_text("- [2026-03-26 14:30] ☐ buy milk #todo\n", encoding="utf-8")

    notes = parse_notes(notes_file)

    assert len(notes) == 1
    note = notes[0]
    assert note.index == 1
    assert note.timestamp == datetime(2026, 3, 26, 14, 30)
    assert note.text == "☐ buy milk #todo"
    assert note.tags == ["todo"]
    assert note.is_done is False
    assert note.line_number == 0


def test_parse_notes_multiline(tmp_path):
    from cogstash.core import parse_notes

    notes_file = tmp_path / "cogstash.md"
    notes_file.write_text(
        "- [2026-03-26 14:30] first line\n"
        "  second line\n"
        "  third line\n",
        encoding="utf-8",
    )

    notes = parse_notes(notes_file)

    assert len(notes) == 1
    assert notes[0].text == "first line\nsecond line\nthird line"


def test_parse_notes_empty_file(tmp_path):
    from cogstash.core import parse_notes

    notes_file = tmp_path / "cogstash.md"
    notes_file.write_text("", encoding="utf-8")

    assert parse_notes(notes_file) == []


def test_parse_notes_missing_file(tmp_path):
    from cogstash.core import parse_notes

    assert parse_notes(tmp_path / "nonexistent.md") == []


def test_parse_notes_done_status(tmp_path):
    from cogstash.core import parse_notes

    notes_file = tmp_path / "cogstash.md"
    notes_file.write_text(
        "- [2026-03-26 14:30] ☐ open item #todo\n"
        "- [2026-03-26 15:00] ☑ done item #todo\n",
        encoding="utf-8",
    )

    notes = parse_notes(notes_file)

    assert notes[0].is_done is False
    assert notes[1].is_done is True


def _make_notes_file(tmp_path):
    notes_file = tmp_path / "cogstash.md"
    notes_file.write_text(
        "- [2026-03-26 14:30] ☐ buy milk and eggs #todo\n"
        "- [2026-03-26 11:20] ⭐ team lunch next Tuesday #important\n"
        "- [2026-03-25 09:15] 💡 voice capture idea #idea\n"
        "- [2026-03-24 18:42] ☑ buy bread #todo\n",
        encoding="utf-8",
    )
    return notes_file


def test_search_and_filter(tmp_path):
    from cogstash.core import filter_by_tag, parse_notes, search_notes

    notes = parse_notes(_make_notes_file(tmp_path))

    assert len(search_notes(notes, "buy")) == 2
    assert len(search_notes(notes, "MILK")) == 1
    assert len(search_notes(notes, "buy eggs")) == 1
    todo_notes = filter_by_tag(notes, "todo")
    assert len(todo_notes) == 2
    assert all("todo" in note.tags for note in todo_notes)


def test_merge_tags_builtin_defaults():
    from cogstash.core import DEFAULT_SMART_TAGS, DEFAULT_TAG_COLORS, CogStashConfig, merge_tags

    smart_tags, tag_colors = merge_tags(CogStashConfig())

    assert smart_tags == DEFAULT_SMART_TAGS
    assert tag_colors == DEFAULT_TAG_COLORS


def test_merge_tags_custom_and_override():
    from cogstash.core import CogStashConfig, merge_tags

    config = CogStashConfig(
        tags={
            "work": {"emoji": "💼", "color": "#4A90D9"},
            "todo": {"emoji": "✅", "color": "#00FF00"},
        }
    )

    smart_tags, tag_colors = merge_tags(config)

    assert smart_tags["work"] == "💼"
    assert smart_tags["todo"] == "✅"
    assert tag_colors["work"] == "#4A90D9"
    assert tag_colors["todo"] == "#00FF00"


def test_parse_smart_tags_variants():
    from cogstash.core import parse_smart_tags

    assert parse_smart_tags("Review PR #42 #todo #urgent").startswith("☐ 🔴 ")
    assert parse_smart_tags("do thing #todo and also #todo").count("☐") == 1
    result = parse_smart_tags("see http://example.com#section for details")
    assert not result.startswith(("☐", "🔴", "⭐", "💡"))
    assert parse_smart_tags("meeting notes #work", smart_tags={"work": "💼", "todo": "☐"}).startswith("💼")


def test_append_note_to_file(tmp_path):
    from cogstash.core import append_note_to_file

    out = tmp_path / "notes.md"

    assert append_note_to_file("hello world", out) is True

    content = out.read_text(encoding="utf-8")
    assert "hello world" in content
    assert content.startswith("- [")


def test_append_note_to_file_smart_tags_and_multiline(tmp_path):
    from cogstash.core import append_note_to_file

    out = tmp_path / "notes.md"

    append_note_to_file("meeting #work\nline two\nline three", out, smart_tags={"work": "💼"})

    content = out.read_text(encoding="utf-8")
    assert "💼" in content
    assert "  line two\n" in content
    assert "  line three\n" in content


def test_append_note_to_file_empty(tmp_path):
    from cogstash.core import append_note_to_file

    out = tmp_path / "notes.md"

    assert append_note_to_file("  ", out) is False
    assert not out.exists()


def test_mark_done_and_stale_line_rejected(tmp_path):
    from cogstash.core import MutationStatus, mark_done, parse_notes

    notes_file = tmp_path / "cogstash.md"
    notes_file.write_text(
        "- [2026-03-26 14:00] first\n"
        "- [2026-03-26 15:00] ☐ target #todo\n"
        "- [2026-03-26 16:00] ☐ last #todo\n",
        encoding="utf-8",
    )

    notes = parse_notes(notes_file)
    assert mark_done(notes_file, notes[1]) is MutationStatus.SUCCESS
    assert "☑ target #todo" in notes_file.read_text(encoding="utf-8")

    stale_note = parse_notes(notes_file)[2]
    notes_file.write_text(
        "- [2026-03-26 15:00] ☑ target #todo\n"
        "- [2026-03-26 16:00] ☐ last #todo\n",
        encoding="utf-8",
    )
    assert mark_done(notes_file, stale_note) is MutationStatus.STALE_NOTE


def test_mark_done_already_done(tmp_path):
    from cogstash.core import MutationStatus, mark_done, parse_notes

    notes_file = tmp_path / "cogstash.md"
    notes_file.write_text("- [2026-03-26 14:30] ☑ already done #todo\n", encoding="utf-8")

    note = parse_notes(notes_file)[0]

    assert mark_done(notes_file, note) is MutationStatus.ALREADY_DONE
    assert notes_file.read_text(encoding="utf-8") == "- [2026-03-26 14:30] ☑ already done #todo\n"


def test_mark_done_returns_io_error_when_write_fails(tmp_path, monkeypatch):
    from cogstash.core import MutationStatus, mark_done, parse_notes
    from cogstash.core import notes as notes_mod

    notes_file = tmp_path / "cogstash.md"
    original = "- [2026-03-26 14:30] ☐ target #todo\n"
    notes_file.write_text(original, encoding="utf-8")

    note = parse_notes(notes_file)[0]
    monkeypatch.setattr(notes_mod, "_atomic_write", lambda _path, _content: (_ for _ in ()).throw(OSError("disk full")))

    assert mark_done(notes_file, note) is MutationStatus.IO_ERROR
    assert notes_file.read_text(encoding="utf-8") == original


def test_note_line_span_single_and_multiline(tmp_path):
    from cogstash.core import parse_notes
    from cogstash.core.notes import _note_line_span

    notes_file = tmp_path / "cogstash.md"
    notes_file.write_text(
        "- [2026-03-26 14:30] first line\n"
        "  second line\n"
        "  third line\n"
        "- [2026-03-26 15:00] next note\n",
        encoding="utf-8",
    )

    notes = parse_notes(notes_file)
    lines = notes_file.read_text(encoding="utf-8").splitlines(keepends=True)

    assert _note_line_span(lines, notes[0].line_number) == (0, 3)
    assert _note_line_span(lines, notes[1].line_number) == (3, 4)


def test_edit_note(tmp_path):
    from cogstash.core import MutationStatus, edit_note, parse_notes

    notes_file = tmp_path / "cogstash.md"
    notes_file.write_text(
        "- [2026-03-26 14:30] old first\n"
        "  old second\n"
        "- [2026-03-26 15:00] keep this\n",
        encoding="utf-8",
    )

    notes = parse_notes(notes_file)

    assert edit_note(notes_file, notes[0], "new first\nnew second\nnew third") is MutationStatus.SUCCESS
    assert edit_note(notes_file, notes[1], "   ") is MutationStatus.INVALID_INPUT

    content = notes_file.read_text(encoding="utf-8")
    assert "- [2026-03-26 14:30] new first\n" in content
    assert "  new second\n" in content
    assert "  new third\n" in content
    assert "- [2026-03-26 15:00] keep this\n" in content


def test_edit_note_single_line(tmp_path):
    from cogstash.core import MutationStatus, edit_note, parse_notes

    notes_file = tmp_path / "cogstash.md"
    notes_file.write_text(
        "- [2026-03-26 14:30] buy milk #todo\n"
        "- [2026-03-26 15:00] meeting\n",
        encoding="utf-8",
    )

    note = parse_notes(notes_file)[0]

    assert edit_note(notes_file, note, "buy oat milk #todo") is MutationStatus.SUCCESS

    content = notes_file.read_text(encoding="utf-8")
    assert "- [2026-03-26 14:30] buy oat milk #todo\n" in content
    assert "buy milk" not in content
    assert "- [2026-03-26 15:00] meeting\n" in content


def test_edit_and_delete_stale_line_rejected(tmp_path):
    from cogstash.core import MutationStatus, delete_note, edit_note, parse_notes

    notes_file = tmp_path / "cogstash.md"
    notes_file.write_text(
        "- [2026-03-26 14:00] first\n"
        "- [2026-03-26 15:00] target #todo\n"
        "- [2026-03-26 16:00] last\n",
        encoding="utf-8",
    )

    note = parse_notes(notes_file)[1]
    current = "- [2026-03-26 15:00] target #todo\n- [2026-03-26 16:00] last\n"
    notes_file.write_text(current, encoding="utf-8")

    assert edit_note(notes_file, note, "updated #todo") is MutationStatus.STALE_NOTE
    assert delete_note(notes_file, note) is MutationStatus.STALE_NOTE
    assert notes_file.read_text(encoding="utf-8") == current


def test_delete_note(tmp_path):
    from cogstash.core import MutationStatus, delete_note, parse_notes

    notes_file = tmp_path / "cogstash.md"
    notes_file.write_text(
        "- [2026-03-26 14:30] delete me\n"
        "  continuation\n"
        "- [2026-03-26 15:00] keep me\n",
        encoding="utf-8",
    )

    note = parse_notes(notes_file)[0]

    assert delete_note(notes_file, note) is MutationStatus.SUCCESS

    content = notes_file.read_text(encoding="utf-8")
    assert "delete me" not in content
    assert "continuation" not in content
    assert "- [2026-03-26 15:00] keep me\n" in content


def test_edit_note_returns_io_error_when_write_fails(tmp_path, monkeypatch):
    from cogstash.core import MutationStatus, edit_note, parse_notes
    from cogstash.core import notes as notes_mod

    notes_file = tmp_path / "cogstash.md"
    original = "- [2026-03-26 14:30] old text\n"
    notes_file.write_text(original, encoding="utf-8")

    note = parse_notes(notes_file)[0]
    monkeypatch.setattr(notes_mod, "_atomic_write", lambda _path, _content: (_ for _ in ()).throw(OSError("disk full")))

    assert edit_note(notes_file, note, "new text") is MutationStatus.IO_ERROR
    assert notes_file.read_text(encoding="utf-8") == original


def test_delete_note_returns_io_error_when_write_fails(tmp_path, monkeypatch):
    from cogstash.core import MutationStatus, delete_note, parse_notes
    from cogstash.core import notes as notes_mod

    notes_file = tmp_path / "cogstash.md"
    original = "- [2026-03-26 14:30] delete me\n"
    notes_file.write_text(original, encoding="utf-8")

    note = parse_notes(notes_file)[0]
    monkeypatch.setattr(notes_mod, "_atomic_write", lambda _path, _content: (_ for _ in ()).throw(OSError("disk full")))

    assert delete_note(notes_file, note) is MutationStatus.IO_ERROR
    assert notes_file.read_text(encoding="utf-8") == original


def test_atomic_write_cleans_up_temp_file_on_replace_failure(tmp_path, monkeypatch):
    from cogstash.core import notes as notes_mod

    path = tmp_path / "cogstash.md"
    path.write_text("original\n", encoding="utf-8")
    tmp = path.with_suffix(".tmp")

    monkeypatch.setattr(notes_mod.os, "replace", lambda _src, _dst: (_ for _ in ()).throw(OSError("replace failed")))

    try:
        notes_mod._atomic_write(path, "updated\n")
    except OSError:
        pass

    assert not tmp.exists()
    assert path.read_text(encoding="utf-8") == "original\n"


def test_compute_stats_basic_and_empty(tmp_path):
    from cogstash.core import compute_stats, parse_notes

    notes_file = tmp_path / "cogstash.md"
    notes_file.write_text(
        "- [2026-01-15 09:00] first note #todo\n"
        "- [2026-02-10 14:30] ☑ done item #todo\n"
        "- [2026-03-27 16:00] latest note #idea\n",
        encoding="utf-8",
    )

    stats = compute_stats(parse_notes(notes_file))
    empty_stats = compute_stats([])

    assert stats["total"] == 3
    assert stats["done"] == 1
    assert stats["pending"] == 2
    assert stats["tag_counts"]["todo"] == 2
    assert stats["avg_length"] > 0
    assert stats["longest"] >= stats["avg_length"]
    assert empty_stats["total"] == 0
    assert empty_stats["tag_counts"] == {}


def test_count_tags_empty_input_returns_empty_dict():
    from cogstash.core.notes import count_tags

    assert count_tags([]) == {}


def test_count_tags_aggregates_counts_and_orders_ties_by_tag_name(tmp_path):
    from cogstash.core import parse_notes
    from cogstash.core.notes import count_tags

    notes_file = tmp_path / "cogstash.md"
    notes_file.write_text(
        "- [2026-03-26 09:00] first #beta #alpha\n"
        "- [2026-03-26 10:00] second #beta #gamma\n"
        "- [2026-03-26 11:00] third #alpha\n",
        encoding="utf-8",
    )

    tag_counts = count_tags(parse_notes(notes_file))

    assert tag_counts == {"alpha": 2, "beta": 2, "gamma": 1}
    assert list(tag_counts.items()) == [("alpha", 2), ("beta", 2), ("gamma", 1)]


def test_compute_stats_reuses_shared_tag_count_ordering(tmp_path):
    from cogstash.core import compute_stats, parse_notes

    notes_file = tmp_path / "cogstash.md"
    notes_file.write_text(
        "- [2026-03-26 09:00] first #beta #alpha\n"
        "- [2026-03-26 10:00] second #beta #gamma\n"
        "- [2026-03-26 11:00] third #alpha\n",
        encoding="utf-8",
    )

    stats = compute_stats(parse_notes(notes_file))

    assert stats["tag_counts"] == {"alpha": 2, "beta": 2, "gamma": 1}
    assert list(stats["tag_counts"].items()) == [("alpha", 2), ("beta", 2), ("gamma", 1)]


def test_compute_stats_streaks(tmp_path):
    from cogstash.core import compute_stats, parse_notes

    today = date.today()
    dates = [today - timedelta(days=i) for i in range(3, -1, -1)]
    notes_file = tmp_path / "cogstash.md"
    notes_file.write_text(
        "".join(f"- [{day.strftime('%Y-%m-%d')} 09:00] day {idx}\n" for idx, day in enumerate(dates, start=1)),
        encoding="utf-8",
    )

    stats = compute_stats(parse_notes(notes_file))

    assert stats["current_streak"] == 4
    assert stats["longest_streak"] == 4
    assert stats["notes_this_week"] >= 1


def test_compute_stats_current_streak_reuses_date_set(tmp_path, monkeypatch):
    from cogstash.core import compute_stats, parse_notes

    today = date.today()
    dates = [today - timedelta(days=i) for i in range(3, -1, -1)]
    notes_file = tmp_path / "cogstash.md"
    notes_file.write_text(
        "".join(f"- [{day.strftime('%Y-%m-%d')} 09:00] day {idx}\n" for idx, day in enumerate(dates, start=1)),
        encoding="utf-8",
    )
    notes = parse_notes(notes_file)

    real_set = builtins.set
    set_calls = 0

    def counting_set(*args, **kwargs):
        nonlocal set_calls
        set_calls += 1
        return real_set(*args, **kwargs)

    monkeypatch.setattr(builtins, "set", counting_set)

    stats = compute_stats(notes)

    assert stats["current_streak"] == 4
    assert set_calls == 1
