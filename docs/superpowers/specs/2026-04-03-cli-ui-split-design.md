# CogStash CLI/UI Split Design

## Summary

This phase splits CogStash into three explicit layers inside the existing `cogstash` package:

- `cogstash.core` — shared domain, storage, config, and note logic
- `cogstash.cli` — terminal-facing command parsing and output
- `cogstash.ui` — tkinter, tray, hotkey, and desktop startup flows

The same phase also introduces a dedicated CLI executable alongside the existing UI application. The UI build remains the desktop-first product, while the new CLI executable becomes the preferred terminal entrypoint.

## Goals

- Separate shared logic from CLI and UI concerns
- Make the CLI importable and runnable without tkinter, pystray, or Pillow
- Add a dedicated CLI executable alongside the existing UI application
- Keep the Windows installer focused on the full desktop experience while installing both executables
- Preserve current user-visible behavior unless the split explicitly changes entrypoint ownership
- Keep `pytest`, `ruff`, and `mypy` green throughout the refactor

## Non-Goals

- Creating separate repositories
- Publishing separate PyPI packages in this phase
- Creating a separate Windows CLI installer
- Redesigning existing commands or desktop workflows beyond what the split requires
- Moving user data paths

## Chosen Approach

The preferred direction is to keep one top-level `cogstash` package and introduce strong internal boundaries with new subpackages:

- `cogstash.core`
- `cogstash.cli`
- `cogstash.ui`

This gives the project cleaner architectural seams without paying the migration cost of a full package-namespace breakup. It also allows release automation to produce a dedicated CLI executable now, while leaving open the option of promoting these layers into separately published packages later if there is a real need.

## Architecture

### 1. `cogstash.core`

`core` should contain all logic that is shared by both terminal and desktop flows and that can be tested without GUI dependencies.

Expected ownership:

- domain models such as `Note` and `CogStashConfig`
- note parsing, search, filtering, edit, delete, and stats logic
- config loading and saving
- file/path helpers related to notes, config, and logs
- shared tag parsing and normalization
- Windows-agnostic shared output or utility helpers that are not terminal-formatting specific

`core` must not import tkinter, pystray, Pillow, or CLI formatting code.

### 2. `cogstash.cli`

`cli` should own:

- argument parsing
- command dispatch
- terminal formatting
- color and stream detection
- exit-code behavior
- Windows console-preparation helpers needed only for terminal execution
- the new dedicated CLI executable entrypoint

`cli` may depend on `core`, but it must not import UI modules at import time. A terminal-only environment should be able to import and run `cogstash.cli` without desktop dependencies installed.

### 3. `cogstash.ui`

`ui` should own:

- tkinter application startup
- tray icon setup
- global hotkey wiring
- browse/settings/wizard windows
- Windows GUI-specific helpers
- the existing desktop application entrypoint

`ui` may depend on `core`, but not on `cli`.

### 4. Boundary rule

The migration rule should stay simple:

- reusable behavior moves to `core`
- terminal-only behavior stays in `cli`
- window/tray/hotkey behavior stays in `ui`

If a module needs both terminal formatting and tkinter state, the boundary is wrong and should be reconsidered before moving more code.

### 5. Existing helper ownership

The current helper modules need explicit treatment during the split:

- `_output.py` should move into `core` if it remains a shared safe-writing helper used by both terminal and desktop startup paths
- `_windows.py` should not stay monolithic; CLI console-attachment behavior belongs in `cli`, while any GUI-instance or desktop-runtime behavior belongs in `ui`

If `_windows.py` currently mixes both concerns, the implementation plan should split it rather than relocating it unchanged.

## Entrypoints and Product Shape

This phase should end with two shipped executables:

- **CogStash** — the UI application for tray capture and desktop use
- **CogStash CLI** — the preferred terminal executable for command-line workflows

The UI executable should stop being the primary CLI surface. If a tiny compatibility behavior such as `--version` remains useful for smoke tests, that can be retained intentionally, but the design should treat the dedicated CLI executable as the supported terminal entrypoint.

## Release and Installer Design

### Release artifacts

Release automation should publish:

- the existing UI artifacts
- one additional CLI artifact per platform

This keeps the desktop product intact while giving terminal-first users a cleaner install/run story.

### Build process changes

The current `scripts/build.py` builds a single UI-oriented executable from `src/cogstash/__main__.py` and includes GUI-related hidden imports. This phase should make the build targets explicit rather than trying to infer the right artifact from one bootstrap path.

Preferred direction:

- keep one build helper, but teach it `--target ui|cli|both`
- build the UI executable from a UI-only entrypoint
- build the CLI executable from a CLI-only entrypoint
- keep hidden imports/data files target-specific so the CLI build does not pull in tkinter, pystray, or Pillow packaging assumptions

