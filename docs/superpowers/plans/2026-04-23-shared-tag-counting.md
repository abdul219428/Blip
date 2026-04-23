# Shared Tag Counting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove duplicated tag-counting logic by defining one shared helper in `src/cogstash/core/notes.py` and reusing it from both note statistics and the CLI tag-listing flow.

**Architecture:** Keep tag aggregation owned by the notes layer. Add one focused helper in `src/cogstash/core/notes.py`, consume it from `compute_stats()` and `cmd_tags()`, and keep formatting concerns local to `src/cogstash/cli/main.py`. Do not create a new helper module or widen the refactor beyond the duplicated counting path.

**Tech Stack:** Python 3.9+, pytest

---

## File / Artifact Map

- Modify: `src/cogstash/core/notes.py`
  - add the shared tag-count helper
  - reuse it inside `compute_stats()`
- Modify: `src/cogstash/cli/main.py`
  - replace inline tag counting in `cmd_tags()` with the shared helper
- Modify: `tests/`
  - add focused tests for helper behavior, stats integration, and CLI ordering
- Reference: `docs/superpowers/specs/2026-04-23-shared-tag-counting-design.md`
  - scope and contract for issue `#26`

## Baseline Verification

Before implementation starts, run:

```bash
uv run pytest tests -k "tag or stats" -q
```

Expected: existing tag and stats coverage should pass before new tests are added, so any later failure is attributable to the `#26` change set.

## Task 1: Lock the shared tag-count contract with focused tests

**Files:**
- Modify: relevant test modules under `tests/`

- [ ] **Step 1: Identify the current test homes for notes stats and CLI tag output**

Find the most local existing tests that cover:

- `compute_stats()`
- `cmd_tags()`

Add new `#26` coverage there unless the existing files are clearly the wrong boundary.

- [ ] **Step 2: Write failing tests for the shared counting contract**

Add focused tests that cover:

- empty input returns `{}`
- multi-note aggregation returns correct counts
- ties are ordered alphabetically by tag name
- higher counts sort before lower counts

If the helper is public, test it directly from `cogstash.core.notes`.

- [ ] **Step 3: Write integration tests for both consumers**

Add or extend tests to verify:

- `compute_stats(notes)["tag_counts"]` matches the shared ordering contract
- `cmd_tags()` renders tags in the same order without recomputing counts inline

- [ ] **Step 4: Run the focused tests to confirm red state**

Run only the new or closely related tests.

Expected: FAIL before implementation because the helper does not exist yet and/or current inline logic is still duplicated.

## Task 2: Implement the shared helper in the notes layer

**Files:**
- Modify: `src/cogstash/core/notes.py`

- [ ] **Step 1: Add the shared helper**

Implement a focused helper in `src/cogstash/core/notes.py`:

```python
def count_tags(notes: list[Note]) -> dict[str, int]:
    ...
```

Contract:

- counts every tag occurrence across notes
- returns deterministic order
- sort rule: descending count, then ascending tag name

- [ ] **Step 2: Reuse the helper inside `compute_stats()`**

Replace the inline `Counter` loop in `compute_stats()` with a call to the new helper.

- [ ] **Step 3: Keep the API surface intentional**

If the helper is part of the public notes-layer contract, export it consistently alongside the other public names. Avoid exposing additional low-value helpers.

- [ ] **Step 4: Run focused notes-layer tests**

Run the helper and stats-related tests.

Expected: PASS.

- [ ] **Step 5: Commit the notes-layer refactor**

Expected commit:

```bash
git add src/cogstash/core/notes.py tests/...
git commit -m "refactor: share tag counting logic"
```

## Task 3: Replace CLI duplication with the shared contract

**Files:**
- Modify: `src/cogstash/cli/main.py`
- Modify: CLI-facing tests under `tests/`

- [ ] **Step 1: Update `cmd_tags()` to consume the helper**

Remove the inline counting dictionary and use the shared notes-layer helper instead.

Keep unchanged:

- empty-state message
- CLI formatting
- pluralization
- color handling

- [ ] **Step 2: Re-run focused CLI tests**

Run only the `cmd_tags()`-related coverage.

Expected: PASS with output ordering preserved by the shared helper contract.

- [ ] **Step 3: Review for accidental behavior drift**

Confirm the CLI still:

- prints `No tags found.` when appropriate
- aligns counts and labels the same way as before
- only changes the counting source, not presentation behavior

- [ ] **Step 4: Commit the CLI reuse change if it is separate from Task 2**

Expected commit:

```bash
git add src/cogstash/cli/main.py tests/...
git commit -m "refactor: reuse shared tag counts in cli"
```

## Task 4: Run verification and prepare for review

**Files:**
- Verify: `src/cogstash/core/notes.py`
- Verify: `src/cogstash/cli/main.py`
- Verify: affected tests

- [ ] **Step 1: Run targeted verification**

Run:

```bash
uv run pytest tests -k "tag or stats" -q
```

Expected: PASS.

- [ ] **Step 2: Run quality checks for touched files**

Run the relevant linter/type-check commands for the modified scope.

Expected: PASS.

- [ ] **Step 3: Review the diff for scope control**

Confirm the change remains limited to:

- shared tag counting helper
- `compute_stats()` reuse
- `cmd_tags()` reuse
- focused regression tests

- [ ] **Step 4: Summarize the branch outcome for issue `#26`**

Final review summary should call out:

1. one shared tag-count contract in the notes layer
2. stats and CLI both reuse it
3. deterministic ordering is covered by tests
