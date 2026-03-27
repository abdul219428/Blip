# Phase 4: CLI Commands — Design Spec

## Goal

Add three CLI subcommands (`recent`, `search`, `tags`) so users can query their CogStash notes directly from the terminal without opening the GUI.

## Architecture

A new `cogstash_cli.py` module owns all CLI logic: argparse setup, command handlers, and ANSI output formatting. The existing `cogstash.py:main()` entry point gains a simple `sys.argv` check — if subcommands are present it delegates to `cogstash_cli.cli_main()`; otherwise it launches the GUI as today.

All data operations reuse `cogstash_search.py` (`parse_notes()`, `search_notes()`, `filter_by_tag()`). Zero data logic is duplicated — `cogstash_cli.py` is purely presentation.

**Tech stack:** argparse (stdlib), ANSI escape codes for color (no dependencies).

## Commands

### `cogstash recent [--limit N]`

Show the most recent N notes (default 20), newest first.

```
$ cogstash recent
[2026-03-27 14:30] ☐ buy milk #todo
[2026-03-27 11:20] meeting notes with the team
[2026-03-26 09:00] ☑ fix login bug #urgent

$ cogstash recent --limit 5
(shows 5 most recent)
```

### `cogstash search <query> [--limit N]`

Full-text search through note text. Results ordered by recency (newest first). Default limit: 20.

```
$ cogstash search "milk"
[2026-03-27 14:30] ☐ buy milk #todo

$ cogstash search "meeting" --limit 10
(up to 10 matching results)
```

### `cogstash tags`

List all tags with note counts, sorted by count descending.

```
$ cogstash tags
#todo        3 notes
#important   2 notes
#urgent      1 note
#idea        1 note
```

## Output Formatting

- **Timestamps** — dimmed (ANSI gray `\033[90m`)
- **Tags** — ANSI approximations of TAG_COLORS from `cogstash_search.py`: todo=cyan, urgent=red, important=yellow, idea=green. Unknown tags get default terminal color.
- **Done items** — strikethrough + dimmed (`\033[9m\033[90m`)
- **Tag counts** — bold count number
- **Pipe-safe** — when `sys.stdout.isatty()` is False, all ANSI codes are stripped. This ensures `cogstash recent | grep todo` and `cogstash tags > tags.txt` work cleanly.

## File Structure

### Create: `cogstash_cli.py` (~80-100 lines)

Module responsible for CLI argument parsing and formatted output.

**Public API:**
- `cli_main(argv: list[str]) -> None` — entry point, parses args, loads config, dispatches to handler
- `build_parser() -> argparse.ArgumentParser` — constructs parser with 3 subcommands

**Internal functions:**
- `cmd_recent(args, config)` — calls `parse_notes()`, slices by limit, prints formatted output
- `cmd_search(args, config)` — calls `search_notes()`, prints formatted output
- `cmd_tags(args, config)` — calls `parse_notes()`, aggregates tag counts, prints formatted output
- `format_note(note: Note, use_color: bool) -> str` — formats a single note line with optional ANSI
- `strip_ansi(text: str) -> str` — remove ANSI escape sequences (for pipe output)

### Create: `test_cogstash_cli.py` (~80-100 lines)

Tests for each command, output formatting, and pipe detection.

**Test cases:**
- `test_cmd_recent_default` — shows up to 20 notes, newest first
- `test_cmd_recent_limit` — `--limit 3` shows only 3
- `test_cmd_recent_empty` — empty/missing file shows "No notes found."
- `test_cmd_search_match` — finds matching notes
- `test_cmd_search_no_match` — shows "No matching notes."
- `test_cmd_tags_counts` — correct counts, sorted descending
- `test_cmd_tags_empty` — empty file shows "No tags found."
- `test_format_note_color` — ANSI codes present when use_color=True
- `test_format_note_plain` — no ANSI codes when use_color=False
- `test_format_done_note` — done notes get strikethrough + dimmed

### Modify: `cogstash.py:main()`

Add a check at the top of `main()`:

```python
def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("recent", "search", "tags"):
        from cogstash_cli import cli_main
        cli_main(sys.argv[1:])
        return
    # ... existing GUI code unchanged ...
```

This uses lazy import (same pattern as `_open_browse()`) to avoid loading argparse/CLI code when launching the GUI.

### Modify: `pyproject.toml`

Add `cogstash_cli` to the `py-modules` list.

## Data Flow

```
User types: cogstash search "milk"
  → cogstash.py:main()
    → detects sys.argv[1] == "search"
    → cogstash_cli.cli_main(["search", "milk"])
      → loads config (for output_file path)
      → calls cogstash_search.search_notes(notes, "milk")
      → formats each Note with ANSI colors
      → prints to stdout
```

## Edge Cases

- **No notes file** — print "No notes found." and exit 0
- **Empty search results** — print "No matching notes." and exit 0
- **No tags** — print "No tags found." and exit 0
- **Piped output** — auto-detect with `isatty()`, strip ANSI
- **Unknown subcommand** — argparse handles this with usage message
- **`--limit 0` or negative** — treat as "show all"

## Out of Scope

- `cogstash add` (quick-add from terminal) — future phase
- `cogstash done` (mark done from CLI) — future phase
- `cogstash export` (JSON/CSV export) — future phase
- Shell completions — future phase
- Config file creation/editing via CLI — future phase