Expected naming:

- UI artifact keeps the `CogStash` name
- CLI artifact uses a distinct name such as `CogStash-CLI` in packaged outputs and installed files

The release workflow should smoke-test both targets independently.

### Windows installer

The Windows installer should:

- remain the installer for the desktop app
- install both UI and CLI executables into the application directory
- create shortcuts only for the UI application
- leave the CLI executable available for manual shell use from the install directory

For this phase, the installer should **not** silently modify PATH. PATH exposure can remain a separate explicit installer option or later follow-up, but this architecture split should not bundle a new environment-mutation decision into the refactor.

This avoids a second installer surface and keeps Windows setup simple.

### Installer behavior assumptions

- no separate CLI installer in this phase
- no extra Start Menu/Desktop shortcuts for the CLI executable by default
- installer and release names must clearly distinguish UI and CLI artifacts
- the installed CLI executable should use a stable versionless filename such as `CogStash-CLI.exe`

## Testing Strategy

The test suite should be reorganized to reflect the new boundaries:

- `tests/core/`
- `tests/cli/`
- `tests/ui/`

Small end-to-end integration tests should remain around the real entrypoints so packaging and startup regressions are still detected.

### New regression expectations

- `cogstash.cli` imports without tkinter, pystray, or Pillow present
- CLI commands run using `core` only
- UI startup still exercises the expected desktop flows
- packaged CLI and UI entrypoints resolve to the correct executables
- installer/release tests verify both executable outputs and expected naming

### Conftest and fixture split

The current root `tests/conftest.py` initializes tkinter and applies defensive pystray/pynput stubs at session scope. That does not fit the long-term goal of keeping CLI tests independent from UI dependencies.

The migration should therefore make test isolation explicit:

- keep a small root `tests/conftest.py` only for fixtures that are safe for every layer
- move Tk/shared-root fixtures and UI-only stubs into `tests/ui/conftest.py`
- move CLI-only stream/output fixtures into `tests/cli/conftest.py` if that improves separation
- add a CLI import smoke test that runs without tkinter initialization and without UI packages present

To satisfy the "must not break existing tests" constraint, test reorganization should happen only after replacement fixtures exist for the destination directories. Existing tests can remain where they are temporarily during the migration, but no moved CLI test should still depend on root-level tkinter setup.

## Risks

### 1. Hidden import coupling

The biggest risk is that a supposedly shared module still pulls in UI dependencies indirectly. That would defeat the point of the split and could silently break CLI-only packaging.

### 2. Duplicate logic during migration

Config, path, and note behaviors are easy to duplicate accidentally while moving code. The plan should force a single source of truth to emerge in `core` instead of temporary duplication becoming permanent.

### 3. Packaged entrypoint drift

It is easy for the code structure to look correct in source form while build scripts still package the wrong startup behavior. Dedicated artifact and smoke checks are needed before calling the split complete.

### 4. Test coverage no longer matching architecture

If tests keep their old mixed structure, architectural regressions may become harder to spot. The suite should reflect the intended boundaries, not just the historical file layout.

## Migration Strategy

The safest execution order is:

1. Define the public `core` surface first, including explicit exports for the first shared modules moved behind it
2. Move CLI code to depend only on that surface
3. Move UI code to depend on that same surface
4. Add the dedicated CLI executable
5. Reorganize tests to mirror the new boundaries
6. Update build, release, and installer wiring after the code split is already passing

This keeps the refactor incremental and reduces the chance of packaging work hiding architectural mistakes.

After each move, the implementation should verify that the migrated behavior is imported from `core` rather than duplicated in `cli` or `ui`. Temporary wrappers are acceptable during the transition, but duplicate business logic is not.

## Components Expected to Move

### Likely into `core`

- most of `search.py`
- config and path logic currently in `app.py`
- shared note/tag helpers
- shared domain models
- `_output.py` if it remains shared by both entrypaths

### Likely into `cli`

- current `cli.py`
- terminal-formatting helpers and output policy specific to CLI execution
- the CLI-specific portion of `_windows.py`

### Likely into `ui`

- most of `app.py`
- `browse.py`
- `settings.py`
- Windows GUI/runtime helpers that are only relevant to desktop startup
- any UI-specific remainder of `_windows.py`

## Success Criteria

This phase is successful when:

- the repository has explicit `core`, `cli`, and `ui` boundaries
- the dedicated CLI executable is built and released alongside the UI app
- the CLI imports and runs without GUI dependencies
- the Windows installer installs both executables but remains UI-first
- tests, lint, and type checks stay green during the migration
- artifact, installer, and entrypoint behavior are clear enough that future packaging work does not depend on accidental import side effects
