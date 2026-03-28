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


def test_cmd_recent_default(tmp_path, capsys):
    """Shows notes newest-first, up to 20 by default."""
    f = _make_notes_file(tmp_path)
    from cogstash.cli import cmd_recent
    from cogstash.app import CogStashConfig
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
    from cogstash.cli import cmd_recent
    from cogstash.app import CogStashConfig
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
    from cogstash.cli import cmd_recent
    from cogstash.app import CogStashConfig
    from types import SimpleNamespace

    cmd_recent(SimpleNamespace(limit=20), CogStashConfig(output_file=f))
    output = capsys.readouterr().out
    assert "No notes found." in output


def test_cmd_search_match(tmp_path, capsys):
    """Finds notes matching the query, newest first."""
    f = _make_notes_file(tmp_path)
    from cogstash.cli import cmd_search
    from cogstash.app import CogStashConfig
    from types import SimpleNamespace

    cmd_search(SimpleNamespace(query="milk", limit=20), CogStashConfig(output_file=f))
    output = capsys.readouterr().out
    lines = [l for l in output.strip().split("\n") if l.strip()]

    assert len(lines) == 1
    assert "buy milk" in lines[0]


def test_cmd_search_no_match(tmp_path, capsys):
    """No matches shows 'No matching notes.' message."""
    f = _make_notes_file(tmp_path)
    from cogstash.cli import cmd_search
    from cogstash.app import CogStashConfig
    from types import SimpleNamespace

    cmd_search(SimpleNamespace(query="nonexistent xyz", limit=20), CogStashConfig(output_file=f))
    output = capsys.readouterr().out
    assert "No matching notes." in output


def test_cmd_tags_counts(tmp_path, capsys):
    """Tags listed with correct counts, sorted by count descending."""
    f = _make_notes_file(tmp_path)
    from cogstash.cli import cmd_tags
    from cogstash.app import CogStashConfig
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
    from cogstash.cli import cmd_tags
    from cogstash.app import CogStashConfig
    from types import SimpleNamespace

    cmd_tags(SimpleNamespace(), CogStashConfig(output_file=f))
    output = capsys.readouterr().out
    assert "No tags found." in output


def test_hex_to_ansi():
    """hex_to_ansi maps hex colors to nearest ANSI codes."""
    from cogstash.cli import hex_to_ansi

    assert hex_to_ansi("#ff0000") == "\033[31m"  # red
    assert hex_to_ansi("#00ff00") == "\033[32m"  # green
    assert hex_to_ansi("#0000ff") == "\033[34m"  # blue
    assert hex_to_ansi("#ffff00") == "\033[33m"  # yellow


def test_format_note_custom_tag(tmp_path):
    """format_note colors custom tags when ansi_tag map provided."""
    from cogstash.cli import format_note
    from cogstash.search import Note
    from datetime import datetime

    note = Note(
        index=1,
        timestamp=datetime(2026, 3, 27, 10, 0),
        text="meeting #work",
        tags=["work"],
    )
    ansi_map = {"work": "\033[34m"}
    result = format_note(note, use_color=True, ansi_tag=ansi_map)
    assert "\033[34m" in result  # blue for #work
    assert "#work" in result


def test_cmd_add_argument(tmp_path):
    """cogstash add 'text' saves note via argument."""
    from cogstash.cli import cmd_add
    from cogstash.app import CogStashConfig
    from types import SimpleNamespace

    f = tmp_path / "cogstash.md"
    cmd_add(SimpleNamespace(text=["hello", "world"]), CogStashConfig(output_file=f))
    content = f.read_text(encoding="utf-8")
    assert "hello world" in content
    assert content.startswith("- [")


def test_cmd_add_stdin(tmp_path, monkeypatch):
    """cogstash add reads from stdin when no argument given."""
    import io
    from cogstash.cli import cmd_add
    from cogstash.app import CogStashConfig
    from types import SimpleNamespace

    monkeypatch.setattr("sys.stdin", io.StringIO("from stdin"))
    f = tmp_path / "cogstash.md"
    cmd_add(SimpleNamespace(text=[]), CogStashConfig(output_file=f))
    content = f.read_text(encoding="utf-8")
    assert "from stdin" in content


def test_cmd_add_smart_tags(tmp_path):
    """cogstash add applies smart tag emoji prefixes."""
    from cogstash.cli import cmd_add
    from cogstash.app import CogStashConfig
    from types import SimpleNamespace

    f = tmp_path / "cogstash.md"
    cmd_add(SimpleNamespace(text=["buy", "milk", "#todo"]), CogStashConfig(output_file=f))
    content = f.read_text(encoding="utf-8")
    assert "☐" in content
    assert "#todo" in content


