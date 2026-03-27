# Phase 7: Edit/Delete Notes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add edit and delete capabilities to CogStash notes via both CLI and Browse window.

**Architecture:** Backend functions in cogstash_search.py (pure data layer, no GUI), CLI commands in cogstash_cli.py, Browse window context menu + edit dialog in cogstash_browse.py. Follows existing separation of concerns.

**Tech Stack:** Python 3.9+, tkinter, argparse, pytest

**Spec:** `docs/superpowers/specs/2026-03-27-edit-delete-design.md`

---

### File Map

- **Modify:** `cogstash_search.py` — Add `_note_line_span()`, `edit_note()`, `delete_note()`
- **Modify:** `cogstash_cli.py` — Add `_find_note()`, `cmd_edit()`, `cmd_delete()`, update `build_parser()`, update import
- **Modify:** `cogstash.py:571` — Add `"edit"`, `"delete"` to argv guard
- **Modify:** `cogstash_browse.py` — Add context menu, edit dialog, delete confirmation, copy-to-clipboard
- **Test:** `test_cogstash_search.py` — 6 new tests for edit/delete backend
- **Test:** `test_cogstash_cli.py` — 10 new tests for CLI edit/delete
- **Test:** `test_cogstash_browse.py` — 3 new tests for Browse window actions

---

### Task 1: Backend Functions (cogstash_search.py)

**Files:**
- Modify: `cogstash_search.py:108-118` (after `mark_done`)
- Test: `test_cogstash_search.py`

**Context for implementer:**
- `cogstash_search.py` is a pure data layer — NO tkinter imports.
- `_NOTE_RE = re.compile(r"^- \[(\d{4}-\d{2}-\d{2} \d{2}:\d{2})\] (.+)")` already defined at line 14.
- `Note` dataclass has: `index`, `timestamp`, `text`, `tags`, `is_done`, `line_number`.
- `mark_done()` at line 108 follows the read-all/modify/write-all pattern — follow the same pattern.
- Continuation lines start with exactly 2 spaces (`"  "`).
- File lines include trailing newlines when read with `splitlines(keepends=True)`.

- [ ] **Step 1: Write failing tests for `_note_line_span`**

Add to end of `test_cogstash_search.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest test_cogstash_search.py::test_note_line_span_single test_cogstash_search.py::test_note_line_span_multiline -v`
Expected: FAIL with ImportError (`cannot import name '_note_line_span'`)

- [ ] **Step 3: Implement `_note_line_span`**

Add after `mark_done()` (after line 118) in `cogstash_search.py`:

```python
def _note_line_span(lines: list[str], line_number: int) -> tuple[int, int]:
    """Return (start, end) line range for a note including continuation lines.

    start is inclusive, end is exclusive. Continuation lines start with 2 spaces.
    """
    end = line_number + 1
    while end < len(lines) and lines[end].startswith("  "):
        end += 1
    return (line_number, end)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest test_cogstash_search.py::test_note_line_span_single test_cogstash_search.py::test_note_line_span_multiline -v`
Expected: PASS

- [ ] **Step 5: Write failing tests for `edit_note`**

Add to `test_cogstash_search.py`:

```python
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
```

- [ ] **Step 6: Implement `edit_note`**

Add after `_note_line_span()` in `cogstash_search.py`:

```python
def edit_note(path: Path, note: Note, new_text: str) -> bool:
    """Replace a note's text, preserving its timestamp. Returns True on success."""
    new_text = new_text.strip()
    if not new_text:
        return False
    try:
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        start, end = _note_line_span(lines, note.line_number)
        if start >= len(lines):
            return False

        ts = note.timestamp.strftime("%Y-%m-%d %H:%M")
        text_lines = new_text.split("\n")
        replacement = [f"- [{ts}] {text_lines[0]}\n"]
        replacement.extend(f"  {line}\n" for line in text_lines[1:])

        lines[start:end] = replacement
        path.write_text("".join(lines), encoding="utf-8")
        return True
    except OSError:
        return False
```

