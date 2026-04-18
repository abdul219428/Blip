# Browse Filter Clarity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Browse filter state obvious with a compact active-filters summary bar, one clear-all action, and a filter-aware empty state.

**Architecture:** Keep this change localized to `src/cogstash/ui/browse.py` and existing Browse UI tests. The implementation should add lightweight UI elements on top of the current search + tag filtering flow without changing the underlying filter semantics. The clear-all action should reuse the existing state variables (`search_var`, `_active_tag`) and the existing `_apply_filters()` flow rather than introducing a new filter model.

**Tech Stack:** Python 3.9+, tkinter, pytest

---

## File / Artifact Map

- Modify: `src/cogstash/ui/browse.py`
  - add active-filter summary UI
  - add one clear-all action
  - add filter-aware empty state inside the cards area
- Modify: `tests/ui/test_browse.py`
  - add focused Browse filter-clarity tests for the new UI/state behavior
- Reference: `docs/superpowers/specs/2026-04-12-browse-filter-clarity.md`
  - approved scope and UX contract for issue `#18`

## Baseline Verification

Before implementation starts, run:

```bash
uv run pytest tests\ui\test_browse.py -v
```

Expected: PASS on the current branch before any new tests are added.

## Task 1: Lock active-filter summary behavior with failing tests

**Files:**
- Modify: `tests/ui/test_browse.py`
- Modify later: `src/cogstash/ui/browse.py`

- [ ] **Step 1: Write a failing test for hidden summary state when no filters are active**

Add a test that opens Browse with multiple notes and asserts the new summary row is absent or hidden before filters are applied.

```python
@needs_display
def test_browse_hides_filter_summary_when_unfiltered(tmp_path, tk_root):
    from cogstash.ui.app import CogStashConfig
    from cogstash.ui.browse import BrowseWindow

    notes = tmp_path / "cogstash.md"
    notes.write_text(
        "- [2026-03-26 14:30] buy milk #todo\n"
        "- [2026-03-26 11:20] meeting notes #work\n",
        encoding="utf-8",
    )

    win = BrowseWindow(tk_root, CogStashConfig(output_file=notes))

    assert win._filter_summary_frame is None or not win._filter_summary_frame.winfo_ismapped()

    win.window.destroy()
```

- [ ] **Step 2: Write a failing test for combined search + tag summary text**

Add a test that applies both a search query and tag filter, then asserts the summary bar is visible and includes both the search and tag state.

```python
@needs_display
def test_browse_shows_combined_filter_summary(tmp_path, tk_root):
    ...
    win.search_var.set("install")
    win._on_tag_filter("todo")
    win._on_search()

    assert win._filter_summary_label is not None
    summary = win._filter_summary_label.cget("text")
    assert 'Search: "install"' in summary
    assert "Tag: todo" in summary
```

- [ ] **Step 3: Write failing tests for search-only and tag-only summary states**

Add one focused test for each single-filter state so the implementation cannot skip either case:

1. search-only active summary text
2. tag-only active summary text

Both tests should assert the summary bar is visible and only mentions the active filter type for that scenario.

- [ ] **Step 4: Write a failing test for clear-all behavior**

Add a test that activates both filters, invokes the new clear action, and asserts:

1. `search_var` becomes empty
2. `_active_tag` becomes `None`
3. full note list returns

- [ ] **Step 5: Run the focused tests to verify they fail**

Run:

```bash
uv run pytest tests\ui\test_browse.py -k "filter_summary or clear_filters" -v
```

Expected: FAIL because the summary/clear-all UI does not exist yet.

- [ ] **Step 6: Commit the red tests**

```bash
git add tests/ui/test_browse.py
git commit -m "test: lock browse filter summary UX"
```

## Task 2: Implement the summary bar and clear-all action

**Files:**
- Modify: `src/cogstash/ui/browse.py`
- Existing tests: `tests/ui/test_browse.py`

- [ ] **Step 1: Add minimal UI state for the summary bar**

In `BrowseWindow`, add focused instance attributes for the new UI:

- summary frame
- summary label
- clear-filters button

Prefer explicit attributes like:

```python
self._filter_summary_frame: tk.Frame | None = None
self._filter_summary_label: tk.Label | None = None
self._clear_filters_button: tk.Button | None = None
```

- [ ] **Step 2: Add a helper that builds/updates the summary bar**

Add a helper with one responsibility, for example:

```python
def _update_filter_summary(self) -> None:
    ...
```

It should:

1. hide the summary UI when no filters are active
2. show the summary UI when search/tag filters are active
3. render combined summary text when both are active

- [ ] **Step 3: Add one clear-all action**

Add a helper such as:

```python
def _clear_filters(self) -> None:
    self.search_var.set("")
    self._active_tag = None
    self._update_pill_styles()
    self._apply_filters()
```

Keep it small and reuse the existing filter pipeline.

- [ ] **Step 4: Call the summary update from the existing filter flow**

Update `_apply_filters()` so it refreshes the summary state before rendering cards.

- [ ] **Step 5: Run the focused tests to verify they pass**

Run:

```bash
uv run pytest tests\ui\test_browse.py -k "filter_summary or clear_filters" -v
```

Expected: PASS.

- [ ] **Step 6: Commit the summary-bar implementation**

```bash
git add src/cogstash/ui/browse.py tests/ui/test_browse.py
git commit -m "feat: clarify active browse filters"
```

## Task 3: Lock filtered empty-state behavior with failing tests

**Files:**
- Modify: `tests/ui/test_browse.py`
- Modify later: `src/cogstash/ui/browse.py`

- [ ] **Step 1: Write a failing test for filter-aware empty state**

Add a test that produces zero results with active filters and asserts:

1. an empty-state message appears
2. it mentions no notes match the filters
3. it echoes the active filters
4. a clear action is visible

- [ ] **Step 2: Write a failing regression test for the unfiltered empty state**

Add a separate test that opens Browse with no notes at all and asserts the filtered empty-state wording does **not** appear when no filters are active.

This prevents the implementation from accidentally replacing the general empty state with the filtered message.

- [ ] **Step 3: Write a failing test for empty-state clear-all recovery**

Add a test that invokes the empty-state clear action and asserts the full note list returns.

- [ ] **Step 4: Run the focused tests to verify they fail**

Run:

```bash
uv run pytest tests\ui\test_browse.py -k "empty_state and filter" -v
```

Expected: FAIL because the filtered empty state is not implemented yet.

- [ ] **Step 5: Commit the red tests**

```bash
git add tests/ui/test_browse.py
git commit -m "test: lock browse filtered empty state"
```

## Task 4: Implement the filtered empty state

**Files:**
- Modify: `src/cogstash/ui/browse.py`
- Existing tests: `tests/ui/test_browse.py`

- [ ] **Step 1: Add minimal empty-state UI rendering**

Update `_render_cards()` so when `self._visible_cards` is empty:

1. filtered-zero-result states render a dedicated empty-state block
2. unfiltered-zero-result states do **not** render the filtered empty-state wording or clear-filters action

- [ ] **Step 2: Reuse the active-filter summary wording**

Avoid duplicating logic for describing filters. Extract a small helper if needed, e.g.:

```python
def _format_filter_summary(self) -> str | None:
    ...
```

Use it for both the summary bar and the filtered empty state.

- [ ] **Step 3: Reuse the same clear-all action**

The empty-state button should call the same `_clear_filters()` helper used by the summary bar.

- [ ] **Step 4: Run focused Browse tests**

Run:

```bash
uv run pytest tests\ui\test_browse.py -k "filter_summary or clear_filters or empty_state" -v
```

Expected: PASS.

- [ ] **Step 5: Commit the empty-state implementation**

```bash
git add src/cogstash/ui/browse.py tests/ui/test_browse.py
git commit -m "feat: improve browse empty filter state"
```

## Task 5: Full verification and PR preparation

**Files:**
- Verify: `src/cogstash/ui/browse.py`
- Verify: `tests/ui/test_browse.py`

- [ ] **Step 1: Run focused Browse tests**

Run:

```bash
uv run pytest tests\ui\test_browse.py -v
```

Expected: PASS.

- [ ] **Step 2: Run full repo verification**

Run:

```bash
uv run pytest tests\ -q
uv run ruff check src\ tests\
uv run mypy src\cogstash\
```

Expected: PASS.

- [ ] **Step 3: Review the diff for scope control**

Confirm the branch stays focused on:

- `src/cogstash/ui/browse.py`
- `tests/ui/test_browse.py`
- issue `#18` spec/plan docs

- [ ] **Step 4: Open PR and update issue `#18`**

PR summary should call out:

1. active filter summary bar
2. one clear-all action
3. filter-aware empty state
