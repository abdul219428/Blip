# Phase 3: Recall & Review — Design Spec

## Problem

Blip captures notes via a global hotkey, appending them to `~/blip.md`. There is currently no way to search, browse, or act on past notes from within the app. Users must open the file manually or use external tools like grep. Phase 3 adds a **Browse Window** accessible from the system tray, with search, tag filtering, and the ability to mark `#todo` items as done.

## Approach

- **GUI-first**: Browse Window opened from the tray icon — fits the Windows-native packaged-app workflow the user envisions.
- **CLI deferred**: Terminal commands (`blip search`, `blip recent`) are out of scope for Phase 3; they may be added alongside packaging in Phase 4.
- **Module split**: Search/parsing logic lives in a new `blip_search.py` (pure functions, no tkinter). The browse UI lives in `blip_browse.py`. This addresses the reviewer-flagged concern of `blip.py` exceeding 450 lines.
- **No new dependencies**: Search uses pure Python string matching. No database, no search library.
- **Read-only + mark-done**: Notes cannot be edited or deleted from the browse window. The one write operation is toggling `☐` → `☑` for `#todo` items.

## Data Model

### Note dataclass (`blip_search.py`)

```python
@dataclass
class Note:
    index: int          # 1-based position in file (stable for append-only)
    timestamp: datetime # parsed from [YYYY-MM-DD HH:MM]
    text: str           # full note text (continuation lines joined with \n)
    tags: list[str]     # extracted hashtags without # prefix (e.g., ["todo", "urgent"])
    is_done: bool       # True if ☑ prefix, False if ☐ or no prefix
    line_number: int    # starting line in blip.md (for mark_done rewriting)
```

### Parsing rules

- A line matching `^- \[\d{4}-\d{2}-\d{2} \d{2}:\d{2}\] ` starts a new note.
- Subsequent lines indented with 2 spaces are continuation lines, joined to the previous note's `text` with `\n` (leading 2-space indent stripped).
- Tags extracted via `(?:^|\s)#(\w+)` regex from the full text (same pattern as `blip.py` — excludes URL fragments). Stored **without** the `#` prefix (e.g., `"todo"` not `"#todo"`) to match `SMART_TAGS` dict keys.
- Smart-tag emoji prefixes (`☐`, `☑`, `🔴`, `⭐`, `💡`) are part of `text` — not stripped.
- `is_done` is determined by presence of `☐` (False) or `☑` (True) in the text prefix. Notes without either are `is_done=False`.

## Module Structure

### `blip_search.py` (~120 lines, no tkinter)

Pure functions for note parsing, search, and mutation:

| Function | Signature | Purpose |
|----------|-----------|---------|
| `parse_notes` | `(path: Path) → list[Note]` | Read blip.md into Note objects in a single pass |
| `search_notes` | `(notes: list[Note], query: str) → list[Note]` | Case-insensitive substring match; multiple words are AND'd |
| `filter_by_tag` | `(notes: list[Note], tag: str) → list[Note]` | Keep only notes containing the given tag |
| `mark_done` | `(path: Path, note: Note) → bool` | Rewrite note's line: `☐` → `☑`. One-way only. Returns True on success. |

**Search implementation**: `all(word in note.text.lower() for word in query.lower().split())`. No indexing, no tokenization. Fast enough for thousands of notes (<50ms for 10,000 entries).

**Upgrade path**: If search becomes slow in the future, swap to SQLite FTS5 (stdlib `sqlite3`) without changing the public API.

### `blip_browse.py` (~250 lines)

Browse window UI using tkinter:

| Class/Function | Purpose |
|----------------|---------|
| `BrowseWindow` | tkinter Toplevel — search box, tag filter pills, scrollable card list |
| `_build_ui` | Constructs the window layout |
| `_refresh_cards` | Re-renders visible cards based on current filters |
| `_on_search` | Debounced keystroke handler — filters cards in real-time |
| `_on_tag_filter` | Toggle a tag filter pill on/off |
| `_on_mark_done` | Click handler for `☐` checkbox — calls `mark_done()`, updates card |

### `blip.py` — minimal changes

- Tray icon menu gains **"Browse Notes"** option (between "Open notes" and "Quit").
- On click → creates `BrowseWindow` in the main tkinter thread via the existing `app_queue` IPC mechanism.
- No structural changes to existing code.

## Browse Window Design

### Opening

- **Trigger**: Tray icon right-click → "Browse Notes"
- The window is a `tk.Toplevel` child of the main root window (same process).
- Notes are parsed fresh via `parse_notes()` each time the window opens.
- Themed using the user's configured theme from `BlipConfig` + `THEMES` dict.
- Window is resizable with a sensible default size (~480×500px).

### Layout (Card View)

```
┌─────────────────────────────────────────────┐
│  🔍 Search...          [All][☐][🔴][⭐][💡] │  ← search + tag filters
├─────────────────────────────────────────────┤
│  TODAY                                       │  ← date group header
│  ┌─────────────────────────────────────────┐ │
│  │ ▎ 14:30                            [☐]  │ │  ← card with checkbox
│  │ ▎ 🔴 Deploy backend by Friday           │ │
│  │ ▎ Need to finalize migration script     │ │
│  │ ▎ #todo #urgent                         │ │
│  └─────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────┐ │
│  │ ▎ 11:20                                 │ │  ← card without checkbox
│  │ ▎ ⭐ Team lunch next Tuesday             │ │
│  │ ▎ #important                            │ │
│  └─────────────────────────────────────────┘ │
│  YESTERDAY                                   │
│  ┌─────────────────────────────────────────┐ │
│  │ ▎ 18:42                            [☑]  │ │  ← done card (dimmed)
│  │ ▎ ̶b̶u̶y̶ ̶m̶i̶l̶k̶ ̶a̶n̶d̶ ̶e̶g̶g̶s̶                    │ │
│  │ ▎ #todo                                 │ │
│  └─────────────────────────────────────────┘ │
├─────────────────────────────────────────────┤
│  5 notes · 2 open todos            Esc close │  ← footer
└─────────────────────────────────────────────┘
```

