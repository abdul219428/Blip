# Windows Responsibility Boundaries Design

## Parent Issues

- Umbrella: `#12` — Tighten post-split architecture boundaries
- Current slice:
  - `#23` — Consolidate and document Windows-specific responsibilities

## Summary

Windows behavior now works across CLI, UI, and installer flows, but the
responsibility model is still easy to misread from the codebase. The current
split is partly explicit:

- CLI console attachment lives in `cogstash.cli.windows`
- GUI single-instance behavior lives in `cogstash.ui.windows`
- installed-run and startup-script detection lives in `cogstash.ui.install_state`

But some UI-only Windows runtime behavior still sits inside `cogstash.ui.app`
and `cogstash.ui.settings`, while installer behavior is encoded separately in
`installer/windows/CogStash.iss`. That leaves future contributors without one
clear answer to a basic question: when a Windows-specific change is needed,
which layer owns it?

This slice should define and enforce that ownership model with a small,
practical consolidation. The goal is not to redesign Windows behavior. The goal
is to make the existing behavior land in the right modules and to document the
rules clearly enough that later changes do not drift back into `app.py`,
settings code, or installer script comments by accident.

## Problem

Windows-specific behavior is currently spread across these places:

- `src/cogstash/cli/windows.py`
- `src/cogstash/ui/windows.py`
- `src/cogstash/ui/install_state.py`
- `src/cogstash/ui/app.py`
- `src/cogstash/ui/settings.py`
- `installer/windows/CogStash.iss`
- compatibility wrapper `src/cogstash/_windows.py`

The split is not arbitrary, but it is not fully documented or reflected in the
module structure either.

Current examples of drift:

- `ui.app` owns GUI startup and tray logic, but also still contains a Windows
  DPI helper and Windows-specific file-opening behavior inside the tray flow
- `ui.settings` owns settings UI, but also directly implements startup-script
  creation/removal behavior while separately consulting `ui.install_state` for
  installer-managed state
- the installer script writes `.cogstash-installed` and startup scripts, but
  the runtime-side contract for consuming those artifacts is only implicit in
  tests and scattered helper usage
- `_windows.py` still presents a compatibility surface that combines CLI and UI
  Windows helpers, even though the real owners now live in separate layers

This is not a correctness bug today. It is a maintenance hazard:

- contributors may add new Windows logic to `app.py` because it already has
  some, even when a dedicated owner exists
- installer/runtime contracts can drift because the code and script are not
  described together anywhere
- future cleanup becomes riskier because there is no explicit rule for what
  belongs in `cli.windows` vs `ui.windows` vs `ui.install_state`

## Goals

- Define the ownership model for Windows-specific code across CLI, UI runtime,
  installer-aware runtime state, and installer script behavior
- Reduce scattered Windows-specific runtime helpers where a small consolidation
  makes the ownership clearer
- Keep the runtime/install-state contract visible in code and documentation
- Preserve current behavior while improving module boundaries
- Keep the slice small enough that it does not absorb queue/thread lifecycle
  work from `#24` or build/artifact contract work from `#25`

## Non-Goals

- Rewriting installer behavior
- Changing the current startup-at-login user experience
- Changing the duplicate-instance policy
- Redesigning CLI console attachment behavior
- Removing the root `_windows.py` compatibility shim in this slice
- Bundling build/release contract changes into the Windows ownership cleanup

## Current Ownership Inventory

### 1. `src/cogstash/cli/windows.py`

Current role:

- attach packaged CLI processes to the parent Windows console when stdio is
  missing

Assessment:

- correct owner for CLI-only Windows console preparation
- should remain narrow and CLI-only
- should not grow UI or installer detection responsibilities

### 2. `src/cogstash/ui/windows.py`

Current role:

- GUI single-instance mutex acquisition and release

Assessment:

- correct owner for GUI-runtime-only Windows process coordination
- should remain focused on UI runtime process primitives
- should not absorb installer-detection or startup-script concerns

### 3. `src/cogstash/ui/install_state.py`

Current role:

- determine whether the app is running as an installed Windows build
- expose installer marker and startup-script presence state to runtime code

Assessment:

- correct owner for runtime visibility into installer-managed state
- should remain the bridge between installer artifacts and UI runtime decisions
- should not own GUI actions like creating/removing startup scripts directly

### 4. `src/cogstash/ui/app.py`

Current Windows-specific behavior:

- `configure_dpi()`
- Windows branch in tray file opening (`os.startfile`)
- consumption of `ui.windows` and `ui.install_state` during startup

