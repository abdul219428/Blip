# Phase 2: Capture Experience — Design Spec

Extends Blip with a config file, multi-line input, smart tags with autocomplete, and theme presets. The app stays single-file (~400-450 lines).

## 1. Config File

**File:** `~/.blip.json` (created with defaults on first run)

```json
{
  "hotkey": "<ctrl>+<shift>+<space>",
  "output_file": "~/blip.md",
  "log_file": "~/blip.log",
  "theme": "tokyo-night",
  "window_size": "default"
}
```

**Implementation:**
- `@dataclass BlipConfig` with fields: hotkey, output_file, log_file, theme, window_size
- `load_config() -> BlipConfig`: read JSON, merge with defaults, return dataclass
- Missing file → create with defaults, log info
- Partial JSON → fill missing keys from defaults
- Malformed JSON → log warning, use all defaults
- Unknown theme/window_size → log warning, fall back to defaults
- `~` paths expanded via `Path.home()`
- Config loaded once at startup (no hot-reload)

## 2. Multi-line Input

Replace `tk.Entry` with `tk.Text` widget.

**Keybindings (Slack/Discord convention):**
- `Enter` → save & close
- `Shift+Enter` → insert newline
- `Escape` → dismiss (unchanged)

**Widget behavior:**
- Default height from window_size preset (e.g., 3 lines for "default")
- Grows dynamically as user types, up to max_lines
- Hint text: `Enter to save · Shift+Enter for new line · Esc to cancel`

**Storage in blip.md:**
Multi-line notes use indented continuation lines:
```
- [2026-03-26 17:50] Meeting notes from standup:
  - Deploy by Friday #todo
  - Review PR #42 #urgent
- [2026-03-26 17:45] buy milk #todo
```

## 3. Smart Tags

4 smart tags with emoji prefixes, plus inline hashtag preservation.

| Tag | Emoji | Purpose |
|-----|-------|---------|
| `#todo` | ☐ | Unchecked task |
| `#urgent` | 🔴 | Immediate action |
| `#important` | ⭐ | High value |
| `#idea` | 💡 | Creative thought |

**Parsing rules:**
- Regex: `(?:^|\s)#(\w+)` — matches `#word` preceded by whitespace or start-of-line
- Smart tag emojis prepended to the first line of the note (deduplicated)
- Original `#tag` text preserved inline for searchability
- Tags inside URLs (`http://example.com#section`) are not matched

**Example — input:** `Review PR #42 #todo #urgent`
**Saved as:** `- [2026-03-26 17:50] ☐ 🔴 Review PR #42 #todo #urgent`

## 4. Tag Discoverability

Two complementary features:

### Footer hints
A faded label below the input showing all 4 smart tags:
```
☐ #todo  🔴 #urgent  ⭐ #important  💡 #idea
```
Always visible, unobtrusive. Uses theme's `muted` color.

### Autocomplete popup
- Triggered when user types `#`
- Shows a `tk.Toplevel` popup near the cursor with the 4 options
- Filters as user continues typing (e.g., `#to` → `#todo`)
- Arrow keys to navigate, Enter/Tab to insert, Escape to dismiss
- Escape dismisses popup first; if no popup is open, Escape dismisses the window (innermost-first)
- Positioned via `tk.Text.bbox()` relative to cursor
- Popup uses theme colors (entry_bg background, fg text, accent highlight)

## 5. Theme Presets

5 built-in themes stored as a `THEMES` dict in blip.py:

| Theme | BG | FG | Input BG | Accent | Muted | Error |
|-------|----|----|----------|--------|-------|-------|
| `tokyo-night` (default) | `#1a1b26` | `#a9b1d6` | `#24283b` | `#7aa2f7` | `#565f89` | `#f7768e` |
| `light` | `#faf4ed` | `#575279` | `#f2e9e1` | `#d7827e` | `#9893a5` | `#b4637a` |
| `dracula` | `#282a36` | `#f8f8f2` | `#44475a` | `#bd93f9` | `#6272a4` | `#ff5555` |
| `gruvbox` | `#282828` | `#ebdbb2` | `#3c3836` | `#b8bb26` | `#665c54` | `#fb4934` |
| `mono` | `#0a0a0a` | `#d0d0d0` | `#1a1a1a` | `#d0d0d0` | `#4a4a4a` | `#ff3333` |

