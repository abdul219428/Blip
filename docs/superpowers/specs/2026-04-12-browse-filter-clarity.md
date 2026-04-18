# Browse Filter Clarity Spec

**Issue:** `#18` Improve Browse filter clarity and reset affordances

**Problem**

The Browse window supports combined search and tag filtering, but the active filter state is mostly implicit. Users can end up in filtered states that are not obvious, and when no notes match they are not given a clear recovery path.

**Goal**

Make active Browse filters obvious, give users one clear way to reset them, and make the filtered empty state explain what happened and how to recover.

## In Scope

1. Show active filter state more clearly when a search query or tag filter is active.
2. Add one obvious **Clear filters** action that resets both the search query and active tag together.
3. Improve the no-results state when filters are active so it:
   - explains that filters produced no matches
   - echoes the active filters
   - offers the same **Clear filters** action
4. Keep the interaction lightweight and consistent with the current Browse layout.

## Out of Scope

1. Redesigning the search field or tag pill row.
2. Adding separate per-filter clear controls.
3. Changing filter logic, search semantics, or tag semantics.
4. Reworking card layout, context menu behavior, or note actions.

## Agreed UX Direction

The first pass should use a **compact summary bar** directly below the existing search + tag controls.

### Active filter summary bar

- Hidden when no filters are active.
- Visible when:
  - the search query is non-empty, or
  - a tag filter is active.
- Shows a concise readable summary of the active filters.
- Includes a single **Clear filters** action that:
  - clears the search query
  - clears the active tag filter
  - refreshes the visible note list

Example summary patterns:

- `Filters active: Search: "install"`
- `Filters active: Tag: todo`
- `Filters active: Search: "install" · Tag: todo`

### Filtered empty state

- When no notes match active filters, the cards area should show a dedicated filtered empty state instead of a silent blank list.
- It must:
  - say no notes match the current filters
  - mention the active filters
  - offer **Clear filters**
- This empty state should only appear for filtered zero-result states, not for the general “there are no notes at all” case.

## Behavior Details

1. **No filters active**
   - summary bar hidden
   - normal card list behavior
   - existing footer still updates normally

2. **Search only active**
   - summary bar visible with the search text
   - clear action resets the search query to empty and returns to the unfiltered list

3. **Tag only active**
   - summary bar visible with the tag name
   - clear action clears the active tag and returns to the unfiltered list

4. **Search + tag active**
   - summary bar visible with both parts in one line
   - clear action resets both together

5. **Filtered zero-result state**
   - cards area shows filter-aware empty-state content
   - clear action is available there too

## UX Constraints

- Keep the change visually small and fast to understand.
- Do not add multiple competing reset affordances in this pass.
- Do not introduce modal dialogs for clearing filters.
- Keep wording concise and recovery-oriented.

## Testing Expectations

1. Add UI tests for summary-bar visibility/content across:
   - no filters
   - search only
   - tag only
   - combined search + tag
2. Add UI tests for the **Clear filters** action resetting both filter inputs.
3. Add UI tests for the filtered empty state and its clear action.
4. Preserve existing Browse filtering behavior and current Browse tests.
