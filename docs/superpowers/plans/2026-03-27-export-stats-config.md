# Phase 8: Export, Stats, Config CLI — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add three CLI commands: `cogstash export` (JSON/CSV/Markdown), `cogstash stats` (extended summary), and `cogstash config` (interactive wizard + get/set).

**Architecture:** All three commands are pure CLI additions. Export and stats read notes via `parse_notes()` and produce output — no new data layer needed. Config reads/writes `~/.cogstash.json` directly. Each command is a `cmd_*` function in `cogstash_cli.py` wired through `build_parser()`. Stats computation is extracted into `cogstash_search.py` as a pure function for testability.

**Tech Stack:** Python 3.9+, argparse, json, csv (stdlib), datetime, collections

---

## File Map

| File | Role | Changes |
|------|------|---------|
| `cogstash_search.py` | Pure data layer | Add `compute_stats()` function |
| `cogstash_cli.py` | CLI commands | Add `cmd_export`, `cmd_stats`, `cmd_config`, wire into `build_parser()` |
| `cogstash.py` | Main app | Add `"export"`, `"stats"`, `"config"` to argv guard (line 571) |
| `test_cogstash_search.py` | Search tests | Add stats computation tests |
| `test_cogstash_cli.py` | CLI tests | Add export, stats, config tests |

---

## Task 1: Stats Computation (cogstash_search.py)

**Files:**
- Modify: `cogstash_search.py` (add `compute_stats()` after `delete_note()` at ~line 168)
- Test: `test_cogstash_search.py` (add 3 tests at end)

### Step 1: Write the failing tests

Add to end of `test_cogstash_search.py`:

```python
def test_compute_stats_basic(tmp_path):
    """Stats returns correct totals, done/pending, date range."""
    f = tmp_path / "cogstash.md"
    f.write_text(
        "- [2026-01-15 09:00] first note #todo\n"
        "- [2026-02-10 14:30] ☑ done item #todo\n"
        "- [2026-03-27 16:00] latest note #idea\n",
        encoding="utf-8",
    )
    from cogstash_search import parse_notes, compute_stats
    notes = parse_notes(f)
    stats = compute_stats(notes)

    assert stats["total"] == 3
    assert stats["done"] == 1
    assert stats["pending"] == 2
    assert stats["first_date"].year == 2026
    assert stats["first_date"].month == 1
    assert stats["last_date"].month == 3
    assert "todo" in stats["tag_counts"]
    assert stats["tag_counts"]["todo"] == 2
    assert stats["avg_length"] > 0
    assert stats["longest"] >= stats["avg_length"]


def test_compute_stats_empty():
    """Empty note list returns zeroed stats."""
    from cogstash_search import compute_stats
    stats = compute_stats([])

    assert stats["total"] == 0
    assert stats["done"] == 0
    assert stats["pending"] == 0
    assert stats["first_date"] is None
    assert stats["last_date"] is None
    assert stats["tag_counts"] == {}
    assert stats["avg_length"] == 0


def test_compute_stats_streaks(tmp_path):
    """Streak calculation finds consecutive days with notes."""
    from datetime import timedelta, date
    from cogstash_search import parse_notes, compute_stats

    today = date.today()
    dates = [today - timedelta(days=i) for i in range(3, -1, -1)]  # 4 consecutive days ending today
    lines = []
    for i, d in enumerate(dates):
        ts = d.strftime("%Y-%m-%d") + " 09:00"
        lines.append(f"- [{ts}] day {i + 1}\n")

    f = tmp_path / "cogstash.md"
    f.write_text("".join(lines), encoding="utf-8")
    notes = parse_notes(f)
    stats = compute_stats(notes)

    assert stats["current_streak"] == 4
    assert stats["longest_streak"] == 4
    assert stats["notes_this_week"] >= 1
```

### Step 2: Run tests to verify they fail

Run: `python -m pytest test_cogstash_search.py::test_compute_stats_basic test_cogstash_search.py::test_compute_stats_empty test_cogstash_search.py::test_compute_stats_streaks -v`
Expected: FAIL with `ImportError: cannot import name 'compute_stats'`

### Step 3: Implement `compute_stats()`

Add to `cogstash_search.py` after `delete_note()` (after line 167):