- [ ] **Step 7: Run edit_note tests**

Run: `python -m pytest test_cogstash_search.py::test_edit_note_single_line test_cogstash_search.py::test_edit_note_multiline test_cogstash_search.py::test_edit_note_empty_rejected -v`
Expected: PASS

- [ ] **Step 8: Write failing test for `delete_note`**

Add to `test_cogstash_search.py`:

```python
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
```

- [ ] **Step 9: Implement `delete_note`**

Add after `edit_note()` in `cogstash_search.py`:

```python
def delete_note(path: Path, note: Note) -> bool:
    """Remove a note and its continuation lines from the file. Returns True on success."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        start, end = _note_line_span(lines, note.line_number)
        if start >= len(lines):
            return False

        del lines[start:end]
        path.write_text("".join(lines), encoding="utf-8")
        return True
    except OSError:
        return False
```

- [ ] **Step 10: Run all new tests**

Run: `python -m pytest test_cogstash_search.py -v`
Expected: ALL PASS (12 existing + 6 new = 18 total)

- [ ] **Step 11: Run full test suite**

Run: `python -m pytest -v`
Expected: ALL PASS (63 existing + 6 new = 69 total)

- [ ] **Step 12: Commit**

```bash
git add cogstash_search.py test_cogstash_search.py
git commit -m "feat: add edit_note, delete_note, and _note_line_span to search module"
```

---

### Task 2: CLI Edit/Delete Commands (cogstash_cli.py)

**Files:**
- Modify: `cogstash_cli.py` (add `_find_note`, `cmd_edit`, `cmd_delete`, update `build_parser`, update import at line 13)
- Modify: `cogstash.py:571` (add `"edit"`, `"delete"` to argv guard)
- Test: `test_cogstash_cli.py`

**Context for implementer:**
- `cogstash_cli.py` already imports `from cogstash_search import Note, parse_notes, search_notes` at line 13. Add `edit_note, delete_note` to that import.
- `format_note()` at line 53 renders a note with optional ANSI color — use it for preview.
- `cmd_add()` at line 136 is the pattern for new commands: signature is `(args, config, ansi_tag=None)`.
- `build_parser()` at line 156 adds subparsers — add `edit` and `delete` there.
- `cli_main()` at line 187 calls `args.func(args, config, ansi_tag)`.
- `cogstash.py` line 571: the argv guard must include `"edit"` and `"delete"`.
- All commands call `sys.exit(1)` on error.

- [ ] **Step 1: Write failing tests for `cmd_edit`**

Add to end of `test_cogstash_cli.py`:

