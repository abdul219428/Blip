"""Tests for cogstash_cli.py — CLI command handlers and output formatting."""

from datetime import datetime

from _helpers import CaptureStream, StrictEncodedStream


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
    from cogstash.cli import format_note
    from cogstash.search import Note

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
    from cogstash.cli import format_note
    from cogstash.search import Note

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
    from cogstash.cli import format_note
    from cogstash.search import Note

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


def test_stream_supports_color_handles_none():
    from cogstash.cli import stream_supports_color

    assert stream_supports_color(None) is False


def test_stream_supports_color_handles_missing_isatty():
    from cogstash.cli import stream_supports_color

    class StreamWithoutIsatty:
        pass

    assert stream_supports_color(StreamWithoutIsatty()) is False


def test_stream_supports_color_handles_isatty_errors():
    from cogstash.cli import stream_supports_color

    class BrokenStream:
        def isatty(self):
            raise OSError("broken")

    assert stream_supports_color(BrokenStream()) is False


def test_stream_supports_color_true_and_false_paths():
    from cogstash.cli import stream_supports_color

    class TtyStream:
        def isatty(self):
            return True

    class NonTtyStream:
        def isatty(self):
            return False

    assert stream_supports_color(TtyStream()) is True
    assert stream_supports_color(NonTtyStream()) is False


def test_cmd_recent_default(tmp_path, capsys):
    """Shows notes newest-first, up to 20 by default."""
    f = _make_notes_file(tmp_path)
    from types import SimpleNamespace

    from cogstash.cli import cmd_recent
    from cogstash.core import CogStashConfig

    cmd_recent(SimpleNamespace(limit=20), CogStashConfig(output_file=f))
    output = capsys.readouterr().out
    lines = [line for line in output.strip().split("\n") if line.strip()]

    assert len(lines) == 5
    assert "redesign dashboard" in lines[0]
    assert "old note" in lines[4]


def test_cmd_recent_limit(tmp_path, capsys):
    """--limit restricts number of notes shown."""
    f = _make_notes_file(tmp_path)
    from types import SimpleNamespace

    from cogstash.cli import cmd_recent
    from cogstash.core import CogStashConfig

    cmd_recent(SimpleNamespace(limit=2), CogStashConfig(output_file=f))
    output = capsys.readouterr().out
    lines = [line for line in output.strip().split("\n") if line.strip()]

    assert len(lines) == 2
    assert "redesign dashboard" in lines[0]
    assert "fix login bug" in lines[1]


def test_cmd_recent_empty(tmp_path, capsys):
    """Empty/missing file shows 'No notes found.' message."""
    f = tmp_path / "cogstash.md"
    from types import SimpleNamespace

    from cogstash.cli import cmd_recent
    from cogstash.core import CogStashConfig

    cmd_recent(SimpleNamespace(limit=20), CogStashConfig(output_file=f))
    output = capsys.readouterr().out
    assert "No notes found." in output


def test_cmd_search_match(tmp_path, capsys):
    """Finds notes matching the query, newest first."""
    f = _make_notes_file(tmp_path)
    from types import SimpleNamespace

    from cogstash.cli import cmd_search
    from cogstash.core import CogStashConfig

    cmd_search(SimpleNamespace(query="milk", limit=20), CogStashConfig(output_file=f))
    output = capsys.readouterr().out
    lines = [line for line in output.strip().split("\n") if line.strip()]

    assert len(lines) == 1
    assert "buy milk" in lines[0]


def test_cmd_search_no_match(tmp_path, capsys):
    """No matches shows 'No matching notes.' message."""
    f = _make_notes_file(tmp_path)
    from types import SimpleNamespace

    from cogstash.cli import cmd_search
    from cogstash.core import CogStashConfig

    cmd_search(SimpleNamespace(query="nonexistent xyz", limit=20), CogStashConfig(output_file=f))
    output = capsys.readouterr().out
    assert "No matching notes." in output


def test_cmd_tags_counts(tmp_path, capsys):
    """Tags listed with correct counts, sorted by count descending."""
    f = _make_notes_file(tmp_path)
    from types import SimpleNamespace

    from cogstash.cli import cmd_tags
    from cogstash.core import CogStashConfig

    cmd_tags(SimpleNamespace(), CogStashConfig(output_file=f))
    output = capsys.readouterr().out
    lines = [line for line in output.strip().split("\n") if line.strip()]

    assert len(lines) == 3
    assert "#important" in lines[0]
    assert "#todo" in lines[1]
    assert "#urgent" in lines[2]
    assert "1 note" in lines[0]


