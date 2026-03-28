# Phase 4: CLI Commands Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add three CLI subcommands (`recent`, `search`, `tags`) so users can query CogStash notes from the terminal.

**Architecture:** New `cogstash_cli.py` module handles argparse + ANSI-formatted output. All data operations reuse `cogstash_search.py` (zero duplication). `cogstash.py:main()` gains a `sys.argv` check that delegates to `cogstash_cli.cli_main()` when subcommands are present; otherwise launches the GUI.

**Tech Stack:** argparse (stdlib), ANSI escape codes (no deps), `cogstash_search.parse_notes` / `search_notes` for data.

**Spec:** `docs/superpowers/specs/2026-03-27-cli-commands-design.md`

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `cogstash_cli.py` | Create (~100 lines) | argparse, ANSI formatting, 3 command handlers |
| `test_cogstash_cli.py` | Create (~130 lines) | 10 tests for commands + formatting |
| `cogstash.py` | Modify (3 lines in `main()`) | `sys.argv` guard to delegate to CLI |
| `pyproject.toml` | Modify (1 line) | Add `cogstash_cli` to `py-modules` |

---

### Task 1: ANSI Formatting Helpers + `format_note()`

**Files:**
- Create: `cogstash_cli.py` (partial — ANSI constants + `format_note`)
- Create: `test_cogstash_cli.py` (partial — 3 formatting tests)

- [ ] **Step 1: Write the failing tests**

Create `test_cogstash_cli.py`:

```python
"""Tests for cogstash_cli.py — CLI command handlers and output formatting."""

from pathlib import Path
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
    assert "\033[" in result  # contains ANSI codes
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
    assert "\033[9" in result  # strikethrough
    assert "fix login bug" in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest test_cogstash_cli.py::test_format_note_color test_cogstash_cli.py::test_format_note_plain test_cogstash_cli.py::test_format_done_note -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cogstash_cli'`

- [ ] **Step 3: Write the implementation**

Create `cogstash_cli.py` (partial — will be extended in later tasks):

```python
"""cogstash_cli.py — CLI subcommands for querying CogStash notes.

Provides `recent`, `search`, and `tags` commands with ANSI-colored output.
All data operations delegate to cogstash_search.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

from cogstash_search import Note

# ANSI escape codes — approximations of TAG_COLORS hex values
ANSI_RESET = "\033[0m"
ANSI_BOLD = "\033[1m"
ANSI_DIM = "\033[90m"
ANSI_STRIKE_DIM = "\033[9;90m"

ANSI_TAG = {
    "urgent": "\033[31m",
    "important": "\033[33m",
    "idea": "\033[32m",
    "todo": "\033[36m",
}


def format_note(note: Note, use_color: bool = True) -> str:
    """Format a single note as one line of CLI output."""
    ts = note.timestamp.strftime("[%Y-%m-%d %H:%M]")
    text = note.text

    if not use_color:
        return f"{ts} {text}"

    if note.is_done:
        return f"{ANSI_STRIKE_DIM}{ts} {text}{ANSI_RESET}"

    # Dim timestamp, color tags in text
    colored = text
    for tag in note.tags:
        color = ANSI_TAG.get(tag)
        if color:
            colored = colored.replace(f"#{tag}", f"{color}#{tag}{ANSI_RESET}")

    return f"{ANSI_DIM}{ts}{ANSI_RESET} {colored}"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest test_cogstash_cli.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add cogstash_cli.py test_cogstash_cli.py
git commit -m "feat(cli): add ANSI formatting helpers and format_note"
```

---

### Task 2: `cmd_recent` + `build_parser` + `cli_main`

**Files:**
- Modify: `cogstash_cli.py` (add `build_parser`, `cli_main`, `cmd_recent`)
- Modify: `test_cogstash_cli.py` (add 3 tests for `recent`)

- [ ] **Step 1: Write the failing tests**

