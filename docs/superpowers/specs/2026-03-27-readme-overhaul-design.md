# Phase 5: README Overhaul — Design Spec

**Goal:** Replace the stale 73-line README with a comprehensive ~250-line document that covers all current features.

**Scope:** README.md only. No code changes.

## Sections (in order)

### 1. Header
- `# CogStash ⚡` title
- One-liner tagline: "A global hotkey brain dump — press, type, gone."
- Screenshot placeholder (`<!-- screenshot -->` comment with text)

### 2. Features
- Bullet list covering: global hotkey capture, smart tags with autocomplete, 5 themes, browse window, CLI commands, system tray, cross-platform

### 3. Requirements
- Python 3.9+, tkinter, pynput
- Note: pystray + Pillow installed automatically via pip

### 4. Installation
- `git clone` + `pip install -r requirements.txt`
- Or `pip install .` for CLI entry point

### 5. Quick Start
- `python cogstash.py` or `cogstash` (if pip-installed)
- Hotkey table: Ctrl+Shift+Space (open), Enter (save), Shift+Enter (newline), Escape (dismiss)
- Note format example with timestamp

### 6. Smart Tags
- Table of 4 tags: #todo (☐), #urgent (🔴), #important (⭐), #idea (💡)
- Mention autocomplete: type `#` to trigger suggestions

### 7. CLI Commands
- `cogstash recent [--limit N]` — show latest N notes (default 20)
- `cogstash search "query" [--limit N]` — full-text search
- `cogstash tags` — list all tags with counts
- Include example output for each

### 8. Browse Window
- Describe: open via tray icon → "Browse Notes"
- Features: card view, live search, tag filter pills, mark-done for #todo, date headers
- Screenshot placeholder

### 9. Themes
- Table of 5 themes: tokyo-night (default), light, dracula, gruvbox, mono
- Window sizes: compact, default, wide

### 10. Configuration
- Config file: `~/.cogstash.json`
- Table of all 5 keys with defaults:
  - hotkey: `<ctrl>+<shift>+<space>`
  - output_file: `~/cogstash.md`
  - log_file: `~/cogstash.log`
  - theme: `tokyo-night`
  - window_size: `default`
- Example JSON snippet

### 11. Cross-Platform Notes
- Windows/macOS/Linux file paths
- macOS accessibility permission note

### 12. License
- Placeholder or "MIT" if applicable

## Constraints
- No roadmap/future features section
- Screenshot sections use `<!-- TODO: add screenshot -->` placeholders
- Keep note format examples consistent with actual parser output
- All CLI examples must match real argument names from build_parser()
