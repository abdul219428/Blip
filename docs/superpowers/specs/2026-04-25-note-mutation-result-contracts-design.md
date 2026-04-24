# Note Mutation Result Contracts Design

## Summary

Issue `#29` improves note mutation result contracts so callers can distinguish expected user-state outcomes from real write failures. The current boolean return values from note mutation helpers are too coarse for CLI and UI callers.

## Current Problem

The note mutation helpers in `src/cogstash/core/notes.py` currently return `bool`:

- `mark_done()`
- `edit_note()`
- `delete_note()`

That collapses several different outcomes into the same result:

- successful mutation
- stale note reference / line mismatch
- invalid input
- already-done note
- file I/O failure

As a result, callers in the CLI and browse UI cannot express better user-facing behavior without re-deriving low-level conditions themselves.

## Goals

- replace coarse boolean mutation results with a small explicit status contract
- distinguish expected user conditions from true I/O failures
- improve API clarity for both CLI and UI callers
- keep the contract lightweight and easy to adopt

## Non-Goals

- introducing a large result object hierarchy
- redesigning note mutation flow or file format
- broad refactoring outside note mutation helpers and their direct callers

## Recommended Design

Add a small mutation status contract in `src/cogstash/core/notes.py`.

Recommended shape:

- an `Enum` or equivalent typed status values
- one shared result type used by:
  - `mark_done()`
  - `edit_note()`
  - `delete_note()`

Representative statuses:

- `SUCCESS`
- `STALE_NOTE`
- `INVALID_INPUT`
- `ALREADY_DONE`
- `IO_ERROR`

Not every mutation needs every status, but all helpers should return from the same contract family.

## Boundary Decision

The result contract should live in `src/cogstash/core/notes.py` with the mutation helpers because it is part of their API. CLI and UI callers should consume the statuses, not reconstruct the meaning of `False`.

This keeps ownership in the notes layer and avoids introducing a heavier dataclass or exception-only design.

## Caller Expectations

CLI and UI callers should translate statuses into user-facing behavior:

- `SUCCESS`
  - continue with current success path
- `STALE_NOTE`
  - treat as a user-visible conflict or “note changed/not found” condition
- `INVALID_INPUT`
  - surface a caller-appropriate validation message
- `ALREADY_DONE`
  - surface a no-op / already-complete message where relevant
- `IO_ERROR`
  - surface a real failure message

The key improvement is that callers no longer need to guess why a mutation failed.

## Testing

Add or update tests to cover:

- each mutation helper returning the correct status for success
- stale-note mismatch paths returning `STALE_NOTE`
- blank edit input returning `INVALID_INPUT`
- mark-done on an already completed note returning `ALREADY_DONE`
- write failures returning `IO_ERROR`
- CLI and UI callers responding appropriately to the new statuses

## Risks

- changing the return type without updating all callers would create silent regressions
- adding too many statuses would overcomplicate the contract
- tests that only cover success paths would miss the main value of the change

## Outcome

After this change, note mutations expose a clear lightweight API, callers can differentiate expected conflicts from real failures, and the codebase becomes easier to maintain without overengineering the result model.
