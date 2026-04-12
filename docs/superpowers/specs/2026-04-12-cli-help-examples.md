# CLI Help Text and Examples Spec

**Issue:** `#16` Improve CLI help text and examples for complex commands

**Problem**

CogStash CLI help is functional but too terse for commands with multiple usage modes. In particular, `edit`, `delete`, and `config` do not explain their branching behavior clearly enough in `--help`, which makes the CLI harder to discover without reading the README or source.

**Goal**

Make `cogstash edit --help`, `cogstash delete --help`, and `cogstash config --help` self-sufficient enough that a user can understand the command modes and copy a working example directly from the CLI.

## In Scope

1. Improve the built-in `argparse` help output for:
   - `cogstash edit`
   - `cogstash delete`
   - `cogstash config`
2. Add practical examples to those help surfaces.
3. Clarify positional versus `--search` usage for `edit` and `delete`.
4. Clarify `config` wizard mode, `get` / `set` usage, and key restrictions.
5. Refresh the matching README command examples so the docs stay aligned with the CLI help text.

## Out of Scope

1. Adding new CLI commands or flags.
2. Changing command behavior, parsing rules, or config semantics.
3. Refreshing help text for every subcommand.
4. Reworking README sections unrelated to the chosen commands.

## Behavior Decisions

### `edit --help`

- Must explain the two supported targeting modes:
  - note number as the first positional token
  - `--search` / `-s` keyword targeting
- Must include at least one example of each mode.
- Must make it clear that replacement text follows the selected note target.

### `delete --help`

- Must explain the two supported targeting modes:
  - positional note number
  - `--search` / `-s` keyword targeting
- Must mention confirmation behavior and `--yes`.
- Must include at least one example of number-based deletion and one search-based deletion.

### `config --help`

- Must explain that running `cogstash config` with no action starts the interactive wizard.
- Must include examples for:
  - wizard/default mode
  - `config get`
  - `config set`
- Must document that:
  - `tags` is readable via `config get` but not writable via `config set`
  - internal/non-CLI config keys are not supported through the command

## UX Constraints

- Keep help text concise enough to stay readable in a terminal.
- Favor examples over long prose.
- Do not promise behavior the CLI does not support today.
- Keep wording aligned with current command behavior and current README examples.

## Acceptance Criteria

1. Focused CLI tests assert the help output for `edit`, `delete`, and `config` includes the new examples and guidance.
2. Those tests fail before implementation and pass after implementation.
3. CLI behavior remains unchanged aside from help output.
4. README examples for `edit`, `delete`, and `config` match the intended help guidance.
5. The final verification for the implementation can rely on existing project commands only.
