# CLI/UI Split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split CogStash into `core`, `cli`, and `ui` layers, ship a dedicated CLI executable, and keep the Windows installer UI-first while installing both binaries.

**Architecture:** Introduce `src/cogstash/core`, `src/cogstash/cli`, and `src/cogstash/ui` as explicit subpackages, then migrate shared logic behind `core` while converting CLI and UI code to depend on it. Keep the refactor incremental with compatibility wrappers where needed so tests stay green throughout, then update build/release/installer wiring after the runtime boundaries are already proven.

**Tech Stack:** Python 3.9+, tkinter, pynput, pystray, Pillow, pytest, ruff, mypy, uv, PyInstaller, GitHub Actions, Inno Setup

**Spec:** `docs/superpowers/specs/2026-04-03-cli-ui-split-design.md`

---

## File Structure Map

**New packages**

- Create: `src/cogstash/core/__init__.py` — public shared API exports
- Create: `src/cogstash/core/config.py` — `CogStashConfig`, config path/defaults, load/save helpers
- Create: `src/cogstash/core/notes.py` — `Note`, parse/search/filter/edit/delete/mark-done/stats helpers, append/tag helpers
- Create: `src/cogstash/core/output.py` — shared safe output helpers moved from `_output.py`
- Create: `src/cogstash/cli/__init__.py` — public CLI API preserving `from cogstash.cli import ...`
- Create: `src/cogstash/cli/main.py` — CLI command handlers and dispatcher logic moved from current `cli.py`
- Create: `src/cogstash/cli/formatting.py` — terminal formatting/color helpers if `main.py` becomes too large
- Create: `src/cogstash/cli/windows.py` — Windows console-preparation helpers for terminal execution
- Create: `src/cogstash/cli/__main__.py` — dedicated CLI executable/bootstrap entry
- Create: `src/cogstash/ui/__init__.py` — UI package exports
- Create: `src/cogstash/ui/app.py` — main tkinter app logic moved from current `app.py`
- Create: `src/cogstash/ui/browse.py` — browse window logic moved from current `browse.py`
- Create: `src/cogstash/ui/settings.py` — settings/wizard dialogs moved from current `settings.py`
- Create: `src/cogstash/ui/windows.py` — UI-specific Windows helpers such as single-instance handling if kept separate
- Create: `src/cogstash/ui/__main__.py` — dedicated UI bootstrap entry

**Compatibility shims to keep imports stable during migration**

- Modify: `src/cogstash/app.py` — thin re-export/wrapper to `cogstash.ui.app`
- Modify: `src/cogstash/browse.py` — thin re-export/wrapper to `cogstash.ui.browse`
- Modify: `src/cogstash/settings.py` — thin re-export/wrapper to `cogstash.ui.settings`
- Modify: `src/cogstash/search.py` — thin re-export/wrapper to `cogstash.core.notes`
- Modify: `src/cogstash/_output.py` — thin re-export/wrapper to `cogstash.core.output`
- Modify: `src/cogstash/_windows.py` — thin re-export/wrapper or compatibility aliases during migration
- Replace: `src/cogstash/cli.py` with package directory `src/cogstash/cli/`

**Bootstrap/build/release**

- Modify: `src/cogstash/__main__.py` — stop acting as the dual CLI/UI dispatcher; make it explicitly delegate to UI or a narrow compatibility path
- Modify: `src/cogstash/__init__.py` — keep version/bootstrap behavior aligned with new entrypoints
- Modify: `scripts/build.py` — support `--target ui|cli|both` with target-specific entry files and hidden imports
- Modify: `.github/workflows/release.yml` — build/upload both UI and CLI artifacts
- Modify: `.github/workflows/ci.yml` — add CLI-entry smoke coverage if needed
- Modify: `scripts/build_installer.py` — stage/install both UI and CLI executables
- Modify: `installer/windows/CogStash.iss` — install both executables, keep only UI shortcuts
- Modify: `README.md` — explain new CLI executable and release artifacts

**Tests**