```python
def compute_stats(notes: list[Note]) -> dict:
    """Compute extended statistics from a list of notes.

    Returns a dict with keys: total, done, pending, first_date, last_date,
    tag_counts, avg_length, longest, notes_this_week, notes_last_week,
    busiest_day, avg_per_week, current_streak, longest_streak.
    """
    if not notes:
        return {
            "total": 0, "done": 0, "pending": 0,
            "first_date": None, "last_date": None,
            "tag_counts": {}, "avg_length": 0, "longest": 0,
            "notes_this_week": 0, "notes_last_week": 0,
            "busiest_day": None, "avg_per_week": 0.0,
            "current_streak": 0, "longest_streak": 0,
        }

    from collections import Counter
    from datetime import timedelta, date

    total = len(notes)
    done = sum(1 for n in notes if n.is_done)
    pending = total - done

    timestamps = sorted(n.timestamp for n in notes)
    first_date = timestamps[0]
    last_date = timestamps[-1]

    # Tag counts
    tag_counter: Counter[str] = Counter()
    for n in notes:
        for tag in n.tags:
            tag_counter[tag] += 1
    tag_counts = dict(tag_counter.most_common())

    # Note lengths
    lengths = [len(n.text) for n in notes]
    avg_length = sum(lengths) // total
    longest = max(lengths)

    # Weekly activity
    today = date.today()
    week_start = today - timedelta(days=today.weekday())  # Monday
    last_week_start = week_start - timedelta(days=7)
    notes_this_week = sum(1 for n in notes if n.timestamp.date() >= week_start)
    notes_last_week = sum(
        1 for n in notes
        if last_week_start <= n.timestamp.date() < week_start
    )

    # Busiest day of week (0=Monday, 6=Sunday)
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    day_counts = Counter(n.timestamp.weekday() for n in notes)
    busiest_idx = day_counts.most_common(1)[0][0]
    busiest_day = day_names[busiest_idx]

    # Average per week
    span_days = (last_date.date() - first_date.date()).days + 1
    span_weeks = max(span_days / 7, 1)
    avg_per_week = round(total / span_weeks, 1)

    # Streaks — consecutive days with at least one note
    note_dates = sorted(set(n.timestamp.date() for n in notes))
    current_streak = 0
    longest_streak = 0
    streak = 1

    for i in range(1, len(note_dates)):
        if (note_dates[i] - note_dates[i - 1]).days == 1:
            streak += 1
        else:
            longest_streak = max(longest_streak, streak)
            streak = 1
    longest_streak = max(longest_streak, streak)

    # Current streak: count backwards from today
    if today in note_dates:
        current_streak = 1
        check = today - timedelta(days=1)
        while check in set(note_dates):
            current_streak += 1
            check -= timedelta(days=1)
    else:
        current_streak = 0

    return {
        "total": total, "done": done, "pending": pending,
        "first_date": first_date, "last_date": last_date,
        "tag_counts": tag_counts, "avg_length": avg_length, "longest": longest,
        "notes_this_week": notes_this_week, "notes_last_week": notes_last_week,
        "busiest_day": busiest_day, "avg_per_week": avg_per_week,
        "current_streak": current_streak, "longest_streak": longest_streak,
    }
```

### Step 4: Run tests to verify they pass

Run: `python -m pytest test_cogstash_search.py -v`
Expected: All 21 tests PASS

### Step 5: Commit

```bash
git add cogstash_search.py test_cogstash_search.py
git commit -m "feat: add compute_stats for extended note statistics"
```

---

## Task 2: Export Command (cogstash_cli.py)

**Files:**
- Modify: `cogstash_cli.py` (add `cmd_export`, wire into `build_parser()`)
- Modify: `cogstash.py` line 571 (add `"export"` to argv guard)
- Test: `test_cogstash_cli.py` (add 5 tests at end)

**Depends on:** None (uses existing `parse_notes` only)

### Step 1: Write the failing tests

Add to end of `test_cogstash_cli.py`:

