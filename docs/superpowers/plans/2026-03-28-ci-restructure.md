# Phase 9: CI + Package Restructure — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure CogStash from flat files into `src/cogstash/` package layout, then add GitHub Actions CI with pytest, ruff, and mypy.

**Architecture:** Move 4 source files into `src/cogstash/` as a proper Python package, move 4 test files + conftest.py into `tests/`, rewrite all cross-module imports, add `__init__.py` and `__main__.py`, update pyproject.toml. Then add ruff linting, mypy type checking, and a GitHub Actions CI workflow running on Python 3.9–3.13.

**Tech Stack:** Python 3.9+, setuptools (src layout), pytest, ruff, mypy, GitHub Actions

---

## Task 1: Package Restructure (move files + fix all imports)

**Files:**
- Create: `src/cogstash/__init__.py`, `src/cogstash/__main__.py`
- Move (git mv): all 4 source files → `src/cogstash/`, all 4 test files + conftest → `tests/`
- Modify: all source and test files (import rewiring)
- Modify: `pyproject.toml`

This is a single atomic task — nothing works until all moves + import rewrites are done.

### Step 1: Create directories

```bash
mkdir -p src/cogstash tests
```

### Step 2: Move source files with git mv

```bash
git mv cogstash.py src/cogstash/app.py
git mv cogstash_search.py src/cogstash/search.py
git mv cogstash_browse.py src/cogstash/browse.py
git mv cogstash_cli.py src/cogstash/cli.py
git mv conftest.py tests/conftest.py
git mv test_cogstash.py tests/test_app.py
git mv test_cogstash_search.py tests/test_search.py
git mv test_cogstash_browse.py tests/test_browse.py
git mv test_cogstash_cli.py tests/test_cli.py
```

### Step 3: Create `src/cogstash/__init__.py`

```python
"""CogStash — A global hotkey brain dump."""

from __future__ import annotations


def main():
    """Entry point for the cogstash command."""
    from cogstash.app import main as _main
    _main()
```

### Step 4: Create `src/cogstash/__main__.py`

```python
"""Allow running CogStash with `python -m cogstash`."""

from cogstash import main

main()
```

### Step 5: Fix imports in `src/cogstash/search.py`

No changes needed — `cogstash_search.py` has no cross-module imports. Only stdlib imports.

### Step 6: Fix imports in `src/cogstash/browse.py`

Change line 14:
```python
# OLD
from cogstash import THEMES, DEFAULT_SMART_TAGS, CogStashConfig, platform_font
# NEW
from cogstash.app import THEMES, DEFAULT_SMART_TAGS, CogStashConfig, platform_font
```

Change line 15:
```python
# OLD
from cogstash_search import parse_notes, search_notes, filter_by_tag, mark_done, edit_note, delete_note, DEFAULT_TAG_COLORS, Note
# NEW
from cogstash.search import parse_notes, search_notes, filter_by_tag, mark_done, edit_note, delete_note, DEFAULT_TAG_COLORS, Note
```

### Step 7: Fix imports in `src/cogstash/cli.py`

Change line 14:
```python
# OLD
from cogstash_search import Note, parse_notes, search_notes, edit_note, delete_note
# NEW
from cogstash.search import Note, parse_notes, search_notes, edit_note, delete_note
```

Find and replace ALL lazy imports inside functions (there are several scattered throughout):

```python
# In cmd_add() — change:
from cogstash import append_note_to_file, merge_tags
# To:
from cogstash.app import append_note_to_file, merge_tags

# In cmd_stats() — change:
from cogstash_search import compute_stats
# To:
from cogstash.search import compute_stats

# In _get_valid_themes() — change:
from cogstash import THEMES
# To:
from cogstash.app import THEMES

# In _get_valid_window_sizes() — change:
from cogstash import WINDOW_SIZES
# To:
from cogstash.app import WINDOW_SIZES

# In cli_main() — change:
from cogstash import load_config, merge_tags
# To:
from cogstash.app import load_config, merge_tags
```

### Step 8: Fix imports in `src/cogstash/app.py`

Find the lazy import of `DEFAULT_TAG_COLORS` (inside `merge_tags` function):
```python
# OLD
from cogstash_search import DEFAULT_TAG_COLORS
# NEW
from cogstash.search import DEFAULT_TAG_COLORS
```

Find the lazy import of `BrowseWindow` (inside the browse handler):
```python
# OLD
from cogstash_browse import BrowseWindow
# NEW
from cogstash.browse import BrowseWindow
```

