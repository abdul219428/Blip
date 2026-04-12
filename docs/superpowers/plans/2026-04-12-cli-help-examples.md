# CLI Help Text and Examples Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `edit`, `delete`, and `config` help output self-sufficient with concrete examples and clear mode guidance, then align the README examples with that help.

**Architecture:** Keep this as a parser/help-text-only change in `src/cogstash/cli/main.py`, with regression coverage in `tests/cli/test_cli.py`. Do not change runtime command semantics. After the parser help is locked by tests, update the README examples for the same commands so the CLI and docs stay in sync.

**Tech Stack:** Python 3.9+, argparse, pytest, README markdown

---

## File / Artifact Map

- Modify: `src/cogstash/cli/main.py`
  - enrich subparser help for `edit`, `delete`, and `config`
  - add command descriptions / examples / restrictions without changing command behavior
- Modify: `tests/cli/test_cli.py`
  - add focused parser help tests for `edit`, `delete`, and `config`
- Modify: `README.md`
  - align examples and wording for `edit`, `delete`, and `config`
- Reference: `docs/superpowers/specs/2026-04-12-cli-help-examples.md`
  - scope, behavior, and acceptance criteria for issue `#16`

## Baseline Verification

Before implementation starts, run:

```bash
uv run pytest tests\cli\test_cli.py -v
```

Expected: PASS on the current branch before any new tests are added, so later failures can be attributed to the new red tests rather than unrelated baseline breakage.

## Task 1: Lock `edit` and `delete` help expectations with failing tests

**Files:**
- Modify: `tests/cli/test_cli.py`
- Modify: `src/cogstash/cli/main.py`

- [ ] **Step 1: Write failing `edit --help` and `delete --help` tests**

Add focused tests in `tests/cli/test_cli.py` that call `build_parser()` and capture `parser.parse_args([...,"--help"])` output.

```python
def test_edit_help_includes_examples_and_search_guidance(capsys):
    from cogstash.cli import build_parser

    parser = build_parser()
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["edit", "--help"])

    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "note number or --search" in out
    assert "cogstash edit 42 \"Updated note text\"" in out
    assert "cogstash edit --search \"installer\" \"Updated note text\"" in out


def test_delete_help_includes_confirmation_and_examples(capsys):
    from cogstash.cli import build_parser

    parser = build_parser()
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["delete", "--help"])

    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "--yes" in out
    assert "cogstash delete 42" in out
    assert "cogstash delete --search \"installer\" --yes" in out
```

- [ ] **Step 2: Run the focused tests to verify they fail**

Run:

```bash
uv run pytest tests\cli\test_cli.py -k "edit_help or delete_help" -v
```

Expected: FAIL because the current subparser help output does not yet include these examples or guidance.

- [ ] **Step 3: Implement the minimal parser help improvements for `edit` and `delete`**

Update `src/cogstash/cli/main.py` so the `edit` and `delete` subparsers use richer help text. Use `description=` and `epilog=` (with an `argparse` formatter that preserves examples cleanly) rather than changing command behavior.

Minimum target shape:

```python
p_edit = sub.add_parser(
    "edit",
    help="Edit a note by number or search",
    description="Edit an existing note by number or with --search.",
    epilog=(
        "Examples:\n"
        "  cogstash edit 42 \"Updated note text\"\n"
        "  cogstash edit --search \"installer\" \"Updated note text\""
    ),
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
```

Apply the same pattern to `delete`, including wording about confirmation and `--yes`.

- [ ] **Step 4: Re-run the focused tests to verify they pass**

Run:

```bash
uv run pytest tests\cli\test_cli.py -k "edit_help or delete_help" -v
```

Expected: PASS.

- [ ] **Step 5: Commit the parser help changes for `edit` and `delete`**

```bash
git add tests/cli/test_cli.py src/cogstash/cli/main.py
git commit -m "feat: improve edit and delete CLI help"
```

## Task 2: Lock `config --help` wizard and restriction guidance with failing tests

**Files:**
- Modify: `tests/cli/test_cli.py`
- Modify: `src/cogstash/cli/main.py`

- [ ] **Step 1: Write a failing `config --help` test**

Add a focused test in `tests/cli/test_cli.py` that verifies `config --help` documents the command modes and key restrictions.

```python
def test_config_help_includes_wizard_examples_and_key_restrictions(capsys):
    from cogstash.cli import build_parser

    parser = build_parser()
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["config", "--help"])

    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "omit action to open the wizard" in out
    assert "cogstash config" in out
    assert "cogstash config get theme" in out
    assert "cogstash config set window_size wide" in out
    assert "tags" in out
    assert "get-only" in out
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run:

```bash
uv run pytest tests\cli\test_cli.py -k "config_help" -v
```

Expected: FAIL because the current `config` help output does not yet explain wizard mode or the key restrictions.

- [ ] **Step 3: Implement the minimal `config` help improvements**

Update the `config` subparser in `src/cogstash/cli/main.py` so its help text documents:

1. default wizard mode when no action is provided
2. `get` and `set` examples
3. supported CLI-facing keys
4. that `tags` is readable but not writable via `config set`
5. that internal keys are not exposed through this command

Keep the current command behavior untouched.
Prefer deriving key lists from existing constants/helpers in `src/cogstash/cli/main.py` rather than duplicating them in multiple strings where practical.

- [ ] **Step 4: Re-run the focused test to verify it passes**

Run:

```bash
uv run pytest tests\cli\test_cli.py -k "config_help" -v
```

Expected: PASS.

- [ ] **Step 5: Commit the `config` help update**

```bash
git add tests/cli/test_cli.py src/cogstash/cli/main.py
git commit -m "feat: improve config CLI help"
```

## Task 3: Align README examples with the improved CLI help

**Files:**
- Modify: `README.md`
- Reference: `src/cogstash/cli/main.py`

- [ ] **Step 1: Update the README command examples**

Refresh the README sections for:

- `cogstash edit`
- `cogstash delete`
- `cogstash config`

Make sure they match the help output language and examples introduced in Tasks 1 and 2. Keep the docs limited to this issue’s scope.

- [ ] **Step 2: Manually verify README alignment against CLI help**

Check that the README examples match the parser help strings for the same commands and do not claim unsupported behavior.

- [ ] **Step 3: Run the focused CLI help tests again**

Run:

```bash
uv run pytest tests\cli\test_cli.py -k "edit_help or delete_help or config_help" -v
```

Expected: PASS.

- [ ] **Step 4: Commit the README alignment**

```bash
git add README.md
git commit -m "docs: align CLI help examples"
```

## Task 4: Run full verification and prepare the branch for review

**Files:**
- Modify: none
- Verify: `src/cogstash/cli/main.py`
- Verify: `tests/cli/test_cli.py`
- Verify: `README.md`

- [ ] **Step 1: Run targeted CLI tests**

Run:

```bash
uv run pytest tests\cli\test_cli.py -v
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

- [ ] **Step 3: Review the diff for accidental scope creep**

Confirm only the intended files changed:

- `src/cogstash/cli/main.py`
- `tests/cli/test_cli.py`
- `README.md`

- [ ] **Step 4: Create the implementation branch commit set**

Expected commit boundaries:

1. `feat: improve edit and delete CLI help`
2. `feat: improve config CLI help`
3. `docs: align CLI help examples`

- [ ] **Step 5: Open PR and update issue `#16`**

PR summary should call out:

1. richer help output for `edit`, `delete`, and `config`
2. wizard-mode and config-key restriction guidance
3. README alignment for those examples
