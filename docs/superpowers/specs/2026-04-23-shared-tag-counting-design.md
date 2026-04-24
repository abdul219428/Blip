# Shared Tag Counting Design

## Summary

Issue `#26` addresses duplicated tag counting logic that currently lives in both the notes domain layer and the CLI command layer. The change should remove duplication without introducing a new module boundary or coupling callers to unrelated statistics behavior.

## Current Problem

Two code paths count tags from a list of notes independently:

- `src/cogstash/core/notes.py` inside `compute_stats()`
- `src/cogstash/cli/main.py` inside `cmd_tags()`

Both iterate every note and every tag, but they implement the logic separately. This creates drift risk if counting or ordering rules change.

## Goals

- Define one shared tag-counting contract in `src/cogstash/core/notes.py`
- Reuse that contract from both `compute_stats()` and `cmd_tags()`
- Keep display formatting in the CLI layer
- Preserve stable ordering for tag listings and stats output

## Non-Goals

- Creating a new helper module
- Refactoring broader note statistics behavior
- Changing CLI output formatting

## Recommended Design

Add one focused helper in `src/cogstash/core/notes.py`:

- shape: `count_tags(notes: list[Note]) -> dict[str, int]`
- responsibility: count all tags across the provided notes
- ordering: return counts ordered by descending count, then ascending tag name

The helper becomes the single source of truth for tag aggregation. `compute_stats()` uses it to populate `tag_counts`, and `cmd_tags()` uses it to render the tag list.

## Boundary Decision

The helper stays in `src/cogstash/core/notes.py` because tag aggregation is a notes-domain concern. This avoids a low-value extraction into a separate helpers module while still making the logic explicit and reusable.

## Behavioral Contract

- Empty input returns an empty dictionary
- Repeated tags across notes are accumulated
- Returned mapping order is deterministic:
  - higher counts first
  - alphabetical tag order for count ties

This ordering contract is intentional because both statistics output and CLI tag listing rely on stable presentation.

## Testing

Add or update tests to cover:

- empty note lists
- single-note and multi-note aggregation
- tie ordering by tag name
- `compute_stats()` consuming the shared helper
- `cmd_tags()` rendering counts based on the shared helper output

## Risks

- If ordering is not tested directly, later refactors may regress CLI output stability
- If the helper is made too generic, it can blur the domain boundary instead of clarifying it

## Outcome

After this change, tag counting exists in one place, callers share the same contract, and the cleanup remains scoped to `#26` without creating unnecessary architecture churn.