```python
def test_cmd_export_json(tmp_path, monkeypatch, capsys):
    """Export to JSON creates file with all notes."""
    import json
    f = _make_notes_file(tmp_path)
    monkeypatch.chdir(tmp_path)
    from cogstash_cli import cmd_export
    from cogstash import CogStashConfig
    from types import SimpleNamespace

    cmd_export(
        SimpleNamespace(format="json", output=None),
        CogStashConfig(output_file=f),
    )
    output = capsys.readouterr().out
    assert "Exported" in output


def test_cmd_export_json_content(tmp_path, monkeypatch, capsys):
    """JSON export contains correct note data."""
    import json
    f = _make_notes_file(tmp_path)
    monkeypatch.chdir(tmp_path)
    from cogstash_cli import cmd_export
    from cogstash import CogStashConfig
    from types import SimpleNamespace

    cmd_export(
        SimpleNamespace(format="json", output=None),
        CogStashConfig(output_file=f),
    )
    exported = list(tmp_path.glob("cogstash-export-*.json"))
    assert len(exported) == 1
    data = json.loads(exported[0].read_text(encoding="utf-8"))
    assert len(data) == 5
    assert "text" in data[0]
    assert "timestamp" in data[0]
    assert "tags" in data[0]


def test_cmd_export_csv(tmp_path, monkeypatch, capsys):
    """CSV export creates valid CSV file."""
    import csv
    f = _make_notes_file(tmp_path)
    monkeypatch.chdir(tmp_path)
    from cogstash_cli import cmd_export
    from cogstash import CogStashConfig
    from types import SimpleNamespace

    cmd_export(
        SimpleNamespace(format="csv", output=None),
        CogStashConfig(output_file=f),
    )
    exported = list(tmp_path.glob("cogstash-export-*.csv"))
    assert len(exported) == 1
    with open(exported[0], encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
    assert len(rows) == 5
    assert "timestamp" in reader.fieldnames
    assert "text" in reader.fieldnames


def test_cmd_export_md(tmp_path, monkeypatch, capsys):
    """Markdown export creates valid .md file."""
    f = _make_notes_file(tmp_path)
    monkeypatch.chdir(tmp_path)
    from cogstash_cli import cmd_export
    from cogstash import CogStashConfig
    from types import SimpleNamespace

    cmd_export(
        SimpleNamespace(format="md", output=None),
        CogStashConfig(output_file=f),
    )
    exported = list(tmp_path.glob("cogstash-export-*.md"))
    assert len(exported) == 1
    content = exported[0].read_text(encoding="utf-8")
    assert "# CogStash Export" in content
    assert "buy milk" in content


def test_cmd_export_custom_output(tmp_path, capsys):
    """--output flag writes to specified path."""
    import json
    f = _make_notes_file(tmp_path)
    out_path = tmp_path / "custom.json"
    from cogstash_cli import cmd_export
    from cogstash import CogStashConfig
    from types import SimpleNamespace

    cmd_export(
        SimpleNamespace(format="json", output=str(out_path)),
        CogStashConfig(output_file=f),
    )
    assert out_path.exists()
    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert len(data) == 5
```

### Step 2: Run tests to verify they fail

Run: `python -m pytest test_cogstash_cli.py::test_cmd_export_json -v`
Expected: FAIL with `ImportError: cannot import name 'cmd_export'`

### Step 3: Implement `cmd_export()`

Add to `cogstash_cli.py` after `cmd_delete()` (after line 228):

```python
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
```

Also add at the top of the file with other imports (line 9):

```python
from datetime import datetime
```

### Step 4: Wire into `build_parser()`

Add to `build_parser()` after the `delete` subparser block (before `return parser`):

```python
    # export
    p_export = sub.add_parser("export", help="Export all notes to file")
    p_export.add_argument(
        "--format", "-f", choices=["json", "csv", "md"], default="json",
        help="Export format (default: json)",
    )
    p_export.add_argument("--output", "-o", help="Output file path (default: auto-named)")
    p_export.set_defaults(func=cmd_export)
```

### Step 5: Update argv guard in cogstash.py

Change line 571 of `cogstash.py` from:

```python
    if len(sys.argv) > 1 and sys.argv[1] in ("recent", "search", "tags", "add", "edit", "delete"):
```

To:

```python
    if len(sys.argv) > 1 and sys.argv[1] in ("recent", "search", "tags", "add", "edit", "delete", "export", "stats", "config"):
```

(Add all three new commands at once to avoid modifying this line again.)

### Step 6: Run tests to verify they pass

