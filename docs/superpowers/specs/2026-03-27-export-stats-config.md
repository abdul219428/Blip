# Phase 8: Export, Stats, Config — Design Spec

## Overview

Three new CLI commands for CogStash:

1. **`cogstash export`** — Export all notes to JSON, CSV, or Markdown
2. **`cogstash stats`** — Extended statistics summary
3. **`cogstash config`** — Interactive wizard + quick get/set

## Design Decisions

### Export

| Decision | Choice |
|----------|--------|
| Formats | JSON, CSV, Markdown |
| Output | Auto-named file in cwd (e.g., `cogstash-export-2026-03-27.json`) |
| Override | `--output FILE` flag to write to specific path |
| Filtering | None — always exports all notes |
| Format flag | `--format {json,csv,md}`, default `json` |

### Stats

| Decision | Choice |
|----------|--------|
| Level | Extended summary |
| Sections | Totals, date range, done/pending %, avg/longest length |
|  | Weekly activity (this week, last week, avg per week, busiest day) |
|  | Tag breakdown with bar charts and percentages |
|  | Streaks (current + longest) |
| Color | ANSI colors when stdout is a TTY |

### Config

| Decision | Choice |
|----------|--------|
| Default action | Interactive wizard (all 6 settings) |
| Quick access | `cogstash config get KEY` / `cogstash config set KEY VALUE` |
| Wizard scope | All settings: hotkey, theme, window_size, output_file, log_file, tags |
| Validation | theme validated against THEMES dict, window_size against WINDOW_SIZES |
| Tags in wizard | Directs user to edit JSON directly (complex nested structure) |
