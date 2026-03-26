# Phase 3: Recall & Review — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Browse Window (accessible from the tray icon) that lets users search, filter by tag, and mark `#todo` items as done.

**Architecture:** Three new files — `blip_search.py` for pure parsing/search logic (no tkinter), `blip_browse.py` for the browse window UI, and test files for each. Minimal changes to `blip.py` (tray menu + queue handler). TDD throughout.

**Tech Stack:** Python 3.9+, tkinter (existing), dataclasses (existing), re (existing). No new dependencies.

**Spec:** `docs/superpowers/specs/2026-03-26-recall-review-design.md`

---

## File Structure

| File | Action | Responsibility | Budget |
|------|--------|---------------|--------|
| `blip_search.py` | Create | Note dataclass, parse_notes, search_notes, filter_by_tag, mark_done, TAG_COLORS dict | ~120 lines |
| `blip_browse.py` | Create | BrowseWindow class — tkinter Toplevel with search, tag filters, scrollable cards | ~250 lines |
| `test_blip_search.py` | Create | 11 tests for all search/parse/filter/mark_done logic | ~130 lines |
| `test_blip_browse.py` | Create | 3 display-dependent tests for browse window UI | ~50 lines |
| `blip.py` | Modify | Add "Browse Notes" to tray menu, handle `"browse"` in poll_queue | ~15 lines added |
| `pyproject.toml` | Modify | Add new modules to setuptools config | ~2 lines |

---

### Task 1: Note dataclass and parse_notes()

**Files:**
- Create: `blip_search.py`
- Create: `test_blip_search.py`

This task creates the core data model and parser. All subsequent tasks depend on this.

- [ ] **Step 1: Write failing tests for parse_notes**

Create `test_blip_search.py`:

```python
"""Tests for blip_search.py — note parsing and search logic."""

from pathlib import Path
from datetime import datetime


def test_parse_notes_basic(tmp_path):
    """Single note parsed correctly: timestamp, text, tags, line_number."""
    f = tmp_path / "blip.md"
    f.write_text("- [2026-03-26 14:30] ☐ buy milk #todo\n", encoding="utf-8")

    from blip_search import parse_notes
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
    f = tmp_path / "blip.md"
    f.write_text(
        "- [2026-03-26 14:30] first line\n"
        "  second line\n"
        "  third line\n",
        encoding="utf-8",
    )

    from blip_search import parse_notes
    notes = parse_notes(f)

    assert len(notes) == 1
    assert notes[0].text == "first line\nsecond line\nthird line"


def test_parse_notes_empty_file(tmp_path):
    """Empty file returns empty list."""
    f = tmp_path / "blip.md"
    f.write_text("", encoding="utf-8")

    from blip_search import parse_notes
    notes = parse_notes(f)
    assert notes == []


def test_parse_notes_missing_file(tmp_path):
    """Missing file returns empty list."""
    from blip_search import parse_notes
    notes = parse_notes(tmp_path / "nonexistent.md")
    assert notes == []


def test_parse_notes_done_status(tmp_path):
    """☐ → is_done=False, ☑ → is_done=True."""
    f = tmp_path / "blip.md"
    f.write_text(
        "- [2026-03-26 14:30] ☐ open item #todo\n"
        "- [2026-03-26 15:00] ☑ done item #todo\n",
        encoding="utf-8",
    )

    from blip_search import parse_notes
    notes = parse_notes(f)

    assert notes[0].is_done is False
    assert notes[1].is_done is True


def test_parse_notes_no_prefix(tmp_path):
    """Note without smart-tag emoji → is_done=False."""
    f = tmp_path / "blip.md"
    f.write_text("- [2026-03-26 14:30] plain note\n", encoding="utf-8")

    from blip_search import parse_notes
    notes = parse_notes(f)

    assert notes[0].is_done is False
    assert notes[0].tags == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest test_blip_search.py -v`
Expected: All 6 tests FAIL with `ModuleNotFoundError: No module named 'blip_search'`