def test_cmd_add_multiline_stdin(tmp_path, monkeypatch):
    """Multi-line stdin produces continuation-indented output."""
    import io
    from cogstash.cli import cmd_add
    from cogstash.app import CogStashConfig
    from types import SimpleNamespace

    monkeypatch.setattr("sys.stdin", io.StringIO("line one\nline two"))
    f = tmp_path / "cogstash.md"
    cmd_add(SimpleNamespace(text=[]), CogStashConfig(output_file=f))
    content = f.read_text(encoding="utf-8")
    assert "line one" in content
    assert "  line two" in content  # continuation indent


def test_cmd_add_empty(tmp_path, monkeypatch):
    """Empty input causes sys.exit(1)."""
    import io
    import pytest
    from cogstash.cli import cmd_add
    from cogstash.app import CogStashConfig
    from types import SimpleNamespace

    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    f = tmp_path / "cogstash.md"
    with pytest.raises(SystemExit):
        cmd_add(SimpleNamespace(text=[]), CogStashConfig(output_file=f))


def test_cmd_edit_by_number(tmp_path, capsys):
    """Edit by note number replaces text, preserves timestamp."""
    f = _make_notes_file(tmp_path)
    from cogstash.cli import cmd_edit
    from cogstash.app import CogStashConfig
    from types import SimpleNamespace

    cmd_edit(SimpleNamespace(args=["3", "updated", "note"], search=None), CogStashConfig(output_file=f))
    content = f.read_text(encoding="utf-8")
    assert "updated note" in content
    assert "- [2026-03-26 14:30]" in content
    output = capsys.readouterr().out
    assert "updated" in output.lower() or "Note 3" in output


def test_cmd_edit_by_search(tmp_path, capsys):
    """Edit by search keyword finds and replaces note."""
    f = _make_notes_file(tmp_path)
    from cogstash.cli import cmd_edit
    from cogstash.app import CogStashConfig
    from types import SimpleNamespace

    cmd_edit(SimpleNamespace(args=["get", "oat", "milk"], search="buy milk"), CogStashConfig(output_file=f))
    content = f.read_text(encoding="utf-8")
    assert "get oat milk" in content
    assert "buy milk" not in content


def test_cmd_edit_not_found(tmp_path):
    """Edit with invalid number exits with code 1."""
    import pytest
    f = _make_notes_file(tmp_path)
    from cogstash.cli import cmd_edit
    from cogstash.app import CogStashConfig
    from types import SimpleNamespace

    with pytest.raises(SystemExit):
        cmd_edit(SimpleNamespace(args=["99", "nope"], search=None), CogStashConfig(output_file=f))


def test_cmd_edit_no_text(tmp_path):
    """Edit with empty text exits with code 1."""
    import pytest
    f = _make_notes_file(tmp_path)
    from cogstash.cli import cmd_edit
    from cogstash.app import CogStashConfig
    from types import SimpleNamespace

    with pytest.raises(SystemExit):
        cmd_edit(SimpleNamespace(args=["1"], search=None), CogStashConfig(output_file=f))


def test_cmd_edit_search_multiple_matches(tmp_path, capsys):
    """Edit with ambiguous search shows matches and exits with code 1."""
    import pytest
    f = _make_notes_file(tmp_path)
    from cogstash.cli import cmd_edit
    from cogstash.app import CogStashConfig
    from types import SimpleNamespace

    with pytest.raises(SystemExit):
        cmd_edit(SimpleNamespace(args=["new"], search="note"), CogStashConfig(output_file=f))
    err = capsys.readouterr().err
    assert "Multiple matches" in err


def test_cmd_delete_with_yes(tmp_path, capsys):
    """Delete with --yes skips confirmation and removes note."""
    f = _make_notes_file(tmp_path)
    from cogstash.cli import cmd_delete
    from cogstash.app import CogStashConfig
    from types import SimpleNamespace

    cmd_delete(SimpleNamespace(number=3, yes=True, search=None), CogStashConfig(output_file=f))
    content = f.read_text(encoding="utf-8")
    assert "buy milk" not in content
    output = capsys.readouterr().out
    assert "deleted" in output.lower() or "Note 3" in output


def test_cmd_delete_by_search(tmp_path, capsys):
    """Delete by search keyword finds and removes note."""
    f = _make_notes_file(tmp_path)
    from cogstash.cli import cmd_delete
    from cogstash.app import CogStashConfig
    from types import SimpleNamespace

    cmd_delete(SimpleNamespace(number=None, yes=True, search="buy milk"), CogStashConfig(output_file=f))
    content = f.read_text(encoding="utf-8")
    assert "buy milk" not in content
    output = capsys.readouterr().out
    assert "deleted" in output.lower()


def test_cmd_delete_confirm_yes(tmp_path, monkeypatch):
    """Delete with interactive confirmation (user types 'y')."""
    f = _make_notes_file(tmp_path)
    from cogstash.cli import cmd_delete
    from cogstash.app import CogStashConfig
    from types import SimpleNamespace

    monkeypatch.setattr("builtins.input", lambda _: "y")
    cmd_delete(SimpleNamespace(number=3, yes=False, search=None), CogStashConfig(output_file=f))
    content = f.read_text(encoding="utf-8")
    assert "buy milk" not in content