Append to `test_cogstash_cli.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest test_cogstash_cli.py::test_cmd_recent_default test_cogstash_cli.py::test_cmd_recent_limit test_cogstash_cli.py::test_cmd_recent_empty -v`
Expected: FAIL with `ImportError: cannot import name 'cmd_recent'`

- [ ] **Step 3: Write the implementation**

Append to `cogstash_cli.py`:

```python
import argparse

from cogstash_search import parse_notes, search_notes


def cmd_recent(args, config):
    """Show the most recent N notes."""
    notes = parse_notes(config.output_file)
    if not notes:
        print("No notes found.")
        return

    use_color = sys.stdout.isatty()
    newest_first = list(reversed(notes))
    limited = newest_first[:args.limit] if args.limit > 0 else newest_first

    for note in limited:
        print(format_note(note, use_color))


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        prog="cogstash",
        description="CogStash — query your brain dump from the terminal.",
    )
    sub = parser.add_subparsers(dest="command")

    # recent
    p_recent = sub.add_parser("recent", help="Show latest notes")
    p_recent.add_argument("--limit", type=int, default=20, help="Max notes to show (default: 20)")
    p_recent.set_defaults(func=cmd_recent)

    return parser


def cli_main(argv: list[str]) -> None:
    """Entry point for CLI subcommands."""
    from cogstash import load_config, CogStashConfig

    parser = build_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, "func"):
        parser.print_help()
        return

    config = load_config(Path.home() / ".cogstash.json")
    args.func(args, config)
```

- [ ] **Step 4: Run all CLI tests to verify they pass**

Run: `python -m pytest test_cogstash_cli.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add cogstash_cli.py test_cogstash_cli.py
git commit -m "feat(cli): add 'cogstash recent' command with build_parser and cli_main"
```

---

### Task 3: `cmd_search`

**Files:**
- Modify: `cogstash_cli.py` (add `cmd_search`, register in `build_parser`)
- Modify: `test_cogstash_cli.py` (add 2 tests)

- [ ] **Step 1: Write the failing tests**

Append to `test_cogstash_cli.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest test_cogstash_cli.py::test_cmd_search_match test_cogstash_cli.py::test_cmd_search_no_match -v`
Expected: FAIL with `ImportError: cannot import name 'cmd_search'`

- [ ] **Step 3: Write the implementation**

Add `cmd_search` function to `cogstash_cli.py` (after `cmd_recent`):

```python
def cmd_search(args, config):
    """Search notes by keyword."""
    notes = parse_notes(config.output_file)
    results = search_notes(notes, args.query)

    if not results:
        print("No matching notes.")
        return

    use_color = sys.stdout.isatty()
    newest_first = list(reversed(results))
    limited = newest_first[:args.limit] if args.limit > 0 else newest_first

    for note in limited:
        print(format_note(note, use_color))
```

Register in `build_parser()` (add after the `# recent` block):

```python
    # search
    p_search = sub.add_parser("search", help="Search notes by keyword")
    p_search.add_argument("query", help="Search term")
    p_search.add_argument("--limit", type=int, default=20, help="Max results (default: 20)")
    p_search.set_defaults(func=cmd_search)
```

- [ ] **Step 4: Run all CLI tests to verify they pass**

Run: `python -m pytest test_cogstash_cli.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add cogstash_cli.py test_cogstash_cli.py
git commit -m "feat(cli): add 'cogstash search' command"
```

---

### Task 4: `cmd_tags`

**Files:**
- Modify: `cogstash_cli.py` (add `cmd_tags`, register in `build_parser`)
- Modify: `test_cogstash_cli.py` (add 2 tests)

- [ ] **Step 1: Write the failing tests**

Append to `test_cogstash_cli.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest test_cogstash_cli.py::test_cmd_tags_counts test_cogstash_cli.py::test_cmd_tags_empty -v`
Expected: FAIL with `ImportError: cannot import name 'cmd_tags'`

