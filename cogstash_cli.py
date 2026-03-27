"""cogstash_cli.py — CLI subcommands for querying CogStash notes.

Provides `recent`, `search`, and `tags` commands with ANSI-colored output.
All data operations delegate to cogstash_search.py.
"""

from __future__ import annotations

import sys
import argparse
from pathlib import Path

from cogstash_search import Note, parse_notes, search_notes

# ANSI escape codes — approximations of TAG_COLORS hex values
ANSI_RESET = "\033[0m"
ANSI_BOLD = "\033[1m"
ANSI_DIM = "\033[90m"
ANSI_STRIKE_DIM = "\033[9;90m"

ANSI_TAG = {
    "urgent": "\033[31m",
    "important": "\033[33m",
    "idea": "\033[32m",
    "todo": "\033[36m",
}


def format_note(note: Note, use_color: bool = True) -> str:
    """Format a single note as one line of CLI output."""
    ts = note.timestamp.strftime("[%Y-%m-%d %H:%M]")
    text = note.text

    if not use_color:
        return f"{ts} {text}"

    if note.is_done:
        return f"{ANSI_STRIKE_DIM}{ts} {text}{ANSI_RESET}"

    # Dim timestamp, color tags in text
    colored = text
    for tag in note.tags:
        color = ANSI_TAG.get(tag)
        if color:
            colored = colored.replace(f"#{tag}", f"{color}#{tag}{ANSI_RESET}")

    return f"{ANSI_DIM}{ts}{ANSI_RESET} {colored}"


def cmd_recent(args, config):
    """Show the most recent N notes."""
    notes = parse_notes(config.output_file)
    if not notes:
        print("No notes found.")
        return

    use_color = sys.stdout.isatty()
    newest_first = list(reversed(notes))
    limited = newest_first[:args.limit] if args.limit > 0 else newest_first

    for note in limited:
        print(format_note(note, use_color))


def cmd_search(args, config):
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
        print(format_note(note, use_color))


def cmd_tags(args, config):
    """List all tags with note counts."""
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
            color = ANSI_TAG.get(tag, "")
            reset = ANSI_RESET if color else ""
            print(f"  {color}{label:<{max_len}}{reset}  {ANSI_BOLD}{count}{ANSI_RESET} {noun}")
        else:
            print(f"  {label:<{max_len}}  {count} {noun}")


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

    return parser


def cli_main(argv: list[str]) -> None:
    """Entry point for CLI subcommands."""
    from cogstash import load_config

    parser = build_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, "func"):
        parser.print_help()
        return

    config = load_config(Path.home() / ".cogstash.json")
    args.func(args, config)