Run: `python -m pytest test_cogstash_cli.py -v`
Expected: All 32 tests PASS

### Step 7: Commit

```bash
git add cogstash_cli.py cogstash.py test_cogstash_cli.py
git commit -m "feat: add cogstash export command (JSON, CSV, Markdown)"
```

---

## Task 3: Stats Command (cogstash_cli.py)

**Files:**
- Modify: `cogstash_cli.py` (add `cmd_stats`, wire into `build_parser()`)
- Test: `test_cogstash_cli.py` (add 3 tests at end)

**Depends on:** Task 1 (`compute_stats`)

### Step 1: Write the failing tests

Add to end of `test_cogstash_cli.py`:

```python
def test_cmd_stats_output(tmp_path, capsys):
    """Stats displays totals, tags, and date range."""
    f = _make_notes_file(tmp_path)
    from cogstash_cli import cmd_stats
    from cogstash import CogStashConfig
    from types import SimpleNamespace

    cmd_stats(SimpleNamespace(), CogStashConfig(output_file=f))
    output = capsys.readouterr().out

    assert "Total notes" in output or "5" in output
    assert "#todo" in output or "todo" in output
    assert "2026" in output


def test_cmd_stats_empty(tmp_path, capsys):
    """Stats on empty file shows no-notes message."""
    f = tmp_path / "cogstash.md"
    from cogstash_cli import cmd_stats
    from cogstash import CogStashConfig
    from types import SimpleNamespace

    cmd_stats(SimpleNamespace(), CogStashConfig(output_file=f))
    output = capsys.readouterr().out
    assert "No notes" in output


def test_cmd_stats_done_pending(tmp_path, capsys):
    """Stats shows correct done/pending counts."""
    f = _make_notes_file(tmp_path)
    from cogstash_cli import cmd_stats
    from cogstash import CogStashConfig
    from types import SimpleNamespace

    cmd_stats(SimpleNamespace(), CogStashConfig(output_file=f))
    output = capsys.readouterr().out
    # Fixture has 1 done (☑ fix login bug), 4 pending
    assert "1" in output  # done count
    assert "4" in output  # pending count
```

### Step 2: Run tests to verify they fail

Run: `python -m pytest test_cogstash_cli.py::test_cmd_stats_output -v`
Expected: FAIL with `ImportError: cannot import name 'cmd_stats'`

### Step 3: Implement `cmd_stats()`

Add to `cogstash_cli.py` after `cmd_export()`:

```python
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
```

### Step 4: Wire into `build_parser()`

Add to `build_parser()` after the `export` subparser block:

```python
    # stats
    p_stats = sub.add_parser("stats", help="Show note statistics")
    p_stats.set_defaults(func=cmd_stats)
```

### Step 5: Run tests to verify they pass

Run: `python -m pytest test_cogstash_cli.py -v`
Expected: All 35 tests PASS

### Step 6: Commit

```bash
git add cogstash_cli.py test_cogstash_cli.py
git commit -m "feat: add cogstash stats command with extended statistics"
```

---

## Task 4: Config Command (cogstash_cli.py)

**Files:**
- Modify: `cogstash_cli.py` (add `cmd_config`, `_config_wizard`, wire into `build_parser()`)
- Test: `test_cogstash_cli.py` (add 5 tests at end)

**Depends on:** None

### Step 1: Write the failing tests

Add to end of `test_cogstash_cli.py`:

