"""cogstash_cli.py — CLI subcommands for querying CogStash notes.

Provides `recent`, `search`, and `tags` commands with ANSI-colored output.
All data operations delegate to cogstash_search.py.
"""

from __future__ import annotations

import sys
import argparse
from datetime import datetime
from pathlib import Path

from cogstash_search import Note, parse_notes, search_notes, edit_note, delete_note

# ANSI escape codes — approximations of TAG_COLORS hex values
ANSI_RESET = "\033[0m"
ANSI_BOLD = "\033[1m"
ANSI_DIM = "\033[90m"
ANSI_STRIKE_DIM = "\033[9;90m"

DEFAULT_ANSI_TAG = {
    "urgent": "\033[31m",
    "important": "\033[33m",
    "idea": "\033[32m",
    "todo": "\033[36m",
}


def hex_to_ansi(hex_color: str) -> str:
    """Map a hex color to the nearest 8-color ANSI escape code."""
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    ansi_map = [
        (0, 0, 0, "\033[30m"),
        (255, 0, 0, "\033[31m"),
        (0, 255, 0, "\033[32m"),
        (255, 255, 0, "\033[33m"),
        (0, 0, 255, "\033[34m"),
        (255, 0, 255, "\033[35m"),
        (0, 255, 255, "\033[36m"),
        (255, 255, 255, "\033[37m"),
    ]
    best = min(ansi_map, key=lambda c: (c[0] - r) ** 2 + (c[1] - g) ** 2 + (c[2] - b) ** 2)
    return best[3]


def build_ansi_tag_map(tag_colors: dict[str, str]) -> dict[str, str]:
    """Build ANSI color map from hex tag colors. All tags converted from hex."""
    return {tag: hex_to_ansi(color) for tag, color in tag_colors.items()}


def format_note(note: Note, use_color: bool = True, ansi_tag: dict[str, str] | None = None) -> str:
    """Format a single note as one line of CLI output."""
    tag_map = ansi_tag if ansi_tag is not None else DEFAULT_ANSI_TAG
    ts = note.timestamp.strftime("[%Y-%m-%d %H:%M]")
    text = note.text

    if not use_color:
        return f"{ts} {text}"

    if note.is_done:
        return f"{ANSI_STRIKE_DIM}{ts} {text}{ANSI_RESET}"

    # Dim timestamp, color tags in text
    colored = text
    for tag in note.tags:
        color = tag_map.get(tag)
        if color:
            colored = colored.replace(f"#{tag}", f"{color}#{tag}{ANSI_RESET}")

    return f"{ANSI_DIM}{ts}{ANSI_RESET} {colored}"


def cmd_recent(args, config, ansi_tag=None):
    """Show the most recent N notes."""
    notes = parse_notes(config.output_file)
    if not notes:
        print("No notes found.")
        return

    use_color = sys.stdout.isatty()
    newest_first = list(reversed(notes))
    limited = newest_first[:args.limit] if args.limit > 0 else newest_first

    for note in limited:
        print(format_note(note, use_color, ansi_tag))


def cmd_search(args, config, ansi_tag=None):
    """Search notes by keyword."""
    notes = parse_notes(config.output_file)
    results = search_notes(notes, args.query)

    if not results:
        print("No matching notes.")
        return

    use_color = sys.stdout.isatty()
    newest_first = list(reversed(results))
    limited = newest_first[:args.limit] if args.limit > 0 else newest_first

    for note in limited:
        print(format_note(note, use_color, ansi_tag))


def cmd_tags(args, config, ansi_tag=None):
    """List all tags with note counts."""
    tag_map = ansi_tag or DEFAULT_ANSI_TAG
    notes = parse_notes(config.output_file)

    tag_counts: dict[str, int] = {}
    for note in notes:
        for tag in note.tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    if not tag_counts:
        print("No tags found.")
        return

    use_color = sys.stdout.isatty()
    sorted_tags = sorted(tag_counts.items(), key=lambda x: (-x[1], x[0]))
    max_len = max(len(f"#{tag}") for tag, _ in sorted_tags)

    for tag, count in sorted_tags:
        label = f"#{tag}"
        noun = "note" if count == 1 else "notes"
        if use_color:
            color = tag_map.get(tag, "")
            reset = ANSI_RESET if color else ""
            print(f"  {color}{label:<{max_len}}{reset}  {ANSI_BOLD}{count}{ANSI_RESET} {noun}")
        else:
            print(f"  {label:<{max_len}}  {count} {noun}")