- Create: `tests/core/test_config.py`
- Create: `tests/core/test_notes.py`
- Create: `tests/core/test_output.py`
- Create: `tests/cli/conftest.py`
- Create: `tests/cli/test_main.py`
- Create: `tests/cli/test_import_boundary.py`
- Create: `tests/ui/conftest.py`
- Create: `tests/ui/test_app.py`
- Create: `tests/ui/test_browse.py`
- Create: `tests/ui/test_settings.py`
- Modify: `tests/conftest.py` — reduce to shared non-UI fixtures only
- Modify: `tests/test_build_installer.py` — assert dual-executable installer behavior

**Entrypoint matrix**

- `cogstash` console script in `pyproject.toml` -> CLI entrypoint
- `python -m cogstash` -> keep source/developer compatibility by delegating to the UI bootstrap unless explicitly redefined in the implementation review
- packaged `CogStash.exe` / platform-equivalent -> UI application
- packaged `CogStash-CLI.exe` / platform-equivalent -> CLI application

**Artifact matrix**

- UI target -> keep current onefile + onedir outputs
- CLI target -> onefile output only
- Windows installer -> stage UI onedir payload + stable versionless CLI executable in the install directory

---

### Task 1: Add boundary tests and package skeletons

**Files:**
- Create: `src/cogstash/core/__init__.py`
- Create: `src/cogstash/cli/__init__.py`
- Create: `src/cogstash/ui/__init__.py`
- Create: `tests/cli/test_import_boundary.py`
- Create: `tests/core/test_notes.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write the failing CLI import-boundary test**

Create `tests/cli/test_import_boundary.py`:

```python
from __future__ import annotations

import subprocess
import sys


def test_cogstash_cli_imports_without_gui_dependencies(tmp_path):
    script = tmp_path / "import_cli.py"
    script.write_text(
        "import builtins\n"
        "blocked = {'tkinter', 'pystray', 'PIL', 'Pillow'}\n"
        "orig = builtins.__import__\n"
        "def guarded(name, *args, **kwargs):\n"
        "    if name.split('.')[0] in blocked:\n"
        "        raise AssertionError(f'unexpected GUI import: {name}')\n"
        "    return orig(name, *args, **kwargs)\n"
        "builtins.__import__ = guarded\n"
        "import cogstash.cli\n",
        encoding="utf-8",
    )
    subprocess.run([sys.executable, str(script)], check=True)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/cli/test_import_boundary.py -v`
Expected: FAIL because `cogstash.cli` still resolves through `src/cogstash/cli.py` and current imports are not package-scoped yet.

- [ ] **Step 3: Create empty package skeletons with safe exports**

Create:

- `src/cogstash/core/__init__.py`
- `src/cogstash/cli/__init__.py`
- `src/cogstash/ui/__init__.py`

Start with minimal exports only; do not move real logic yet.

- [ ] **Step 4: Add a temporary CLI package export**

In `src/cogstash/cli/__init__.py`, export the full current CLI public API from the temporary implementation path so the existing suite stays green while the package path is being introduced.

```python
from cogstash.cli_legacy import *
```

Rename `src/cogstash/cli.py` to a temporary implementation file only if needed to make the package import path legal.

Recommended temporary name:

```text
src/cogstash/cli_legacy.py
```

- [ ] **Step 5: Run the new boundary test and existing CLI smoke tests**

Run: `uv run pytest tests/cli/test_import_boundary.py tests/test_cli.py::test_cli_path_does_not_call_gui_main -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/cogstash/core src/cogstash/cli src/cogstash/ui tests/cli/test_import_boundary.py tests/test_cli.py
git commit -m "test: add package boundary scaffolding and CLI import guard"
```

---

### Task 2: Extract shared config and note logic into `core`

**Files:**
- Create: `src/cogstash/core/config.py`
- Create: `src/cogstash/core/notes.py`
- Modify: `src/cogstash/search.py`
- Modify: `src/cogstash/app.py`
- Modify: `tests/core/test_config.py`
- Modify: `tests/core/test_notes.py`
- Modify: `tests/test_app.py`
- Modify: `tests/test_search.py`

- [ ] **Step 1: Copy current config and note tests into `tests/core/` as failing targets**

Seed `tests/core/test_config.py` from config-related coverage in `tests/test_app.py`.

Seed `tests/core/test_notes.py` from parsing/edit/delete/search coverage in `tests/test_search.py`.

Add one explicit public-API test:

```python
def test_core_exports_note_and_config_symbols():
    from cogstash.core import CogStashConfig, Note, load_config, parse_notes
