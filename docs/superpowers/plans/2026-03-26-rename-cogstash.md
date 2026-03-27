# Rename Blip → CogStash Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rename the entire project from "Blip" to "CogStash" (Cognitive Stash) — all files, classes, strings, config, docs.

**Architecture:** This is a mechanical rename across ~120 occurrences in 8 source files + README + pyproject.toml. Git `mv` preserves history for file renames. The docs/ directory contains historical specs/plans that reference "blip" but should NOT be renamed (they are historical artifacts).

**Tech Stack:** Python, git mv, pytest

**Rename Mapping:**

| Old | New |
|---|---|
| `blip.py` | `cogstash.py` |
| `blip_search.py` | `cogstash_search.py` |
| `blip_browse.py` | `cogstash_browse.py` |
| `test_blip.py` | `test_cogstash.py` |
| `test_blip_search.py` | `test_cogstash_search.py` |
| `test_blip_browse.py` | `test_cogstash_browse.py` |
| `Blip` (class) | `CogStash` (class) |
| `BlipConfig` (class) | `CogStashConfig` (class) |
| `blip.md` (notes file) | `cogstash.md` |
| `blip.log` (log file) | `cogstash.log` |
| `.blip.json` (config) | `.cogstash.json` |
| `"blip"` (logger name) | `"cogstash"` |
| `"Blip ⚡"` (tray/UI) | `"CogStash ⚡"` |
| `"Blip — Browse Notes"` | `"CogStash — Browse Notes"` |
| `"Blip is running..."` | `"CogStash is running..."` |
| `"Blip stopped."` | `"CogStash stopped."` |

**What NOT to rename:**
- `docs/superpowers/` — historical specs/plans, leave as-is
- `venv/`, `__pycache__/`, `.git/` — ignored

---

### Task 1: Rename files with git mv

**Files:**
- Rename: `blip.py` → `cogstash.py`
- Rename: `blip_search.py` → `cogstash_search.py`
- Rename: `blip_browse.py` → `cogstash_browse.py`
- Rename: `test_blip.py` → `test_cogstash.py`
- Rename: `test_blip_search.py` → `test_cogstash_search.py`
- Rename: `test_blip_browse.py` → `test_cogstash_browse.py`

- [ ] **Step 1: Create feature branch**

```bash
git checkout -b rename/cogstash
```

- [ ] **Step 2: Rename all 6 files with git mv**

```bash
git mv blip.py cogstash.py
git mv blip_search.py cogstash_search.py
git mv blip_browse.py cogstash_browse.py
git mv test_blip.py test_cogstash.py
git mv test_blip_search.py test_cogstash_search.py
git mv test_blip_browse.py test_cogstash_browse.py
```

- [ ] **Step 3: Commit file renames only**

```bash
git add -A
git commit -m "rename: git mv blip*.py → cogstash*.py"
```

This separate commit preserves git's rename detection for `git log --follow`.

---

### Task 2: Update cogstash.py (main app)

**Files:**
- Modify: `cogstash.py`

All string/class/config references inside the main app file.

- [ ] **Step 1: Update module docstring**

Old:
```python
"""
blip.py — A global hotkey brain dump — press, type, gone.
Hotkey: Ctrl + Shift + Space
Enter  → appends timestamped note to blip.md
Escape → hides window
"""
```

New:
```python
"""
cogstash.py — A global hotkey brain dump — press, type, gone.
Hotkey: Ctrl + Shift + Space
Enter  → appends timestamped note to cogstash.md
Escape → hides window
"""
```

- [ ] **Step 2: Update file path constants**

Old:
```python
OUTPUT_FILE = Path.home() / "blip.md"
LOG_FILE    = Path.home() / "blip.log"
```

New:
```python
OUTPUT_FILE = Path.home() / "cogstash.md"
LOG_FILE    = Path.home() / "cogstash.log"
```

- [ ] **Step 3: Update logger name**

Old: `logger = logging.getLogger("blip")`
New: `logger = logging.getLogger("cogstash")`

- [ ] **Step 4: Rename BlipConfig → CogStashConfig**

Replace class definition:
```python
class CogStashConfig:
```

Update `__post_init__` defaults:
```python
        if self.output_file is None:
            self.output_file = Path.home() / "cogstash.md"
        if self.log_file is None:
            self.log_file = Path.home() / "cogstash.log"
```