def test_cmd_tags_empty(tmp_path, capsys):
    """Empty file shows 'No tags found.' message."""
    f = tmp_path / "cogstash.md"
    f.write_text("", encoding="utf-8")
    from types import SimpleNamespace

    from cogstash.cli import cmd_tags
    from cogstash.core import CogStashConfig

    cmd_tags(SimpleNamespace(), CogStashConfig(output_file=f))
    output = capsys.readouterr().out
    assert "No tags found." in output


def test_hex_to_ansi():
    """hex_to_ansi maps hex colors to nearest ANSI codes."""
    from cogstash.cli import hex_to_ansi

    assert hex_to_ansi("#ff0000") == "\033[31m"
    assert hex_to_ansi("#00ff00") == "\033[32m"
    assert hex_to_ansi("#0000ff") == "\033[34m"
    assert hex_to_ansi("#ffff00") == "\033[33m"


def test_format_note_custom_tag(tmp_path):
    """format_note colors custom tags when ansi_tag map provided."""
    from datetime import datetime

    from cogstash.cli import format_note
    from cogstash.search import Note

    note = Note(
        index=1,
        timestamp=datetime(2026, 3, 27, 10, 0),
        text="meeting #work",
        tags=["work"],
    )
    ansi_map = {"work": "\033[34m"}
    result = format_note(note, use_color=True, ansi_tag=ansi_map)
    assert "\033[34m" in result
    assert "#work" in result


def test_cmd_add_argument(tmp_path):
    """cogstash add 'text' saves note via argument."""
    from types import SimpleNamespace

    from cogstash.cli import cmd_add
    from cogstash.core import CogStashConfig

    f = tmp_path / "cogstash.md"
    cmd_add(SimpleNamespace(text=["hello", "world"]), CogStashConfig(output_file=f))
    content = f.read_text(encoding="utf-8")
    assert "hello world" in content
    assert content.startswith("- [")


def test_cmd_add_stdin(tmp_path, monkeypatch):
    """cogstash add reads from stdin when no argument given."""
    import io
    from types import SimpleNamespace

    from cogstash.cli import cmd_add
    from cogstash.core import CogStashConfig

    monkeypatch.setattr("sys.stdin", io.StringIO("from stdin"))
    f = tmp_path / "cogstash.md"
    cmd_add(SimpleNamespace(text=[]), CogStashConfig(output_file=f))
    content = f.read_text(encoding="utf-8")
    assert "from stdin" in content


def test_cmd_add_interactive_stdin_shows_error(monkeypatch, tmp_path, capsys):
    import argparse

    import pytest

    from cogstash.cli import cmd_add
    from cogstash.core import CogStashConfig

    class InteractiveStdin:
        def isatty(self):
            return True

    config = CogStashConfig(output_file=tmp_path / "cogstash.md")
    monkeypatch.setattr("sys.stdin", InteractiveStdin())

    with pytest.raises(SystemExit) as exc:
        cmd_add(argparse.Namespace(text=[]), config)

    assert exc.value.code == 1
    assert "provide note text" in capsys.readouterr().err.lower()


def test_cmd_add_missing_stdin_none_shows_error(monkeypatch, tmp_path, capsys):
    import argparse

    import pytest

    from cogstash.cli import cmd_add
    from cogstash.core import CogStashConfig

    config = CogStashConfig(output_file=tmp_path / "cogstash.md")
    monkeypatch.setattr("sys.stdin", None)

    with pytest.raises(SystemExit) as exc:
        cmd_add(argparse.Namespace(text=[]), config)

    assert exc.value.code == 1
    err = capsys.readouterr().err.lower()
    assert "provide note text" in err


def test_cmd_add_smart_tags(tmp_path):
    """cogstash add applies smart tag emoji prefixes."""
    from types import SimpleNamespace

    from cogstash.cli import cmd_add
    from cogstash.core import CogStashConfig

    f = tmp_path / "cogstash.md"
    cmd_add(SimpleNamespace(text=["buy", "milk", "#todo"]), CogStashConfig(output_file=f))
    content = f.read_text(encoding="utf-8")
    assert "☐" in content
    assert "#todo" in content