```

- [ ] **Step 2: Run core tests to verify they fail**

Run: `uv run pytest tests/core/test_config.py tests/core/test_notes.py -v`
Expected: FAIL because `cogstash.core` does not export the moved symbols yet.

- [ ] **Step 3: Move config logic into `src/cogstash/core/config.py`**

Move from current `src/cogstash/app.py`:

- `CogStashConfig`
- `get_default_config_path`
- `load_config`
- `save_config`
- any config-default/path helpers tightly coupled to those functions

- [ ] **Step 4: Move note/search/edit/delete/stats logic into `src/cogstash/core/notes.py`**

Move from current `src/cogstash/search.py`:

- `Note`
- `parse_notes`
- `search_notes`
- `filter_by_tag`
- `mark_done`
- `edit_note`
- `delete_note`
- `compute_stats`
- `DEFAULT_TAG_COLORS`

- [ ] **Step 5: Move shared append/tag logic into `src/cogstash/core/notes.py`**

Move from current `src/cogstash/app.py`:

- `DEFAULT_SMART_TAGS`
- `merge_tags`
- `parse_smart_tags`
- `append_note_to_file`

The CLI `add` path and UI capture path should both call the same shared functions after this step.

- [ ] **Step 6: Export a clean shared API from `src/cogstash/core/__init__.py`**

```python
from .config import CogStashConfig, get_default_config_path, load_config, save_config
from .notes import (
    DEFAULT_SMART_TAGS,
    DEFAULT_TAG_COLORS,
    Note,
    append_note_to_file,
    compute_stats,
    delete_note,
    edit_note,
    filter_by_tag,
    mark_done,
    merge_tags,
    parse_notes,
    parse_smart_tags,
    search_notes,
)
```

- [ ] **Step 7: Convert legacy modules into compatibility wrappers**

`src/cogstash/search.py`:

```python
from cogstash.core.notes import *
```

`src/cogstash/app.py` should import shared config, append, and tag helpers from `cogstash.core` instead of owning them.

- [ ] **Step 8: Run focused tests**

Run: `uv run pytest tests/core/test_config.py tests/core/test_notes.py tests/test_search.py tests/test_app.py tests/test_cli.py -v`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add src/cogstash/core src/cogstash/search.py src/cogstash/app.py tests/core tests/test_search.py tests/test_app.py
git commit -m "refactor: move shared config and note logic into core"
```

---

### Task 3: Convert CLI into a real package depending only on `core`

**Files:**
- Create: `src/cogstash/cli/main.py`
- Create: `src/cogstash/cli/formatting.py`
- Create: `src/cogstash/cli/windows.py`
- Create: `src/cogstash/cli/__main__.py`
- Remove/replace: `src/cogstash/cli.py`
- Modify: `src/cogstash/__main__.py`
- Modify: `src/cogstash/__init__.py`
- Modify: `pyproject.toml`
- Modify: `tests/cli/test_main.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing CLI package tests**

Create `tests/cli/test_main.py`:

```python
from __future__ import annotations


def test_cli_main_uses_core_config(tmp_path, monkeypatch):
    from cogstash.cli import cli_main
    from cogstash.core import CogStashConfig

    config = CogStashConfig(output_file=tmp_path / "notes.md")
    monkeypatch.setattr("cogstash.cli.main.load_config", lambda _path: config)
    cli_main(["recent"])
```

Add a package entry smoke test:

```python
import pytest