- [ ] **Step 3: Write the implementation**

Add `cmd_tags` function to `cogstash_cli.py` (after `cmd_search`):

```python
def cmd_tags(args, config):
    """List all tags with note counts."""
    notes = parse_notes(config.output_file)

    tag_counts: dict[str, int] = {}
    for note in notes:
        for tag in note.tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    if not tag_counts:
        print("No tags found.")
        return

    use_color = sys.stdout.isatty()
    sorted_tags = sorted(tag_counts.items(), key=lambda x: (-x[1], x[0]))
    max_len = max(len(f"#{tag}") for tag, _ in sorted_tags)

    for tag, count in sorted_tags:
        label = f"#{tag}"
        noun = "note" if count == 1 else "notes"
        if use_color:
            color = ANSI_TAG.get(tag, "")
            reset = ANSI_RESET if color else ""
            print(f"  {color}{label:<{max_len}}{reset}  {ANSI_BOLD}{count}{ANSI_RESET} {noun}")
        else:
            print(f"  {label:<{max_len}}  {count} {noun}")
```

Register in `build_parser()` (add after the `# search` block):

```python
    # tags
    p_tags = sub.add_parser("tags", help="List all tags with counts")
    p_tags.set_defaults(func=cmd_tags)
```

- [ ] **Step 4: Run all CLI tests to verify they pass**

Run: `python -m pytest test_cogstash_cli.py -v`
Expected: 10 passed

- [ ] **Step 5: Commit**

```bash
git add cogstash_cli.py test_cogstash_cli.py
git commit -m "feat(cli): add 'cogstash tags' command"
```

---

### Task 5: Integration — Wire into `main()` + `pyproject.toml`

**Files:**
- Modify: `cogstash.py:main()` (~line 519) — add 4-line `sys.argv` guard
- Modify: `pyproject.toml:18` — add `cogstash_cli` to `py-modules`

- [ ] **Step 1: Modify `cogstash.py:main()`**

Add at the very top of `main()`, before the `config = load_config(...)` line:

```python
def main():
    # CLI subcommands — delegate before loading GUI
    if len(sys.argv) > 1 and sys.argv[1] in ("recent", "search", "tags"):
        from cogstash_cli import cli_main
        cli_main(sys.argv[1:])
        return

    config = load_config(Path.home() / ".cogstash.json")
    # ... rest unchanged ...
```

Note: `cogstash.py` already imports `sys` (used elsewhere). The `from cogstash_cli import cli_main` is a lazy import inside the function body, matching the existing `_open_browse()` pattern.

- [ ] **Step 2: Update `pyproject.toml`**

Change the `py-modules` line:

```toml
py-modules = ["cogstash", "cogstash_search", "cogstash_browse", "cogstash_cli"]
```

- [ ] **Step 3: Run the full test suite**

Run: `python -m pytest -v`
Expected: 44 passed (34 existing + 10 new CLI tests), 0 failed

- [ ] **Step 4: Manual smoke test**

```bash
python -m cogstash recent --limit 5
python -m cogstash search "some word"
python -m cogstash tags
```

Verify: colored output in terminal, correct data from `~/cogstash.md`.

- [ ] **Step 5: Commit**

```bash
git add cogstash.py pyproject.toml
git commit -m "feat(cli): wire CLI subcommands into main() entry point"
```

---

## Summary

| Task | What | Tests |
|------|------|-------|
| 1 | ANSI helpers + `format_note()` | 3 (color, plain, done) |
| 2 | `cmd_recent` + `build_parser` + `cli_main` | 3 (default, limit, empty) |
| 3 | `cmd_search` | 2 (match, no match) |
| 4 | `cmd_tags` | 2 (counts, empty) |
| 5 | Wire into `main()` + `pyproject.toml` | Full suite verification |

**Total:** 10 new tests, 2 new files, 2 modified files.
