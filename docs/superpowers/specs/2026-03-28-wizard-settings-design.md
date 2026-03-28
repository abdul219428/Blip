# Phase 11: First-Run Wizard & Settings Window — Design Spec

## Goal

Add a graphical first-run wizard (shown on first launch when no config file exists) and a persistent Settings window (accessible from tray menu) so users can configure CogStash without editing JSON. Include a "What's New" dialog shown once per version upgrade.

## Current State

- Config stored in `~/.cogstash.json`, created with defaults on first launch
- `CogStashConfig` dataclass: hotkey, output_file, log_file, theme, window_size, tags
- `load_config()` reads JSON, merges with defaults, validates
- 5 themes (`THEMES` dict), 3 window sizes (`WINDOW_SIZES` dict)
- Custom tags with emoji + hex color (`config.tags`)
- CLI wizard exists (`cogstash config` in cli.py) — text-based only
- Tray menu: "Open notes", "Browse Notes", "Quit"
- No GUI configuration, no onboarding, no version upgrade notification
- 100 tests passing, CI green

## Design

### 1. New Module: `src/cogstash/settings.py`

All wizard, settings, and What's New UI lives in a **new module** `settings.py`. This keeps `app.py` focused on the capture window and avoids growing it further.

- `settings.py` imports from `app.py` at module level (like `browse.py` does)
- `app.py` lazy-imports `settings.py` (like it lazy-imports `browse.py`)
- `settings.py` is pure GUI — no data logic (data ops use `app.py` helpers)

### 2. Config Additions

Add these fields to `CogStashConfig` and `load_config()`:

```python
@dataclass
class CogStashConfig:
    # ... existing fields ...
    launch_at_startup: bool = False
    last_seen_version: str = ""
```

**`launch_at_startup`**: Whether to auto-start on login. Platform-specific:
- Windows: Creates/removes a shortcut in `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\`
- macOS/Linux: Documented as manual (no auto-registration in v1)

**`last_seen_version`**: Tracks the last version the user saw. If current `__version__` differs, show the What's New dialog.

**Config JSON additions:**
```json
{
  "launch_at_startup": false,
  "last_seen_version": "0.1.0"
}
```

### 3. First-Run Wizard

**Trigger:** `load_config()` creates a new config file (i.e., no `~/.cogstash.json` existed). The `main()` function in `app.py` detects this and shows the wizard before entering the main loop.

**Detection:** `load_config()` returns a tuple `(config, is_new)` where `is_new=True` when the file was just created. Alternatively, add a sentinel: if `last_seen_version == ""`, it's a first run.

**Chosen approach:** Check `config.last_seen_version == ""` — simpler, no API change to `load_config()`.

**5 Pages (step-by-step, Next/Back navigation):**

#### Page 1: Welcome
- CogStash branding + tagline
- Notes file path (text entry with Browse button, default `~/cogstash.md`)
- Hotkey display (read-only in v1 — hotkey editing is complex)
- "Next" button

#### Page 2: Theme & Size
- 5 theme swatches arranged in a grid (clickable)
- Selected theme has a highlight border
- 3 window size options (compact/default/wide) as radio buttons
- **Live preview**: Changing theme updates the wizard's own colors
- "Back" / "Next" buttons

#### Page 3: Tags
- List of built-in tags (todo, urgent, important, idea) — shown but not removable
- Section for custom tags: Add button opens inline fields (name, emoji, hex color)
- Remove button (X) for custom tags
- "Back" / "Next" buttons

#### Page 4: Quick Tour
- 3 tutorial cards explaining key features:
  1. **Capture**: Press hotkey → type → Enter to save
  2. **Browse**: Right-click tray → Browse Notes (or use browse hotkey)
  3. **CLI**: `cogstash recent`, `cogstash search`, `cogstash tags`
- Each card has an icon/emoji and brief text
- "Back" / "Next" buttons

#### Page 5: Done
- Summary of chosen settings
- "Start Using CogStash" button → saves config, closes wizard, starts normal app

**Implementation:** `WizardWindow` class using `tk.Toplevel`. Each page is a `tk.Frame` that gets packed/unpacked. Shared footer with Back/Next/page indicator dots.

### 4. Settings Window

**Trigger:** Tray menu → "Settings" (new menu item). Also accessible as queue message `"SETTINGS"`.

**Implementation:** `SettingsWindow` class using `tk.Toplevel`. Tab-based layout using a custom tab bar (styled Labels that act as tab buttons — not ttk.Notebook, to match CogStash's custom look).

#### General Tab
- **Hotkey**: Display current hotkey (read-only label + info text "edit in ~/.cogstash.json")
- **Notes file**: Text entry + Browse button (file dialog)
- **Launch at startup**: Checkbox (Windows-only in v1)
- Apply happens on Save; a "Save" button at the bottom

#### Appearance Tab
- **Theme**: 5 clickable swatches (same as wizard), selected has border
- **Window size**: 3 radio buttons (compact/default/wide)
- **Live preview**: Changing theme updates the settings window colors immediately
- Save button

#### Tags Tab
- **Built-in tags**: Listed with emoji, label "Built-in" badge (non-editable)
- **Custom tags**: Listed with emoji + color swatch + Remove (X) button
- **Add tag**: Button reveals inline form (name, emoji text field, color hex field)
- Save button

#### About Tab
- **Version**: `CogStash v{__version__}`
- **Links**: GitHub repo, Open notes file, Open config file
- **Credits**: "Built with Python, tkinter, pynput, pystray"

**Behavior:**
- Only one Settings window at a time (if already open, focus it)
- Closing settings window: if unsaved changes, ask to save/discard
- After saving, config is written to `~/.cogstash.json`
- Theme/window_size changes require restart to take full effect (show info label)
- Tag changes take effect on next note save (no restart needed)

### 5. What's New Dialog

**Trigger:** On app start, after loading config, if `config.last_seen_version != __version__` and `config.last_seen_version != ""` (skip on first run — wizard handles that).

**Implementation:** `WhatsNewDialog` class using `tk.Toplevel`. Simple modal dialog.

**Content structure:**
```python
WHATS_NEW = {
    "0.2.0": {
        "title": "CogStash 0.2.0",
        "items": [
            ("new", "First-run wizard for easy setup"),
            ("new", "Settings window (tray → Settings)"),
            ("improved", "Live theme preview"),
            ("fixed", "..."),
        ]
    }
}
```

Each item has a badge type (`new`=green, `improved`=blue, `fixed`=orange) and text.

**Behavior:**
- Shown once per version (after showing, `last_seen_version` is updated in config)
- "Got it" button closes the dialog
- Non-blocking (not truly modal — lets you use the app while it's open)

### 6. Tray Menu Update

Add "Settings" item to tray menu:

```python
menu = pystray.Menu(
    pystray.MenuItem("CogStash ⚡", None, enabled=False),
    pystray.Menu.SEPARATOR,
    pystray.MenuItem(f"Open {config.output_file.name}", lambda: open_notes()),
    pystray.MenuItem("Browse Notes", lambda: browse_notes()),
    pystray.MenuItem("Settings", lambda: open_settings()),  # NEW
    pystray.Menu.SEPARATOR,  # NEW
    pystray.MenuItem("Quit", quit_app),
)
```

`open_settings()` puts `"SETTINGS"` on `app_queue`. `poll_queue()` handles it by calling `self._open_settings()`.

### 7. App Startup Flow

```
main()
  → load_config()
  → create root Tk
  → is first run? (last_seen_version == "")
      YES → show WizardWindow (blocking-ish: wizard calls root.wait_window)
           → wizard saves config, updates last_seen_version
      NO  → version changed? (last_seen_version != __version__)
           YES → show WhatsNewDialog (non-blocking)
                → update last_seen_version in config
  → update last_seen_version = __version__ (save to config)
  → create CogStash app
  → create tray icon
  → mainloop