def test_cmd_add_multiline_stdin(tmp_path, monkeypatch):
    """Multi-line stdin produces continuation-indented output."""
    import io
    from types import SimpleNamespace

    from cogstash.cli import cmd_add
    from cogstash.core import CogStashConfig

    monkeypatch.setattr("sys.stdin", io.StringIO("line one\nline two"))
    f = tmp_path / "cogstash.md"
    cmd_add(SimpleNamespace(text=[]), CogStashConfig(output_file=f))
    content = f.read_text(encoding="utf-8")
    assert "line one" in content
    assert "  line two" in content


def test_cmd_add_empty(tmp_path, monkeypatch):
    """Empty input causes sys.exit(1)."""
    import io
    from types import SimpleNamespace

    import pytest

    from cogstash.cli import cmd_add
    from cogstash.core import CogStashConfig

    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    f = tmp_path / "cogstash.md"
    with pytest.raises(SystemExit):
        cmd_add(SimpleNamespace(text=[]), CogStashConfig(output_file=f))


def test_cmd_edit_by_number(tmp_path, capsys):
    """Edit by note number replaces text, preserves timestamp."""
    f = _make_notes_file(tmp_path)
    from types import SimpleNamespace

    from cogstash.cli import cmd_edit
    from cogstash.core import CogStashConfig

    cmd_edit(SimpleNamespace(args=["3", "updated", "note"], search=None), CogStashConfig(output_file=f))
    content = f.read_text(encoding="utf-8")
    assert "updated note" in content
    assert "- [2026-03-26 14:30]" in content
    output = capsys.readouterr().out
    assert "updated" in output.lower() or "Note 3" in output


def test_cmd_edit_by_search(tmp_path, capsys):
    """Edit by search keyword finds and replaces note."""
    f = _make_notes_file(tmp_path)
    from types import SimpleNamespace

    from cogstash.cli import cmd_edit
    from cogstash.core import CogStashConfig

    cmd_edit(SimpleNamespace(args=["get", "oat", "milk"], search="buy milk"), CogStashConfig(output_file=f))
    content = f.read_text(encoding="utf-8")
    assert "get oat milk" in content
    assert "buy milk" not in content


def test_cmd_edit_not_found(tmp_path):
    """Edit with invalid number exits with code 1."""
    import pytest
    f = _make_notes_file(tmp_path)
    from types import SimpleNamespace

    from cogstash.cli import cmd_edit
    from cogstash.core import CogStashConfig

    with pytest.raises(SystemExit):
        cmd_edit(SimpleNamespace(args=["99", "nope"], search=None), CogStashConfig(output_file=f))


def test_cmd_edit_no_text(tmp_path):
    """Edit with empty text exits with code 1."""
    import pytest
    f = _make_notes_file(tmp_path)
    from types import SimpleNamespace

    from cogstash.cli import cmd_edit
    from cogstash.core import CogStashConfig

    with pytest.raises(SystemExit):
        cmd_edit(SimpleNamespace(args=["1"], search=None), CogStashConfig(output_file=f))


def test_cmd_edit_search_multiple_matches(tmp_path, capsys):
    """Edit with ambiguous search shows matches and exits with code 1."""
    import pytest
    f = _make_notes_file(tmp_path)
    from types import SimpleNamespace

    from cogstash.cli import cmd_edit
    from cogstash.core import CogStashConfig

    with pytest.raises(SystemExit):
        cmd_edit(SimpleNamespace(args=["new"], search="note"), CogStashConfig(output_file=f))
    err = capsys.readouterr().err
    assert "Multiple matches" in err


def test_cmd_delete_with_yes(tmp_path, capsys):
    """Delete with --yes skips confirmation and removes note."""
    f = _make_notes_file(tmp_path)
    from types import SimpleNamespace

    from cogstash.cli import cmd_delete
    from cogstash.core import CogStashConfig

    cmd_delete(SimpleNamespace(number=3, yes=True, search=None), CogStashConfig(output_file=f))
    content = f.read_text(encoding="utf-8")
    assert "buy milk" not in content
    output = capsys.readouterr().out
    assert "deleted" in output.lower() or "Note 3" in output