- [ ] **Step 3: Implement Note dataclass and parse_notes**

Create `blip_search.py`:

```python
"""blip_search.py — Note parsing, search, and filtering logic.

Pure functions with no tkinter dependency. Used by blip_browse.py
for the Browse Window and potentially CLI tools in the future.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

_NOTE_RE = re.compile(r"^- \[(\d{4}-\d{2}-\d{2} \d{2}:\d{2})\] (.+)")
_TAG_RE = re.compile(r"(?:^|\s)#(\w+)")

TAG_COLORS = {
    "urgent": "#f7768e",
    "important": "#e0af68",
    "idea": "#9ece6a",
    "todo": "#7aa2f7",
}


@dataclass
class Note:
    index: int
    timestamp: datetime
    text: str
    tags: list[str] = field(default_factory=list)
    is_done: bool = False
    line_number: int = 0


def parse_notes(path: Path) -> list[Note]:
    """Parse blip.md into a list of Note objects."""
    if not path.exists():
        return []

    notes: list[Note] = []
    current_text_lines: list[str] = []
    current_ts = None
    current_line = 0

    lines = path.read_text(encoding="utf-8").splitlines()

    for i, line in enumerate(lines):
        m = _NOTE_RE.match(line)
        if m:
            # Flush previous note
            if current_ts is not None:
                _flush_note(notes, current_ts, current_text_lines, current_line)

            current_ts = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M")
            current_text_lines = [m.group(2)]
            current_line = i
        elif line.startswith("  ") and current_ts is not None:
            current_text_lines.append(line[2:])

    # Flush last note
    if current_ts is not None:
        _flush_note(notes, current_ts, current_text_lines, current_line)

    return notes


def _flush_note(
    notes: list[Note], ts: datetime, text_lines: list[str], line_number: int
) -> None:
    """Build a Note from accumulated lines and append to notes list."""
    text = "\n".join(text_lines)
    tags = _TAG_RE.findall(text)
    # Deduplicate while preserving order
    seen = set()
    unique_tags = []
    for t in tags:
        if t not in seen:
            seen.add(t)
            unique_tags.append(t)

    is_done = text.startswith("☑")

    notes.append(
        Note(
            index=len(notes) + 1,
            timestamp=ts,
            text=text,
            tags=unique_tags,
            is_done=is_done,
            line_number=line_number,
        )
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest test_blip_search.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add blip_search.py test_blip_search.py
git commit -m "feat: add Note dataclass and parse_notes()"
```

---

### Task 2: search_notes() and filter_by_tag()

**Files:**
- Modify: `blip_search.py`
- Modify: `test_blip_search.py`

Depends on: Task 1

- [ ] **Step 1: Write failing tests for search and filter**

Append to `test_blip_search.py`:

```python
def _make_notes_file(tmp_path):
    """Helper: create a blip.md with several notes for search tests."""
    f = tmp_path / "blip.md"
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
    from blip_search import parse_notes, search_notes
    notes = parse_notes(_make_notes_file(tmp_path))
    results = search_notes(notes, "buy")
    assert len(results) == 2


def test_search_case_insensitive(tmp_path):
    """Search is case-insensitive."""
    from blip_search import parse_notes, search_notes
    notes = parse_notes(_make_notes_file(tmp_path))
    results = search_notes(notes, "MILK")
    assert len(results) == 1
    assert "milk" in results[0].text


def test_search_multi_word(tmp_path):
    """Multiple words are AND'd."""
    from blip_search import parse_notes, search_notes
    notes = parse_notes(_make_notes_file(tmp_path))
    results = search_notes(notes, "buy eggs")
    assert len(results) == 1
    assert "eggs" in results[0].text


def test_filter_by_tag(tmp_path):
    """Filters to only notes with given tag."""
    from blip_search import parse_notes, filter_by_tag
    notes = parse_notes(_make_notes_file(tmp_path))
    results = filter_by_tag(notes, "todo")
    assert len(results) == 2
    assert all("todo" in n.tags for n in results)
```