- [ ] **Step 5: Update load_config function**

Update signature: `def load_config(config_path: Path) -> CogStashConfig:`

Update defaults dict:
```python
    defaults = {
        "output_file": str(Path.home() / "cogstash.md"),
        "log_file": str(Path.home() / "cogstash.log"),
```

Update all `BlipConfig` → `CogStashConfig` (3 return statements in load_config).

Update config file path in main():
```python
config = load_config(Path.home() / ".cogstash.json")
```

- [ ] **Step 6: Rename Blip class → CogStash**

```python
class CogStash:
    def __init__(self, root: tk.Tk, config: CogStashConfig):
```

- [ ] **Step 7: Update create_tray_icon signature and strings**

```python
def create_tray_icon(app_queue: queue.Queue, config: CogStashConfig) -> None:
```

Update tray strings:
```python
        pystray.MenuItem("CogStash ⚡", None, enabled=False),
```
```python
    icon = pystray.Icon("cogstash", img, "CogStash", menu)
```

- [ ] **Step 8: Update UI label**

Old: `frame, text="⚡  Blip", bg=t["bg"], fg=t["fg"],`
New: `frame, text="⚡  CogStash", bg=t["bg"], fg=t["fg"],`

- [ ] **Step 9: Update _open_browse import**

Old: `from blip_browse import BrowseWindow`
New: `from cogstash_browse import BrowseWindow`

- [ ] **Step 10: Update main() strings**

Old:
```python
print(f"Blip is running. ({config.hotkey} to capture · Ctrl+C to quit)")
```
New:
```python
print(f"CogStash is running. ({config.hotkey} to capture · Ctrl+C to quit)")
```

Old: `app = Blip(root, config)`
New: `app = CogStash(root, config)`

Old: `print("\nBlip stopped.")`
New: `print("\nCogStash stopped.")`

- [ ] **Step 11: Commit**

```bash
git add cogstash.py
git commit -m "rename: update all references in cogstash.py"
```

---

### Task 3: Update cogstash_search.py and cogstash_browse.py

**Files:**
- Modify: `cogstash_search.py`
- Modify: `cogstash_browse.py`

- [ ] **Step 1: Update cogstash_search.py docstrings**

Old:
```python
"""blip_search.py — Note parsing, search, and filtering logic.

Pure functions with no tkinter dependency. Used by blip_browse.py
for the Browse Window and potentially CLI tools in the future.
"""
```

New:
```python
"""cogstash_search.py — Note parsing, search, and filtering logic.

Pure functions with no tkinter dependency. Used by cogstash_browse.py
for the Browse Window and potentially CLI tools in the future.
"""
```

Old: `"""Parse blip.md into a list of Note objects."""`
New: `"""Parse cogstash.md into a list of Note objects."""`

- [ ] **Step 2: Update cogstash_browse.py**

Old docstring:
```python
"""blip_browse.py — Browse Window for viewing and filtering past notes.

Card-view UI with search, tag filtering, and mark-done for #todo items.
Opened from the system tray icon. Uses blip_search for all data operations.
"""
```

New:
```python
"""cogstash_browse.py — Browse Window for viewing and filtering past notes.

Card-view UI with search, tag filtering, and mark-done for #todo items.
Opened from the system tray icon. Uses cogstash_search for all data operations.
"""
```

Update imports:
Old:
```python
from blip import THEMES, SMART_TAGS, BlipConfig, platform_font
from blip_search import parse_notes, search_notes, filter_by_tag, mark_done, TAG_COLORS, Note
```

New:
```python
from cogstash import THEMES, SMART_TAGS, CogStashConfig, platform_font
from cogstash_search import parse_notes, search_notes, filter_by_tag, mark_done, TAG_COLORS, Note
```

Update class references:
Old: `def __init__(self, root: tk.Tk, config: BlipConfig):`
New: `def __init__(self, root: tk.Tk, config: CogStashConfig):`

Update window title:
Old: `self.window.title("Blip — Browse Notes")`
New: `self.window.title("CogStash — Browse Notes")`

- [ ] **Step 3: Commit**

```bash
git add cogstash_search.py cogstash_browse.py
git commit -m "rename: update references in cogstash_search.py and cogstash_browse.py"
```

---

### Task 4: Update all test files

