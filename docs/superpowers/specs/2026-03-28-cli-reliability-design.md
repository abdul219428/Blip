# CogStash CLI Reliability Design

## Summary

This phase improves packaged Windows reliability for CogStash's command-line behavior while keeping the product simple to ship and use. The design keeps a single installed executable, adds a clearer runtime split between CLI and GUI startup, hardens console output for packaged Windows runs, and completes installer-managed PATH cleanup on uninstall.

The immediate user-visible goals are:

- `cogstash` commands from the installed Windows app should run reliably
- packaged Windows runs should not crash because of missing stream features or console encoding limits
- the installer's optional PATH task should be reversible on uninstall without removing user-managed PATH entries

## Chosen Direction

Use a **single packaged executable** with an explicit **CLI-only vs GUI-only startup path** decided as early as possible at process start.

This avoids premature packaging complexity from shipping separate GUI and CLI binaries while still creating a clean runtime boundary. The split happens in startup behavior, not in distribution shape.

## Goals

- Keep one installed Windows executable for both GUI and CLI usage
- Make packaged CLI commands reliable on Windows
- Preserve rich CLI/output symbols when the console encoding can support them
- Gracefully degrade to safe fallback output when the console cannot encode current symbols
- Ensure installer-managed PATH changes can be removed during uninstall
- Preserve current GUI behavior and current portable/distribution behavior as much as possible

## Non-Goals

- Shipping separate GUI and CLI binaries in this phase
- Redesigning CLI output formatting wholesale
- Adding major new CLI commands or scripting features
- Changing data locations or installer install mode
- Reworking the release/distribution model beyond what is needed for PATH handling and runtime reliability

## Architecture

### Runtime split

Startup should branch as early as possible into one of two modes:

1. **CLI mode**
   - Triggered when arguments match CLI command usage
   - Must not initialize GUI/tray runtime
   - Must use console-safe output and error handling

2. **GUI mode**
   - Current normal app startup path
   - May still emit startup text, but only through the same safe-output path used by CLI mode

The codebase remains one application. Shared logic stays shared; only bootstrap/runtime handling becomes more explicit.

### Console-safe output

Packaged Windows runs can fail when the active console encoding cannot represent characters such as `→`, emoji, or other decorative symbols. They can also fail when stream objects do not support interactive assumptions.

To address this, output should pass through a shared safe-output helper that:

- writes to the target stream when available
- avoids assuming `.isatty()` exists
- preserves current rich text when the stream encoding supports it
- falls back with replacement-safe text when a `UnicodeEncodeError` occurs
- behaves consistently for `stdout` and `stderr`

This applies to CLI commands and any startup/status messages printed during packaged app startup.

### Installer-managed PATH ownership

The installer should keep the optional **Add CogStash to PATH** task, but treat PATH removal as an ownership problem rather than a simple string removal.

The installer should:

- add the install directory to the **user PATH** only when the user selects the PATH task
- persist a durable ownership marker only when the installer owns that PATH entry
- remove only installer-owned PATH entries during uninstall
- avoid removing a PATH entry that the user added or preserved independently

The preferred mechanism is an installer-owned marker stored in the installed app directory, because the uninstaller can inspect it directly and does not need to rely on fragile previous-data state.

## Components

### `src/cogstash/__main__.py` / bootstrap

- Make the CLI-vs-GUI split explicit and early
- Ensure CLI mode avoids GUI initialization paths
- Route startup output through safe output helpers

### `src/cogstash/cli.py`

- Centralize console-safe writing behavior
- Audit commands for stream assumptions and direct `print()` calls that can break packaged runs
- Keep current output style where possible, but make failure-safe fallback behavior the default when encoding is limited

### `src/cogstash/app.py`

- Any startup console output should use the same safe-output behavior
- GUI startup should not crash because the active console cannot encode decorative characters

### `installer/windows/CogStash.iss`

- Keep the PATH task optional
- Persist installer PATH ownership robustly
- Remove PATH on uninstall only when ownership is proven

## Behavior

### CLI mode behavior

- Runs the requested command without starting tray/GUI infrastructure
- Uses safe stdout/stderr handling
- Returns stable exit codes for success vs failure
- Uses colored/rich output only when supported
- Falls back to plain-safe output when encoding or stream capability does not support richer output

### GUI mode behavior

- Keeps current app behavior
- Uses safe output for any console-facing startup/status messages
- Does not crash on Windows packaged runs because of console encoding

### PATH behavior

- Installer checkbox controls PATH addition
- User PATH only, not system PATH
- Uninstall removes only the installer-managed entry
- If the user later manages PATH manually, uninstall should not remove user-managed entries accidentally

## Error Handling

- Missing or non-interactive stream features should not crash CLI commands
- Encoding failures should degrade output, not abort the process
- User-facing CLI errors should remain short and readable
- Unexpected internal errors should still surface clearly, but not by triggering unrelated GUI behavior
- PATH cleanup should be best-effort and ownership-aware

## Testing Strategy

Add regression coverage for:

- packaged-like CLI stream conditions (`stdout`/`stderr` missing or lacking interactive helpers)
- Unicode-safe output fallback when a stream cannot encode current symbols
- representative commands such as `stats`, `search`, and at least one other common command
- installer PATH task presence and ownership marker behavior
- uninstall PATH cleanup behavior based on ownership

Verification should include:

- `pytest`
- `ruff`
- `mypy`
- Windows installer smoke verification for PATH add/remove behavior where feasible

## Risks and Trade-offs

### Why not split GUI and CLI binaries now?

Separate packaged entrypoints would likely produce the cleanest Windows console behavior, but for CogStash's current size that adds packaging, installer, PATH, documentation, and support complexity. The single-executable approach is the simpler near-term choice and should be tried first.

### Main risk

The main risk is incomplete auditing of output paths, where one remaining direct `print()` or stream assumption could still crash packaged runs. The mitigation is a combination of centralized helpers and focused regression coverage.

## Rollout Scope

### In scope

- packaged Windows CLI reliability
- safe output fallback for console encoding problems
- explicit CLI vs GUI startup split
- installer PATH add/remove ownership behavior

### Out of scope

- separate GUI/CLI binaries
- large CLI UX redesign
- shell completions
- new installer modes
- unrelated feature work

## Expected Outcome

After this phase:

- installed Windows users can run `cogstash` commands more reliably
- packaged runs no longer crash on common console encoding limitations
- the installer can add CogStash to PATH optionally
- uninstall removes only installer-owned PATH changes