- [ ] **Step 2: Run tests to verify new tests fail**

Run: `python -m pytest test_blip_search.py::test_search_keyword test_blip_search.py::test_search_case_insensitive test_blip_search.py::test_search_multi_word test_blip_search.py::test_filter_by_tag -v`
Expected: All 4 FAIL with `ImportError: cannot import name 'search_notes'` / `'filter_by_tag'`

- [ ] **Step 3: Implement search_notes and filter_by_tag**

Add to `blip_search.py` (after `_flush_note`):

```python
def search_notes(notes: list[Note], query: str) -> list[Note]:
    """Case-insensitive substring search. Multiple words are AND'd."""
    words = query.lower().split()
    if not words:
        return list(notes)
    return [n for n in notes if all(w in n.text.lower() for w in words)]


def filter_by_tag(notes: list[Note], tag: str) -> list[Note]:
    """Return only notes containing the given tag (without # prefix)."""
    return [n for n in notes if tag in n.tags]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest test_blip_search.py -v`
Expected: All 10 tests PASS

- [ ] **Step 5: Commit**

```bash
git add blip_search.py test_blip_search.py
git commit -m "feat: add search_notes() and filter_by_tag()"
```

---

### Task 3: mark_done()

**Files:**
- Modify: `blip_search.py`
- Modify: `test_blip_search.py`

Depends on: Task 1

- [ ] **Step 1: Write failing tests for mark_done**

Append to `test_blip_search.py`:

```python
def test_mark_done(tmp_path):
    """☐ flipped to ☑ in file, returns True."""
    f = tmp_path / "blip.md"
    f.write_text("- [2026-03-26 14:30] ☐ buy milk #todo\n", encoding="utf-8")

    from blip_search import parse_notes, mark_done
    notes = parse_notes(f)
    result = mark_done(f, notes[0])

    assert result is True
    content = f.read_text(encoding="utf-8")
    assert "☑" in content
    assert "☐" not in content


def test_mark_done_already_done(tmp_path):
    """Already ☑ → no change, returns True."""
    f = tmp_path / "blip.md"
    f.write_text("- [2026-03-26 14:30] ☑ already done #todo\n", encoding="utf-8")

    from blip_search import parse_notes, mark_done
    notes = parse_notes(f)
    result = mark_done(f, notes[0])

    assert result is True
    content = f.read_text(encoding="utf-8")
    assert content.count("☑") == 1
```

- [ ] **Step 2: Run tests to verify new tests fail**

Run: `python -m pytest test_blip_search.py::test_mark_done test_blip_search.py::test_mark_done_already_done -v`
Expected: Both FAIL with `ImportError: cannot import name 'mark_done'`

- [ ] **Step 3: Implement mark_done**

Add to `blip_search.py`:

```python
def mark_done(path: Path, note: Note) -> bool:
    """Rewrite note's line in the file: ☐ → ☑. Returns True on success."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        if note.line_number >= len(lines):
            return False
        lines[note.line_number] = lines[note.line_number].replace("☐", "☑", 1)
        path.write_text("".join(lines), encoding="utf-8")
        return True
    except OSError:
        return False
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest test_blip_search.py -v`
Expected: All 12 tests PASS

- [ ] **Step 5: Commit**

```bash
git add blip_search.py test_blip_search.py
git commit -m "feat: add mark_done() to flip ☐ → ☑"
```

---

### Task 4: BrowseWindow UI

**Files:**
- Create: `blip_browse.py`
- Create: `test_blip_browse.py`

Depends on: Task 1, Task 2, Task 3

This is the largest task. It creates the full browse window with card view, search, tag filters, and mark-done.

- [ ] **Step 1: Write failing tests for BrowseWindow**

Create `test_blip_browse.py`:

```python
"""Tests for blip_browse.py — Browse Window UI."""

import tkinter as tk
import pytest
from pathlib import Path

try:
    _test_root = tk.Tk()
    _test_root.destroy()
    _has_display = True
except tk.TclError:
    _has_display = False

needs_display = pytest.mark.skipif(not _has_display, reason="No display or Tcl unavailable")


@needs_display
def test_browse_window_creates(tmp_path):
    """BrowseWindow opens without error."""
    f = tmp_path / "blip.md"
    f.write_text("- [2026-03-26 14:30] ☐ test note #todo\n", encoding="utf-8")

    from blip_browse import BrowseWindow
    from blip import BlipConfig

    root = tk.Tk()
    root.withdraw()
    config = BlipConfig(output_file=f)
    win = BrowseWindow(root, config)
    assert win.window.winfo_exists()
    win.window.destroy()
    root.destroy()


@needs_display
def test_browse_search_filters(tmp_path):
    """Typing in search box reduces visible cards."""
    f = tmp_path / "blip.md"
    f.write_text(
        "- [2026-03-26 14:30] ☐ buy milk #todo\n"
        "- [2026-03-26 11:20] meeting notes\n",
        encoding="utf-8",
    )

    from blip_browse import BrowseWindow
    from blip import BlipConfig

    root = tk.Tk()
    root.withdraw()
    config = BlipConfig(output_file=f)
    win = BrowseWindow(root, config)
    total_before = len(win._visible_cards)

    win.search_var.set("milk")
    win._on_search()
    total_after = len(win._visible_cards)

    assert total_before == 2
    assert total_after == 1
    win.window.destroy()
    root.destroy()


@needs_display
def test_browse_tag_filter(tmp_path):
    """Tag pill click filters cards."""
    f = tmp_path / "blip.md"
    f.write_text(
        "- [2026-03-26 14:30] ☐ buy milk #todo\n"
        "- [2026-03-26 11:20] ⭐ lunch #important\n",
        encoding="utf-8",
    )

    from blip_browse import BrowseWindow
    from blip import BlipConfig

    root = tk.Tk()
    root.withdraw()
    config = BlipConfig(output_file=f)
    win = BrowseWindow(root, config)

    win._on_tag_filter("todo")
    assert len(win._visible_cards) == 1
    assert win._visible_cards[0].tags == ["todo"]

    win._on_tag_filter(None)  # "All" — clear filter
    assert len(win._visible_cards) == 2
    win.window.destroy()
    root.destroy()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest test_blip_browse.py -v`
Expected: All 3 FAIL with `ModuleNotFoundError: No module named 'blip_browse'`

- [ ] **Step 3: Implement BrowseWindow**

Create `blip_browse.py`. This is the full implementation:

```python
"""blip_browse.py — Browse Window for viewing and filtering past notes.

Card-view UI with search, tag filtering, and mark-done for #todo items.
Opened from the system tray icon. Uses blip_search for all data operations.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont
from datetime import datetime, timedelta
from pathlib import Path

from blip import THEMES, SMART_TAGS, BlipConfig, platform_font
from blip_search import parse_notes, search_notes, filter_by_tag, mark_done, TAG_COLORS, Note


class BrowseWindow:
    """Toplevel window for browsing and filtering notes."""

    def __init__(self, root: tk.Tk, config: BlipConfig):
        self.root = root
        self.config = config
        self.theme = THEMES[config.theme]
        self._all_notes: list[Note] = []
        self._visible_cards: list[Note] = []
        self._active_tag: str | None = None
        self._card_frames: list[tk.Frame] = []

        self.window = tk.Toplevel(root)
        self.window.title("Blip — Browse Notes")
        self.window.configure(bg=self.theme["bg"])
        self.window.geometry("480x520")
        self.window.minsize(360, 300)

        self.search_var = tk.StringVar()
        self._build_ui()
        self._load_notes()

        self.window.bind("<Escape>", lambda e: self.window.destroy())

    def _build_ui(self):
        t = self.theme
        fnt = platform_font()

        # Top bar frame
        top = tk.Frame(self.window, bg=t["entry_bg"], padx=8, pady=6)
        top.pack(fill="x")

        # Search entry
        self.search_entry = tk.Entry(
            top, textvariable=self.search_var, bg=t["bg"], fg=t["fg"],
            insertbackground=t["fg"], font=(fnt, 11),
            relief="flat", bd=0, highlightthickness=1,
            highlightbackground=t["muted"], highlightcolor=t["accent"],
        )
        self.search_entry.pack(fill="x", pady=(0, 6))
        self.search_entry.insert(0, "")
        self.search_var.trace_add("write", lambda *_: self._schedule_search())

        # Tag filter pills
        pills_frame = tk.Frame(top, bg=t["entry_bg"])
        pills_frame.pack(fill="x")

        self._pill_buttons: dict[str | None, tk.Label] = {}
        # "All" pill
        all_pill = tk.Label(
            pills_frame, text="All", bg=t["accent"], fg=t["bg"],
            font=(fnt, 9, "bold"), padx=8, pady=2, cursor="hand2",
        )
        all_pill.pack(side="left", padx=(0, 4))
        all_pill.bind("<Button-1>", lambda e: self._on_tag_filter(None))
        self._pill_buttons[None] = all_pill

        for tag, emoji in SMART_TAGS.items():
            color = TAG_COLORS.get(tag, t["muted"])
            pill = tk.Label(
                pills_frame, text=f"{emoji} {tag}", bg=t["bg"], fg=t["fg"],
                font=(fnt, 9), padx=6, pady=2, cursor="hand2",
                highlightthickness=1, highlightbackground=t["muted"],
            )
            pill.pack(side="left", padx=(0, 4))
            pill.bind("<Button-1>", lambda e, tg=tag: self._on_tag_filter(tg))
            self._pill_buttons[tag] = pill

        # Scrollable card area
        container = tk.Frame(self.window, bg=t["bg"])
        container.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(container, bg=t["bg"], highlightthickness=0, bd=0)
        scrollbar = tk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        self.cards_frame = tk.Frame(self.canvas, bg=t["bg"])

        self.cards_frame.bind(
            "<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas_window = self.canvas.create_window((0, 0), window=self.cards_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.bind("<Configure>", self._on_canvas_resize)

        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        # Mousewheel scrolling (bound to canvas only, not globally)
        self.canvas.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(-1 * (e.delta // 120), "units"))
        self.cards_frame.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(-1 * (e.delta // 120), "units"))

        # Footer
        self.footer = tk.Label(
            self.window, bg=t["entry_bg"], fg=t["muted"],
            font=(fnt, 9), anchor="center", pady=4,
        )
        self.footer.pack(fill="x")

    def _on_canvas_resize(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _load_notes(self):
        self._all_notes = parse_notes(self.config.output_file)
        self._apply_filters()

    def _schedule_search(self):
        """Debounce search by 200ms."""
        if hasattr(self, "_search_after_id"):
            self.window.after_cancel(self._search_after_id)
        self._search_after_id = self.window.after(200, self._on_search)

    def _on_search(self, *_args):
        self._apply_filters()

    def _on_tag_filter(self, tag: str | None):
        """Toggle tag filter. None = show all."""
        self._active_tag = tag
        self._update_pill_styles()
        self._apply_filters()

    def _update_pill_styles(self):
        t = self.theme
        fnt = platform_font()
        for tag_key, pill in self._pill_buttons.items():
            if tag_key == self._active_tag:
                pill.configure(bg=t["accent"], fg=t["bg"], font=(fnt, 9, "bold"))
            else:
                pill.configure(bg=t["bg"], fg=t["fg"], font=(fnt, 9))

    def _apply_filters(self):
        """Apply search query + tag filter, then re-render cards."""
        notes = self._all_notes
        query = self.search_var.get().strip()
        if query:
            notes = search_notes(notes, query)
        if self._active_tag:
            notes = filter_by_tag(notes, self._active_tag)

        self._visible_cards = notes
        self._render_cards()

    def _render_cards(self):
        """Clear and re-render all visible cards."""
        for widget in self.cards_frame.winfo_children():
            widget.destroy()
        self._card_frames.clear()

        t = self.theme
        fnt = platform_font()
        notes = self._visible_cards
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        current_date = None

        for note in reversed(notes):  # newest first
            note_date = note.timestamp.date()
            if note_date != current_date:
                current_date = note_date
                if note_date == today:
                    header_text = "TODAY"
                elif note_date == yesterday:
                    header_text = "YESTERDAY"
                else:
                    header_text = note_date.strftime("%b %d").upper()

                header = tk.Label(
                    self.cards_frame, text=header_text, bg=t["bg"],
                    fg=t["muted"], font=(fnt, 9), anchor="w", pady=4, padx=12,
                )
                header.pack(fill="x")

            self._render_card(note, fnt)

        # Footer
        open_todos = sum(1 for n in self._all_notes if "todo" in n.tags and not n.is_done)
        self.footer.configure(text=f"{len(self._visible_cards)} notes · {open_todos} open todos · Esc close")

    def _render_card(self, note: Note, fnt: str):
        """Render a single note card."""
        t = self.theme

        # Determine left border color
        border_color = t["muted"]
        for tag in note.tags:
            if tag in TAG_COLORS:
                border_color = TAG_COLORS[tag]
                break

        opacity_fg = t["muted"] if note.is_done else t["fg"]
        card_bg = t["entry_bg"]

        # Card outer frame (provides colored left border)
        outer = tk.Frame(self.cards_frame, bg=border_color, padx=0, pady=0)
        outer.pack(fill="x", padx=12, pady=(0, 6))

        # Card inner frame
        card = tk.Frame(outer, bg=card_bg, padx=10, pady=8)
        card.pack(fill="x", padx=(3, 0))  # 3px left border

        # Top row: time + checkbox
        top_row = tk.Frame(card, bg=card_bg)
        top_row.pack(fill="x")

        time_str = note.timestamp.strftime("%H:%M")
        tk.Label(
            top_row, text=time_str, bg=card_bg, fg=t["muted"], font=(fnt, 9),
        ).pack(side="left")

        if "todo" in note.tags:
            check_text = "☑" if note.is_done else "☐"
            check_btn = tk.Label(
                top_row, text=check_text, bg=card_bg, fg=opacity_fg,
                font=(fnt, 14), cursor="hand2",
            )
            check_btn.pack(side="right")
            if not note.is_done:
                check_btn.bind("<Button-1>", lambda e, n=note: self._on_mark_done(n))

        # Note text
        text_display = note.text
        text_font_opts = (fnt, 11)
        if note.is_done:
            text_font_opts = (fnt, 11, "overstrike")

        text_label = tk.Label(
            card, text=text_display, bg=card_bg, fg=opacity_fg,
            font=text_font_opts, anchor="w", justify="left", wraplength=400,
        )
        text_label.pack(fill="x", pady=(4, 0))

        # Tag pills
        if note.tags:
            tags_frame = tk.Frame(card, bg=card_bg)
            tags_frame.pack(fill="x", pady=(4, 0), anchor="w")
            for tag in note.tags:
                color = TAG_COLORS.get(tag, t["muted"])
                tk.Label(
                    tags_frame, text=f"#{tag}", bg=t["bg"], fg=color,
                    font=(fnt, 9), padx=4, pady=1,
                ).pack(side="left", padx=(0, 4))

        self._card_frames.append(outer)

    def _on_mark_done(self, note: Note):
        """Mark a todo note as done and refresh the display."""
        if mark_done(self.config.output_file, note):
            self._load_notes()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest test_blip_browse.py -v`
