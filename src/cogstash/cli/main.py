from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

from cogstash.core import (
    VALID_THEMES,
    VALID_WINDOW_SIZES,
    CogStashConfig,
    MutationStatus,
    append_note_to_file,
    compute_stats,
    count_tags,
    delete_note,
    edit_note,
    filter_by_tag,
    get_default_config_path,
    load_config,
    merge_tags,
    parse_notes,
    safe_print,
    search_notes,
)
from cogstash.core.config import to_pretty_json, write_json_file
from cogstash.core.notes import Note

from .formatting import (
    ANSI_BOLD,
    ANSI_DIM,
    ANSI_RESET,
    DEFAULT_ANSI_TAG,
    build_ansi_tag_map,
    format_note,
    stream_is_interactive,
    stream_supports_color,
)

VALID_CONFIG_KEYS = {"hotkey", "theme", "window_size", "output_file", "log_file", "tags"}
CONFIG_GET_KEYS = tuple(sorted(VALID_CONFIG_KEYS))
CONFIG_SET_KEYS = tuple(key for key in CONFIG_GET_KEYS if key != "tags")


class _MultilineHelpFormatter(argparse.RawDescriptionHelpFormatter):
    def _split_lines(self, text: str, width: int) -> list[str]:
        if "\n" in text:
            return text.splitlines()
        return argparse.HelpFormatter._split_lines(self, text, width)


def _output_file(config: CogStashConfig) -> Path:
    output_file = config.output_file
    assert output_file is not None, "output_file should be set by CogStashConfig"
    return output_file


def _apply_tag_filter(notes: list[Note], tag: str | None) -> list[Note]:
    """Optionally restrict a note list to one tag."""
    if not tag:
        return notes
    return filter_by_tag(notes, tag)


def cmd_recent(args, config: CogStashConfig, ansi_tag=None):
    """Show the most recent N notes."""
    tag = getattr(args, "tag", None)
    notes = _apply_tag_filter(parse_notes(_output_file(config)), tag)
    if not notes:
        if tag:
            safe_print(f"No notes found for tag #{tag}.")
        else:
            safe_print("No notes found.")
        return

    use_color = stream_supports_color(sys.stdout)
    newest_first = list(reversed(notes))
    limited = newest_first[:args.limit] if args.limit > 0 else newest_first

    for note in limited:
        safe_print(format_note(note, use_color, ansi_tag))


def cmd_search(args, config: CogStashConfig, ansi_tag=None):
    """Search notes by keyword."""
    tag = getattr(args, "tag", None)
    notes = _apply_tag_filter(parse_notes(_output_file(config)), tag)
    results = search_notes(notes, args.query)

    if not results:
        if tag:
            safe_print(f"No matching notes for tag #{tag}.")
        else:
            safe_print("No matching notes.")
        return

    use_color = stream_supports_color(sys.stdout)
    newest_first = list(reversed(results))
    limited = newest_first[:args.limit] if args.limit > 0 else newest_first

    for note in limited:
        safe_print(format_note(note, use_color, ansi_tag))


def cmd_tags(args, config: CogStashConfig, ansi_tag=None):
    """List all tags with note counts."""
    tag_map = ansi_tag or DEFAULT_ANSI_TAG
    notes = parse_notes(_output_file(config))
    tag_counts = count_tags(notes)

    if not tag_counts:
        safe_print("No tags found.")
        return

    use_color = stream_supports_color(sys.stdout)
    max_len = max(len(f"#{tag}") for tag in tag_counts)

    for tag, count in tag_counts.items():
        label = f"#{tag}"
        noun = "note" if count == 1 else "notes"
        if use_color:
            color = tag_map.get(tag, "")
            reset = ANSI_RESET if color else ""
            safe_print(f"  {color}{label:<{max_len}}{reset}  {ANSI_BOLD}{count}{ANSI_RESET} {noun}")
        else:
            safe_print(f"  {label:<{max_len}}  {count} {noun}")