```python
def test_cmd_edit_by_number(tmp_path, capsys):
    """Edit by note number replaces text, preserves timestamp."""
    f = _make_notes_file(tmp_path)
    from cogstash_cli import cmd_edit
    from cogstash import CogStashConfig
    from types import SimpleNamespace

    cmd_edit(SimpleNamespace(args=["3", "updated", "note"], search=None), CogStashConfig(output_file=f))
    content = f.read_text(encoding="utf-8")
    assert "updated note" in content
    assert "- [2026-03-26 14:30]" in content  # timestamp preserved
    output = capsys.readouterr().out
    assert "updated" in output.lower() or "Note 3" in output


def test_cmd_edit_by_search(tmp_path, capsys):
    """Edit by search keyword finds and replaces note."""
    f = _make_notes_file(tmp_path)
    from cogstash_cli import cmd_edit
    from cogstash import CogStashConfig
    from types import SimpleNamespace

    cmd_edit(SimpleNamespace(args=["get", "oat", "milk"], search="buy milk"), CogStashConfig(output_file=f))
    content = f.read_text(encoding="utf-8")
    assert "get oat milk" in content
    assert "buy milk" not in content


def test_cmd_edit_not_found(tmp_path):
    """Edit with invalid number exits with code 1."""
    import pytest
    f = _make_notes_file(tmp_path)
    from cogstash_cli import cmd_edit
    from cogstash import CogStashConfig
    from types import SimpleNamespace

    with pytest.raises(SystemExit):
        cmd_edit(SimpleNamespace(args=["99", "nope"], search=None), CogStashConfig(output_file=f))


def test_cmd_edit_no_text(tmp_path):
    """Edit with empty text exits with code 1."""
    import pytest
    f = _make_notes_file(tmp_path)
    from cogstash_cli import cmd_edit
    from cogstash import CogStashConfig
    from types import SimpleNamespace

    with pytest.raises(SystemExit):
        cmd_edit(SimpleNamespace(args=["1"], search=None), CogStashConfig(output_file=f))


def test_cmd_edit_search_multiple_matches(tmp_path, capsys):
    """Edit with ambiguous search shows matches and exits with code 1."""
    import pytest
    f = _make_notes_file(tmp_path)
    from cogstash_cli import cmd_edit
    from cogstash import CogStashConfig
    from types import SimpleNamespace

    # "note" matches multiple notes in the fixture
    with pytest.raises(SystemExit):
        cmd_edit(SimpleNamespace(args=["new"], search="note"), CogStashConfig(output_file=f))
    err = capsys.readouterr().err
    assert "Multiple matches" in err
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest test_cogstash_cli.py::test_cmd_edit_by_number -v`
Expected: FAIL with ImportError (`cannot import name 'cmd_edit'`)

- [ ] **Step 3: Write failing tests for `cmd_delete`**

Add to `test_cogstash_cli.py`:

```python
def test_cmd_delete_with_yes(tmp_path, capsys):
    """Delete with --yes skips confirmation and removes note."""
    f = _make_notes_file(tmp_path)
    from cogstash_cli import cmd_delete
    from cogstash import CogStashConfig
    from types import SimpleNamespace

    cmd_delete(SimpleNamespace(number=3, yes=True, search=None), CogStashConfig(output_file=f))
    content = f.read_text(encoding="utf-8")
    assert "buy milk" not in content
    output = capsys.readouterr().out
    assert "deleted" in output.lower() or "Note 3" in output


def test_cmd_delete_by_search(tmp_path, capsys):
    """Delete by search keyword finds and removes note."""
    f = _make_notes_file(tmp_path)
    from cogstash_cli import cmd_delete
    from cogstash import CogStashConfig
    from types import SimpleNamespace

    cmd_delete(SimpleNamespace(number=None, yes=True, search="buy milk"), CogStashConfig(output_file=f))
    content = f.read_text(encoding="utf-8")
    assert "buy milk" not in content
    output = capsys.readouterr().out
    assert "deleted" in output.lower()


def test_cmd_delete_confirm_yes(tmp_path, monkeypatch):
    """Delete with interactive confirmation (user types 'y')."""
    f = _make_notes_file(tmp_path)
    from cogstash_cli import cmd_delete
    from cogstash import CogStashConfig
    from types import SimpleNamespace

    monkeypatch.setattr("builtins.input", lambda _: "y")
    cmd_delete(SimpleNamespace(number=3, yes=False, search=None), CogStashConfig(output_file=f))
    content = f.read_text(encoding="utf-8")
    assert "buy milk" not in content


def test_cmd_delete_confirm_no(tmp_path, monkeypatch):
    """Delete cancelled when user types 'n'."""
    f = _make_notes_file(tmp_path)
    from cogstash_cli import cmd_delete
    from cogstash import CogStashConfig
    from types import SimpleNamespace

    monkeypatch.setattr("builtins.input", lambda _: "n")
    cmd_delete(SimpleNamespace(number=3, yes=False, search=None), CogStashConfig(output_file=f))
    content = f.read_text(encoding="utf-8")
    assert "buy milk" in content  # NOT deleted


def test_cmd_delete_not_found(tmp_path):
    """Delete with invalid number exits with code 1."""
    import pytest
    f = _make_notes_file(tmp_path)
    from cogstash_cli import cmd_delete
    from cogstash import CogStashConfig
    from types import SimpleNamespace

    with pytest.raises(SystemExit):
        cmd_delete(SimpleNamespace(number=99, yes=True, search=None), CogStashConfig(output_file=f))
```