Expected: All 3 tests PASS (or SKIP if no display)

- [ ] **Step 5: Run all tests to check for regressions**

Run: `python -m pytest test_blip.py test_blip_search.py test_blip_browse.py -v`
Expected: All tests PASS (19 existing + 12 search + 3 browse = 34 total)

- [ ] **Step 6: Commit**

```bash
git add blip_browse.py test_blip_browse.py
git commit -m "feat: add BrowseWindow with card view, search, and tag filters"
```

---

### Task 5: Wire Browse into tray icon and poll_queue

**Files:**
- Modify: `blip.py` (lines 158-206 `create_tray_icon`, lines 428-440 `poll_queue`)

Depends on: Task 4

- [ ] **Step 1: Add "Browse Notes" to tray menu**

In `blip.py`, modify `create_tray_icon()`. The current menu is at approximately lines 196-203:

```python
    menu = pystray.Menu(
        pystray.MenuItem("Blip ⚡", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(f"Open {config.output_file.name}", lambda: open_notes()),
        pystray.MenuItem("Quit", quit_app),
    )
```

Replace with:

```python
    def browse_notes():
        app_queue.put("BROWSE")

    menu = pystray.Menu(
        pystray.MenuItem("Blip ⚡", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(f"Open {config.output_file.name}", lambda: open_notes()),
        pystray.MenuItem("Browse Notes", lambda: browse_notes()),
        pystray.MenuItem("Quit", quit_app),
    )
```

