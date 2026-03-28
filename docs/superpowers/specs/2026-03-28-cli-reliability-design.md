# CogStash CLI Reliability Design

## Summary

This phase focuses on making packaged Windows CLI commands reliable without splitting CogStash into separate GUI and CLI applications. The installed `cogstash` command should remain a single executable, but startup should branch early into a CLI-only path or the existing GUI/tray path. The same phase also adds an optional installer checkbox to expose CogStash on the user's `PATH`, so installed CLI commands work without manual environment-variable edits.

The core problem to solve is that packaged CLI commands currently inherit assumptions from the GUI build/runtime path. In practice that means commands like `cogstash stats` can crash when stdout/stderr or TTY detection behaves differently in the installed Windows executable than it does during source-based development.

## Goals

- Keep one installed Windows executable for both GUI and CLI usage
- Make packaged CLI commands reliable on Windows
- Detect CLI mode before any GUI or tray startup happens
- Make stream and color handling safe when stdout/stderr is missing, redirected, or non-interactive
- Add an optional installer checkbox to add CogStash to the user `PATH`
- Keep uninstall cleanup limited to installer-managed `PATH` changes

## Non-Goals

- Splitting CogStash into separate packaged GUI and CLI binaries
- Adding a major new CLI feature set
- Redesigning the entire CLI output format
- Adding shell completions or advanced scripting integrations
- Changing existing user-data locations

## Chosen Approach

The chosen direction is to keep a single packaged executable and introduce a clean runtime split very early in startup:

- If the process is invoked with no additional arguments, route into the existing GUI/tray startup path.
- If the process is invoked with additional arguments, treat that as an explicit CLI invocation and route into a CLI-only execution path.
- Valid CLI commands and flags should then be resolved by the real CLI parser/dispatcher so invalid CLI-like input fails as a CLI error instead of accidentally launching the GUI.

This avoids turning a small desktop app into a two-binary product while still addressing the real problem: packaged CLI execution should not depend on GUI-oriented startup assumptions.

## Windows Packaging Constraint

Keeping one executable means the design must explicitly account for Windows packaging behavior. The packaged executable must remain usable from PowerShell and Command Prompt for CLI commands while still serving as the normal GUI entrypoint when launched without arguments.

This phase therefore assumes:

- the packaged Windows executable remains callable as a CLI process from a shell
- CLI mode behavior must be validated against the packaged executable itself, not only source execution
- any unavoidable GUI-versus-console tradeoff in packaging must be treated as an implementation checkpoint, not discovered late in testing

The implementation plan should include an explicit packaging validation step to confirm that the chosen single-executable build still delivers acceptable CLI behavior on Windows.

If that packaging checkpoint fails, this phase should stop and return to design review rather than silently expanding scope mid-implementation. The fallback decision at that point would be whether to accept a packaging compromise or explicitly redesign around split packaged entrypoints in a later phase.

## Architecture

### 1. Early mode detection

Preferred ownership:

- `__main__.py` should be the primary bootstrap boundary for deciding CLI mode vs GUI mode
- `__init__.py` should remain thin and avoid becoming a second source of startup truth

The process entry path should determine whether the invocation is CLI or GUI before initializing Tkinter, tray setup, or other GUI-only behavior.

The rule should be simple and stable:

- no additional arguments -> GUI mode
- any invocation with additional arguments -> CLI mode, with command validity decided by the real CLI parser

This creates one executable with two runtime paths, instead of one path that conditionally tries to unwind GUI assumptions later.

### 2. CLI-only startup path

The CLI runtime path should:

- avoid Tkinter and tray initialization entirely
- call the CLI command dispatcher directly
- use console-safe stream handling
- return meaningful exit codes
- never attempt to recover by opening GUI mode

This path should behave the same way whether CogStash is run from source or from the installed Windows executable.

### 3. Existing GUI path remains unchanged

The current GUI startup path should continue to behave as it does today for tray use, hotkey capture, settings, wizard, and browse flows. This phase is specifically about improving CLI reliability without destabilizing the desktop app.

## Runtime Behavior

### Stream handling

CLI output should not assume `sys.stdout` or `sys.stderr` is always a normal interactive stream.

The CLI layer should use a safe helper for:

- checking whether a stream exists
- checking whether a stream supports `.isatty()`
- deciding whether ANSI/color output is appropriate
- writing fallback plain text when color support is unavailable

The helper should treat missing or non-TTY-like streams as plain text, not as exceptional conditions.

CLI mode should derive command recognition from the actual parser/dispatcher rather than maintaining a separate hardcoded list of commands in the bootstrap layer.

### Error handling

CLI mode should classify failures more clearly:

- expected user/input errors -> short readable message, nonzero exit code
- unexpected internal errors -> readable stderr output and nonzero exit code
- no GUI fallback, no tray startup, no hidden crash path

The intent is to make packaged CLI behavior predictable and script-friendly without broadening scope into a full CLI redesign.

### Exit-code behavior

Commands should terminate cleanly with explicit exit status:

- `0` for success
- nonzero for operational or internal failure

This matters for shell use, release confidence, and future automation support.

## Installer Integration

The Windows installer should gain an optional task such as:

- `addtopath` -> add `%LocalAppData%\Programs\CogStash` to the current user's `PATH`

This should be exposed as an installer checkbox rather than enabled silently by default.

### PATH behavior requirements

- modify only the user `PATH`, not the system `PATH`
- add the resolved install directory actually used by the installer
- avoid duplicate entries using normalized, case-insensitive Windows path comparison
- record whether the installer actually inserted the `PATH` entry so uninstall only removes installer-owned changes
- if the same path already existed before install, leave it untouched on uninstall
- note in installer UX that newly opened shells may be required before the updated `PATH` is visible everywhere

This keeps environment changes explicit and reversible while solving the real usability issue you encountered.

## Components Affected

- `src/cogstash/__main__.py` and/or `src/cogstash/__init__.py`
  - early CLI-vs-GUI mode split
- `src/cogstash/cli.py`
  - safe stream detection, color fallback, robust packaged execution
- installer script and installer helper
  - add optional `PATH` task and uninstall cleanup
- tests
  - CLI runtime regressions and installer task coverage

## Testing Strategy

### CLI reliability tests

Add focused regression coverage for packaged-like conditions:

- stdout/stderr missing or replaced with objects that do not expose `.isatty()`
- non-interactive output mode falls back to plain text
- representative commands such as `stats`, `search`, and one additional command complete without crashing
- `--help` and `--version` work in packaged-like mode
- invalid commands and invalid flags fail as CLI errors instead of launching GUI mode
- stderr-only error paths remain readable
- redirected or piped output remains stable
- CLI mode bootstrap does not trigger GUI startup

### Installer tests

Add or extend installer-level tests to verify:

- presence of an optional `PATH` installer task
- expected install-time behavior for that task
- uninstall cleanup for the installer-managed `PATH` entry

### Verification

This phase should end with the usual repository verification:

- `uv run pytest tests/ -q`
- `uv run ruff check src/ tests/`
- `uv run mypy src/cogstash/`
- required packaged Windows smoke verification from a real Windows shell context using the packaged executable itself, including `--help` and at least one real command such as `stats` or `search`

## Trade-Offs

### Why not split GUI and CLI into separate packaged binaries?

That approach is viable, but it adds:

- more packaging complexity
- installer and PATH complexity for two launchers
- more user-facing documentation and support overhead

For a relatively small app like CogStash, that would likely be premature. A single executable with a clean early runtime split gives most of the reliability benefit with less product and packaging complexity.

### Why add PATH as an installer option instead of default?

Making it optional avoids surprising environment changes while still solving the practical problem for users who want CLI access from any shell.

## Rollout Scope

### In scope

- reliable packaged CLI execution on Windows
- one executable with early CLI/GUI branching
- safe stream and color handling
- installer checkbox to add CogStash to user `PATH`
- uninstall cleanup for installer-managed `PATH` changes

### Out of scope

- dual packaged GUI/CLI products
- broad CLI feature expansion
- large output redesign
- shell-completion support

## Success Criteria

This phase is successful when:

- installed Windows `cogstash stats` and `cogstash search` no longer crash
- CLI commands do not initialize GUI/tray behavior
- color handling degrades safely to plain text when stream capabilities are limited
- installer can optionally make `cogstash` available via `PATH`
- uninstall removes only installer-managed `PATH` changes
- source and packaged CLI behavior are consistent from the user's perspective