def test_python_m_cogstash_cli_runs_help():
    from cogstash.cli.__main__ import main

    with pytest.raises(SystemExit) as excinfo:
        main(["--help"])

    assert excinfo.value.code == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/cli/test_main.py tests/cli/test_import_boundary.py -v`
Expected: FAIL because CLI package implementation is incomplete.

- [ ] **Step 3: Move CLI logic into package modules**

Suggested split:

- `src/cogstash/cli/main.py` — `cli_main`, command dispatch, argparse
- `src/cogstash/cli/formatting.py` — `format_note`, `stream_supports_color`, `stream_is_interactive`, ANSI helpers
- `src/cogstash/cli/windows.py` — `prepare_windows_cli_console`

- [ ] **Step 4: Export stable symbols from `src/cogstash/cli/__init__.py`**

Keep existing public imports working:

```python
from .main import build_parser, cli_main, cmd_add, cmd_config, cmd_delete, cmd_edit, cmd_export, cmd_recent, cmd_search, cmd_stats, cmd_tags
from .formatting import format_note, hex_to_ansi, stream_is_interactive, stream_supports_color
```

- [ ] **Step 5: Add a dedicated CLI bootstrap**

Create `src/cogstash/cli/__main__.py`:

```python
from __future__ import annotations

import sys

from .main import cli_main
from .windows import prepare_windows_cli_console


def main(argv: list[str] | None = None) -> None:
    prepare_windows_cli_console()
    cli_main(sys.argv[1:] if argv is None else argv)
```

- [ ] **Step 6: Narrow the top-level bootstrap**

Update:

- `src/cogstash/__main__.py` so it no longer acts as the main dual-mode runtime for packaged releases
- `src/cogstash/__init__.py` so bootstrap helpers remain consistent
- `pyproject.toml` so the `cogstash` console script points at the new CLI entrypoint

Keep only the minimum compatibility behavior needed by current tests and source execution.

- [ ] **Step 7: Run focused tests**

Run: `uv run pytest tests/cli/test_main.py tests/cli/test_import_boundary.py tests/test_cli.py -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add src/cogstash/cli src/cogstash/__main__.py src/cogstash/__init__.py pyproject.toml tests/cli tests/test_cli.py
git commit -m "refactor: split CLI into package with core-only dependencies"
```

---

### Task 4: Move desktop code under `ui` and preserve current behavior

**Files:**
- Create: `src/cogstash/ui/app.py`
- Create: `src/cogstash/ui/browse.py`
- Create: `src/cogstash/ui/settings.py`
- Create: `src/cogstash/ui/windows.py`
- Create: `src/cogstash/ui/__main__.py`
- Modify: `src/cogstash/app.py`
- Modify: `src/cogstash/browse.py`
- Modify: `src/cogstash/settings.py`
- Modify: `src/cogstash/_windows.py`
- Modify: `tests/ui/conftest.py`
- Modify: `tests/ui/test_app.py`
- Modify: `tests/ui/test_browse.py`
- Modify: `tests/ui/test_settings.py`
- Modify: existing UI tests under `tests/test_app.py`, `tests/test_browse.py`, `tests/test_settings.py`

- [ ] **Step 1: Create UI-specific conftest before moving tests**

Create `tests/ui/conftest.py` with the shared Tk root fixture and UI-only pystray/pynput stubs moved out of the root test conftest.

- [ ] **Step 2: Move a small set of existing UI tests into `tests/ui/`**

Move one representative file at a time, starting with browse tests.

Run: `uv run pytest tests/ui/test_browse.py -v`
Expected: FAIL until imports and fixtures are updated.

- [ ] **Step 3: Move current UI modules into `src/cogstash/ui/`**

Move code from:

- `src/cogstash/app.py` -> `src/cogstash/ui/app.py`
- `src/cogstash/browse.py` -> `src/cogstash/ui/browse.py`
- `src/cogstash/settings.py` -> `src/cogstash/ui/settings.py`

Put only UI-relevant Windows logic into `src/cogstash/ui/windows.py`.

- [ ] **Step 4: Convert top-level modules into thin wrappers**

Examples:

`src/cogstash/app.py`

```python
from cogstash.ui.app import *
```

`src/cogstash/browse.py`

```python
from cogstash.ui.browse import *
```

- [ ] **Step 5: Add a dedicated UI bootstrap**

Create `src/cogstash/ui/__main__.py` that launches the desktop app without touching CLI package internals.

- [ ] **Step 6: Run focused UI tests**

Run: `uv run pytest tests/ui/test_app.py tests/ui/test_browse.py tests/ui/test_settings.py -v`
Expected: PASS

- [ ] **Step 7: Run legacy compatibility tests**

Run: `uv run pytest tests/test_app.py tests/test_browse.py tests/test_settings.py -v`
Expected: PASS until the suite is fully migrated.

- [ ] **Step 8: Commit**

```bash
git add src/cogstash/ui src/cogstash/app.py src/cogstash/browse.py src/cogstash/settings.py src/cogstash/_windows.py tests/ui tests/test_app.py tests/test_browse.py tests/test_settings.py
git commit -m "refactor: move desktop runtime into ui package"
```

---

### Task 5: Finish helper ownership and remove mixed boundaries

**Files:**
- Modify: `src/cogstash/_output.py`
- Modify: `src/cogstash/_windows.py`
- Modify: `src/cogstash/core/output.py`
- Modify: `src/cogstash/cli/windows.py`
- Modify: `src/cogstash/ui/windows.py`
- Test: `tests/core/test_output.py`
- Test: `tests/cli/test_main.py`
- Test: `tests/ui/test_app.py`

- [ ] **Step 1: Write failing tests for helper ownership**

Create `tests/core/test_output.py`:

```python
def test_safe_print_is_exported_from_core_output():
    from cogstash.core.output import safe_print
