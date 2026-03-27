# Phase 7: Edit/Delete Notes — Design Spec

**Goal:** Allow users to edit and delete notes from both the Browse window and CLI.

## Design Decisions

### Edit
- **Scope:** Replace note text only (timestamp preserved)
- **Browse UI:** Custom themed popup dialog (multi-line text area, Save/Cancel buttons, matches CogStash theme)
- **CLI:** `cogstash edit <number> "new text"` or `cogstash edit --search "keyword" "new text"`

### Delete
- **Type:** Hard delete (permanently removes lines from file)
- **Browse UI:** Right-click context menu → Delete → confirmation dialog ("Are you sure?")
- **CLI:** `cogstash delete <number>` with interactive confirmation; `--yes` flag to skip confirmation
- **CLI search:** `cogstash delete --search "keyword"` also supported

### Browse Window Interaction
- **Right-click context menu** on any card with options: ✏️ Edit, 🗑️ Delete, 📋 Copy text
- Native `tk.Menu` + `tk_popup()` for the context menu
- Edit opens a themed Toplevel dialog with pre-populated text
- Delete shows a confirmation dialog before acting

### Note Identification
- **By index:** Notes are 1-indexed (most recent = highest number). `Note.index` already exists.
- **By search:** First matching note is acted on. If multiple matches, show them and ask user to pick (CLI) or act on the right-clicked card (Browse).

## Backend Functions (cogstash_search.py)

### `edit_note(path, note, new_text) -> bool`
- Read file, locate note at `note.line_number`
- Count continuation lines (lines starting with 2-space indent until next `- [` or EOF)
- Replace header + continuation lines with new formatted text (preserving original timestamp)
- Handle multi-line new_text with continuation indent
- Rewrite entire file (same pattern as `mark_done`)

### `delete_note(path, note) -> bool`
- Read file, locate note at `note.line_number`
- Count continuation lines (same logic as edit)
- Remove header + continuation lines
- Rewrite file

### Shared helper: `_note_line_span(lines, line_number) -> (start, end)`
- Returns the line range (start inclusive, end exclusive) for a note including continuation lines
- Used by both edit_note and delete_note

## CLI Commands (cogstash_cli.py)

### `cogstash edit <number> "new text"`
- `cogstash edit 3 "updated note text"`
- `cogstash edit --search "milk" "buy oat milk instead"`
- Prints confirmation: "Note 3 updated."
- sys.exit(1) on errors (note not found, write failure)

### `cogstash delete <number>`
- `cogstash delete 3` → prompts "Delete note 3: '☐ buy milk #todo'? [y/N]"
- `cogstash delete 3 --yes` → skips confirmation
- `cogstash delete --search "milk"` → finds + confirms
- Prints: "Note 3 deleted."
- sys.exit(1) on errors

## Browse Window (cogstash_browse.py)

### Context Menu
- Right-click any card → popup menu: Edit / Delete / Copy text
- Bind `<Button-3>` on card frames
- Store `note` reference on each card for action dispatch

### Edit Dialog
- `Toplevel` window, themed to match current CogStash theme
- Title: "Edit Note" with timestamp shown read-only
- `tk.Text` widget pre-populated with note text
- Save button → calls `edit_note()` → refreshes cards
- Cancel button / Escape → closes dialog
- ~40 lines of code

### Delete Confirmation
- `tkinter.messagebox.askyesno("Delete Note", "Delete this note?")`
- On yes → calls `delete_note()` → refreshes cards

## Error Handling
- Note not found → error message (CLI: stderr + exit 1, Browse: messagebox)
- Write failure → error message, no data loss
- Empty edit text → rejected (same as empty note in append)