def test_cmd_delete_confirm_no(tmp_path, monkeypatch):
    """Delete cancelled when user types 'n'."""
    f = _make_notes_file(tmp_path)
    from cogstash.cli import cmd_delete
    from cogstash.app import CogStashConfig
    from types import SimpleNamespace

    monkeypatch.setattr("builtins.input", lambda _: "n")
    cmd_delete(SimpleNamespace(number=3, yes=False, search=None), CogStashConfig(output_file=f))
    content = f.read_text(encoding="utf-8")
    assert "buy milk" in content


def test_cmd_delete_not_found(tmp_path):
    """Delete with invalid number exits with code 1."""
    import pytest
    f = _make_notes_file(tmp_path)
    from cogstash.cli import cmd_delete
    from cogstash.app import CogStashConfig
    from types import SimpleNamespace

    with pytest.raises(SystemExit):
        cmd_delete(SimpleNamespace(number=99, yes=True, search=None), CogStashConfig(output_file=f))


def test_cmd_export_json(tmp_path, monkeypatch, capsys):
    """Export to JSON creates file with all notes."""
    import json
    f = _make_notes_file(tmp_path)
    monkeypatch.chdir(tmp_path)
    from cogstash.cli import cmd_export
    from cogstash.app import CogStashConfig
    from types import SimpleNamespace

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
    from cogstash.cli import cmd_export
    from cogstash.app import CogStashConfig
    from types import SimpleNamespace

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
    from cogstash.cli import cmd_export
    from cogstash.app import CogStashConfig
    from types import SimpleNamespace

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
    from cogstash.cli import cmd_export
    from cogstash.app import CogStashConfig
    from types import SimpleNamespace

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
    from cogstash.cli import cmd_export
    from cogstash.app import CogStashConfig
    from types import SimpleNamespace

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
    from cogstash.cli import cmd_stats
    from cogstash.app import CogStashConfig
    from types import SimpleNamespace

    cmd_stats(SimpleNamespace(), CogStashConfig(output_file=f))
    output = capsys.readouterr().out

    assert "Total notes" in output or "5" in output
    assert "#todo" in output or "todo" in output
    assert "2026" in output


def test_cmd_stats_empty(tmp_path, capsys):
    """Stats on empty file shows no-notes message."""
    f = tmp_path / "cogstash.md"
    from cogstash.cli import cmd_stats
    from cogstash.app import CogStashConfig
    from types import SimpleNamespace

    cmd_stats(SimpleNamespace(), CogStashConfig(output_file=f))
    output = capsys.readouterr().out
    assert "No notes" in output


def test_cmd_stats_done_pending(tmp_path, capsys):
    """Stats shows correct done/pending counts."""
    f = _make_notes_file(tmp_path)
    from cogstash.cli import cmd_stats
    from cogstash.app import CogStashConfig
    from types import SimpleNamespace

    cmd_stats(SimpleNamespace(), CogStashConfig(output_file=f))
    output = capsys.readouterr().out
    # Fixture has 1 done (☑ fix login bug), 4 pending
    assert "1" in output  # done count
    assert "4" in output  # pending count


def test_cmd_config_get(tmp_path, capsys):
    """cogstash config get returns current value."""
    config_path = tmp_path / ".cogstash.json"
    config_path.write_text('{"theme": "dracula"}', encoding="utf-8")
    from cogstash.cli import cmd_config
    from cogstash.app import CogStashConfig
    from types import SimpleNamespace

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
    from cogstash.cli import cmd_config
    from cogstash.app import CogStashConfig
    from types import SimpleNamespace

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
    from cogstash.cli import cmd_config
    from cogstash.app import CogStashConfig
    from types import SimpleNamespace
    import pytest

    with pytest.raises(SystemExit):
        cmd_config(
            SimpleNamespace(action="set", key="theme", value="nope"),
            CogStashConfig(),
            config_path=config_path,
        )


def test_cmd_config_wizard(tmp_path, monkeypatch, capsys):
    """Interactive wizard updates config file."""
    import json
    config_path = tmp_path / ".cogstash.json"
    config_path.write_text('{}', encoding="utf-8")

    # Simulate user pressing Enter for all prompts (keeping defaults)
    monkeypatch.setattr("builtins.input", lambda _: "")

    from cogstash.cli import cmd_config
    from cogstash.app import CogStashConfig
    from types import SimpleNamespace

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
    config_path.write_text('{}', encoding="utf-8")
    from cogstash.cli import cmd_config
    from cogstash.app import CogStashConfig
    from types import SimpleNamespace
    import pytest

    with pytest.raises(SystemExit):
        cmd_config(
            SimpleNamespace(action="get", key="nonexistent", value=None),
            CogStashConfig(),
            config_path=config_path,
        )