```

Add a CLI-only test that imports `cogstash.cli.windows.prepare_windows_cli_console` without importing tkinter.

- [ ] **Step 2: Run tests to verify the boundary failure**

Run: `uv run pytest tests/core/test_output.py tests/cli/test_import_boundary.py -v`
Expected: FAIL until helpers are moved/split cleanly.

- [ ] **Step 3: Move `_output.py` into `core/output.py` and keep a shim**

Move only `safe_print` into `src/cogstash/core/output.py`.

`src/cogstash/_output.py`

```python
from cogstash.core.output import safe_print
from cogstash.cli.formatting import stream_is_interactive, stream_supports_color
```

- [ ] **Step 4: Split `_windows.py` by responsibility**

- CLI console attachment -> `src/cogstash/cli/windows.py`
- UI/single-instance helpers -> `src/cogstash/ui/windows.py`
- temporary compatibility imports remain in `src/cogstash/_windows.py`

- [ ] **Step 5: Run focused tests**

Run: `uv run pytest tests/core/test_output.py tests/cli/test_main.py tests/ui/test_app.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/cogstash/_output.py src/cogstash/_windows.py src/cogstash/core/output.py src/cogstash/cli/windows.py src/cogstash/ui/windows.py tests/core/test_output.py tests/cli/test_main.py tests/ui/test_app.py
git commit -m "refactor: split shared and platform helpers by layer"
```

---

### Task 6: Build, release, and installer support for separate CLI artifacts

**Files:**
- Modify: `scripts/build.py`
- Modify: `.github/workflows/release.yml`
- Modify: `.github/workflows/ci.yml`
- Modify: `scripts/build_installer.py`
- Modify: `installer/windows/CogStash.iss`
- Modify: `tests/test_build_installer.py`
- Modify: `README.md`

- [ ] **Step 1: Write failing packaging tests**

Add to `tests/test_build_installer.py`:

```python
def test_release_workflow_uploads_ui_and_cli_artifacts():
    workflow = Path(".github/workflows/release.yml").read_text(encoding="utf-8")
    assert "CogStash-CLI" in workflow