- [ ] **Step 2: Handle "BROWSE" in poll_queue**

In `blip.py`, modify the `poll_queue` method (lines 428-440). The current handler checks for `"SHOW"` and `"QUIT"`. Add `"BROWSE"`:

```python
    def poll_queue(self):
        """Check the queue for messages from the pynput/tray threads."""
        try:
            while True:
                msg = self.queue.get_nowait()
                if msg == "SHOW":
                    self.show_window()
                elif msg == "BROWSE":
                    self._open_browse()
                elif msg == "QUIT":
                    self.root.quit()
                    return
        except queue.Empty:
            pass
        self.root.after(100, self.poll_queue)
```

- [ ] **Step 3: Add _open_browse method to Blip class**

Add this method to the `Blip` class (after `poll_queue`):

```python
    def _open_browse(self):
        """Open the Browse Notes window."""
        from blip_browse import BrowseWindow
        BrowseWindow(self.root, self.config)
```

The lazy import avoids a circular dependency and keeps the browse module optional.

- [ ] **Step 4: Run all tests**

Run: `python -m pytest test_blip.py test_blip_search.py test_blip_browse.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add blip.py
git commit -m "feat: wire Browse Notes into tray menu and poll_queue"
```

---

### Task 6: Update pyproject.toml and final verification

**Files:**
- Modify: `pyproject.toml`

Depends on: Task 5

- [ ] **Step 1: Update pyproject.toml**

The current `[tool.setuptools]` section (line 19) has:

```toml
[tool.setuptools]
py-modules = ["blip"]
```

Replace with:

```toml
[tool.setuptools]
py-modules = ["blip", "blip_search", "blip_browse"]
```

- [ ] **Step 2: Run all tests one final time**

Run: `python -m pytest test_blip.py test_blip_search.py test_blip_browse.py -v`
Expected: All tests PASS. Confirm total count is ~34 tests.

- [ ] **Step 3: Verify imports and module structure**

Run: `python -c "from blip_search import parse_notes, search_notes, filter_by_tag, mark_done, TAG_COLORS, Note; print('blip_search OK')"` and `python -c "from blip_browse import BrowseWindow; print('blip_browse OK')"`
Expected: Both print OK without errors.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "chore: add blip_search and blip_browse to pyproject.toml"
```

---

## Task Dependency Graph

```
Task 1 (Note + parse_notes)
  ├── Task 2 (search + filter)
  ├── Task 3 (mark_done)
  │       │
  └───────┴── Task 4 (BrowseWindow UI)
                  │
              Task 5 (tray + queue wiring)
                  │
              Task 6 (pyproject + verification)
```

Tasks 2 and 3 can run in parallel after Task 1. Task 4 requires all three. Tasks 5 and 6 are sequential after Task 4.
