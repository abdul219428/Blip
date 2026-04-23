# Export Failure Handling Design

## Summary

Issue `#28` hardens export failure behavior for the CLI export flow. Current export paths cover the success case, but they do not convert file I/O failures into clear user-facing errors with stable command behavior.

## Current Problem

`cmd_export()` currently writes JSON, CSV, and Markdown outputs directly. If file opening or writing fails, the command can surface a raw exception path instead of a clear export-specific error.

Affected areas:

- JSON export write path
- CSV export file open/write path
- Markdown export write path

Existing tests focus mainly on success behavior and do not pin realistic failure handling.

## Goals

- make export write failures explicit and user-friendly
- keep failure behavior consistent across JSON, CSV, and Markdown exports
- add focused tests for realistic I/O failure scenarios
- avoid broad export architecture churn

## Non-Goals

- creating a new export module
- redesigning export payload shapes
- changing success-path output format
- broader function decomposition beyond what is needed for failure handling

## Recommended Design

Keep the change local to `src/cogstash/cli/main.py`.

Add one small private export-write boundary that:

- performs the final file write for the chosen export format
- catches `OSError` from file open/write operations
- reports a clear error to `stderr`
- exits with status `1`

Example user-facing behavior:

- `Error: failed to export notes to <path>.`

The success path remains unchanged:

- export file is written
- success message still prints `Exported N notes → <path>`

## Boundary Decision

The failure handling should stay local to `cmd_export()` because the behavior is specific to export, not a general-purpose I/O concern. This avoids introducing a new shared abstraction that would be too broad for the issue.

The helper should be private and scoped to export only.

## Behavioral Contract

- if there are no notes, existing no-op behavior remains unchanged
- if writing succeeds, success output remains unchanged
- if any export write step raises `OSError`, the command:
  - prints a clear export-specific error to `stderr`
  - exits with code `1`
  - does not print the success message

This contract should apply consistently to:

- JSON exports
- CSV exports
- Markdown exports

## Testing

Add or extend tests to cover:

- JSON export failure via write error
- CSV export failure via file open/write error
- Markdown export failure via write error
- success message not emitted on failure
- failure message includes the target path

Use realistic failure injection with monkeypatching around file-write operations rather than depending on machine-specific unwritable paths.

## Risks

- wrapping only one branch would leave inconsistent behavior across formats
- over-refactoring the export function would bleed into issue `#30`
- tests that only assert `SystemExit` without stderr content would miss user-facing clarity regressions

## Outcome

After this change, export failures become explicit and consistent, the user gets a clear error instead of a raw crash path, and the behavior is protected by focused regression tests.