def test_cmd_delete_by_search(tmp_path, capsys):
    """Delete by search keyword finds and removes note."""
    f = _make_notes_file(tmp_path)
    from types import SimpleNamespace

    from cogstash.cli import cmd_delete
    from cogstash.core import CogStashConfig

    cmd_delete(SimpleNamespace(number=None, yes=True, search="buy milk"), CogStashConfig(output_file=f))
    content = f.read_text(encoding="utf-8")
    assert "buy milk" not in content
    output = capsys.readouterr().out
    assert "deleted" in output.lower()


def test_cmd_delete_confirm_yes(tmp_path, monkeypatch):
    """Delete with interactive confirmation (user types 'y')."""
    f = _make_notes_file(tmp_path)
    from types import SimpleNamespace

    from cogstash.cli import cmd_delete
    from cogstash.core import CogStashConfig

    monkeypatch.setattr("builtins.input", lambda _: "y")
    cmd_delete(SimpleNamespace(number=3, yes=False, search=None), CogStashConfig(output_file=f))
    content = f.read_text(encoding="utf-8")
    assert "buy milk" not in content


def test_cmd_delete_confirm_no(tmp_path, monkeypatch):
    """Delete cancelled when user types 'n'."""
    f = _make_notes_file(tmp_path)
    from types import SimpleNamespace

    from cogstash.cli import cmd_delete
    from cogstash.core import CogStashConfig

    monkeypatch.setattr("builtins.input", lambda _: "n")
    cmd_delete(SimpleNamespace(number=3, yes=False, search=None), CogStashConfig(output_file=f))
    content = f.read_text(encoding="utf-8")
    assert "buy milk" in content


def test_cmd_delete_not_found(tmp_path):
    """Delete with invalid number exits with code 1."""
    import pytest
    f = _make_notes_file(tmp_path)
    from types import SimpleNamespace

    from cogstash.cli import cmd_delete
    from cogstash.core import CogStashConfig

    with pytest.raises(SystemExit):
        cmd_delete(SimpleNamespace(number=99, yes=True, search=None), CogStashConfig(output_file=f))


def test_cmd_export_json(tmp_path, monkeypatch, capsys):
    """Export to JSON creates file with all notes."""
    f = _make_notes_file(tmp_path)
    monkeypatch.chdir(tmp_path)
    from types import SimpleNamespace

    from cogstash.cli import cmd_export
    from cogstash.core import CogStashConfig

    cmd_export(
        SimpleNamespace(format="json", output=None),
        CogStashConfig(output_file=f),
    )
    output = capsys.readouterr().out
    assert "Exported" in output


def test_cmd_export_json_content(tmp_path, monkeypatch, capsys):
    """JSON export contains correct note data."""
    import json
    f = _make_notes_file(tmp_path)
    monkeypatch.chdir(tmp_path)
    from types import SimpleNamespace

    from cogstash.cli import cmd_export
    from cogstash.core import CogStashConfig

    cmd_export(
        SimpleNamespace(format="json", output=None),
        CogStashConfig(output_file=f),
    )
    exported = list(tmp_path.glob("cogstash-export-*.json"))
    assert len(exported) == 1
    data = json.loads(exported[0].read_text(encoding="utf-8"))
    assert len(data) == 5
    assert "text" in data[0]
    assert "timestamp" in data[0]
    assert "tags" in data[0]