```

### 8. Theming the New Windows

All new windows use the existing `THEMES` dict for colors. The helper `platform_font()` is reused. New windows follow the same pattern as `BrowseWindow`:
- `tk.Toplevel` with `overrideredirect(False)` (standard window chrome)
- Background from `theme["bg"]`
- Text from `theme["fg"]`
- Input fields from `theme["entry_bg"]`
- Accent for highlights/selections from `theme["accent"]`
- Muted for secondary text from `theme["muted"]`

### 9. File Changes

**New files:**
- `src/cogstash/settings.py` — WizardWindow, SettingsWindow, WhatsNewDialog
- `tests/test_settings.py` — Unit tests

**Modified files:**
- `src/cogstash/app.py`:
  - Add `launch_at_startup` and `last_seen_version` to `CogStashConfig`
  - Update `load_config()` to handle new fields
  - Add "Settings" to tray menu
  - Add `"SETTINGS"` handler in `poll_queue()`
  - Add `_open_settings()` method to `CogStash`
  - Update `main()` startup flow (wizard/what's-new detection)
- `src/cogstash/__init__.py`:
  - No changes (entry point unchanged)

### 10. Testing Plan

New tests in `tests/test_settings.py`:

| Test | Coverage |
|------|----------|
| `test_config_new_fields_defaults` | `launch_at_startup=False`, `last_seen_version=""` in fresh config |
| `test_config_new_fields_roundtrip` | Write and read back new fields through load_config |
| `test_first_run_detection` | `last_seen_version==""` means first run |
| `test_whats_new_detection` | `last_seen_version != __version__` triggers what's new |
| `test_whats_new_skip_first_run` | Don't show What's New on first run (wizard instead) |
| `test_settings_queue_message` | `"SETTINGS"` message in queue opens settings |
| `test_tray_menu_has_settings` | Tray menu includes "Settings" item |
| `test_wizard_saves_config` | Wizard writes valid config with all fields |
| `test_save_config_helper` | `save_config()` writes JSON correctly |
| `test_launch_at_startup_windows` | Startup shortcut creation/removal (Windows) |

GUI tests (wizard pages, settings tabs, what's new dialog) use `@needs_display` marker and test widget creation/basic interaction, not pixel-perfect rendering.
