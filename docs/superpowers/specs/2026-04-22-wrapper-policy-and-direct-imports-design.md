# Wrapper Policy and Direct Imports Design

## Parent Issues

- Umbrella: `#12` — Tighten post-split architecture boundaries
- First slice:
  - `#21` — Define the long-term role of root-level compatibility wrappers
  - `#22` — Replace facade imports with direct owning-layer imports

## Summary

This slice tightens the first post-split architecture boundary by doing two things together:

1. define a temporary but explicit compatibility role for the root-level wrapper modules
2. migrate internal modules and tests toward the true owning layers instead of wrapper/facade imports

The goal is not to remove every wrapper immediately. The goal is to stop new hidden coupling, make ownership visible in the code, and reduce the maintenance cost of the current compatibility surface without creating an avoidable public-API break.

## Problem

The CLI/UI/core split shipped, but several root-level modules still behave as broad re-export layers:

- `src/cogstash/app.py`
- `src/cogstash/browse.py`
- `src/cogstash/settings.py`
- `src/cogstash/search.py`
- `src/cogstash/_windows.py`

At the same time, some internal code still imports through facades rather than directly from their owning layer:

- `src/cogstash/ui/browse.py`
- `src/cogstash/ui/settings.py`

The result is architectural drift:

- true ownership is harder to see
- internal dependency direction is less obvious than it should be
- tests and internal callers keep wrapper modules alive by habit rather than intent
- future cleanup becomes riskier because there is no explicit wrapper policy

## Goals

- Define which root-level wrappers are compatibility shims for now
- Reduce internal imports that rely on wrappers or unrelated façade modules
- Start migrating tests toward owning modules where they are testing internals rather than compatibility
- Preserve a deliberate migration path for external/public imports
- Keep the slice small enough that it can land without mixing in Windows/lifecycle/build refactors from later child issues

## Non-Goals

- Removing every root-level wrapper in this slice
- Breaking public entrypoints without a migration plan
- Reworking Windows ownership (`#23`)
- Reworking UI queue/thread lifecycle (`#24`)
- Reworking build/installer contracts (`#25`)
- Broad unrelated file reorganization

## Current Wrapper Inventory

### 1. `src/cogstash/app.py`

Current behavior:

- broad `from cogstash.ui.app import *`
- used by compatibility-oriented tests and by `src/cogstash/__main__.py`

Assessment:

- should remain temporarily as a compatibility shim
- should not be used by new internal modules as the preferred import source

### 2. `src/cogstash/browse.py`

Current behavior:

- broad `from cogstash.ui.browse import *`
- used mostly by older/compatibility-style UI tests

Assessment:

- should remain temporarily as a compatibility shim
- internal imports should prefer `cogstash.ui.browse`

### 3. `src/cogstash/settings.py`

Current behavior:

- broad `from cogstash.ui.settings import *`
- used mostly by older/compatibility-style UI tests

Assessment:

- should remain temporarily as a compatibility shim
- internal imports should prefer `cogstash.ui.settings`

### 4. `src/cogstash/search.py`

Current behavior:

- compatibility wrapper around `cogstash.core.notes`
- also re-exports internal helpers such as `_atomic_write` and `_note_line_span`

Assessment:

- this is the most architecturally misleading wrapper because it hides the real owner (`core.notes`)
- internal imports should stop using it where possible in this slice
- compatibility behavior can remain temporarily for callers/tests that still need it

### 5. `src/cogstash/_windows.py`

Current behavior:

- thin aggregator of CLI- and UI-owned Windows helpers

Assessment:

- keep as a compatibility surface for now
- do not expand its role in this slice
- defer deeper ownership changes to `#23`

## Chosen Approach

The preferred direction is a **two-speed migration**:

### A. Compatibility wrappers stay, but become explicitly compatibility-only

Root wrapper modules remain in place during this slice so external compatibility is preserved.

However, they should be treated as:

- transitional public/import compatibility surfaces
- not the preferred internal import path
- intentionally narrow in purpose

Where helpful, wrapper modules should be documented in code as compatibility shims so future contributors do not mistake them for the owning implementation modules.

### B. Internal modules and tests migrate to owning layers now

The actual architecture cleanup happens by changing internal callers and non-compatibility tests to import from the real owner:

- `core` for shared note/config/domain logic
- `ui` for UI implementation modules
- `cli` for CLI-specific behavior

This preserves a migration path while still making the internal architecture clearer immediately.

## Import Policy After This Slice

### Internal module rules

Within `src/cogstash/`, the preferred imports should be:

- shared domain/note/config helpers -> `cogstash.core...`
- UI implementation modules -> `cogstash.ui...`
- CLI implementation modules -> `cogstash.cli...`

Internal modules should not import through:

- `cogstash.search` when `cogstash.core.notes` or `cogstash.core` is the real owner
- `cogstash.app` when `cogstash.ui.app` is the real owner
- `cogstash.browse` or `cogstash.settings` when `cogstash.ui.browse` / `cogstash.ui.settings` is the real owner