def test_cmd_export_csv(tmp_path, monkeypatch, capsys):
    """CSV export creates valid CSV file."""
    import csv
    f = _make_notes_file(tmp_path)
    monkeypatch.chdir(tmp_path)
    from types import SimpleNamespace

    from cogstash.cli import cmd_export
    from cogstash.core import CogStashConfig

    cmd_export(
        SimpleNamespace(format="csv", output=None),
        CogStashConfig(output_file=f),
    )
    exported = list(tmp_path.glob("cogstash-export-*.csv"))
    assert len(exported) == 1
    with open(exported[0], encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
    assert len(rows) == 5
    assert "timestamp" in reader.fieldnames
    assert "text" in reader.fieldnames


def test_cmd_export_md(tmp_path, monkeypatch, capsys):
    """Markdown export creates valid .md file."""
    f = _make_notes_file(tmp_path)
    monkeypatch.chdir(tmp_path)
    from types import SimpleNamespace

    from cogstash.cli import cmd_export
    from cogstash.core import CogStashConfig

    cmd_export(
        SimpleNamespace(format="md", output=None),
        CogStashConfig(output_file=f),
    )
    exported = list(tmp_path.glob("cogstash-export-*.md"))
    assert len(exported) == 1
    content = exported[0].read_text(encoding="utf-8")
    assert "# CogStash Export" in content
    assert "buy milk" in content


def test_cmd_export_custom_output(tmp_path, capsys):
    """--output flag writes to specified path."""
    import json
    f = _make_notes_file(tmp_path)
    out_path = tmp_path / "custom.json"
    from types import SimpleNamespace

    from cogstash.cli import cmd_export
    from cogstash.core import CogStashConfig

    cmd_export(
        SimpleNamespace(format="json", output=str(out_path)),
        CogStashConfig(output_file=f),
    )
    assert out_path.exists()
    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert len(data) == 5


def test_cmd_stats_output(tmp_path, capsys):
    """Stats displays totals, tags, and date range."""
    f = _make_notes_file(tmp_path)
    from types import SimpleNamespace

    from cogstash.cli import cmd_stats
    from cogstash.core import CogStashConfig

    cmd_stats(SimpleNamespace(), CogStashConfig(output_file=f))
    output = capsys.readouterr().out

    assert "Total notes" in output or "5" in output
    assert "#todo" in output or "todo" in output
    assert "2026" in output


def test_cmd_stats_empty(tmp_path, capsys):
    """Stats on empty file shows no-notes message."""
    f = tmp_path / "cogstash.md"
    from types import SimpleNamespace

    from cogstash.cli import cmd_stats
    from cogstash.core import CogStashConfig

    cmd_stats(SimpleNamespace(), CogStashConfig(output_file=f))
    output = capsys.readouterr().out
    assert "No notes" in output


def test_cmd_stats_done_pending(tmp_path, capsys):
    """Stats shows correct done/pending counts."""
    f = _make_notes_file(tmp_path)
    from types import SimpleNamespace

    from cogstash.cli import cmd_stats
    from cogstash.core import CogStashConfig

    cmd_stats(SimpleNamespace(), CogStashConfig(output_file=f))
    output = capsys.readouterr().out
    assert "1" in output
    assert "4" in output


def test_cmd_stats_handles_none_stdout(monkeypatch, tmp_path):
    """Stats prints through sys.__stdout__ when sys.stdout is None."""
    from types import SimpleNamespace

    from cogstash.cli import cmd_stats
    from cogstash.core import CogStashConfig

    capture = CaptureStream()
    f = _make_notes_file(tmp_path)
    import sys

    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "__stdout__", capture)

    cmd_stats(SimpleNamespace(), CogStashConfig(output_file=f))

    output = capture.getvalue()
    assert "Total notes" in output
    assert "5" in output


def test_cmd_search_plain_output_without_isatty(monkeypatch, tmp_path):
    """Search falls back to plain text when stdout lacks isatty()."""
    from types import SimpleNamespace

    from cogstash.cli import cmd_search
    from cogstash.core import CogStashConfig

    capture = CaptureStream()
    f = _make_notes_file(tmp_path)
    import sys

    monkeypatch.setattr(sys, "stdout", capture)

    cmd_search(SimpleNamespace(query="milk", limit=20), CogStashConfig(output_file=f))

    output = capture.getvalue()
    assert "\033[" not in output
    assert "buy milk" in output


def test_cmd_stats_replaces_unencodable_chars(monkeypatch, tmp_path):
    """Stats stays readable when stdout encoding cannot emit emoji."""
    from types import SimpleNamespace

    from cogstash.cli import cmd_stats
    from cogstash.core import CogStashConfig

    capture = StrictEncodedStream("cp1252")
    f = _make_notes_file(tmp_path)
    import sys

    monkeypatch.setattr(sys, "stdout", capture)

    cmd_stats(SimpleNamespace(), CogStashConfig(output_file=f))

    output = capture.getvalue()
    assert "CogStash Stats" in output
    assert "Total notes" in output
    assert "📊" not in output


def test_cmd_search_replaces_unencodable_note_chars(monkeypatch, tmp_path):
    """Search should not crash when note text contains characters outside stdout encoding."""
    from types import SimpleNamespace

    from cogstash.cli import cmd_search
    from cogstash.core import CogStashConfig

    capture = StrictEncodedStream("cp1252")
    f = tmp_path / "cogstash.md"
    f.write_text("- [2026-03-28 09:00] smile 😀 note\n", encoding="utf-8")
    import sys

    monkeypatch.setattr(sys, "stdout", capture)

    cmd_search(SimpleNamespace(query="smile", limit=20), CogStashConfig(output_file=f))

    output = capture.getvalue()
    assert "smile" in output
    assert "😀" not in output