Each theme provides: bg, fg, entry_bg, accent (flash border success, autocomplete highlight), muted (footer hints, keybinding hints), error (flash border on save failure).

## 6. Window Size Presets

3 built-in window sizes stored as a `WINDOW_SIZES` dict:

| Preset | Width | Lines | Max Lines |
|--------|-------|-------|-----------|
| `compact` | 320 | 2 | 5 |
| `default` | 400 | 3 | 8 |
| `wide` | 520 | 4 | 10 |

## 7. Error Handling

Builds on Phase 1's logging infrastructure:

- **Config errors:** log + use defaults (never crash on bad config)
- **Empty submit:** whitespace-only text ignored, window stays open
- **Long text:** silently truncate at 10,000 characters
- **Widget height:** clamped between preset min and max lines
- **Tag edge cases:** URL fragments not matched, duplicate smart tags deduplicated

All errors go to existing `~/blip.log` file handler. No new error modalities.

## 8. Architecture

Single-file stays at ~400-450 lines. New additions:

```
blip.py
├── THEMES dict                    # 4 theme color palettes
├── WINDOW_SIZES dict              # 3 window presets  
├── SMART_TAGS dict                # tag → emoji mapping
├── BlipConfig dataclass           # config structure
├── load_config()                  # JSON → BlipConfig
├── parse_smart_tags(text) -> str  # prepend emoji markers
├── class Blip
│   ├── setup_ui()                 # updated: Text widget, footer hints
│   ├── on_key_press()             # Enter saves, Shift+Enter newline
│   ├── show_autocomplete()        # popup on # keystroke
│   ├── hide_autocomplete()        # dismiss popup
│   ├── insert_tag()               # insert selected tag
│   ├── on_submit()                # updated: multi-line + tags
│   ├── append_note()              # updated: indented continuation lines
│   └── (existing methods unchanged)
└── main()                         # updated: load_config, pass to Blip
```

## 9. Testing Plan

11 new tests added to `test_blip.py` (19 total with Phase 1's 8):

| Test | Coverage |
|------|----------|
| `test_load_config_defaults` | No config file → default BlipConfig |
| `test_load_config_partial` | Partial JSON → merged with defaults |
| `test_load_config_malformed` | Bad JSON → warning logged, defaults |
| `test_load_config_unknown_theme` | Unknown theme → falls back to tokyo-night |
| `test_theme_colors` | All 5 themes have valid bg/fg/entry_bg/accent/muted/error |
| `test_window_size_presets` | All 3 sizes have valid width/lines/max_lines |
| `test_parse_tags_smart` | `#todo #urgent` → ☐ 🔴 prefix |
| `test_parse_tags_dedup` | `#todo #todo` → single ☐ prefix |
| `test_parse_tags_url_safe` | URL fragment → no false match |
| `test_multiline_format` | Multi-line → indented continuation lines |
| `test_empty_submit_ignored` | Whitespace-only → not saved |

All tests use `tmp_path` fixtures, no tkinter dependency.

## 10. Migration Notes

- Phase 1's hardcoded colors (BG, FG, ENTRY_BG) replaced by theme system
- Phase 1's hardcoded WINDOW_WIDTH replaced by window_size preset
- `tk.Entry` → `tk.Text` changes the widget API (`.get()`, `.insert()`, `.delete()`)
- Existing `on_submit()` and `append_note()` updated for multi-line format
- Flash border continues to use accent color (success) and error color (failure) from active theme
- `create_tray_icon()` references global `OUTPUT_FILE` — must thread config output_file path through instead
