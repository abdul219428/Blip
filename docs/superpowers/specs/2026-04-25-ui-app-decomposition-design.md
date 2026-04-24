# UI App Decomposition Design

## Summary

Issue `#30` targets the remaining broad functions and low-value indirections that are still worth cleaning up after the larger architectural and release work stabilized. The highest-value slice is in `src/cogstash/ui/app.py`.

## Current Problem

Two functions in `src/cogstash/ui/app.py` still carry too many responsibilities:

- `create_tray_icon()`
- `main()`

They currently mix concerns that are easier to understand and change when separated:

- resource loading and icon generation
- platform-specific file opening
- tray menu wiring
- thread startup
- config/bootstrap setup
- onboarding/update dialog flow
- hotkey registration
- shutdown cleanup

There are also a few low-value indirections that no longer pay for themselves, such as simple alias/wrapper helpers.

## Goals

- decompose the broad startup/tray functions in `src/cogstash/ui/app.py`
- keep behavior unchanged
- trim obvious low-value indirection where it adds no abstraction value
- keep the cleanup small, practical, and YAGNI-aligned

## Non-Goals

- broad refactors across the whole repo
- redesigning the app lifecycle architecture again
- speculative abstractions for future startup modes
- changing user-facing tray or startup behavior

## Recommended Design

Focus the implementation on one coherent slice:

1. decompose `create_tray_icon()` into a few focused private helpers
2. decompose `main()` into focused startup helpers
3. remove only the clearest low-value wrappers/aliases

### `create_tray_icon()` decomposition

Recommended private helper responsibilities:

- load bundled tray image or generate fallback image
- open notes file with platform-specific behavior
- build tray menu actions
- start the tray thread

This keeps tray construction readable without introducing a new module.

### `main()` decomposition

Recommended private helper responsibilities:

- bootstrap config and logger
- run first-run / version-based dialog flow
- register the global hotkey
- perform final shutdown cleanup

`main()` should become an orchestrator rather than owning every startup branch inline.

### Low-value indirection trimming

Trim only the wrappers that clearly add no value, for example:

- alias-only re-export patterns inside `ui/app.py`
- tiny wrapper helpers that only call `sorted(...)` or equivalent with no domain meaning

Do not sweep compatibility wrappers across the repo in this issue; keep the cleanup attached to the main decomposition slice.

## Boundary Decision

This issue should stay centered on `src/cogstash/ui/app.py` because that is where the broadest remaining functions live. Small wrapper trimming is acceptable only when it directly supports readability in the touched flow.

The cleanup should avoid becoming a repo-wide wrapper purge.

## Testing

Add or update tests to cover:

- startup helper behavior where it is now directly testable
- tray helper behavior where logic moved out of the broad function
- unchanged startup/hotkey warning behavior
- any removed wrapper behavior only if it was externally depended on

Prioritize preserving observable behavior over testing implementation details of every extracted helper.

## Risks

- moving startup logic carelessly can change ordering-sensitive behavior
- splitting helpers too aggressively would create indirection instead of reducing it
- wrapper cleanup can accidentally widen scope if compatibility layers are touched unnecessarily

## Outcome

After this change, `ui/app.py` should read more clearly, startup responsibilities should be easier to follow, and a small amount of unhelpful indirection should be removed without turning the issue into a speculative cleanup campaign.