def test_cmd_config_get(tmp_path, capsys):
    """cogstash config get returns current value."""
    config_path = tmp_path / ".cogstash.json"
    config_path.write_text('{"theme": "dracula"}', encoding="utf-8")
    from types import SimpleNamespace

    from cogstash.cli import cmd_config
    from cogstash.core import CogStashConfig

    cmd_config(
        SimpleNamespace(action="get", key="theme", value=None),
        CogStashConfig(theme="dracula"),
        config_path=config_path,
    )
    output = capsys.readouterr().out
    assert "dracula" in output


def test_cmd_config_set(tmp_path, capsys):
    """cogstash config set updates JSON file."""
    import json
    config_path = tmp_path / ".cogstash.json"
    config_path.write_text('{"theme": "tokyo-night"}', encoding="utf-8")
    from types import SimpleNamespace

    from cogstash.cli import cmd_config
    from cogstash.core import CogStashConfig

    cmd_config(
        SimpleNamespace(action="set", key="theme", value="dracula"),
        CogStashConfig(theme="tokyo-night"),
        config_path=config_path,
    )
    data = json.loads(config_path.read_text(encoding="utf-8"))
    assert data["theme"] == "dracula"
    output = capsys.readouterr().out
    assert "dracula" in output


def test_cmd_config_set_invalid_theme(tmp_path, capsys):
    """cogstash config set rejects invalid theme."""
    config_path = tmp_path / ".cogstash.json"
    config_path.write_text('{"theme": "tokyo-night"}', encoding="utf-8")
    from types import SimpleNamespace

    import pytest

    from cogstash.cli import cmd_config
    from cogstash.core import CogStashConfig

    with pytest.raises(SystemExit):
        cmd_config(
            SimpleNamespace(action="set", key="theme", value="nope"),
            CogStashConfig(),
            config_path=config_path,
        )


def test_cmd_config_wizard(tmp_path, monkeypatch, capsys):
    """Interactive wizard updates config file."""
    config_path = tmp_path / ".cogstash.json"
    config_path.write_text("{}", encoding="utf-8")

    monkeypatch.setattr("builtins.input", lambda _: "")

    from types import SimpleNamespace

    from cogstash.cli import cmd_config
    from cogstash.core import CogStashConfig

    cmd_config(
        SimpleNamespace(action=None, key=None, value=None),
        CogStashConfig(),
        config_path=config_path,
    )
    output = capsys.readouterr().out
    assert "saved" in output.lower() or "Config" in output


def test_cmd_config_get_invalid_key(tmp_path, capsys):
    """cogstash config get with unknown key shows error."""
    config_path = tmp_path / ".cogstash.json"
    config_path.write_text("{}", encoding="utf-8")
    from types import SimpleNamespace

    import pytest

    from cogstash.cli import cmd_config
    from cogstash.core import CogStashConfig

    with pytest.raises(SystemExit):
        cmd_config(
            SimpleNamespace(action="get", key="nonexistent", value=None),
            CogStashConfig(),
            config_path=config_path,
        )


def test_version_flag(capsys):
    """cogstash --version prints the version string."""
    from cogstash.cli import build_parser

    parser = build_parser()
    try:
        parser.parse_args(["--version"])
    except SystemExit:
        pass
    captured = capsys.readouterr()
    assert "cogstash" in captured.out.lower() or "0." in captured.out


def test_version_flag_without_isatty(monkeypatch):
    """--version prints even when stdout has no isatty()."""
    import pytest

    from cogstash.cli import build_parser

    capture = CaptureStream()
    import sys

    monkeypatch.setattr(sys, "stdout", capture)

    parser = build_parser()
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["--version"])

    assert exc.value.code == 0
    output = capture.getvalue()
    assert "cogstash" in output.lower()


def test_edit_help_includes_note_number_and_search_examples(capsys):
    """edit help teaches note-number and search-based editing."""
    import pytest

    from cogstash.cli import build_parser

    parser = build_parser()
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["edit", "--help"])

    output = capsys.readouterr().out
    assert exc.value.code == 0
    assert "note number or --search" in output.lower()
    assert 'cogstash edit 42 "Updated note text"' in output
    assert 'cogstash edit --search "installer" "Updated note text"' in output
    assert "(default:" not in output