def test_installer_script_installs_cli_binary_without_shortcut():
    iss = Path("installer/windows/CogStash.iss").read_text(encoding="utf-8")
    assert "CogStash-CLI.exe" in iss
    assert "CogStash CLI" not in iss  # no Start Menu shortcut entry
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_build_installer.py -v`
Expected: FAIL because build/release/installer files only know about the UI executable.

- [ ] **Step 3: Extend `scripts/build.py` with explicit targets**

Implement:

- `--target ui`
- `--target cli`
- `--target both`

Use target-specific entry files and hidden imports. The CLI target must not include GUI-only hidden imports.

- [ ] **Step 4: Update release workflow**

Teach `.github/workflows/release.yml` to:

- build both UI and CLI targets
- archive/upload both per-platform artifacts
- keep names distinct
- smoke-test both entrypoints

Update `.github/workflows/ci.yml` to add at least one CLI-target smoke/build assertion so the extra executable path is exercised before release.

- [ ] **Step 5: Update installer staging and Inno Setup**

`scripts/build_installer.py` and `installer/windows/CogStash.iss` should:

- stage both executables in the install directory
- create UI shortcuts only
- preserve a stable versionless on-disk CLI name (`CogStash-CLI.exe`)
- make no PATH changes as part of this refactor

Rewrite the existing PATH-focused installer expectations in `tests/test_build_installer.py` so they no longer require `addtopath`, ownership markers, or PATH cleanup logic. Add an assertion that the installer files contain `CogStash-CLI.exe` and do not mutate PATH.

- [ ] **Step 6: Update README**

Document:

- new CLI executable name
- release artifact names
- installer behavior (installs both, shortcuts only UI)

- [ ] **Step 7: Run focused packaging tests**

Run: `uv run pytest tests/test_build_installer.py -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add scripts/build.py .github/workflows/release.yml .github/workflows/ci.yml scripts/build_installer.py installer/windows/CogStash.iss tests/test_build_installer.py README.md
git commit -m "build: add separate CLI artifacts and dual-executable installer support"
```

---

### Task 7: Finish test-suite migration and full verification

**Files:**
- Modify: `tests/conftest.py`
- Modify: `tests/test_app.py`
- Modify: `tests/test_browse.py`
- Modify: `tests/test_settings.py`
- Modify: `tests/test_cli.py`
- Modify: any moved files under `tests/core/`, `tests/cli/`, `tests/ui/`

- [ ] **Step 1: Reduce root `tests/conftest.py` to shared fixtures only**

Keep only fixtures safe for all layers, such as generic stream capture helpers.

- [ ] **Step 2: Move remaining tests into layer directories**

Target final structure:

- `tests/core/`
- `tests/cli/`
- `tests/ui/`

Keep imports passing after each move.

- [ ] **Step 3: Run full suite**

Run: `uv run pytest tests/ -v`
Expected: PASS

- [ ] **Step 4: Run lint and type checks**

Run: `uv run ruff check src/ tests/ && uv run mypy src/cogstash/`
Expected: PASS

- [ ] **Step 5: Run build smoke checks**

Run:

```bash
uv run pytest tests/test_build_installer.py -v
uv run python scripts/build.py --target cli
uv run python scripts/build.py --target ui
```

Expected: builds succeed and produce distinct artifacts.

- [ ] **Step 6: Commit**

```bash
git add tests src .github/workflows scripts README.md
git commit -m "test: finish suite migration for core cli and ui split"
```

---

## Notes for implementation

- Prefer compatibility shims during the refactor instead of breaking imports all at once.
- Do not move build/release logic before the code boundaries are proven by tests.
- Keep the CLI package importable without tkinter, pystray, or Pillow at every intermediate checkpoint after Task 3 starts.
- If `cli.py` cannot be converted directly into `src/cogstash/cli/` in one step, use a temporary file such as `src/cogstash/cli_legacy.py` for one commit only, then remove it in the following task.
- After each task, request review before continuing if the implementation diverges from the spec.