def cmd_add(args, config, ansi_tag=None):
    """Add a note from the command line."""
    from cogstash import append_note_to_file, merge_tags

    # Argument takes priority over stdin
    if args.text:
        text = " ".join(args.text)
    else:
        if sys.stdin.isatty():
            print("Error: provide note text as argument or pipe via stdin.", file=sys.stderr)
            sys.exit(1)
        text = sys.stdin.read()

    smart_tags, _ = merge_tags(config)
    ok = append_note_to_file(text, config.output_file, smart_tags)
    if not ok:
        print("Error: failed to save note.", file=sys.stderr)
        sys.exit(1)


def _find_note(config, number: int | None = None, search: str | None = None,
               ansi_tag: dict[str, str] | None = None) -> Note | None:
    """Find a note by number or search. Prints errors and returns None on failure."""
    notes = parse_notes(config.output_file)
    if number is not None:
        for n in notes:
            if n.index == number:
                return n
        print(f"Error: note #{number} not found.", file=sys.stderr)
        return None
    if search is not None:
        results = search_notes(notes, search)
        if len(results) == 1:
            return results[0]
        if len(results) == 0:
            print(f"Error: no notes match '{search}'.", file=sys.stderr)
            return None
        use_color = sys.stdout.isatty()
        print(f"Multiple matches ({len(results)}). Use a note number instead:", file=sys.stderr)
        for n in results:
            print(f"  {n.index}: {format_note(n, use_color, ansi_tag)}", file=sys.stderr)
        return None
    print("Error: provide a note number or --search.", file=sys.stderr)
    return None


def cmd_edit(args, config, ansi_tag=None):
    """Edit a note's text."""
    number = None
    text_parts = list(args.args) if args.args else []

    if args.search:
        pass
    elif text_parts and text_parts[0].isdigit():
        number = int(text_parts.pop(0))
    else:
        print("Error: provide a note number or --search.", file=sys.stderr)
        sys.exit(1)

    if not text_parts:
        print("Error: no replacement text provided.", file=sys.stderr)
        sys.exit(1)

    note = _find_note(config, number=number, search=args.search, ansi_tag=ansi_tag)
    if note is None:
        sys.exit(1)

    new_text = " ".join(text_parts)
    if not edit_note(config.output_file, note, new_text):
        print("Error: failed to update note.", file=sys.stderr)
        sys.exit(1)

    print(f"Note {note.index} updated.")


def cmd_delete(args, config, ansi_tag=None):
    """Delete a note."""
    note = _find_note(config, number=args.number, search=args.search, ansi_tag=ansi_tag)
    if note is None:
        sys.exit(1)

    if not args.yes:
        preview = note.text[:60] + ("..." if len(note.text) > 60 else "")
        answer = input(f"Delete note {note.index}: \"{preview}\"? [y/N] ")
        if answer.lower() != "y":
            print("Cancelled.")
            return

    if not delete_note(config.output_file, note):
        print("Error: failed to delete note.", file=sys.stderr)
        sys.exit(1)

    print(f"Note {note.index} deleted.")