def cmd_add(args, config: CogStashConfig, ansi_tag=None):
    """Add a note from the command line."""
    if args.text:
        text = " ".join(args.text)
    else:
        stdin = sys.stdin
        if stdin is None or stream_is_interactive(stdin):
            safe_print("Error: provide note text as argument or pipe via stdin.", file=sys.stderr)
            sys.exit(1)
        text = stdin.read()

    smart_tags, _ = merge_tags(config)
    ok = append_note_to_file(text, _output_file(config), smart_tags)
    if not ok:
        safe_print("Error: failed to save note.", file=sys.stderr)
        sys.exit(1)


def _find_note(
    config: CogStashConfig,
    number: int | None = None,
    search: str | None = None,
    ansi_tag: dict[str, str] | None = None,
) -> Note | None:
    """Find a note by number or search. Prints errors and returns None on failure."""
    notes = parse_notes(_output_file(config))
    if number is not None:
        for note in notes:
            if note.index == number:
                return note
        safe_print(f"Error: note #{number} not found.", file=sys.stderr)
        return None
    if search is not None:
        results = search_notes(notes, search)
        if len(results) == 1:
            return results[0]
        if len(results) == 0:
            safe_print(f"Error: no notes match '{search}'.", file=sys.stderr)
            return None
        use_color = stream_supports_color(sys.stdout)
        safe_print(f"Multiple matches ({len(results)}). Use a note number instead:", file=sys.stderr)
        for note in results:
            safe_print(f"  {note.index}: {format_note(note, use_color, ansi_tag)}", file=sys.stderr)
        return None
    safe_print("Error: provide a note number or --search.", file=sys.stderr)
    return None


def cmd_edit(args, config: CogStashConfig, ansi_tag=None):
    """Edit a note's text."""
    number = None
    text_parts = list(args.args) if args.args else []

    if not args.search and text_parts and text_parts[0].isdigit():
        number = int(text_parts.pop(0))
    elif not args.search:
        safe_print("Error: provide a note number or --search.", file=sys.stderr)
        sys.exit(1)

    if not text_parts:
        safe_print("Error: no replacement text provided.", file=sys.stderr)
        sys.exit(1)

    note = _find_note(config, number=number, search=args.search, ansi_tag=ansi_tag)
    if note is None:
        sys.exit(1)

    new_text = " ".join(text_parts)
    result = edit_note(_output_file(config), note, new_text)
    if result is MutationStatus.SUCCESS:
        safe_print(f"Note {note.index} updated.")
        return
    if result is MutationStatus.STALE_NOTE:
        safe_print("Error: note changed on disk; reload and try again.", file=sys.stderr)
        sys.exit(1)
    if result is MutationStatus.INVALID_INPUT:
        safe_print("Error: no replacement text provided.", file=sys.stderr)
        sys.exit(1)
    if result is MutationStatus.IO_ERROR:
        safe_print("Error: failed to update note.", file=sys.stderr)
        sys.exit(1)
    safe_print("Error: could not update note.", file=sys.stderr)
    sys.exit(1)


def cmd_delete(args, config: CogStashConfig, ansi_tag=None):
    """Delete a note."""
    note = _find_note(config, number=args.number, search=args.search, ansi_tag=ansi_tag)
    if note is None:
        sys.exit(1)

    if not args.yes:
        preview = note.text[:60] + ("..." if len(note.text) > 60 else "")
        answer = input(f'Delete note {note.index}: "{preview}"? [y/N] ')
        if answer.lower() != "y":
            safe_print("Cancelled.")
            return

    result = delete_note(_output_file(config), note)
    if result is MutationStatus.SUCCESS:
        safe_print(f"Note {note.index} deleted.")
        return
    if result is MutationStatus.STALE_NOTE:
        safe_print("Error: note changed on disk; reload and try again.", file=sys.stderr)
        sys.exit(1)
    if result is MutationStatus.IO_ERROR:
        safe_print("Error: failed to delete note.", file=sys.stderr)
        sys.exit(1)
    safe_print("Error: could not delete note.", file=sys.stderr)
    sys.exit(1)