```python
def test_cmd_config_get(tmp_path, capsys):
    """cogstash config get returns current value."""
    config_path = tmp_path / ".cogstash.json"
    config_path.write_text('{"theme": "dracula"}', encoding="utf-8")
    from cogstash_cli import cmd_config
    from cogstash import CogStashConfig
    from types import SimpleNamespace

    cmd_config(
        SimpleNamespace(action="get", key="theme", value=None),
        CogStashConfig(theme="dracula"),
        config_path=config_path,
    )
    output = capsys.readouterr().out
    assert "dracula" in output


def test_cmd_config_set(tmp_path, capsys):
    """cogstash config set updates JSON file."""
    import json
    config_path = tmp_path / ".cogstash.json"
    config_path.write_text('{"theme": "tokyo-night"}', encoding="utf-8")
    from cogstash_cli import cmd_config
    from cogstash import CogStashConfig
    from types import SimpleNamespace

    cmd_config(
        SimpleNamespace(action="set", key="theme", value="dracula"),
        CogStashConfig(theme="tokyo-night"),
        config_path=config_path,
    )
    data = json.loads(config_path.read_text(encoding="utf-8"))
    assert data["theme"] == "dracula"
    output = capsys.readouterr().out
    assert "dracula" in output


def test_cmd_config_set_invalid_theme(tmp_path, capsys):
    """cogstash config set rejects invalid theme."""
    config_path = tmp_path / ".cogstash.json"
    config_path.write_text('{"theme": "tokyo-night"}', encoding="utf-8")
    from cogstash_cli import cmd_config
    from cogstash import CogStashConfig
    from types import SimpleNamespace
    import pytest

    with pytest.raises(SystemExit):
        cmd_config(
            SimpleNamespace(action="set", key="theme", value="nope"),
            CogStashConfig(),
            config_path=config_path,
        )


def test_cmd_config_wizard(tmp_path, monkeypatch, capsys):
    """Interactive wizard updates config file."""
    import json
    config_path = tmp_path / ".cogstash.json"
    config_path.write_text('{}', encoding="utf-8")

    # Simulate user pressing Enter for all prompts (keeping defaults)
    monkeypatch.setattr("builtins.input", lambda _: "")

    from cogstash_cli import cmd_config
    from cogstash import CogStashConfig
    from types import SimpleNamespace

    cmd_config(
        SimpleNamespace(action=None, key=None, value=None),
        CogStashConfig(),
        config_path=config_path,
    )
    output = capsys.readouterr().out
    assert "saved" in output.lower() or "Config" in output


def test_cmd_config_get_invalid_key(tmp_path, capsys):
    """cogstash config get with unknown key shows error."""
    config_path = tmp_path / ".cogstash.json"
    config_path.write_text('{}', encoding="utf-8")
    from cogstash_cli import cmd_config
    from cogstash import CogStashConfig
    from types import SimpleNamespace
    import pytest

    with pytest.raises(SystemExit):
        cmd_config(
            SimpleNamespace(action="get", key="nonexistent", value=None),
            CogStashConfig(),
            config_path=config_path,
        )
```

### Step 2: Run tests to verify they fail

Run: `python -m pytest test_cogstash_cli.py::test_cmd_config_get -v`
Expected: FAIL with `ImportError: cannot import name 'cmd_config'`

### Step 3: Implement `cmd_config()` and `_config_wizard()`

Add to `cogstash_cli.py` after `cmd_stats()`:

```python
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
```

### Step 4: Wire into `build_parser()`

Add to `build_parser()` after the `stats` subparser block:

```python
    # config
    p_config = sub.add_parser("config", help="View or set configuration")
    p_config.add_argument("action", nargs="?", choices=["get", "set"], default=None,
                          help="Action: get or set (omit for wizard)")
    p_config.add_argument("key", nargs="?", help="Config key")
    p_config.add_argument("value", nargs="?", help="New value (for set)")
    p_config.set_defaults(func=cmd_config)
```

### Step 5: Update `cli_main()` to pass `config_path`

The `cmd_config` function needs `config_path` to read/write the JSON file. Update the dispatch in `cli_main()` to pass it:

Change the dispatch line in `cli_main()` from:

```python
    args.func(args, config, ansi_tag)
```

To:

```python
    if args.func == cmd_config:
        args.func(args, config, ansi_tag, config_path=config_path)
    else:
        args.func(args, config, ansi_tag)
```

And add `config_path` variable before `config = load_config(...)`:

```python
    config_path = Path.home() / ".cogstash.json"
    config = load_config(config_path)
```

So the full updated `cli_main()` becomes:

```python
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
```

### Step 6: Run tests to verify they pass

Run: `python -m pytest test_cogstash_cli.py -v`
Expected: All 40 tests PASS

### Step 7: Run full test suite

Run: `python -m pytest -v`
Expected: All 98 tests PASS (82 existing + 3 search stats + 5 export + 3 CLI stats + 5 config)

### Step 8: Commit

```bash
git add cogstash_cli.py test_cogstash_cli.py
git commit -m "feat: add cogstash config command with wizard and get/set"
```
