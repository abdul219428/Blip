# UI Queue And Thread Lifecycle Design

## Context

Issue `#24` is the next architecture-boundary slice under umbrella issue `#12`.

Today, `src/cogstash/ui/app.py` owns all of the following at once:

- Tk window behavior
- raw queue message names
- tray callback wiring
- global hotkey registration
- main-thread queue polling
- shutdown cleanup for listener state

That works, but the contracts are mostly implicit. Tray and hotkey behavior communicate with the app through ad hoc string messages, and startup/shutdown responsibilities are spread across `create_tray_icon()`, `CogStash.poll_queue()`, and `main()`. This makes the runtime behavior harder to change safely because the message flow is not represented as an explicit boundary.

## Goals

- define an explicit UI runtime contract for queue commands
- give one module ownership of tray, hotkey, and queue-lifecycle wiring
- preserve current user-visible behavior
- improve testability of startup and shutdown behavior
- reduce coupling inside `ui/app.py`

## Non-Goals

- redesign the Tk UI structure
- change the tray menu contents
- change the hotkey feature or recovery behavior
- introduce async or multiprocessing primitives
- move browse/settings window behavior out of `CogStash`

## Recommended Approach

Extract a dedicated runtime boundary module, tentatively `src/cogstash/ui/app_runtime.py`, that owns the lifecycle contract between background integrations and the Tk main thread.

This module will:

- define the supported queue command types in one place
- provide helpers that enqueue those commands from tray and hotkey callbacks
- provide a dispatcher/drain helper for the Tk thread to consume commands through explicit callbacks
- provide startup helpers that initialize tray and hotkey integrations
- return runtime handles that can be shut down consistently during application exit

`src/cogstash/ui/app.py` will remain the home of the `CogStash` UI object and its direct Tk behavior, but it will stop being the source of truth for runtime message semantics.

## Ownership Boundaries

### `ui/app.py`

Owns:

- Tk root creation and top-level app startup sequence
- the `CogStash` UI object
- concrete UI actions such as `show_window()`, `_open_browse()`, `_open_settings()`, and note submission
- config-driven window updates and widget behavior

Does not own:

- queue command definitions
- tray callback message semantics
- hotkey listener construction details
- queue-drain branching over command values
- shutdown sequencing for runtime integrations beyond invoking runtime helpers

### `ui/app_runtime.py`

Owns:

- queue command definitions and naming
- queue enqueue helpers for tray and hotkey integrations
- queue-drain and dispatch behavior
- startup helpers for tray and hotkey runtime pieces
- shutdown handles or cleanup helpers for started integrations

Does not own:

- widget creation
- Tk layout and styling
- settings or browse window implementation
- note-writing behavior

## Contract Shape

The runtime boundary should make the supported message flow explicit. The exact representation can be an enum, named constants, or another typed structure, but the contract must be centralized and testable.

Supported commands remain:

- show the capture window
- open browse
- open settings
- quit the app

The queue consumer must dispatch through explicit callbacks supplied by `app.py`. `app.py` should no longer hardcode raw message strings inside `CogStash.poll_queue()`.

Unknown commands should not crash the poll loop. The runtime boundary should ignore or log them in a controlled way so that queue draining remains robust.

## Startup And Shutdown Design

Startup in `main()` should be split into two layers:

- `app.py` constructs config, root, dialogs, and the `CogStash` instance
- `app_runtime.py` starts integrations that communicate back into the app through the queue contract

The extracted runtime startup should:

- initialize tray behavior against the shared queue
- initialize the global hotkey listener against the shared queue
- surface the hotkey failure condition back to `main()` so existing warning UX remains intact
- return any handles needed for shutdown

Shutdown should be explicit and centralized:

- main loop exit leads to one cleanup path
- started listeners or tray resources are stopped through runtime-owned handles
- cleanup remains safe when startup partially fails, especially when hotkey registration fails

## Error Handling

Behavior should remain unchanged from the user perspective:

- tray support still degrades gracefully if dependencies are unavailable
- hotkey registration failures still produce the existing warning flow and logging
- duplicate-instance protection remains outside this slice

Additional runtime-specific expectations:

- queue dispatch should not break permanently because of one unexpected command
- partially initialized runtime state must still be safe to shut down

## Testing Strategy

Add focused tests for the runtime boundary rather than relying only on end-to-end startup tests.

Required coverage:

- queue dispatch routes each supported command to the expected callback
- queue draining tolerates an empty queue
- unknown commands are handled safely
- tray and hotkey enqueue behavior uses the centralized contract
- startup helpers return handles that can be shut down safely
- `main()` or `CogStash` tests verify delegation into the runtime boundary rather than open-coded lifecycle logic

Existing behavior tests around hotkey failure, startup continuation, and settings opening should continue to pass with minimal semantic changes.

## Migration Plan

Implement this in one slice:

1. create the runtime module and move command definitions plus queue dispatch there
2. move tray and hotkey enqueue wiring into runtime helpers
3. update `app.py` to delegate queue polling and runtime startup/shutdown
4. add or update focused tests

This keeps the change narrow while still establishing a real ownership boundary.

## Risks And Mitigations

Risk: startup behavior regresses because tray or hotkey initialization changes shape.
Mitigation: keep current user-facing behavior identical and preserve existing startup tests.

Risk: queue dispatch moves but Tk-thread assumptions become less obvious.
Mitigation: require callback-based dispatch that is always invoked from the Tk poll loop.

Risk: over-extraction produces too many tiny modules.
Mitigation: keep this slice to a single runtime boundary module.

## Acceptance Criteria

- `ui/app.py` no longer defines raw queue command handling inline as the source of truth
- tray and hotkey integrations enqueue through a shared explicit contract
- runtime startup and shutdown behavior are delegated through a dedicated module
- tests cover the extracted contract directly
- no user-visible behavior change is introduced for capture, browse, settings, tray, or quit flows