def _write_export_file(out_path: Path, export_format: str, notes: list[Note], today: str) -> None:
    import csv

    try:
        if export_format == "json":
            data = [
                {
                    "index": note.index,
                    "timestamp": note.timestamp.strftime("%Y-%m-%d %H:%M"),
                    "text": note.text,
                    "tags": note.tags,
                    "is_done": note.is_done,
                }
                for note in notes
            ]
            write_json_file(out_path, data)
        elif export_format == "csv":
            with open(out_path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["index", "timestamp", "text", "tags", "is_done"])
                writer.writeheader()
                for note in notes:
                    writer.writerow(
                        {
                            "index": note.index,
                            "timestamp": note.timestamp.strftime("%Y-%m-%d %H:%M"),
                            "text": note.text,
                            "tags": ";".join(note.tags),
                            "is_done": note.is_done,
                        }
                    )
        else:
            lines = ["# CogStash Export\n\n", f"*Exported {len(notes)} notes on {today}*\n\n"]
            for note in notes:
                ts = note.timestamp.strftime("%Y-%m-%d %H:%M")
                tags = " ".join(f"`#{tag}`" for tag in note.tags) if note.tags else ""
                status = "☑" if note.is_done else ""
                line = f"- **[{ts}]** {status} {note.text}"
                if tags:
                    line += f"  {tags}"
                lines.append(line + "\n")
            out_path.write_text("".join(lines), encoding="utf-8")
    except OSError:
        safe_print(f"Error: failed to export notes to {out_path}.", file=sys.stderr)
        sys.exit(1)


def cmd_export(args, config: CogStashConfig, ansi_tag=None):
    """Export all notes to JSON, CSV, or Markdown."""
    tag = getattr(args, "tag", None)
    notes = _apply_tag_filter(parse_notes(_output_file(config)), tag)
    if not notes:
        if tag:
            safe_print(f"No notes found for tag #{tag}.")
        else:
            safe_print("No notes to export.")
        return

    today = datetime.now().strftime("%Y-%m-%d")
    ext = {"json": "json", "csv": "csv", "md": "md"}[args.format]
    out_path = Path(args.output) if args.output else Path(f"cogstash-export-{today}.{ext}")
    _write_export_file(out_path, args.format, notes, today)
    safe_print(f"Exported {len(notes)} notes → {out_path}")


