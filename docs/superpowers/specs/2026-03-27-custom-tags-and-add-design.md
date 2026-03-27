# Phase 6: Custom Tags + `cogstash add` — Design Spec

## Overview

Two features in one phase:
1. **Custom tags** — user-defined tags via `~/.cogstash.json` with emoji + color
2. **`cogstash add`** — CLI command to capture notes without opening the GUI

---

## Part A: Custom Tags

### Config Format

Users add a `"tags"` key to `~/.cogstash.json`:

```json
{
  "theme": "dracula",
  "tags": {
    "work": { "emoji": "💼", "color": "#4A90D9" },
    "health": { "emoji": "🏃", "color": "#2ECC71" }
  }
}
```

Each custom tag has:
- `emoji` (string, required) — prepended to notes containing this tag
- `color` (string, required) — hex color for browse card borders and CLI output

### Built-in Tags

The 4 built-in tags are non-removable defaults:

| Tag | Emoji | Color |
|-----|-------|-------|
| `#todo` | ☐ | `#7aa2f7` |
| `#urgent` | 🔴 | `#f7768e` |
| `#important` | ⭐ | `#e0af68` |
| `#idea` | 💡 | `#9ece6a` |

User-defined tags with the same name as a built-in tag **override** the emoji and color. This lets users customize even the built-ins if desired.

### Merging Strategy

At config load time:
1. Start with `DEFAULT_SMART_TAGS` (the 4 built-ins)
2. Merge user `"tags"` on top (user wins on conflict)
3. The merged dict becomes the runtime `SMART_TAGS`

Similarly for colors:
1. Start with `DEFAULT_TAG_COLORS` (the 4 built-in hex colors)
2. Merge user tag colors on top
3. The merged dict becomes the runtime `TAG_COLORS`

### What Changes

**`cogstash.py`:**
- Rename current `SMART_TAGS` → `DEFAULT_SMART_TAGS` (module-level constant)
- `CogStashConfig` gets a new field: `tags: dict[str, dict[str, str]] | None = None`
- `load_config()` parses the `"tags"` key, validates each entry has `emoji` + `color`
- New helper: `merge_tags(config) -> tuple[dict, dict]` returns merged (smart_tags, tag_colors)
- `parse_smart_tags()` takes a `smart_tags` dict parameter instead of using global
- `_on_key_release` autocomplete filters from merged smart_tags (passed via config)
- `show_autocomplete` already works with any list of `(name, emoji)` pairs — no change
- `main()` argv guard adds `"add"` to the recognized subcommands
- Tag pills in browse window: pass merged tags to `BrowseWindow`

**`cogstash_search.py`:**
- Rename current `TAG_COLORS` → `DEFAULT_TAG_COLORS`
- Functions that use `TAG_COLORS` accept an optional `tag_colors` parameter (default to built-ins)
- `parse_notes()` tag extraction still uses regex — no change needed (any `#word` is a tag)

**`cogstash_browse.py`:**
- `BrowseWindow.__init__` receives merged `smart_tags` and `tag_colors` dicts
- Tag filter pills generated dynamically from merged tags (not hardcoded 4)
- Card border colors use merged `tag_colors`

**`cogstash_cli.py`:**
- `ANSI_TAG` becomes dynamic — built from merged tag_colors using nearest ANSI approximation
- Helper: `hex_to_ansi(hex_color) -> str` converts hex → nearest 8-color ANSI code
- `format_note()` receives the tag color map
- `cli_main()` loads config and passes merged colors to commands

### Validation

Invalid tag entries in config are skipped with a warning log:
- Missing `emoji` key → skip, log warning
- Missing `color` key → skip, log warning
- Invalid hex color (not matching `#[0-9a-fA-F]{6}`) → skip, log warning

---

## Part B: `cogstash add` CLI Command

### Usage

```bash
cogstash add "buy milk #todo"            # argument mode → saves with ☐ prefix
echo "review PR #urgent" | cogstash add  # stdin mode → saves with 🔴 prefix
cogstash add                             # reads stdin until EOF (Ctrl+D / Ctrl+Z)
```

### Behavior

1. **Input resolution:** If positional `text` argument provided, use it. Otherwise read `sys.stdin`.
2. **Smart tag processing:** Apply `parse_smart_tags()` with merged tags (same logic as GUI).
3. **Timestamp:** Auto-generate `[YYYY-MM-DD HH:MM]` timestamp.
4. **Multi-line:** Stdin input supports multi-line (continuation lines get 2-space indent).
5. **Write:** Append to configured `output_file` (from `~/.cogstash.json` or default `~/cogstash.md`).
6. **Output:** Print confirmation to stdout: `✓ Note saved to ~/cogstash.md`
7. **Error:** Print error to stderr, exit code 1.

### Parser Addition

```python
p_add = sub.add_parser("add", help="Add a note from the command line")
p_add.add_argument("text", nargs="?", help="Note text (reads stdin if omitted)")
p_add.set_defaults(func=cmd_add)
```

### `cmd_add` Function

Located in `cogstash_cli.py`. Receives config from `cli_main()` (same pattern as other commands). Resolves text (arg or stdin), then delegates to a shared `append_note_to_file(text, config, smart_tags)` helper extracted from `CogStash.append_note()` — this avoids duplicating the timestamp formatting, multi-line indentation, and file-write logic. Prints confirmation on success.

### `main()` Guard Update

In `cogstash.py`, the argv guard expands:
```python
if len(sys.argv) > 1 and sys.argv[1] in ("recent", "search", "tags", "add"):
```

---

## Testing

### Custom Tag Tests (`test_cogstash.py`)

- `test_load_config_custom_tags` — config with `"tags"` key loads custom tags
- `test_load_config_invalid_tag_skipped` — missing emoji/color skipped with warning
- `test_merge_tags_builtin_defaults` — no custom tags returns built-in defaults
- `test_merge_tags_override_builtin` — user can override #todo emoji
- `test_merge_tags_add_new` — custom tag added alongside built-ins
- `test_parse_smart_tags_custom` — custom tag emoji prepended to note text

### Custom Tag Tests (`test_cogstash_browse.py`)

- `test_browse_custom_tag_pills` — custom tags appear as filter pills

### `cogstash add` Tests (`test_cogstash_cli.py`)

- `test_cmd_add_argument` — adds note from argument
- `test_cmd_add_stdin` — adds note from stdin
- `test_cmd_add_smart_tags` — emoji prefix applied
- `test_cmd_add_multiline_stdin` — multi-line stdin formatted correctly
- `test_cmd_add_empty_rejected` — empty input prints error, exit code 1

---

## Constraints

- No new dependencies (custom tags are pure config parsing)
- Built-in tags are always present (non-removable defaults)
- Unknown `#hashtags` in notes are still valid tags — they just don't get emoji prefixes or special colors
- `cogstash add` reuses `parse_smart_tags()` from `cogstash.py` — no duplication
- Config validation is lenient: bad tag entries are skipped, not fatal