Find the lazy import of `cli_main` in `main()`:
```python
# OLD
from cogstash_cli import cli_main
# NEW
from cogstash.cli import cli_main
```

### Step 9: Fix imports in `tests/test_search.py`

Replace all occurrences of `from cogstash_search import` with `from cogstash.search import`.

These occur in many test functions as local imports. The unique patterns to replace:
```python
# All these need cogstash_search → cogstash.search:
from cogstash_search import parse_notes
from cogstash_search import parse_notes, search_notes
from cogstash_search import parse_notes, filter_by_tag
from cogstash_search import parse_notes, mark_done
from cogstash_search import parse_notes, _note_line_span
from cogstash_search import parse_notes, edit_note
from cogstash_search import parse_notes, delete_note
from cogstash_search import parse_notes, compute_stats
from cogstash_search import compute_stats
```

### Step 10: Fix imports in `tests/test_browse.py`

Replace all occurrences:
```python
# OLD → NEW
from cogstash_browse import BrowseWindow  →  from cogstash.browse import BrowseWindow
from cogstash import CogStashConfig  →  from cogstash.app import CogStashConfig
from cogstash_search import edit_note, parse_notes  →  from cogstash.search import edit_note, parse_notes
from cogstash_search import delete_note, parse_notes  →  from cogstash.search import delete_note, parse_notes
```

### Step 11: Fix imports in `tests/test_cli.py`

Replace all occurrences:
```python
# All cogstash_cli imports become cogstash.cli:
from cogstash_cli import format_note  →  from cogstash.cli import format_note
from cogstash_cli import cmd_recent  →  from cogstash.cli import cmd_recent
from cogstash_cli import cmd_search  →  from cogstash.cli import cmd_search
from cogstash_cli import cmd_tags  →  from cogstash.cli import cmd_tags
from cogstash_cli import hex_to_ansi  →  from cogstash.cli import hex_to_ansi
from cogstash_cli import cmd_add  →  from cogstash.cli import cmd_add
from cogstash_cli import cmd_edit  →  from cogstash.cli import cmd_edit
from cogstash_cli import cmd_delete  →  from cogstash.cli import cmd_delete
from cogstash_cli import cmd_export  →  from cogstash.cli import cmd_export
from cogstash_cli import cmd_stats  →  from cogstash.cli import cmd_stats
from cogstash_cli import cmd_config  →  from cogstash.cli import cmd_config

# All cogstash imports (CogStashConfig) become cogstash.app:
from cogstash import CogStashConfig  →  from cogstash.app import CogStashConfig

# cogstash_search imports:
from cogstash_search import Note  →  from cogstash.search import Note
```

### Step 12: Fix imports in `tests/test_app.py`

Replace all occurrences:
```python
# Module alias:
import cogstash as cogstash_mod  →  import cogstash.app as cogstash_mod

# Named imports:
from cogstash import platform_font  →  from cogstash.app import platform_font
from cogstash import THEMES  →  from cogstash.app import THEMES
from cogstash import WINDOW_SIZES  →  from cogstash.app import WINDOW_SIZES
from cogstash import load_config, CogStashConfig  →  from cogstash.app import load_config, CogStashConfig
from cogstash import load_config  →  from cogstash.app import load_config
from cogstash import parse_smart_tags  →  from cogstash.app import parse_smart_tags
from cogstash import merge_tags, DEFAULT_SMART_TAGS, CogStashConfig  →  from cogstash.app import merge_tags, DEFAULT_SMART_TAGS, CogStashConfig
from cogstash import merge_tags, CogStashConfig  →  from cogstash.app import merge_tags, CogStashConfig
from cogstash import append_note_to_file  →  from cogstash.app import append_note_to_file
from cogstash_search import DEFAULT_TAG_COLORS  →  from cogstash.search import DEFAULT_TAG_COLORS
```

### Step 13: Update `pyproject.toml`

Replace entire contents with:
```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "cogstash"
version = "0.1.0"
description = "A global hotkey brain dump — press, type, gone."
readme = "README.md"
requires-python = ">=3.9"
dependencies = [
    "pynput>=1.7",
    "pystray>=0.19",
    "Pillow>=9.0",
]

[project.optional-dependencies]
dev = ["pytest>=7.0", "ruff>=0.4", "mypy>=1.10"]

[project.scripts]
cogstash = "cogstash:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["tests"]
```

### Step 14: Clean up stale artifacts

