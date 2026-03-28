# Phase 10: PyInstaller Packaging & Release Automation — Design Spec

## Goal

Package CogStash as standalone executables for Windows, macOS, and Linux using PyInstaller. Automate builds via GitHub Actions so that pushing a git tag produces a GitHub Release with downloadable binaries.

## Current State

- `src/cogstash/` package with 6 modules (app, cli, search, browse, __init__, __main__)
- 98 tests passing, CI green (pytest + ruff + mypy on Python 3.9–3.13)
- Runtime deps: pynput, pystray, Pillow
- Entry point: `cogstash = "cogstash:main"` in pyproject.toml
- Static version `0.1.0` in pyproject.toml
- User-provided app icon at `assets/cogstash_icon.png`
- No packaging or release automation

## Design

### 1. Build Configuration

**`scripts/build.py`** — Python build script that drives PyInstaller:

- Reads version from `setuptools-scm` (see Section 4)
- Converts `assets/cogstash_icon.png` to platform-appropriate format:
  - Windows: `.ico` (multi-resolution: 16, 32, 48, 64, 128, 256px) via Pillow
  - macOS: `.icns` via Pillow
  - Linux: uses `.png` directly
- Invokes PyInstaller for both distribution formats:
  - `--onefile` → single portable binary
  - `--onedir` → directory bundle
- Flags:
  - `--debug` → enables console window (`--console`)
  - Default → hides console (`--noconsole` / `--windowed`)
  - `--onefile` / `--onedir` → build only one format
- Output goes to `dist/` (gitignored)

**PyInstaller configuration** (passed programmatically, no .spec file committed):

| Setting | Value |
|---------|-------|
| Entry point | `src/cogstash/__main__.py` |
| App name | `CogStash` |
| Icon | Platform-converted from `assets/cogstash_icon.png` |
| Console | `--noconsole` (release) / `--console` (debug) |
| Hidden imports | `pynput.keyboard._win32`, `pynput.keyboard._darwin`, `pynput.keyboard._xorg`, `pynput.mouse._win32`, `pynput.mouse._darwin`, `pynput.mouse._xorg` |
| Data files | `assets/cogstash_icon.png` bundled as data |
| One-file | Both `--onefile` and `--onedir` builds |

**Hidden imports rationale**: pynput uses dynamic imports for platform-specific backends that PyInstaller's static analysis cannot detect. All platform backends are listed so the same spec works cross-platform.

### 2. Icon Handling

**Source**: `assets/cogstash_icon.png` (user-provided, committed to repo)

**Build-time conversion** in `scripts/build.py`:
- Windows: Pillow `Image.save('cogstash.ico', sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])`
- macOS: Pillow `Image.save('cogstash.icns')` (Pillow supports .icns natively)
- Linux: PNG used directly (no conversion needed)

Generated `.ico` and `.icns` files go to `build/` (gitignored), not committed.

The icon is also bundled as a data file inside the binary so the system tray can use it at runtime (replacing the current Pillow-generated tray icon).

### 3. CI Release Workflow

**`.github/workflows/release.yml`** — separate from existing `ci.yml`:

**Trigger**: Push tag matching `v*` (e.g., `v0.1.0`)

**Jobs**:

1. **`validate`** — Runs existing CI checks (reuses ci.yml via `workflow_call` or duplicates lint+test steps). Release only proceeds if validation passes.

2. **`build`** (depends on `validate`) — Matrix strategy:

   | Runner | Onefile artifact | Onedir artifact |
   |--------|-----------------|-----------------|
   | `windows-latest` | `CogStash-{version}-windows.exe` | `CogStash-{version}-windows.zip` |
   | `macos-latest` | `CogStash-{version}-macos` | `CogStash-{version}-macos.zip` |
   | `ubuntu-latest` | `CogStash-{version}-linux` | `CogStash-{version}-linux.tar.gz` |

   Steps per runner:
   1. Checkout code
   2. Setup Python 3.13
   3. `pip install -e ".[dev]" pyinstaller setuptools-scm`
   4. Run `python scripts/build.py`
   5. Smoke test: `./dist/CogStash --version` (verifies binary runs)
   6. Package onedir as zip/tar.gz
   7. Upload artifacts

3. **`release`** (depends on `build`) — Creates a GitHub Release:
   - Uses `softprops/action-gh-release` or similar
   - Title: `CogStash {version}`
   - Auto-generates release notes from commits since last tag
   - Attaches all 6 artifacts

**Python version**: 3.13 for all builds (latest stable supported by CogStash).

### 4. Version Management

**Strategy**: Tag-driven versioning via `setuptools-scm`.

**pyproject.toml changes**:
```toml
[project]
dynamic = ["version"]  # replaces static version = "0.1.0"

[build-system]
requires = ["setuptools>=64", "setuptools-scm>=8"]

[tool.setuptools_scm]
# version derived from git tags
```

**How it works**:
- `git tag v0.1.0` → version `0.1.0`
- Dev installs: `0.1.0.dev3+g5a5b9d3` (3 commits after tag)
- `cogstash --version` reads `importlib.metadata.version("cogstash")`
- Release workflow extracts version from git tag and uses it in artifact names

**Release workflow**:
```
git tag v0.1.0
git push --tags
→ CI: validate → build (3 OS × 2 formats) → create GitHub Release with 6 artifacts
```

### 5. Project File Changes

**New files**:
- `scripts/build.py` — build driver script
- `.github/workflows/release.yml` — release CI workflow

**Modified files**:
- `pyproject.toml` — dynamic version, setuptools-scm config, pyinstaller in dev deps
- `.gitignore` — add `dist/`, `build/`, `*.spec`, `*.ico`, `*.icns`
- `src/cogstash/__init__.py` — add `__version__` via `importlib.metadata`
- `src/cogstash/cli.py` — add `--version` flag support
- `src/cogstash/app.py` — use bundled icon for system tray when running as frozen binary

**Committed assets**:
- `assets/cogstash_icon.png` — source icon (already present)

### 6. Testing & Verification

- **Local build**: `python scripts/build.py` on Windows to verify before tagging
- **CI smoke test**: `./dist/CogStash --version` after build (verifies binary launches, prints version, exits)
- **Existing tests**: No changes to the 98 tests — they test Python source, not binaries
- **Frozen detection**: `getattr(sys, 'frozen', False)` to detect PyInstaller runtime and adjust file paths accordingly (e.g., icon bundled via `sys._MEIPASS`)

### 7. .gitignore Additions

```
dist/
build/
*.spec
*.ico
*.icns
```
