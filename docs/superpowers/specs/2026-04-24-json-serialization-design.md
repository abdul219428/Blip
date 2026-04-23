# JSON Serialization Helper Design

## Summary

Issue `#27` addresses repeated JSON serialization behavior across configuration and CLI code paths. The duplication is not general JSON parsing; it is the repeated output contract for pretty-printed UTF-8 JSON with Unicode preserved.

## Current Problem

Equivalent serialization behavior is repeated in multiple places:

- `src/cogstash/core/config.py` when creating a default config file
- `src/cogstash/core/config.py` when saving config data
- `src/cogstash/cli/main.py` when exporting notes as JSON
- `src/cogstash/cli/main.py` when the config wizard writes updates
- `src/cogstash/cli/main.py` when `config set` writes updates
- `src/cogstash/cli/main.py` when `config get tags` pretty-prints a JSON object

Most of these paths use the same policy:

- pretty JSON indentation
- UTF-8 writes
- Unicode preserved instead of forced ASCII escaping

The behavior is hand-written repeatedly, which makes drift easy.

## Goals

- Define one shared JSON serialization contract in `src/cogstash/core/config.py`
- Reuse it from config writes and CLI JSON-producing flows
- Keep JSON parsing behavior local to each caller
- Standardize indentation, Unicode handling, and file write encoding

## Non-Goals

- Creating a new standalone JSON utility module
- Centralizing all JSON reads or parse error handling
- Changing the data shape of config or export payloads

## Recommended Design

Add a small shared helper boundary in `src/cogstash/core/config.py`:

- `to_pretty_json(data: object) -> str`
- `write_json_file(path: Path, data: object) -> None`

Contract:

- indentation is consistent across all JSON outputs
- Unicode characters are preserved (`ensure_ascii=False`)
- file writes use UTF-8 encoding

`write_json_file()` should only own serialization and file writing. Parent directory creation should remain where it is already semantically required, rather than being hidden in every write path automatically.

## Boundary Decision

The helpers stay in `src/cogstash/core/config.py` because the issue evidence is centered on config and CLI flows, and the repeated policy is small enough that a separate module would add more indirection than value.

CLI code should import and reuse the serialization helpers rather than rebuilding `json.dumps(..., indent=2, ensure_ascii=False)` inline.

## Expected Reuse Points

The shared helpers should be used by:

- default config file creation in `load_config()`
- `save_config()`
- `_config_wizard()` when saving the edited config map
- `cmd_config()` when writing updated config keys
- `cmd_export()` JSON output path
- `cmd_config(get tags)` pretty-print output if the returned value is a dictionary

## Testing

Add or update tests to cover:

- config save preserves Unicode and writes readable JSON
- default config creation uses the same serialization contract
- CLI JSON export uses the shared formatting policy
- config set and wizard writes stay valid JSON
- pretty-print output for dictionary-valued config keys remains stable

## Risks

- Over-centralizing unrelated JSON reads would blur the boundary and add noise
- If directory creation behavior is moved carelessly, write paths could change in subtle ways
- If tests only validate parsed JSON content, formatting drift may still slip through

## Outcome

After this change, JSON serialization policy lives in one place, output behavior stays consistent across config and CLI flows, and the cleanup remains narrow enough to satisfy `#27` without introducing a new utility module.