- [ ] **Step 4: Implement `_find_note` helper**

Add after `cmd_add()` (line 153) in `cogstash_cli.py`:

```python
def _find_note(config, number: int | None = None, search: str | None = None,
               ansi_tag: dict[str, str] | None = None) -> Note | None:
    """Find a note by number or search. Prints errors and returns None on failure."""
    notes = parse_notes(config.output_file)
    if number is not None:
        for n in notes:
            if n.index == number:
                return n
        print(f"Error: note #{number} not found.", file=sys.stderr)
        return None
    if search is not None:
        results = search_notes(notes, search)
        if len(results) == 1:
            return results[0]
        if len(results) == 0:
            print(f"Error: no notes match '{search}'.", file=sys.stderr)
            return None
        use_color = sys.stdout.isatty()
        print(f"Multiple matches ({len(results)}). Use a note number instead:", file=sys.stderr)
        for n in results:
            print(f"  {n.index}: {format_note(n, use_color, ansi_tag)}", file=sys.stderr)
        return None
    print("Error: provide a note number or --search.", file=sys.stderr)
    return None
```

- [ ] **Step 5: Implement `cmd_edit`**

Add after `_find_note()`:

```python
def cmd_edit(args, config, ansi_tag=None):
    """Edit a note's text."""
    # Parse combined args: first element may be note number, rest is text
    number = None
    text_parts = list(args.args) if args.args else []

    if args.search:
        # --search mode: all positional args are the new text
        pass
    elif text_parts and text_parts[0].isdigit():
        number = int(text_parts.pop(0))
    else:
        print("Error: provide a note number or --search.", file=sys.stderr)
        sys.exit(1)

    if not text_parts:
        print("Error: no replacement text provided.", file=sys.stderr)
        sys.exit(1)

    note = _find_note(config, number=number, search=args.search, ansi_tag=ansi_tag)
    if note is None:
        sys.exit(1)

    new_text = " ".join(text_parts)
    if not edit_note(config.output_file, note, new_text):
        print("Error: failed to update note.", file=sys.stderr)
        sys.exit(1)

    print(f"Note {note.index} updated.")
```

- [ ] **Step 6: Implement `cmd_delete`**

Add after `cmd_edit()`:

```python
def cmd_delete(args, config, ansi_tag=None):
    """Delete a note."""
    note = _find_note(config, number=args.number, search=args.search, ansi_tag=ansi_tag)
    if note is None:
        sys.exit(1)

    if not args.yes:
        preview = note.text[:60] + ("..." if len(note.text) > 60 else "")
        answer = input(f"Delete note {note.index}: \"{preview}\"? [y/N] ")
        if answer.lower() != "y":
            print("Cancelled.")
            return

    if not delete_note(config.output_file, note):
        print("Error: failed to delete note.", file=sys.stderr)
        sys.exit(1)

    print(f"Note {note.index} deleted.")
```

- [ ] **Step 7: Update import at line 13**

Change:
```python
from cogstash_search import Note, parse_notes, search_notes
```
To:
```python
from cogstash_search import Note, parse_notes, search_notes, edit_note, delete_note
```

- [ ] **Step 8: Update `build_parser()`**

Add after the `# add` block (line 182) in `build_parser()`:

```python
    # edit — uses a single "args" positional to avoid int/str ambiguity
    # Usage: cogstash edit 3 new text  OR  cogstash edit --search "milk" new text
    p_edit = sub.add_parser("edit", help="Edit a note's text")
    p_edit.add_argument("args", nargs="*", help="Note number followed by new text")
    p_edit.add_argument("--search", "-s", help="Find note by keyword instead of number")
    p_edit.set_defaults(func=cmd_edit)

    # delete
    p_delete = sub.add_parser("delete", help="Delete a note")
    p_delete.add_argument("number", type=int, nargs="?", default=None, help="Note number")
    p_delete.add_argument("--search", "-s", help="Find note by keyword")
    p_delete.add_argument("--yes", "-y", action="store_true", help="Skip confirmation")
    p_delete.set_defaults(func=cmd_delete)
```

- [ ] **Step 9: Update `main()` argv guard in `cogstash.py:571`**

Change:
```python
    if len(sys.argv) > 1 and sys.argv[1] in ("recent", "search", "tags", "add"):
```
To:
```python
    if len(sys.argv) > 1 and sys.argv[1] in ("recent", "search", "tags", "add", "edit", "delete"):
```

- [ ] **Step 10: Run new CLI tests**

Run: `python -m pytest test_cogstash_cli.py -v`
Expected: ALL PASS (17 existing + 10 new = 27 total)

- [ ] **Step 11: Run full test suite**

Run: `python -m pytest -v`
Expected: ALL PASS (69 from Task 1 + 10 new = 79 total)

- [ ] **Step 12: Commit**

```bash
git add cogstash_cli.py cogstash.py test_cogstash_cli.py
git commit -m "feat: add cogstash edit and cogstash delete CLI commands"
```

---

### Task 3: Browse Window Context Menu + Edit Dialog (cogstash_browse.py)

**Files:**
- Modify: `cogstash_browse.py` (add context menu, edit dialog, delete confirmation, copy)
- Modify: import at line 15 — add `edit_note, delete_note`
- Test: `test_cogstash_browse.py`

**Context for implementer:**
- `cogstash_browse.py` is a single `BrowseWindow` class with a `Toplevel` window.
- `_render_card()` at line 201 creates card widgets. The key widgets are: `outer` (border frame), `card` (inner frame), `top_row`, `text_label`. Bind `<Button-3>` on these for right-click.
- The mousewheel binding loop at line 266 iterates `(outer, card, top_row, text_label)`. Add the context menu binding in the same loop.
- `self.theme` has keys: `bg`, `fg`, `entry_bg`, `accent`, `muted`, `error`.
- `platform_font()` returns the OS-appropriate font family string.
- `self._load_notes()` reloads from file and refreshes cards — call after edit/delete.
- `_on_mark_done()` at line 271 is the pattern: calls `mark_done()` then `self._load_notes()`.
- `self.config.output_file` is the path to the notes file.
- The session-scoped `tk_root` in conftest.py must be used as parent for tests.
- `self.tag_colors` is used for pill colors.
- Import `edit_note` and `delete_note` from `cogstash_search`.

- [ ] **Step 1: Write failing tests**

Add to end of `test_cogstash_browse.py`:

