"""cogstash_cli.py — CLI subcommands for querying CogStash notes.

Provides `recent`, `search`, and `tags` commands with ANSI-colored output.
All data operations delegate to cogstash_search.py.
"""

from __future__ import annotations

import sys
import argparse
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

    return parser


def cli_main(argv: list[str]) -> None:
    """Entry point for CLI subcommands."""
    from cogstash import load_config, merge_tags

    parser = build_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, "func"):
        parser.print_help()
        return

    config = load_config(Path.home() / ".cogstash.json")
    _, tag_colors = merge_tags(config)
    ansi_tag = build_ansi_tag_map(tag_colors)
    args.func(args, config, ansi_tag)