### Card design

- **Left border**: Colored by primary tag using hardcoded hex values (consistent across all themes):
  - `#urgent` → `#f7768e` (red)
  - `#important` → `#e0af68` (amber)
  - `#idea` → `#9ece6a` (green)
  - `#todo` → `#7aa2f7` (blue)
  - no recognized tag → theme `muted` color
  These are stored in a `TAG_COLORS` dict in `blip_search.py`.
- **Checkbox**: Only shown for notes with `#todo` tag. Click marks done (`☐` → `☑`, one-way).
- **Done cards**: Text has strikethrough, entire card is dimmed (lower opacity).
- **Multi-line notes**: Full text displayed (continuation lines visible).
- **Tag pills**: Shown at bottom of card, styled with theme colors.
- **Date group headers**: "TODAY", "YESTERDAY", or "MMM DD" for older dates (e.g., "MAR 24"). Uppercase for visual consistency.

### Interactions

| Action | Effect |
|--------|--------|
| Type in search box | Filters cards in real-time (debounced ~200ms after last keystroke) |
| Click a tag filter pill | Toggle: show only notes with that tag. "All" clears all filters. |
| Click `☐` on a card | Calls `mark_done()` → `☐` becomes `☑`, text strikes through, card dims. One-way only — cannot un-done. |
| `Escape` | Closes the browse window |
| Mousewheel | Scrolls through cards |
| Window close (X) | Same as Escape — closes window, daemon keeps running |

### What it does NOT do

- No editing note text
- No deleting or archiving notes
- No drag-and-drop reordering
- No export functionality
- No multi-select operations
- No keyboard navigation between cards (mouse-only for Phase 3)

## Tray Icon Changes

Current menu:
```
Open notes    → opens ~/blip.md in default editor
Quit          → exits the app
```

New menu:
```
Open notes    → opens ~/blip.md in default editor
Browse Notes  → opens BrowseWindow
Quit          → exits the app
```

The "Browse Notes" action sends a `"browse"` message through the existing `app_queue`. The `poll_queue` handler in `Blip` creates the `BrowseWindow`.

## Testing Strategy

### `blip_search.py` tests (~11 tests, no display needed)

| Test | Verifies |
|------|----------|
| `test_parse_notes_basic` | Single note: timestamp, text, tags parsed correctly |
| `test_parse_notes_multiline` | Continuation lines joined to parent note |
| `test_parse_notes_empty_file` | Empty/missing file → empty list |
| `test_parse_notes_done_status` | `☐` → `is_done=False`, `☑` → `is_done=True` |
| `test_parse_notes_no_prefix` | Note without smart-tag emoji → `is_done=False` |
| `test_search_keyword` | Substring match finds correct notes |
| `test_search_case_insensitive` | "MILK" matches "milk" |
| `test_search_multi_word` | "milk eggs" matches notes containing both |
| `test_filter_by_tag` | Filters to only notes with given tag |
| `test_mark_done` | `☐` flipped to `☑` in file, returns True |
| `test_mark_done_already_done` | Already `☑` → no change, returns True |

### `blip_browse.py` tests (~3 tests, display-dependent)

| Test | Verifies |
|------|----------|
| `test_browse_window_creates` | Window opens without error |
| `test_browse_search_filters` | Typing query reduces visible cards |
| `test_browse_tag_filter` | Tag pill click filters correctly |

All display-dependent tests use the existing `@needs_display` skip marker.

### Updated test count

- Phase 1+2 existing: 19 tests
- Phase 3 search logic: 11 tests
- Phase 3 browse UI: 3 tests
- **Total: ~33 tests**

## File Size Budget

| File | Current | After Phase 3 | Notes |
|------|---------|---------------|-------|
| `blip.py` | ~549 lines | ~565 lines | +15 lines (tray menu + queue handler) |
| `blip_search.py` | — | ~120 lines | New: pure search logic |
| `blip_browse.py` | — | ~250 lines | New: browse window UI |
| `test_blip.py` | 188 lines | ~188 lines | Unchanged |
| `test_blip_search.py` | — | ~120 lines | New: search logic tests |
| `test_blip_browse.py` | — | ~50 lines | New: browse UI tests |

Total new code: ~540 lines across 4 new files. Each file stays well under 300 lines.

## Out of Scope

- **CLI commands** (`blip search`, `blip recent`, `blip tags`) — deferred to Phase 4.
- **Note editing** — Blip is a capture tool, not an editor.
- **Note deletion/archiving** — may revisit in a future phase.
- **Keyboard card navigation** — mouse-only in the browse window for now.
- **Persistent search index** — string matching is fast enough; SQLite FTS5 is the upgrade path if needed.
- **Export** — open `~/blip.md` in an editor for now.
