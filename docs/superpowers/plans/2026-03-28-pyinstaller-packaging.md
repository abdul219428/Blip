# Phase 10: PyInstaller Packaging & Release Automation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Package CogStash as standalone executables for all platforms and automate release builds via GitHub Actions.

**Architecture:** Replace static versioning with setuptools-scm (tag-driven), create a build script that converts the icon and invokes PyInstaller for onefile+onedir builds, add a release CI workflow triggered by git tags that builds for 3 platforms and creates a GitHub Release.

**Tech Stack:** PyInstaller, setuptools-scm, Pillow (icon conversion), GitHub Actions

**Spec:** `docs/superpowers/specs/2026-03-28-pyinstaller-packaging-design.md`

---

### Task 1: Version Management (setuptools-scm + __version__)

**Files:**
- Modify: `pyproject.toml` (lines 1-8, 17-18)
- Modify: `src/cogstash/__init__.py` (full file, 9 lines)

- [ ] **Step 1: Update pyproject.toml for dynamic versioning**

Replace the static version and build-system config:

```toml
[build-system]
requires = ["setuptools>=64", "setuptools-scm>=8"]
build-backend = "setuptools.build_meta"

[project]
name = "cogstash"
dynamic = ["version"]
description = "A global hotkey brain dump — press, type, gone."
```

Remove the line `version = "0.1.0"` entirely. Add `dynamic = ["version"]`.

Add setuptools-scm config section after existing `[tool.mypy]`:

```toml
[tool.setuptools_scm]
```

Add `setuptools-scm` and `pyinstaller` to dev dependencies:

```toml
[project.optional-dependencies]
dev = ["pytest>=7.0", "ruff>=0.4", "mypy>=1.10", "setuptools-scm>=8", "pyinstaller>=6.0"]
```

- [ ] **Step 2: Add __version__ to __init__.py**

Replace `src/cogstash/__init__.py` contents with:

```python
"""CogStash — A global hotkey brain dump."""

from __future__ import annotations

try:
    from importlib.metadata import version

    __version__ = version("cogstash")
except Exception:
    __version__ = "0.0.0-unknown"


def main():
    """Entry point for the cogstash command."""
    from cogstash.app import main as _main

    _main()
```

The `try/except` handles both frozen binaries (if metadata is missing) and uninstalled dev environments.

- [ ] **Step 3: Create git tag for initial version**

```bash
git tag v0.1.0
```

Do NOT push the tag yet — this is just so setuptools-scm can resolve a version locally.

- [ ] **Step 4: Reinstall and verify version**

```bash
pip install -e ".[dev]"
python -c "from cogstash import __version__; print(__version__)"
```

Expected output: `0.1.0` (or `0.1.0.devN+gHASH` if commits exist after tag)

- [ ] **Step 5: Run existing tests to verify nothing broke**

```bash
python -m pytest tests/ -v
```

Expected: all 98 tests pass.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml src/cogstash/__init__.py
git commit -m "feat: switch to setuptools-scm for tag-driven versioning"
```

Move the `v0.1.0` tag to this commit:

```bash
git tag -d v0.1.0
git tag v0.1.0
```

---

### Task 2: --version Flag in CLI and App Dispatch

**Files:**
- Modify: `src/cogstash/app.py:572-577` (main function argv dispatch)
- Modify: `src/cogstash/cli.py:521-584` (build_parser)
- Test: `tests/test_cli.py` (add version tests)
- Test: `tests/test_app.py` (add version dispatch test)

- [ ] **Step 1: Write failing tests for --version**

Add to `tests/test_cli.py`:

```python
def test_version_flag(capsys):
    """cogstash --version prints the version string."""
    from cogstash.cli import build_parser

    parser = build_parser()
    try:
        parser.parse_args(["--version"])
    except SystemExit:
        pass
    captured = capsys.readouterr()
    assert "cogstash" in captured.out.lower() or "0." in captured.out
```

Add to `tests/test_app.py`:

```python
def test_main_dispatches_version(monkeypatch, capsys):
    """main() handles --version before GUI launch."""
    import cogstash.app as cogstash_mod

    monkeypatch.setattr("sys.argv", ["cogstash", "--version"])
    try:
        cogstash_mod.main()
    except SystemExit:
        pass
    captured = capsys.readouterr()
    assert "0." in captured.out or "cogstash" in captured.out.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_cli.py::test_version_flag tests/test_app.py::test_main_dispatches_version -v