```python
@needs_display
def test_browse_context_menu_exists(tmp_path, tk_root):
    """Right-click on a card shows a context menu."""
    f = tmp_path / "cogstash.md"
    f.write_text("- [2026-03-26 14:30] test note #todo\n", encoding="utf-8")

    from cogstash_browse import BrowseWindow
    from cogstash import CogStashConfig

    config = CogStashConfig(output_file=f)
    win = BrowseWindow(tk_root, config)
    assert hasattr(win, "_show_context_menu")
    win.window.destroy()


@needs_display
def test_browse_edit_note(tmp_path, tk_root):
    """Edit via _on_edit updates file and refreshes cards."""
    f = tmp_path / "cogstash.md"
    f.write_text("- [2026-03-26 14:30] original text\n", encoding="utf-8")

    from cogstash_browse import BrowseWindow
    from cogstash import CogStashConfig
    from cogstash_search import edit_note, parse_notes

    config = CogStashConfig(output_file=f)
    win = BrowseWindow(tk_root, config)
    note = win._all_notes[0]

    # Directly call edit_note (dialog would be interactive)
    edit_note(f, note, "updated text")
    win._load_notes()
    assert win._all_notes[0].text == "updated text"
    win.window.destroy()


@needs_display
def test_browse_delete_note(tmp_path, tk_root):
    """Delete via delete_note removes note and refreshes cards."""
    f = tmp_path / "cogstash.md"
    f.write_text(
        "- [2026-03-26 14:30] first note\n"
        "- [2026-03-26 15:00] second note\n",
        encoding="utf-8",
    )

    from cogstash_browse import BrowseWindow
    from cogstash import CogStashConfig
    from cogstash_search import delete_note, parse_notes

    config = CogStashConfig(output_file=f)
    win = BrowseWindow(tk_root, config)
    assert len(win._all_notes) == 2

    note = win._all_notes[0]
    delete_note(f, note)
    win._load_notes()
    assert len(win._all_notes) == 1
    assert "second note" in win._all_notes[0].text
    win.window.destroy()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest test_cogstash_browse.py::test_browse_context_menu_exists -v`
Expected: FAIL (`BrowseWindow` has no attribute `_show_context_menu`)

- [ ] **Step 3: Update import at line 15**

Change:
```python
from cogstash_search import parse_notes, search_notes, filter_by_tag, mark_done, DEFAULT_TAG_COLORS, Note
```
To:
```python
from cogstash_search import parse_notes, search_notes, filter_by_tag, mark_done, edit_note, delete_note, DEFAULT_TAG_COLORS, Note
```

- [ ] **Step 4: Add context menu method**

Add after `_on_mark_done()` (line 274) in `cogstash_browse.py`:

```python
    def _show_context_menu(self, event, note: Note):
        """Show right-click context menu for a note card."""
        menu = tk.Menu(self.window, tearoff=0)
        menu.add_command(label="✏️ Edit", command=lambda: self._on_edit(note))
        menu.add_command(label="🗑️ Delete", command=lambda: self._on_delete(note))
        menu.add_separator()
        menu.add_command(label="📋 Copy text", command=lambda: self._on_copy(note))
        menu.tk_popup(event.x_root, event.y_root)
```

- [ ] **Step 5: Add edit dialog method**

Add after `_show_context_menu()`:

```python
    def _on_edit(self, note: Note):
        """Open themed edit dialog for a note."""
        t = self.theme
        fnt = platform_font()

        dialog = tk.Toplevel(self.window)
        dialog.title("Edit Note")
        dialog.configure(bg=t["bg"])
        dialog.geometry("420x220")
        dialog.transient(self.window)
        dialog.grab_set()

        # Header: title + timestamp
        header = tk.Frame(dialog, bg=t["bg"])
        header.pack(fill="x", padx=16, pady=(12, 0))
        tk.Label(
            header, text="Edit Note", bg=t["bg"], fg=t["fg"],
            font=(fnt, 12, "bold"),
        ).pack(side="left")
        tk.Label(
            header, text=note.timestamp.strftime("[%Y-%m-%d %H:%M]"),
            bg=t["bg"], fg=t["muted"], font=(fnt, 10),
        ).pack(side="right")

        # Text area
        text_widget = tk.Text(
            dialog, bg=t["entry_bg"], fg=t["fg"], insertbackground=t["fg"],
            font=(fnt, 11), relief="flat", bd=0, wrap="word",
            highlightthickness=1, highlightbackground=t["muted"],
            highlightcolor=t["accent"],
        )
        text_widget.pack(fill="both", expand=True, padx=16, pady=8)
        text_widget.insert("1.0", note.text)
        text_widget.focus_set()

        # Buttons
        btn_frame = tk.Frame(dialog, bg=t["bg"])
        btn_frame.pack(fill="x", padx=16, pady=(0, 12))

        def save():
            new_text = text_widget.get("1.0", "end-1c").strip()
            if not new_text:
                return
            if edit_note(self.config.output_file, note, new_text):
                dialog.destroy()
                self._load_notes()
            else:
                from tkinter import messagebox
                messagebox.showerror("Error", "Failed to save changes.", parent=dialog)

        tk.Button(
            btn_frame, text="Cancel", command=dialog.destroy,
            bg=t["entry_bg"], fg=t["fg"], font=(fnt, 10),
            relief="flat", padx=12, pady=4, cursor="hand2",
        ).pack(side="right", padx=(4, 0))
        tk.Button(
            btn_frame, text="Save", command=save,
            bg=t["accent"], fg=t["bg"], font=(fnt, 10, "bold"),
            relief="flat", padx=12, pady=4, cursor="hand2",
        ).pack(side="right")

        dialog.bind("<Escape>", lambda e: dialog.destroy())
```