def cmd_export(args, config, ansi_tag=None):
    """Export all notes to JSON, CSV, or Markdown."""
    import json as json_mod
    import csv

    notes = parse_notes(config.output_file)
    if not notes:
        print("No notes to export.")
        return

    today = datetime.now().strftime("%Y-%m-%d")
    ext = {"json": "json", "csv": "csv", "md": "md"}[args.format]

    if args.output:
        out_path = Path(args.output)
    else:
        out_path = Path(f"cogstash-export-{today}.{ext}")

    if args.format == "json":
        data = [
            {
                "index": n.index,
                "timestamp": n.timestamp.strftime("%Y-%m-%d %H:%M"),
                "text": n.text,
                "tags": n.tags,
                "is_done": n.is_done,
            }
            for n in notes
        ]
        out_path.write_text(
            json_mod.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    elif args.format == "csv":
        with open(out_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=["index", "timestamp", "text", "tags", "is_done"])
            writer.writeheader()
            for n in notes:
                writer.writerow({
                    "index": n.index,
                    "timestamp": n.timestamp.strftime("%Y-%m-%d %H:%M"),
                    "text": n.text,
                    "tags": ";".join(n.tags),
                    "is_done": n.is_done,
                })

    elif args.format == "md":
        lines = ["# CogStash Export\n\n"]
        lines.append(f"*Exported {len(notes)} notes on {today}*\n\n")
        for n in notes:
            ts = n.timestamp.strftime("%Y-%m-%d %H:%M")
            tags = " ".join(f"`#{t}`" for t in n.tags) if n.tags else ""
            status = "☑" if n.is_done else ""
            line = f"- **[{ts}]** {status} {n.text}"
            if tags:
                line += f"  {tags}"
            lines.append(line + "\n")
        out_path.write_text("".join(lines), encoding="utf-8")

    print(f"Exported {len(notes)} notes → {out_path}")



def cmd_stats(args, config, ansi_tag=None):
    """Display extended note statistics."""
    from cogstash_search import compute_stats

    notes = parse_notes(config.output_file)
    if not notes:
        print("No notes found.")
        return

    s = compute_stats(notes)
    use_color = sys.stdout.isatty()

    def c(code, text):
        return f"{code}{text}{ANSI_RESET}" if use_color else str(text)

    accent = "\033[36m"
    bold = ANSI_BOLD
    dim = ANSI_DIM

    print(c(accent, "📊 CogStash Stats"))
    print(f"📝 Total notes: {c(bold, s['total'])}")

    if s["first_date"] and s["last_date"]:
        first = s["first_date"].strftime("%Y-%m-%d")
        last = s["last_date"].strftime("%Y-%m-%d")
        span = (s["last_date"].date() - s["first_date"].date()).days
        print(f"📅 Date range: {c(dim, first)} → {c(dim, last)} {c(dim, f'({span} days)')}")

    done_pct = round(s["done"] / s["total"] * 100) if s["total"] else 0
    pend_pct = 100 - done_pct
    done_n = s["done"]
    pending_n = s["pending"]
    avg_len = s["avg_length"]
    longest_len = s["longest"]
    print(f"✅ Done: {c(bold, done_n)} ({done_pct}%) │ ☐ Pending: {c(bold, pending_n)} ({pend_pct}%)")
    print(f"📏 Avg length: {c(dim, f'{avg_len} chars')} │ Longest: {c(dim, f'{longest_len} chars')}")

    # Activity
    tw = s["notes_this_week"]
    lw = s["notes_last_week"]
    apw = s["avg_per_week"]
    print(f"\n{c(accent, '📈 Activity')}")
    print(f"  This week: {c(bold, tw)} notes │ Last week: {c(bold, lw)} notes")
    if s["busiest_day"]:
        print(f"  Most active day: {s['busiest_day']}")
    print(f"  Avg per week: {c(bold, apw)} notes")

    # Tags
    tag_counts = s["tag_counts"]
    total = s["total"]
    if tag_counts:
        n_tags = len(tag_counts)
        print(f"\n{c(accent, '🏷️  Tags')} ({n_tags} unique)")
        tag_map = ansi_tag or DEFAULT_ANSI_TAG
        max_count = max(tag_counts.values())
        for tag, count in tag_counts.items():
            bar_len = round(count / max_count * 10)
            bar = "█" * bar_len + "░" * (10 - bar_len)
            pct = round(count / total * 100)
            color = tag_map.get(tag, "")
            reset = ANSI_RESET if (color and use_color) else ""
            tag_label = f"{color}#{tag}{reset}" if use_color else f"#{tag}"
            print(f"  {tag_label} · {count} notes · {c(dim, f'{bar} {pct}%')}")

    # Streaks
    cur_streak = s["current_streak"]
    long_streak = s["longest_streak"]
    print(f"\n{c(accent, '🔥 Streaks')}")
    print(f"  Current streak: {c(bold, f'{cur_streak} days')}")
    print(f"  Longest streak: {c(bold, f'{long_streak} days')}")


VALID_CONFIG_KEYS = {"hotkey", "theme", "window_size", "output_file", "log_file", "tags"}


def _get_valid_themes() -> list[str]:
    from cogstash import THEMES
    return list(THEMES.keys())


def _get_valid_window_sizes() -> list[str]:
    from cogstash import WINDOW_SIZES
    return list(WINDOW_SIZES.keys())


def _config_wizard(config, config_path: Path) -> None:
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

    print(f"⚙️  CogStash Configuration Wizard")
    print(f"Press Enter to keep current value\n")

    # ❶ Hotkey
    print(f"❶ Hotkey")
    print(f"  Current: {config.hotkey}")
    val = input("  New hotkey: ").strip()
    if val:
        data["hotkey"] = val

    # ❷ Theme
    print(f"\n❷ Theme [{' / '.join(valid_themes)}]")
    print(f"  Current: {config.theme}")
    val = input("  Select theme: ").strip()
    if val:
        if val not in valid_themes:
            print(f"  ⚠ Unknown theme '{val}', keeping {config.theme}")
        else:
            data["theme"] = val

    # ❸ Window Size
    print(f"\n❸ Window Size [{' / '.join(valid_sizes)}]")
    print(f"  Current: {config.window_size}")
    val = input("  Select size: ").strip()
    if val:
        if val not in valid_sizes:
            print(f"  ⚠ Unknown size '{val}', keeping {config.window_size}")
        else:
            data["window_size"] = val

    # ❹ Notes File
    print(f"\n❹ Notes File")
    print(f"  Current: {config.output_file}")
    val = input("  New path: ").strip()
    if val:
        data["output_file"] = val

    # ❺ Log File
    print(f"\n❺ Log File")
    print(f"  Current: {config.log_file}")
    val = input("  New path: ").strip()
    if val:
        data["log_file"] = val

    # ❻ Custom Tags
    print(f"\n❻ Custom Tags")
    if config.tags:
        tags_display = " ".join(f"#{name}" for name in config.tags)
        print(f"  Current tags: {tags_display}")
    else:
        print("  No custom tags configured")
    val = input("  Add/remove tags? (y/N) ").strip().lower()
    if val == "y":
        print("  Edit tags in ~/.cogstash.json directly (JSON format)")

    # Save
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json_mod.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\n✅ Config saved to {config_path}")


def cmd_config(args, config, ansi_tag=None, config_path: Path | None = None):
    """View or modify CogStash configuration."""
    import json as json_mod

    if config_path is None:
        config_path = Path.home() / ".cogstash.json"

    if args.action is None:
        _config_wizard(config, config_path)
        return

    # Map config key to current values
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
            print(f"Error: unknown key '{args.key}'. Valid: {', '.join(sorted(VALID_CONFIG_KEYS))}", file=sys.stderr)
            sys.exit(1)
        value = config_map[args.key]
        if isinstance(value, dict):
            print(json_mod.dumps(value, indent=2, ensure_ascii=False))
        else:
            print(value)
        return

    if args.action == "set":
        if args.key not in VALID_CONFIG_KEYS:
            print(f"Error: unknown key '{args.key}'. Valid: {', '.join(sorted(VALID_CONFIG_KEYS))}", file=sys.stderr)
            sys.exit(1)
        if args.key == "tags":
            print("Error: use the wizard to manage tags, or edit ~/.cogstash.json directly.", file=sys.stderr)
            sys.exit(1)

        # Validate value
        valid_themes = _get_valid_themes()
        valid_sizes = _get_valid_window_sizes()
        if args.key == "theme" and args.value not in valid_themes:
            print(f"Error: invalid theme '{args.value}'. Valid: {', '.join(valid_themes)}", file=sys.stderr)
            sys.exit(1)
        if args.key == "window_size" and args.value not in valid_sizes:
            print(f"Error: invalid window_size '{args.value}'. Valid: {', '.join(valid_sizes)}", file=sys.stderr)
            sys.exit(1)

        # Read, update, write
        data = {}
        if config_path.exists():
            try:
                data = json_mod.loads(config_path.read_text(encoding="utf-8"))
            except (json_mod.JSONDecodeError, OSError):
                data = {}
        data[args.key] = args.value
        config_path.write_text(
            json_mod.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"{args.key} = {args.value}")


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        prog="cogstash",
        description="CogStash — query your brain dump from the terminal.",
    )
    sub = parser.add_subparsers(dest="command")

    # recent
    p_recent = sub.add_parser("recent", help="Show latest notes")
    p_recent.add_argument("--limit", type=int, default=20, help="Max notes to show (default: 20)")
    p_recent.set_defaults(func=cmd_recent)

    # search
    p_search = sub.add_parser("search", help="Search notes by keyword")
    p_search.add_argument("query", help="Search term")
    p_search.add_argument("--limit", type=int, default=20, help="Max results (default: 20)")
    p_search.set_defaults(func=cmd_search)

    # tags
    p_tags = sub.add_parser("tags", help="List all tags with counts")
    p_tags.set_defaults(func=cmd_tags)

    # add
    p_add = sub.add_parser("add", help="Add a note from the CLI")
    p_add.add_argument("text", nargs="*", help="Note text (or pipe via stdin)")
    p_add.set_defaults(func=cmd_add)

    # edit — uses a single "args" positional to avoid int/str ambiguity
    # Usage: cogstash edit 3 new text  OR  cogstash edit --search "milk" new text
    p_edit = sub.add_parser("edit", help="Edit a note's text")
    p_edit.add_argument("args", nargs="*", help="Note number followed by new text")
    p_edit.add_argument("--search", "-s", help="Find note by keyword instead of number")
    p_edit.set_defaults(func=cmd_edit)

    # delete
    p_delete = sub.add_parser("delete", help="Delete a note")
    p_delete.add_argument("number", type=int, nargs="?", default=None, help="Note number")
    p_delete.add_argument("--search", "-s", help="Find note by keyword")
    p_delete.add_argument("--yes", "-y", action="store_true", help="Skip confirmation")
    p_delete.set_defaults(func=cmd_delete)

    # export
    p_export = sub.add_parser("export", help="Export all notes to file")
    p_export.add_argument(
        "--format", "-f", choices=["json", "csv", "md"], default="json",
        help="Export format (default: json)",
    )
    p_export.add_argument("--output", "-o", help="Output file path (default: auto-named)")
    p_export.set_defaults(func=cmd_export)

    # stats
    p_stats = sub.add_parser("stats", help="Show note statistics")
    p_stats.set_defaults(func=cmd_stats)

    # config
    p_config = sub.add_parser("config", help="View or set configuration")
    p_config.add_argument("action", nargs="?", choices=["get", "set"], default=None,
                          help="Action: get or set (omit for wizard)")
    p_config.add_argument("key", nargs="?", help="Config key")
    p_config.add_argument("value", nargs="?", help="New value (for set)")
    p_config.set_defaults(func=cmd_config)

    return parser


def cli_main(argv: list[str]) -> None:
    """Entry point for CLI subcommands."""
    from cogstash import load_config, merge_tags

    parser = build_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, "func"):
        parser.print_help()
        return

    config_path = Path.home() / ".cogstash.json"
    config = load_config(config_path)
    _, tag_colors = merge_tags(config)
    ansi_tag = build_ansi_tag_map(tag_colors)

    if args.func == cmd_config:
        args.func(args, config, ansi_tag, config_path=config_path)
    else:
        args.func(args, config, ansi_tag)