```

Expected: FAIL (no --version support yet)

- [ ] **Step 3: Add --version to CLI parser**

In `src/cogstash/cli.py`, modify `build_parser()` to add version argument right after the parser is created (around line 523):

```python
def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser with subcommands."""
    from cogstash import __version__

    parser = argparse.ArgumentParser(
        prog="cogstash",
        description="CogStash — query your brain dump from the terminal.",
    )
    parser.add_argument("--version", "-V", action="version", version=f"cogstash {__version__}")
    sub = parser.add_subparsers(dest="command")
```

- [ ] **Step 4: Handle --version in app.py dispatch**

In `src/cogstash/app.py`, modify `main()` to check for `--version` before the subcommand check:

```python
def main():
    # --version flag — handle before GUI
    if len(sys.argv) > 1 and sys.argv[1] in ("--version", "-V"):
        from cogstash.cli import build_parser
        build_parser().parse_args(sys.argv[1:])
        return

    # CLI subcommands — delegate before loading GUI
    if len(sys.argv) > 1 and sys.argv[1] in ("recent", "search", "tags", "add", "edit", "delete", "export", "stats", "config"):
        from cogstash.cli import cli_main
        cli_main(sys.argv[1:])
        return
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
python -m pytest tests/test_cli.py::test_version_flag tests/test_app.py::test_main_dispatches_version -v
```

Expected: PASS

- [ ] **Step 6: Run full test suite**

```bash
python -m pytest tests/ -v
```

Expected: 100 tests pass (98 existing + 2 new).

- [ ] **Step 7: Commit**

```bash
git add src/cogstash/app.py src/cogstash/cli.py tests/test_cli.py tests/test_app.py
git commit -m "feat: add --version flag to CLI and app dispatch"
```

---

### Task 3: Build Script + Icon Conversion

**Files:**
- Create: `scripts/build.py`
- Modify: `.gitignore` (add `*.spec`, `*.ico`, `*.icns`)
- Modify: `src/cogstash/app.py:226-279` (tray icon: use bundled icon when frozen)

- [ ] **Step 1: Add .gitignore entries**

Append to `.gitignore`:

```
# PyInstaller
*.spec
*.ico
*.icns
```

(`dist/` and `build/` are already in `.gitignore`)

- [ ] **Step 2: Create scripts/build.py**

Create `scripts/build.py`:

```python
#!/usr/bin/env python3
"""Build CogStash with PyInstaller — onefile and/or onedir."""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ICON_SRC = ROOT / "assets" / "cogstash_icon.png"
BUILD_DIR = ROOT / "build"
DIST_DIR = ROOT / "dist"
ENTRY = ROOT / "src" / "cogstash" / "__main__.py"

HIDDEN_IMPORTS = [
    "pynput.keyboard._win32",
    "pynput.keyboard._darwin",
    "pynput.keyboard._xorg",
    "pynput.mouse._win32",
    "pynput.mouse._darwin",
    "pynput.mouse._xorg",
    "pystray._win32",
    "pystray._darwin",
    "pystray._xorg",
    "pystray._appindicator",
    "pystray._gtk",
]


def get_version() -> str:
    """Get version from setuptools-scm metadata."""
    from importlib.metadata import version
    return version("cogstash")


def convert_icon() -> str | None:
    """Convert PNG icon to platform-appropriate format. Returns path or None."""
    if not ICON_SRC.exists():
        print(f"Warning: icon not found at {ICON_SRC}", file=sys.stderr)
        return None

    from PIL import Image

    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    img = Image.open(ICON_SRC)

    if sys.platform == "win32":
        ico_path = BUILD_DIR / "cogstash.ico"
        sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        img.save(str(ico_path), format="ICO", sizes=sizes)
        return str(ico_path)
    elif sys.platform == "darwin":
        icns_path = BUILD_DIR / "cogstash.icns"
        img.save(str(icns_path), format="ICNS")
        return str(icns_path)
    else:
        return str(ICON_SRC)


def run_pyinstaller(*, onefile: bool, debug: bool, icon_path: str | None, version: str) -> None:
    """Run PyInstaller with the given configuration."""
    mode = "onefile" if onefile else "onedir"
    name = f"CogStash-{version}" if onefile else f"CogStash-{version}-onedir"

    cmd = [
        sys.executable, "-m", "PyInstaller",
        str(ENTRY),
        f"--{'onefile' if onefile else 'onedir'}",
        "--name", name,
        "--copy-metadata", "cogstash",
        "--add-data", f"{ICON_SRC}{os.pathsep}assets",
        "--distpath", str(DIST_DIR),
        "--workpath", str(BUILD_DIR / mode),
        "--specpath", str(BUILD_DIR),
        "--clean",
    ]

    if not debug:
        cmd.append("--noconsole")

    if icon_path:
        cmd.extend(["--icon", icon_path])

    for imp in HIDDEN_IMPORTS:
        cmd.extend(["--hidden-import", imp])

    print(f"\n{'='*60}")
    print(f"Building {mode}...")
    print(f"{'='*60}")
    subprocess.run(cmd, check=True)
    print(f"✅ {mode} build complete → dist/")


def main():
    parser = argparse.ArgumentParser(description="Build CogStash executables")
    parser.add_argument("--onefile", action="store_true", help="Build only onefile")
    parser.add_argument("--onedir", action="store_true", help="Build only onedir")
    parser.add_argument("--debug", action="store_true", help="Enable console window")
    args = parser.parse_args()

    # Default: build both
    build_onefile = args.onefile or (not args.onefile and not args.onedir)
    build_onedir = args.onedir or (not args.onefile and not args.onedir)

    version = get_version()
    print(f"CogStash version: {version}")
    print(f"Platform: {platform.system()} ({sys.platform})")

    icon_path = convert_icon()

    if build_onefile:
        run_pyinstaller(onefile=True, debug=args.debug, icon_path=icon_path, version=version)

    if build_onedir:
        run_pyinstaller(onefile=False, debug=args.debug, icon_path=icon_path, version=version)

    print(f"\n🎉 All builds complete!")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Update tray icon to use bundled icon when frozen**

In `src/cogstash/app.py`, modify `create_tray_icon()` (starting at line 226). Replace the icon generation block (lines 241-250) with code that first tries to load the bundled icon:

```python
def create_tray_icon(app_queue: queue.Queue, config: CogStashConfig) -> None:
    """Create and run a system tray icon on a daemon thread."""
    try:
        import pystray
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        logger.warning("pystray or Pillow not installed — skipping tray icon")
        return

    theme = THEMES[config.theme]

    def hex_to_rgba(h):
        h = h.lstrip("#")
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4)) + (255,)

    # Try bundled icon first (PyInstaller frozen binary)
    img = None
    if getattr(sys, "frozen", False):
        bundle_dir = Path(getattr(sys, "_MEIPASS", "."))
        icon_path = bundle_dir / "assets" / "cogstash_icon.png"
        if icon_path.exists():
            img = Image.open(icon_path).resize((64, 64))

    if img is None:
        # Fallback: generate icon programmatically
        img = Image.new("RGBA", (64, 64), hex_to_rgba(theme["bg"]))
        draw = ImageDraw.Draw(img)
        try:
            font: ImageFont.FreeTypeFont | ImageFont.ImageFont = ImageFont.truetype("arial", 40)
        except OSError:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), "⚡", font=font)
        x = (64 - (bbox[2] - bbox[0])) // 2 - bbox[0]
        y = (64 - (bbox[3] - bbox[1])) // 2 - bbox[1]
        draw.text((x, y), "⚡", fill=hex_to_rgba(theme["fg"]), font=font)
```

The rest of `create_tray_icon()` (lines 252-279) stays unchanged.

- [ ] **Step 4: Run full test suite**

```bash
python -m pytest tests/ -v
```

Expected: 100 tests pass (no existing tests should break).

- [ ] **Step 5: Run lint and type check**

```bash
python -m ruff check src/ tests/ scripts/
python -m mypy src/cogstash/
```

Expected: all pass.

- [ ] **Step 6: Test local build (Windows)**

```bash
python scripts/build.py --onefile
```

Expected: builds successfully, produces `dist/CogStash-{version}.exe`.

Smoke test:

```bash
dist\CogStash-{version}.exe --version
```

Expected: prints `cogstash X.Y.Z` and exits.

- [ ] **Step 7: Commit**

```bash
git add .gitignore scripts/build.py src/cogstash/app.py
git commit -m "feat: add PyInstaller build script with icon conversion"
```

---

### Task 4: GitHub Actions Release Workflow

**Files:**
- Create: `.github/workflows/release.yml`

- [ ] **Step 1: Create release workflow**

Create `.github/workflows/release.yml`:

```yaml
name: Release

on:
  push:
    tags:
      - "v*"

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-python@v6
        with:
          python-version: "3.13"
      - name: Install system dependencies
        run: sudo apt-get update && sudo apt-get install -y xvfb
      - run: pip install -e ".[dev]"
      - run: ruff check src/ tests/
      - run: mypy src/cogstash/
      - name: Run tests
        run: xvfb-run python -m pytest tests/ -v

  build:
    needs: validate
    strategy:
      matrix:
        include:
          - os: windows-latest
            artifact_suffix: windows
            exe_ext: .exe
            archive_cmd: Compress-Archive -Path dist/CogStash-*-onedir -DestinationPath dist/CogStash-${{ github.ref_name }}-windows.zip
            shell: pwsh
          - os: macos-latest
            artifact_suffix: macos
            exe_ext: ""
            archive_cmd: cd dist && zip -r CogStash-${{ github.ref_name }}-macos.zip CogStash-*-onedir
            shell: bash
          - os: ubuntu-latest
            artifact_suffix: linux
            exe_ext: ""
            archive_cmd: cd dist && tar -czf CogStash-${{ github.ref_name }}-linux.tar.gz CogStash-*-onedir
            shell: bash
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v5
        with:
          fetch-depth: 0  # full history for setuptools-scm
      - uses: actions/setup-python@v6
        with:
          python-version: "3.13"
      - run: pip install -e ".[dev]"
      - name: Build executables
        run: python scripts/build.py
      - name: Smoke test onefile
        run: |
          $binary = Get-ChildItem dist/CogStash-*${{ matrix.exe_ext }} -File | Where-Object { $_.Name -notmatch 'onedir' } | Select-Object -First 1
          & $binary.FullName --version
        shell: pwsh
        if: matrix.os == 'windows-latest'
      - name: Smoke test onefile
        run: |
          binary=$(find dist -maxdepth 1 -name 'CogStash-*' -type f ! -name '*onedir*' ! -name '*.tar.gz' ! -name '*.zip' | head -1)
          chmod +x "$binary"
          "$binary" --version
        shell: bash
        if: matrix.os != 'windows-latest'
      - name: Archive onedir bundle
        run: ${{ matrix.archive_cmd }}
        shell: ${{ matrix.shell }}
      - name: Rename onefile for clarity
        run: |
          import glob, os, sys
          version = os.environ.get("GITHUB_REF_NAME", "unknown")
          suffix = "${{ matrix.artifact_suffix }}"
          ext = "${{ matrix.exe_ext }}"
          # Find the onefile binary
          pattern = f"dist/CogStash-*{ext}"
          for f in glob.glob(pattern):
              if "onedir" not in f and not f.endswith((".zip", ".tar.gz")):
                  target = f"dist/CogStash-{version}-{suffix}{ext}"
                  os.rename(f, target)
                  break
        shell: python
      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: cogstash-${{ matrix.artifact_suffix }}
          path: |
            dist/CogStash-*-${{ matrix.artifact_suffix }}*

  release:
    needs: build
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/download-artifact@v4
        with:
          path: artifacts
          merge-multiple: true
      - name: List artifacts
        run: find artifacts -type f | sort
      - name: Create GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          name: CogStash ${{ github.ref_name }}
          generate_release_notes: true
          files: artifacts/*
```

- [ ] **Step 2: Validate YAML syntax**

```bash
python -c "import yaml; yaml.safe_load(open('.github/workflows/release.yml'))"
```

If `pyyaml` is not installed, use:

```bash
python -c "
import json, subprocess, sys
# Basic YAML syntax check — ensure no tabs, proper indentation
content = open('.github/workflows/release.yml').read()
assert '\t' not in content, 'YAML must not contain tabs'
print('YAML syntax looks OK (basic check)')
"
```

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/release.yml
git commit -m "ci: add GitHub Actions release workflow for PyInstaller builds"
```

---

### Task 5: Integration Test + Push

- [ ] **Step 1: Run full test suite**

```bash
python -m pytest tests/ -v
```

Expected: 100 tests pass.

- [ ] **Step 2: Run lint on all code including scripts**

```bash
python -m ruff check src/ tests/ scripts/
```

Expected: no errors.

- [ ] **Step 3: Push all commits**

```bash
git push origin main
```

Wait for CI to pass on the push.

- [ ] **Step 4: Tag and push to trigger release**

```bash
git tag -d v0.1.0
git tag v0.1.0
git push origin v0.1.0
```

This triggers the release workflow: validate → build (3 OS) → create GitHub Release.

- [ ] **Step 5: Verify release**

Check the GitHub Actions "Release" workflow completes successfully and a GitHub Release is created with 6 artifacts:
- `CogStash-v0.1.0-windows.exe` (onefile)
- `CogStash-v0.1.0-windows.zip` (onedir)
- `CogStash-v0.1.0-macos` (onefile)
- `CogStash-v0.1.0-macos.zip` (onedir)
- `CogStash-v0.1.0-linux` (onefile)
- `CogStash-v0.1.0-linux.tar.gz` (onedir)