```bash
# Remove old egg-info and __pycache__ that reference old flat layout
rm -rf cogstash.egg-info __pycache__ build
```

### Step 15: Reinstall in editable mode

```bash
pip install -e ".[dev]"
```

### Step 16: Run full test suite

```bash
python -m pytest tests/ -v
```

Expected: All 98 tests PASS.

### Step 17: Commit

```bash
git add -A
git commit -m "refactor: restructure into src/cogstash/ package layout

Move source files to src/cogstash/ (app, search, browse, cli),
tests to tests/, add __init__.py and __main__.py, update all
cross-module imports, and switch pyproject.toml to src layout."
```

---

## Task 2: Add Ruff Linting

**Files:**
- Modify: `pyproject.toml` (add ruff config)
- Modify: any source/test files that fail linting

**Depends on:** Task 1

### Step 1: Add ruff config to pyproject.toml

Append to end of `pyproject.toml`:

```toml
[tool.ruff]
target-version = "py39"
line-length = 120

[tool.ruff.lint]
select = ["E", "F", "W", "I"]
ignore = ["E501"]  # long formatted strings in CLI output
```

### Step 2: Run ruff and fix issues

```bash
ruff check src/ tests/ --fix
```

If ruff auto-fixes import sorting or removes unused imports, review the changes. Then:

```bash
ruff check src/ tests/
```

Expected: No remaining errors.

### Step 3: Fix any remaining issues manually

Address any issues ruff cannot auto-fix. Common ones:
- F841: assigned but never used
- E711: comparison to None (use `is None`)
- I001: import sorting

### Step 4: Commit

```bash
git add -A
git commit -m "style: add ruff linting configuration and fix lint issues"
```

---

## Task 3: Add Mypy Type Checking

**Files:**
- Modify: `pyproject.toml` (add mypy config)
- Modify: any source files that fail type checking

**Depends on:** Task 1

### Step 1: Add mypy config to pyproject.toml

Append to end of `pyproject.toml`:

```toml
[tool.mypy]
python_version = "3.9"
warn_return_any = true
warn_unused_configs = true
ignore_missing_imports = true
```

`ignore_missing_imports` is needed because pynput, pystray, and Pillow lack complete type stubs.

### Step 2: Run mypy

```bash
mypy src/cogstash/
```

### Step 3: Fix any type errors

Common issues to expect:
- `dict` annotations without type params (use `dict[str, str]` etc.)
- Functions missing return type annotations in public API
- `Path | None` syntax (use `Optional[Path]` for Python 3.9 compat — but we use `from __future__ import annotations` so the `|` syntax should work)

Fix issues in source files. Do NOT add type stubs for third-party packages.

### Step 4: Verify

```bash
mypy src/cogstash/
python -m pytest tests/ -v
```

Both should pass clean.

### Step 5: Commit

```bash
git add -A
git commit -m "chore: add mypy type checking configuration and fix type issues"
```

---

## Task 4: Add GitHub Actions CI Workflow

**Files:**
- Create: `.github/workflows/ci.yml`
- Modify: `requirements.txt` (clean up — runtime only)

**Depends on:** Tasks 2, 3

### Step 1: Update requirements.txt (runtime deps only)

Ensure `requirements.txt` contains only:
```
pynput>=1.7
pystray>=0.19
Pillow>=9.0
```

Remove `pytest>=7.0` if it's still there (dev deps are now in pyproject.toml extras).

### Step 2: Create `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - run: pip install -e ".[dev]"
      - run: ruff check src/ tests/
      - run: mypy src/cogstash/

  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.9", "3.10", "3.11", "3.12", "3.13"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install system dependencies
        run: sudo apt-get update && sudo apt-get install -y xvfb
      - run: pip install -e ".[dev]"
      - name: Run tests
        run: xvfb-run python -m pytest tests/ -v
```

### Step 3: Verify workflow syntax

```bash
python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))" 2>/dev/null || echo "Install pyyaml to verify"
```

Or just visually confirm the YAML is valid.

### Step 4: Run tests locally one final time

```bash
python -m pytest tests/ -v
ruff check src/ tests/
mypy src/cogstash/
```

All should pass.

### Step 5: Commit and push

```bash
git add -A
git commit -m "ci: add GitHub Actions workflow with pytest, ruff, and mypy

Runs on push to main and PRs. Test matrix covers Python 3.9-3.13
on Ubuntu with xvfb for tkinter headless testing."
git push
```

### Step 6: Verify CI run

Check GitHub Actions to confirm the workflow triggers and passes on all Python versions.