def test_delete_help_includes_yes_and_examples(capsys):
    """delete help teaches confirmation and search-based deletion."""
    import pytest

    from cogstash.cli import build_parser

    parser = build_parser()
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["delete", "--help"])

    output = capsys.readouterr().out
    assert exc.value.code == 0
    assert 'cogstash delete 42' in output
    assert 'cogstash delete --search "installer" --yes' in output
    assert "(default:" not in output


def test_cli_main_version_does_not_import_app(monkeypatch):
    """cli_main --version should exit cleanly without importing GUI/app dependencies."""
    import sys
    import types

    import pytest

    from cogstash.cli import cli_main

    capture = CaptureStream()

    app_stub = types.ModuleType("cogstash.app")

    def _fail(name):
        raise AssertionError(f"cli_main --version should not access cogstash.app.{name}")

    app_stub.__getattr__ = _fail
    monkeypatch.setattr(sys, "stdout", capture)
    monkeypatch.setitem(sys.modules, "cogstash.app", app_stub)

    with pytest.raises(SystemExit) as exc:
        cli_main(["--version"])

    assert exc.value.code == 0
    assert "cogstash" in capture.getvalue().lower()


def test_invalid_command_exits_as_cli_error(capsys):
    """Unknown subcommands raise argparse CLI errors."""
    import pytest

    from cogstash.cli import build_parser

    parser = build_parser()
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["bogus"])

    assert exc.value.code == 2
    err = capsys.readouterr().err.lower()
    assert "invalid choice" in err


def test_invalid_flag_exits_as_cli_error(capsys):
    """Unknown flags raise argparse CLI errors."""
    import pytest

    from cogstash.cli import build_parser

    parser = build_parser()
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["--bogus"])

    assert exc.value.code == 2
    err = capsys.readouterr().err.lower()
    assert "unrecognized arguments" in err


def test_cli_path_does_not_call_gui_main(monkeypatch):
    """CLI args should stay in CLI dispatch and avoid GUI main."""
    import cogstash

    cli_called = []
    gui_called = []
    monkeypatch.setattr("cogstash.cli.cli_main", lambda argv: cli_called.append(argv))
    monkeypatch.setattr("cogstash.app.main", lambda: gui_called.append(True))
    monkeypatch.setattr("sys.argv", ["cogstash", "stats"])

    cogstash.main()

    assert cli_called == [["stats"]]
    assert gui_called == []


def test_main_no_args_launches_gui(monkeypatch):
    import cogstash

    launched = []
    monkeypatch.setattr("cogstash.app.main", lambda: launched.append("gui"))
    monkeypatch.setattr("sys.argv", ["cogstash"])

    cogstash.main()

    assert launched == ["gui"]


def test_main_with_cli_args_calls_cli_main(monkeypatch):
    import cogstash

    called = []
    monkeypatch.setattr("cogstash.cli.cli_main", lambda argv: called.append(argv))
    monkeypatch.setattr("sys.argv", ["cogstash", "stats"])

    cogstash.main()

    assert called == [["stats"]]


def test_main_invalid_cli_arg_stays_in_cli_mode(monkeypatch):
    import cogstash

    called = []
    gui_called = []
    monkeypatch.setattr("cogstash.cli.cli_main", lambda argv: called.append(argv))
    monkeypatch.setattr("cogstash.app.main", lambda: gui_called.append(True))
    monkeypatch.setattr("sys.argv", ["cogstash", "statz"])

    cogstash.main()

    assert called == [["statz"]]
    assert gui_called == []


def test_module_main_prepares_windows_console_for_cli(monkeypatch):
    """Windows CLI launches should prepare console streams before running CLI handlers."""
    import cogstash.__main__ as main_mod
    import cogstash.cli
    import cogstash.cli.windows

    calls = []
    monkeypatch.setattr(main_mod.sys, "platform", "win32")
    monkeypatch.setattr(main_mod.sys, "argv", ["cogstash", "stats"])
    monkeypatch.setattr(cogstash.cli.windows, "prepare_windows_cli_console", lambda: calls.append("prepare"))
    monkeypatch.setattr(cogstash.cli, "cli_main", lambda argv: calls.append(("cli", argv)))

    main_mod.main()

    assert calls == ["prepare", ("cli", ["stats"])]