**Files:**
- Modify: `test_cogstash.py`
- Modify: `test_cogstash_search.py`
- Modify: `test_cogstash_browse.py`

- [ ] **Step 1: Update test_cogstash.py**

Docstring: `"""Tests for cogstash.py."""`

Replace ALL occurrences:
- `from blip import` → `from cogstash import`
- `import blip as blip_mod` → `import cogstash as cogstash_mod`
- `blip_mod.Blip(` → `cogstash_mod.CogStash(`
- `blip_mod.BlipConfig(` → `cogstash_mod.CogStashConfig(`
- `BlipConfig` → `CogStashConfig` (in string literals and assertions too)
- `tmp_path / "blip.md"` → `tmp_path / "cogstash.md"` (in test temp files — these are test fixtures, keep consistent)
- `tmp_path / "blip.json"` → `tmp_path / "cogstash.json"`

- [ ] **Step 2: Update test_cogstash_search.py**

Docstring: `"""Tests for cogstash_search.py — note parsing and search logic."""`

Replace ALL occurrences:
- `from blip_search import` → `from cogstash_search import`
- `tmp_path / "blip.md"` → `tmp_path / "cogstash.md"`
- `blip.md` in docstrings → `cogstash.md`

- [ ] **Step 3: Update test_cogstash_browse.py**

Docstring: `"""Tests for cogstash_browse.py — Browse Window UI."""`

Replace ALL occurrences:
- `from blip_browse import` → `from cogstash_browse import`
- `from blip import BlipConfig` → `from cogstash import CogStashConfig`
- `BlipConfig(` → `CogStashConfig(`
- `tmp_path / "blip.md"` → `tmp_path / "cogstash.md"`

- [ ] **Step 4: Run all tests**

```bash
python -m pytest test_cogstash.py test_cogstash_search.py test_cogstash_browse.py -v
```

Expected: All 34 tests PASS (or 31 pass + 3 skip on headless).

- [ ] **Step 5: Commit**

```bash
git add test_cogstash.py test_cogstash_search.py test_cogstash_browse.py
git commit -m "rename: update all test files for CogStash"
```

---

### Task 5: Update pyproject.toml and README.md

**Files:**
- Modify: `pyproject.toml`
- Modify: `README.md`

- [ ] **Step 1: Update pyproject.toml**

```toml
[project]
name = "cogstash"
version = "0.1.0"
description = "A global hotkey brain dump — press, type, gone."
```

```toml
[tool.setuptools]
py-modules = ["cogstash", "cogstash_search", "cogstash_browse"]
[project.scripts]
cogstash = "cogstash:main"
```

- [ ] **Step 2: Update README.md**

Replace heading: `# CogStash ⚡`

Replace all `blip.md` → `cogstash.md` references.

Replace `blip.py` → `cogstash.py`.

Replace `python blip.py` → `python cogstash.py`.

Replace `blip` CLI command → `cogstash`.

Replace clone URL and cd: update repo reference if needed, or leave as-is (repo hasn't been renamed on GitHub).

Replace config table: `~/blip.md` → `~/cogstash.md`.

Replace `Blip runs on` → `CogStash runs on`.

Replace constants reference: `Edit the constants at the top of cogstash.py`.

- [ ] **Step 3: Run all tests one final time**

```bash
python -m pytest test_cogstash.py test_cogstash_search.py test_cogstash_browse.py -v
```

Expected: All 34 tests PASS.

- [ ] **Step 4: Verify imports**

```bash
python -c "from cogstash_search import parse_notes, search_notes, filter_by_tag, mark_done, TAG_COLORS, Note; print('cogstash_search OK')"
python -c "from cogstash_browse import BrowseWindow; print('cogstash_browse OK')"
python -c "from cogstash import CogStash, CogStashConfig, THEMES, SMART_TAGS, platform_font; print('cogstash OK')"
```

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml README.md
git commit -m "rename: update pyproject.toml and README.md for CogStash"
```

---

## Task Dependency Graph

```
Task 1 (file renames)
  └── Task 2 (cogstash.py content)
  └── Task 3 (search + browse content)
  └── Task 4 (test content + verify)
        └── Task 5 (pyproject + README + final verify)
```

Tasks 2 and 3 can run after Task 1 but must complete before Task 4 (tests import from renamed modules). Task 5 is last.