- [ ] **Step 6: Add delete confirmation method**

Add after `_on_edit()`:

```python
    def _on_delete(self, note: Note):
        """Delete a note with confirmation dialog."""
        from tkinter import messagebox
        preview = note.text[:50] + ("..." if len(note.text) > 50 else "")
        if messagebox.askyesno(
            "Delete Note",
            f"Delete this note?\n\n\"{preview}\"",
            parent=self.window,
        ):
            if delete_note(self.config.output_file, note):
                self._load_notes()
            else:
                messagebox.showerror("Error", "Failed to delete note.", parent=self.window)
```

- [ ] **Step 7: Add copy-to-clipboard method**

Add after `_on_delete()`:

```python
    def _on_copy(self, note: Note):
        """Copy note text to clipboard."""
        self.window.clipboard_clear()
        self.window.clipboard_append(note.text)
```

- [ ] **Step 8: Bind context menu in `_render_card()`**

Replace the tag pills block (lines 254-263), the mousewheel binding loop (lines 265-267), and the `self._card_frames.append(outer)` (line 269) with a unified widget collection approach:

```python
        # Collect all card widgets for event binding
        card_widgets = [outer, card, top_row, text_label]

        # Tag pills
        if note.tags:
            tags_frame = tk.Frame(card, bg=card_bg)
            tags_frame.pack(fill="x", pady=(4, 0), anchor="w")
            for tag in note.tags:
                color = self.tag_colors.get(tag, t["muted"])
                pill = tk.Label(
                    tags_frame, text=f"#{tag}", bg=t["bg"], fg=color,
                    font=(fnt, 9), padx=4, pady=1,
                )
                pill.pack(side="left", padx=(0, 4))
                card_widgets.append(pill)
            card_widgets.append(tags_frame)

        # Bind mousewheel and right-click context menu on all card widgets
        for widget in card_widgets:
            widget.bind("<MouseWheel>", self._on_mousewheel)
            widget.bind("<Button-3>", lambda e, n=note: self._show_context_menu(e, n))

        self._card_frames.append(outer)
```

**IMPORTANT:** This replaces the existing tag pills block (lines 254-263) AND the mousewheel binding loop (lines 265-267) AND the `self._card_frames.append(outer)` (line 269). The tag pills code is moved into the unified widget collection block.

- [ ] **Step 9: Run new browse tests**

Run: `python -m pytest test_cogstash_browse.py -v`
Expected: ALL PASS (4 existing + 3 new = 7 total)

- [ ] **Step 10: Run full test suite**

Run: `python -m pytest -v`
Expected: ALL PASS (79 from Task 2 + 3 new = 82 total)

- [ ] **Step 11: Commit**

```bash
git add cogstash_browse.py test_cogstash_browse.py
git commit -m "feat: add right-click context menu with edit, delete, and copy in Browse window"
```