Assessment:

- startup orchestration belongs here
- standalone Windows runtime helpers such as DPI setup and Windows shell file
  opening should not stay embedded here long-term
- startup should depend on well-named Windows helpers rather than defining them
  inline

### 5. `src/cogstash/ui/settings.py`

Current Windows-specific behavior:

- startup batch-script creation/removal
- startup-state reflection based on `startup_script_exists()`
- Windows shell opening branch in About/help actions
- installer-aware wizard completion branch

Assessment:

- settings UX belongs here
- raw Windows startup-script and Windows shell helper behavior should be pushed
  behind a dedicated UI-runtime Windows helper module where practical
- consuming installer state from `ui.install_state` is correct, but the
  imperative Windows file/script operations should not stay scattered across
  settings code

### 6. `installer/windows/CogStash.iss`

Current role:

- write installed marker file
- optionally create startup batch script
- optionally add CLI directory to PATH
- clean up installer-owned artifacts on uninstall

Assessment:

- correct owner for installation-time side effects
- should remain the only owner of installer-time writes to install directory,
  PATH ownership records, and uninstall cleanup
- runtime code should consume installer artifacts; it should not reproduce
  installer policy decisions

## Chosen Approach

The preferred direction is to define **four explicit Windows ownership zones**
and make one small structural change so the code matches that model.

### A. CLI Windows ownership

Owner:

- `cogstash.cli.windows`

Responsibilities:

- CLI console attachment
- CLI stdio restoration for packaged Windows command execution

Rule:

- if the behavior only matters when a terminal-facing CLI process starts, it
  belongs here

### B. UI Windows runtime ownership

Owner:

- `cogstash.ui.windows`
- plus a new dedicated helper module such as `cogstash.ui.windows_runtime`

Responsibilities:

- GUI single-instance primitives
- DPI-awareness setup
- Windows shell/open-file helper behavior used by UI runtime flows
- startup-script create/remove helpers used by the settings UI

Rule:

- if the behavior is an imperative Windows runtime action performed by the GUI
  app, it belongs in the UI Windows runtime layer, not inline in `app.py` or
  `settings.py`

### C. Installer-state ownership

Owner:

- `cogstash.ui.install_state`

Responsibilities:

- detect installed Windows runtime state
- expose install marker presence
- expose startup-script presence
- answer runtime questions such as “should installer welcome show?”

Rule:

- if the runtime is reading installer-managed state rather than performing a UI
  runtime action, it belongs here

### D. Installer ownership

Owner:

- `installer/windows/CogStash.iss`

Responsibilities:

- create/remove install-time artifacts
- manage installer-owned PATH updates
- write install marker
- write uninstall cleanup behavior

Rule:

- if the operation happens because the installer is running, it belongs here,
  not in Python runtime code

## Recommended Structural Change

To make the ownership model visible in code, this slice should introduce a
small UI-runtime Windows helper module, for example:

- `src/cogstash/ui/windows_runtime.py`

Expected responsibilities for that module:

- `configure_dpi()` or renamed equivalent
- Windows shell open helpers used by tray/about/settings flows
- startup script write/remove helpers currently implemented directly in
  `ui.settings`

This is intentionally narrower than a full `ui.windows` expansion.

Why not put everything into `ui.windows`?

- `ui.windows` already has a clear low-level runtime-process role centered on
  the single-instance mutex
- mixing mutex/process primitives with shell-opening and startup-script helpers
  would create another catch-all module

A dedicated `windows_runtime` module keeps the split readable:

- `ui.windows` → process/runtime primitives
- `ui.windows_runtime` → higher-level Windows GUI runtime actions
- `ui.install_state` → installer-derived runtime state

## Module-Level Rules After This Slice

### `cogstash.cli.windows`

Must own:

- CLI console attach/open-stream behavior

Must not own:

- installer marker detection
- GUI mutex logic
- settings/startup-script operations

### `cogstash.ui.windows`

Must own:

- GUI single-instance primitives

Must not own:

- startup batch-script creation/removal
- installer marker detection
- PATH/installer script logic

### `cogstash.ui.windows_runtime`

Must own:

- GUI-runtime Windows actions such as DPI setup
- shell-opening helpers for UI interactions
- startup-script write/remove helpers invoked by settings UI

Must not own:

- installer marker detection logic
- installer PATH ownership logic
- CLI console behavior

### `cogstash.ui.install_state`

Must own:

- reading installed-run state from runtime environment and installer artifacts
- startup-script presence checks
- installer-welcome decision logic

Must not own:

- creating/removing startup scripts
- GUI actions or dialogs
- CLI console or mutex behavior

### `installer/windows/CogStash.iss`

Must own:

- creation/removal of installer-managed artifacts
- PATH modifications and uninstall cleanup

Must not rely on:

- undocumented Python-side magic comments or hidden assumptions

The Python runtime should be able to point to explicit artifact readers in
`ui.install_state` for every installer-managed runtime contract it consumes.

## Compatibility Wrapper Policy

`src/cogstash/_windows.py` should remain a compatibility shim in this slice,
but its role should stay narrow:

- re-export CLI/UI Windows owners for compatibility only
- not serve as the preferred internal import path

Internal code should continue importing:

- `cogstash.cli.windows` for CLI console preparation
- `cogstash.ui.windows` for GUI mutex behavior
- `cogstash.ui.windows_runtime` for GUI Windows runtime actions
- `cogstash.ui.install_state` for installer-derived runtime state

## Alternatives Considered

### 1. Documentation only, no code movement

Pros:

- lowest implementation risk
- almost no regression surface

Cons:

- leaves Windows runtime helpers embedded in `app.py` and `settings.py`
- makes the documented ownership model less enforceable

Rejected because this issue explicitly asks to consolidate where practical.

### 2. Collapse all Windows logic into one module

Pros:

- one obvious place to look

Cons:

- mixes CLI, UI runtime, installer-state, and process primitives together
- recreates a monolith similar to the old `_windows.py` ambiguity

Rejected.

### 3. Recommended: four ownership zones with one new UI runtime helper module

Pros:

- aligns code structure with actual concerns
- small enough to land safely
- documents installer/runtime boundaries clearly

Cons:

- introduces one additional module
- leaves some Windows references in app/settings call sites, though they become
  delegated rather than owned there

Chosen.

## Risks

### 1. Moving too much behavior at once

If this slice tries to also redesign onboarding, queue lifecycle, or build
contracts, the boundary cleanup will lose focus.

Mitigation:

- keep scope to ownership, documentation, and small helper extraction only

### 2. Blurring installer-state vs runtime-action APIs

If `ui.install_state` starts creating or mutating startup scripts, it will blur
the exact contract this issue is trying to clarify.

Mitigation:

- keep read/decision logic in `install_state`
- keep imperative GUI Windows actions in `windows_runtime`

### 3. Hidden test assumptions

Some tests currently assert behavior by monkeypatching symbols in `ui.app` or
`ui.settings`.

Mitigation:

- update tests to patch the new owning helpers where needed
- add lightweight ownership tests that lock the intended module split

## Testing Strategy

This slice should verify:

1. CLI Windows startup still uses `cogstash.cli.windows`
2. GUI single-instance behavior still uses `cogstash.ui.windows`
3. installer-state decisions still flow through `cogstash.ui.install_state`
4. startup-script behavior and Windows shell-opening helpers are delegated
   through the new UI runtime Windows owner
5. compatibility wrapper behavior in `_windows.py` still works where preserved

Expected verification:

- targeted `tests/ui/test_app.py`
- targeted `tests/ui/test_settings.py`
- targeted `tests/ui/test_app_compat.py`
- targeted `tests/cli/test_cli.py` and/or `tests/cli/test_main.py`
- installer contract tests in `tests/test_build_installer.py`
- repository lint/test checks for touched files

## Success Criteria

This slice is successful when:

- Windows-specific responsibilities are documented in one spec with clear
  ownership rules
- UI-only Windows runtime helpers no longer live primarily inside `ui.app` or
  `ui.settings`
- installer-state reads remain centralized in `ui.install_state`
- installer-time artifact creation/removal remains clearly owned by the Inno
  Setup script
- `_windows.py` remains only a compatibility surface, not the preferred
  internal API
- targeted tests and lint stay green

## Likely Files

- `src/cogstash/cli/windows.py`
- `src/cogstash/ui/windows.py`
- `src/cogstash/ui/install_state.py`
- `src/cogstash/ui/app.py`
- `src/cogstash/ui/settings.py`
- `src/cogstash/ui/windows_runtime.py` (new)
- `src/cogstash/_windows.py`
- `installer/windows/CogStash.iss`
- `tests/ui/test_app.py`
- `tests/ui/test_settings.py`
- `tests/ui/test_app_compat.py`
- `tests/cli/test_main.py`
- `tests/test_build_installer.py`