### Allowed compatibility entrypoints

Some root-level imports may remain intentionally during the transition where the point of the file is to preserve a stable external launch/import surface.

Current expected exception:

- `src/cogstash/__main__.py` may continue to route through `cogstash.app` until the project intentionally changes that public bootstrap contract

That exception should stay narrow. It does not make wrapper imports acceptable as a general internal pattern.

### Test rules

Tests should be split conceptually into two categories:

1. **Compatibility tests**
   - may intentionally import wrapper modules
   - exist to verify that those shim surfaces still behave as expected

2. **Owning-layer tests**
   - should import from the real implementation module
   - should not rely on wrappers unless wrapper behavior itself is the thing being tested

This keeps wrapper coverage intentional instead of incidental.

## Concrete Migration Scope

### 1. Internal import cleanup in UI modules

The first internal cleanup targets are:

- `src/cogstash/ui/browse.py`
- `src/cogstash/ui/settings.py`

Expected direction:

- move note/domain imports away from `cogstash.search` to the true core owner
- reduce dependency on `cogstash.ui.app` for values that can live in clearer shared ownership only if that can be done without dragging in unrelated refactors

Constraint:

- do not force a large ownership redesign in this slice
- if `ui.app` still legitimately owns a UI concern such as theme/window constants, it can continue to do so until a later slice extracts that concern cleanly

### 2. Test migration

Tests that currently import wrapper modules out of habit should move toward owning modules where they are not explicitly compatibility tests.

Likely first targets:

- `tests/ui/test_browse_extended.py`
- `tests/ui/test_settings_extended.py`
- `tests/core/test_search.py`
- selected `tests/cli/test_cli.py` imports that reference wrapper-only paths

Compatibility-focused tests such as `tests/ui/test_app_compat.py` should remain wrapper-aware if their purpose is to preserve compatibility behavior.

### 3. Wrapper-module documentation

Wrapper modules that remain should make their role explicit in module docstrings or comments:

- compatibility shim
- re-export owner
- not preferred for new internal imports

That avoids repeating the current ambiguity.

## Alternatives Considered

### 1. Remove wrappers immediately

Pros:

- cleanest architecture
- no more ambiguity

Cons:

- mixes internal cleanup with public/API breakage
- raises migration risk for tests and entrypoints
- too large for the first `#12` slice

Rejected for this slice.

### 2. Keep wrappers and migrate only internal imports

Pros:

- lower immediate risk

Cons:

- `#21` remains underspecified
- tests keep normalizing wrapper usage
- compatibility surface continues to look permanent by default

Rejected because it does not fully answer the wrapper-policy question.

### 3. Recommended: explicit compatibility shims + direct internal imports

Pros:

- resolves policy ambiguity
- improves real architecture immediately
- keeps migration risk controlled

Cons:

- wrappers still exist for now
- full cleanup remains multi-slice work

Chosen.

## Risks

### 1. Over-migrating compatibility tests

If every test is migrated away from wrappers, the compatibility surface may silently break later without detection.

Mitigation:

- preserve explicitly named compatibility tests
- only migrate tests whose purpose is implementation validation rather than API compatibility

### 2. Hidden ownership assumptions in `ui.app`

Some values imported from `ui.app` may reflect legitimate UI ownership, while others may only live there because of history.

Mitigation:

- only move clearly core-owned concepts in this slice
- defer ambiguous ownership extractions to later issues rather than forcing a large refactor here

### 3. Accidental public API break

Changing wrapper behavior too aggressively could break imports outside the direct test suite.

Mitigation:

- keep wrappers in place during this slice
- limit changes to internal imports, test migration, and wrapper documentation

## Testing Strategy

This slice should add or preserve coverage for three things:

1. internal code still works after direct-import cleanup
2. migrated tests continue to pass against owning modules
3. compatibility wrapper surfaces that intentionally remain still import and expose the expected symbols

Expected verification:

- targeted UI tests for browse/settings/app compatibility surfaces
- targeted core/CLI tests affected by import-path changes
- repository lint/type/test checks used by the project for touched areas

## Success Criteria

This slice is successful when:

- internal modules no longer rely on wrapper/facade imports where the owning layer is obvious
- wrapper modules that remain are clearly documented as compatibility shims
- a meaningful subset of tests has been migrated to owning modules
- compatibility tests remain intentional and still cover wrapper behavior where needed
- no user-facing behavior changes
- test/lint/type verification stays green for the touched scope

## Likely Files

- `src/cogstash/app.py`
- `src/cogstash/browse.py`
- `src/cogstash/settings.py`
- `src/cogstash/search.py`
- `src/cogstash/_windows.py`
- `src/cogstash/ui/browse.py`
- `src/cogstash/ui/settings.py`
- `tests/core/test_search.py`
- `tests/ui/test_browse_extended.py`
- `tests/ui/test_settings_extended.py`
- `tests/ui/test_app_compat.py`
- `tests/cli/test_cli.py`