def cmd_stats(args, config: CogStashConfig, ansi_tag=None):
    """Display extended note statistics."""
    notes = parse_notes(_output_file(config))
    if not notes:
        safe_print("No notes found.")
        return

    stats = compute_stats(notes)
    out = sys.stdout if sys.stdout is not None else sys.__stdout__
    if out is None:
        return

    use_color = stream_supports_color(out)

    def c(code, text):
        return f"{code}{text}{ANSI_RESET}" if use_color else str(text)

    def emit(*items, **kwargs):
        safe_print(*items, file=out, **kwargs)

    accent = "\033[36m"
    emit(c(accent, "📊 CogStash Stats"))
    emit(f"📝 Total notes: {c(ANSI_BOLD, stats['total'])}")

    if stats["first_date"] and stats["last_date"]:
        first = stats["first_date"].strftime("%Y-%m-%d")
        last = stats["last_date"].strftime("%Y-%m-%d")
        span = (stats["last_date"].date() - stats["first_date"].date()).days
        emit(f"📅 Date range: {c(ANSI_DIM, first)} → {c(ANSI_DIM, last)} {c(ANSI_DIM, f'({span} days)')}")

    done_pct = round(stats["done"] / stats["total"] * 100) if stats["total"] else 0
    pend_pct = 100 - done_pct
    emit(
        f"✅ Done: {c(ANSI_BOLD, stats['done'])} ({done_pct}%) │ "
        f"☐ Pending: {c(ANSI_BOLD, stats['pending'])} ({pend_pct}%)"
    )
    avg_length_label = f"{stats['avg_length']} chars"
    longest_label = f"{stats['longest']} chars"
    emit(f"📏 Avg length: {c(ANSI_DIM, avg_length_label)} │ Longest: {c(ANSI_DIM, longest_label)}")

    emit(f"\n{c(accent, '📈 Activity')}")
    emit(f"  This week: {c(ANSI_BOLD, stats['notes_this_week'])} notes │ Last week: {c(ANSI_BOLD, stats['notes_last_week'])} notes")
    if stats["busiest_day"]:
        emit(f"  Most active day: {stats['busiest_day']}")
    emit(f"  Avg per week: {c(ANSI_BOLD, stats['avg_per_week'])} notes")

    tag_counts = stats["tag_counts"]
    if tag_counts:
        emit(f"\n{c(accent, '🏷️  Tags')} ({len(tag_counts)} unique)")
        tag_map = ansi_tag or DEFAULT_ANSI_TAG
        max_count = max(tag_counts.values())
        for tag, count in tag_counts.items():
            bar_len = round(count / max_count * 10)
            bar = "█" * bar_len + "░" * (10 - bar_len)
            pct = round(count / stats["total"] * 100)
            color = tag_map.get(tag, "")
            reset = ANSI_RESET if color and use_color else ""
            tag_label = f"{color}#{tag}{reset}" if use_color else f"#{tag}"
            emit(f"  {tag_label} · {count} notes · {c(ANSI_DIM, f'{bar} {pct}%')}")

    emit(f"\n{c(accent, '🔥 Streaks')}")
    current_streak_label = f"{stats['current_streak']} days"
    longest_streak_label = f"{stats['longest_streak']} days"
    emit(f"  Current streak: {c(ANSI_BOLD, current_streak_label)}")
    emit(f"  Longest streak: {c(ANSI_BOLD, longest_streak_label)}")


def _get_valid_themes() -> list[str]:
    return sorted(VALID_THEMES)


def _get_valid_window_sizes() -> list[str]:
    return sorted(VALID_WINDOW_SIZES)


def _config_wizard(config: CogStashConfig, config_path: Path) -> None:
    """Interactive configuration wizard — walks through all settings."""
    import json as json_mod

    valid_themes = _get_valid_themes()
    valid_sizes = _get_valid_window_sizes()

    data = {}
    if config_path.exists():
        try:
            data = json_mod.loads(config_path.read_text(encoding="utf-8"))
        except (json_mod.JSONDecodeError, OSError):
            data = {}

    safe_print("⚙️  CogStash Configuration Wizard")
    safe_print("Press Enter to keep current value\n")

    safe_print("❶ Hotkey")
    safe_print(f"  Current: {config.hotkey}")
    value = input("  New hotkey: ").strip()
    if value:
        data["hotkey"] = value

    safe_print(f"\n❷ Theme [{' / '.join(valid_themes)}]")
    safe_print(f"  Current: {config.theme}")
    value = input("  Select theme: ").strip()
    if value:
        if value not in valid_themes:
            safe_print(f"  ⚠ Unknown theme '{value}', keeping {config.theme}")
        else:
            data["theme"] = value

    safe_print(f"\n❸ Window Size [{' / '.join(valid_sizes)}]")
    safe_print(f"  Current: {config.window_size}")
    value = input("  Select size: ").strip()
    if value:
        if value not in valid_sizes:
            safe_print(f"  ⚠ Unknown size '{value}', keeping {config.window_size}")
        else:
            data["window_size"] = value

    safe_print("\n❹ Notes File")
    safe_print(f"  Current: {config.output_file}")
    value = input("  New path: ").strip()
    if value:
        data["output_file"] = value

    safe_print("\n❺ Log File")
    safe_print(f"  Current: {config.log_file}")
    value = input("  New path: ").strip()
    if value:
        data["log_file"] = value

    safe_print("\n❻ Custom Tags")
    if config.tags:
        safe_print(f"  Current tags: {' '.join(f'#{name}' for name in config.tags)}")
    else:
        safe_print("  No custom tags configured")
    value = input("  Add/remove tags? (y/N) ").strip().lower()
    if value == "y":
        safe_print("  Edit tags in ~/.cogstash.json directly (JSON format)")

    config_path.parent.mkdir(parents=True, exist_ok=True)
    write_json_file(config_path, data)
    safe_print(f"\n✅ Config saved to {config_path}")


def cmd_config(args, config: CogStashConfig, ansi_tag=None, config_path: Path | None = None):
    """View or modify CogStash configuration."""
    import json as json_mod

    if config_path is None:
        config_path = get_default_config_path()

    if args.action is None:
        _config_wizard(config, config_path)
        return

    config_map = {
        "hotkey": config.hotkey,
        "theme": config.theme,
        "window_size": config.window_size,
        "output_file": str(config.output_file),
        "log_file": str(config.log_file),
        "tags": config.tags,
    }

    if args.action == "get":
        if args.key not in VALID_CONFIG_KEYS:
            safe_print(f"Error: unknown key '{args.key}'. Valid: {', '.join(sorted(VALID_CONFIG_KEYS))}", file=sys.stderr)
            sys.exit(1)
        value = config_map[args.key]
        if isinstance(value, dict):
            safe_print(to_pretty_json(value))
        else:
            safe_print(value)
        return

    if args.key not in VALID_CONFIG_KEYS:
        safe_print(f"Error: unknown key '{args.key}'. Valid: {', '.join(sorted(VALID_CONFIG_KEYS))}", file=sys.stderr)
        sys.exit(1)
    if args.key == "tags":
        safe_print("Error: use the wizard to manage tags, or edit ~/.cogstash.json directly.", file=sys.stderr)
        sys.exit(1)

    valid_themes = _get_valid_themes()
    valid_sizes = _get_valid_window_sizes()
    if args.key == "theme" and args.value not in valid_themes:
        safe_print(f"Error: invalid theme '{args.value}'. Valid: {', '.join(valid_themes)}", file=sys.stderr)
        sys.exit(1)
    if args.key == "window_size" and args.value not in valid_sizes:
        safe_print(f"Error: invalid window_size '{args.value}'. Valid: {', '.join(valid_sizes)}", file=sys.stderr)
        sys.exit(1)

    data = {}
    if config_path.exists():
        try:
            data = json_mod.loads(config_path.read_text(encoding="utf-8"))
        except (json_mod.JSONDecodeError, OSError):
            data = {}
    data[args.key] = args.value
    write_json_file(config_path, data)
    safe_print(f"{args.key} = {args.value}")


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser with subcommands."""
    from importlib.metadata import PackageNotFoundError, version

    try:
        package_version = version("cogstash")
    except PackageNotFoundError:
        package_version = "0.0.0-unknown"

    parser = argparse.ArgumentParser(
        prog="cogstash",
        description="CogStash — query your brain dump from the terminal.",
    )
    parser.add_argument("--version", "-V", action="version", version=f"cogstash {package_version}")
    sub = parser.add_subparsers(dest="command")

    p_recent = sub.add_parser("recent", help="Show latest notes")
    p_recent.add_argument("--limit", type=int, default=20, help="Max notes to show (default: 20)")
    p_recent.add_argument("--tag", help="Only include notes with this tag")
    p_recent.set_defaults(func=cmd_recent)

    p_search = sub.add_parser("search", help="Search notes by keyword")
    p_search.add_argument("query", help="Search term")
    p_search.add_argument("--limit", type=int, default=20, help="Max results (default: 20)")
    p_search.add_argument("--tag", help="Only search within notes with this tag")
    p_search.set_defaults(func=cmd_search)

    p_tags = sub.add_parser("tags", help="List all tags with counts")
    p_tags.set_defaults(func=cmd_tags)

    p_add = sub.add_parser("add", help="Add a note from the CLI")
    p_add.add_argument("text", nargs="*", help="Note text (or pipe via stdin)")
    p_add.set_defaults(func=cmd_add)

    p_edit = sub.add_parser(
        "edit",
        help="Edit a note's text",
        description=(
            "Edit a note's text.\n\n"
            "Use a note number or --search to target the note.\n"
            "When using --search, the replacement text follows the search term."
        ),
        epilog=(
            "Examples:\n"
            '  cogstash edit 42 "Updated note text"\n'
            '  cogstash edit --search "installer" "Updated note text"'
        ),
        formatter_class=_MultilineHelpFormatter,
    )
    p_edit.add_argument("args", nargs="*", help="Note number followed by new text")
    p_edit.add_argument("--search", "-s", help="Find note by keyword instead of number")
    p_edit.set_defaults(func=cmd_edit)

    p_delete = sub.add_parser(
        "delete",
        help="Delete a note",
        description=(
            "Delete a note.\n\n"
            "Use a note number or --search to target the note.\n"
            "The command asks for confirmation unless --yes is provided."
        ),
        epilog=(
            "Examples:\n"
            "  cogstash delete 42\n"
            '  cogstash delete --search "installer" --yes'
        ),
        formatter_class=_MultilineHelpFormatter,
    )
    p_delete.add_argument("number", type=int, nargs="?", default=None, help="Note number")
    p_delete.add_argument("--search", "-s", help="Find note by keyword")
    p_delete.add_argument("--yes", "-y", action="store_true", help="Skip confirmation")
    p_delete.set_defaults(func=cmd_delete)

    p_export = sub.add_parser("export", help="Export all notes to file")
    p_export.add_argument("--format", "-f", choices=["json", "csv", "md"], default="json", help="Export format (default: json)")
    p_export.add_argument("--output", "-o", help="Output file path (default: auto-named)")
    p_export.add_argument("--tag", help="Only export notes with this tag")
    p_export.set_defaults(func=cmd_export)

    p_stats = sub.add_parser("stats", help="Show note statistics")
    p_stats.set_defaults(func=cmd_stats)

    p_config = sub.add_parser(
        "config",
        help="View or set configuration",
        description=(
            "View configuration values, update supported keys, or launch the interactive wizard.\n\n"
            "CogStash config with no action starts the interactive wizard.\n"
            "Press Enter to keep current value.\n"
            f"Readable keys: {', '.join(CONFIG_GET_KEYS)}\n"
            f"Writable via config set: {', '.join(CONFIG_SET_KEYS)}\n"
            "Tags are not writable via config set.\n"
            "Internal bookkeeping keys are not exposed through this command."
        ),
        epilog=(
            "Examples:\n"
            "  cogstash config\n"
            "  cogstash config get theme\n"
            "  cogstash config set window_size wide"
        ),
        formatter_class=_MultilineHelpFormatter,
    )
    p_config.add_argument("action", nargs="?", choices=["get", "set"], default=None, help="Action: get or set (omit for wizard)")
    p_config.add_argument("key", nargs="?", help="Config key")
    p_config.add_argument("value", nargs="?", help="New value (for set)")
    p_config.set_defaults(func=cmd_config)

    return parser


def cli_main(argv: list[str]) -> None:
    """Entry point for CLI subcommands."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, "func"):
        parser.print_help()
        return

    config_path = get_default_config_path()
    config = load_config(config_path)
    _, tag_colors = merge_tags(config)
    ansi_tag = build_ansi_tag_map(tag_colors)

    if args.func == cmd_config:
        args.func(args, config, ansi_tag, config_path=config_path)
    else:
        args.func(args, config, ansi_tag)


__all__ = [
    "VALID_CONFIG_KEYS",
    "build_parser",
    "cli_main",
    "cmd_add",
    "cmd_config",
    "cmd_delete",
    "cmd_edit",
    "cmd_export",
    "cmd_recent",
    "cmd_search",
    "cmd_stats",
    "cmd_tags",
]
