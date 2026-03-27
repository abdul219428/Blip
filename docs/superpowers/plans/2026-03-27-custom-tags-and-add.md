# Phase 6: Custom Tags + `cogstash add` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow users to define custom tags with emoji + color in config, and add a `cogstash add` CLI command for capturing notes without the GUI.

**Architecture:** Custom tags merge user-defined entries (from `~/.cogstash.json`) on top of 4 built-in defaults. A new `merge_tags()` helper produces the merged dicts at config load time, and all consumers (autocomplete, browse window, CLI) receive the merged dicts as parameters instead of using module-level globals. The note-writing logic is extracted from `CogStash.append_note()` into a standalone `append_note_to_file()` function so both GUI and CLI can reuse it.

**Tech Stack:** Python, argparse, tkinter, pytest

**Spec:** `docs/superpowers/specs/2026-03-27-custom-tags-and-add-design.md`

---

### Task 1: Config parsing, tag merging, and validation

**Files:**
- Modify: `cogstash.py` (lines 37-42: SMART_TAGS, lines 56-69: CogStashConfig, lines 71-118: load_config)
- Modify: `cogstash_search.py` (lines 17-22: TAG_COLORS)
- Modify: `test_cogstash.py`
- Modify: `test_cogstash_search.py` (if TAG_COLORS is imported in tests)

This task renames the module-level globals to `DEFAULT_*`, adds the `tags` field to `CogStashConfig`, updates `load_config()` to parse and validate custom tags, and introduces a `merge_tags()` helper that merges built-in defaults with user-defined tags.

**Important:** After renaming `SMART_TAGS` → `DEFAULT_SMART_TAGS` in `cogstash.py`, update the import in `cogstash_browse.py` (line 14) from `SMART_TAGS` to `DEFAULT_SMART_TAGS` to prevent import errors. Similarly, after renaming `TAG_COLORS` → `DEFAULT_TAG_COLORS` in `cogstash_search.py`, update the import in `cogstash_browse.py` (line 15). These are mechanical import renames to keep things building.

- [ ] **Step 1: Write failing tests for merge_tags and config parsing**

Add to `test_cogstash.py`:

```python
def test_merge_tags_builtin_defaults():
    """merge_tags with no custom tags returns built-in defaults."""
    from cogstash import merge_tags, DEFAULT_SMART_TAGS, CogStashConfig
    from cogstash_search import DEFAULT_TAG_COLORS
    config = CogStashConfig()
    smart, colors = merge_tags(config)
    assert smart == DEFAULT_SMART_TAGS
    assert colors == DEFAULT_TAG_COLORS


def test_merge_tags_add_new():
    """Custom tag merges alongside built-ins."""
    from cogstash import merge_tags, CogStashConfig
    config = CogStashConfig(tags={"work": {"emoji": "💼", "color": "#4A90D9"}})
    smart, colors = merge_tags(config)
    assert smart["work"] == "💼"
    assert colors["work"] == "#4A90D9"
    assert "todo" in smart  # built-in still present


def test_merge_tags_override_builtin():
    """User can override a built-in tag's emoji and color."""
    from cogstash import merge_tags, CogStashConfig
    config = CogStashConfig(tags={"todo": {"emoji": "✅", "color": "#00FF00"}})
    smart, colors = merge_tags(config)
    assert smart["todo"] == "✅"
    assert colors["todo"] == "#00FF00"


def test_load_config_custom_tags(tmp_path):
    """Config with tags key loads custom tags into CogStashConfig."""
    import json
    from cogstash import load_config
    cfg_path = tmp_path / "cogstash.json"
    cfg_path.write_text(json.dumps({
        "tags": {"work": {"emoji": "💼", "color": "#4A90D9"}}
    }), encoding="utf-8")
    config = load_config(cfg_path)
    assert config.tags == {"work": {"emoji": "💼", "color": "#4A90D9"}}


def test_load_config_invalid_tag_skipped(tmp_path):
    """Tags missing emoji or color are skipped."""
    import json
    from cogstash import load_config
    cfg_path = tmp_path / "cogstash.json"
    cfg_path.write_text(json.dumps({
        "tags": {
            "good": {"emoji": "✅", "color": "#00FF00"},
            "bad_no_emoji": {"color": "#FF0000"},
            "bad_no_color": {"emoji": "❌"},
            "bad_hex": {"emoji": "❌", "color": "not-hex"},
        }
    }), encoding="utf-8")
    config = load_config(cfg_path)
    assert "good" in config.tags
    assert "bad_no_emoji" not in config.tags
    assert "bad_no_color" not in config.tags
    assert "bad_hex" not in config.tags
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest test_cogstash.py -k "merge_tags or load_config_custom or load_config_invalid" -v`
Expected: FAIL (merge_tags doesn't exist, DEFAULT_SMART_TAGS doesn't exist, config.tags doesn't exist)

- [ ] **Step 3: Implement the changes**

In `cogstash.py`:

1. Rename `SMART_TAGS` → `DEFAULT_SMART_TAGS` (line 37)
2. Add to `CogStashConfig` (after line 62):
   ```python
   tags: dict[str, dict[str, str]] | None = None
   ```
3. Add `_HEX_RE` regex near top:
   ```python
   _HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
   ```
4. Add validation + parsing in `load_config()` before the return statement:
   ```python
   # Parse and validate custom tags
   raw_tags = data.get("tags", {})
   valid_tags = {}
   if isinstance(raw_tags, dict):
       for name, props in raw_tags.items():
           if not isinstance(props, dict):
               logger.warning("Tag '%s': expected object, skipping", name)
               continue
           emoji = props.get("emoji")
           color = props.get("color")
           if not emoji:
               logger.warning("Tag '%s': missing emoji, skipping", name)
               continue
           if not color or not _HEX_RE.match(color):
               logger.warning("Tag '%s': missing or invalid color, skipping", name)
               continue
           valid_tags[name] = {"emoji": emoji, "color": color}
   tags = valid_tags if valid_tags else None
   ```
   Pass `tags=tags` to the CogStashConfig constructor.
5. Add `merge_tags()` function after `load_config()`:
   ```python
   def merge_tags(config: CogStashConfig) -> tuple[dict[str, str], dict[str, str]]:
       """Merge built-in tags with user-defined tags. Returns (smart_tags, tag_colors)."""
       from cogstash_search import DEFAULT_TAG_COLORS
       smart_tags = dict(DEFAULT_SMART_TAGS)
       tag_colors = dict(DEFAULT_TAG_COLORS)
       if config.tags:
           for name, props in config.tags.items():
               smart_tags[name] = props["emoji"]
               tag_colors[name] = props["color"]
       return smart_tags, tag_colors
   ```
6. Update all references to `SMART_TAGS` inside cogstash.py to `DEFAULT_SMART_TAGS`:
   - Line 124-134: `parse_smart_tags()` — references `SMART_TAGS` on lines 130 and 134
   - Line 326: `_on_key_release()` — `SMART_TAGS.items()` (will be addressed in Task 3)

In `cogstash_search.py`:
1. Rename `TAG_COLORS` → `DEFAULT_TAG_COLORS` (line 17)

In `cogstash_browse.py` (mechanical import fix):
1. Line 14: Change `from cogstash import THEMES, SMART_TAGS, CogStashConfig, platform_font` → `from cogstash import THEMES, DEFAULT_SMART_TAGS, CogStashConfig, platform_font`
2. Line 15: Change `TAG_COLORS` → `DEFAULT_TAG_COLORS`
3. Line 75: Change `SMART_TAGS.items()` → `DEFAULT_SMART_TAGS.items()`
4. Line 76: Change `TAG_COLORS.get(` → `DEFAULT_TAG_COLORS.get(`
5. Line 204-205: Change `TAG_COLORS` → `DEFAULT_TAG_COLORS`
6. Line 255: Change `TAG_COLORS.get(` → `DEFAULT_TAG_COLORS.get(`

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest test_cogstash.py test_cogstash_search.py test_cogstash_browse.py test_cogstash_cli.py -v`
Expected: All pass (existing + new)

- [ ] **Step 5: Commit**

```bash
git add cogstash.py cogstash_search.py cogstash_browse.py test_cogstash.py
git commit -m "feat: add custom tag config parsing, validation, and merge_tags helper"
```

---

### Task 2: Parameterize parse_smart_tags + extract append_note_to_file

**Files:**
- Modify: `cogstash.py` (lines 124-135: parse_smart_tags, lines 494-516: append_note)
- Modify: `test_cogstash.py`

This task makes `parse_smart_tags()` accept an optional `smart_tags` parameter (defaults to `DEFAULT_SMART_TAGS`) and extracts the file-writing logic from `CogStash.append_note()` into a standalone `append_note_to_file()` function that both the GUI and CLI can call.

- [ ] **Step 1: Write failing tests**

Add to `test_cogstash.py`:

```python
def test_parse_smart_tags_custom():
    """parse_smart_tags uses custom tags when provided."""
    from cogstash import parse_smart_tags
    custom = {"work": "💼", "todo": "☐"}
    result = parse_smart_tags("meeting notes #work", smart_tags=custom)
    assert result.startswith("💼")
    assert "#work" in result


def test_parse_smart_tags_default():
    """parse_smart_tags still works with defaults when no param given."""
    from cogstash import parse_smart_tags
    result = parse_smart_tags("buy milk #todo")
    assert result.startswith("☐")


def test_append_note_to_file(tmp_path):
    """append_note_to_file writes a timestamped note."""
    from cogstash import append_note_to_file
    out = tmp_path / "notes.md"
    result = append_note_to_file("hello world", out)
    assert result is True
    content = out.read_text(encoding="utf-8")
    assert "hello world" in content
    assert content.startswith("- [")


def test_append_note_to_file_smart_tags(tmp_path):
    """append_note_to_file applies smart tag emojis."""
    from cogstash import append_note_to_file
    out = tmp_path / "notes.md"
    custom = {"work": "💼"}
    append_note_to_file("meeting #work", out, smart_tags=custom)
    content = out.read_text(encoding="utf-8")
    assert "💼" in content


def test_append_note_to_file_multiline(tmp_path):
    """Multi-line notes get 2-space indented continuation."""
    from cogstash import append_note_to_file
    out = tmp_path / "notes.md"
    append_note_to_file("line one\nline two\nline three", out)
    content = out.read_text(encoding="utf-8")
    assert "  line two\n" in content
    assert "  line three\n" in content


def test_append_note_to_file_empty(tmp_path):
    """Empty text returns False and writes nothing."""
    from cogstash import append_note_to_file
    out = tmp_path / "notes.md"
    result = append_note_to_file("  ", out)
    assert result is False
    assert not out.exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest test_cogstash.py -k "parse_smart_tags_custom or parse_smart_tags_default or append_note_to_file" -v`
Expected: FAIL (parse_smart_tags doesn't accept smart_tags param, append_note_to_file doesn't exist)

- [ ] **Step 3: Implement the changes**

In `cogstash.py`:

1. Update `parse_smart_tags()` to accept an optional parameter:
   ```python
   def parse_smart_tags(text: str, smart_tags: dict[str, str] | None = None) -> str:
       """Prepend smart-tag emojis to text. Tags stay inline for searchability."""
       tags_dict = smart_tags if smart_tags is not None else DEFAULT_SMART_TAGS
       matches = _TAG_RE.findall(text)
       seen = []
       for tag in matches:
           tag_lower = tag.lower()
           if tag_lower in tags_dict and tag_lower not in seen:
               seen.append(tag_lower)
       if not seen:
           return text
       prefix = " ".join(tags_dict[t] for t in seen)
       return f"{prefix} {text}"
   ```

2. Add `append_note_to_file()` as a module-level function (place it right after `parse_smart_tags`):
   ```python
   def append_note_to_file(
       text: str,
       output_file: Path,
       smart_tags: dict[str, str] | None = None,
   ) -> bool:
       """Append a timestamped note to the given file. Returns True on success."""
       text = text.strip()
       if not text:
           return False
       if len(text) > 10_000:
           text = text[:10_000]

       text = parse_smart_tags(text, smart_tags)
       timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
       lines = text.split("\n")
       first = f"- [{timestamp}] {lines[0]}\n"
       rest = "".join(f"  {line}\n" for line in lines[1:])

       try:
           output_file.parent.mkdir(parents=True, exist_ok=True)
           with output_file.open("a", encoding="utf-8") as f:
               f.write(first + rest)
           return True
       except OSError:
           logger.error("Failed to write to %s", output_file, exc_info=True)
           return False
   ```

3. Simplify `CogStash.append_note()` to delegate:
   ```python
   def append_note(self, text: str) -> bool:
       """Append a timestamped note to output file. Returns True on success."""
       smart_tags, _ = merge_tags(self.config)
       return append_note_to_file(text, self.config.output_file, smart_tags)
   ```

- [ ] **Step 4: Run all tests**

Run: `python -m pytest test_cogstash.py test_cogstash_search.py test_cogstash_browse.py test_cogstash_cli.py -v`
Expected: All pass

- [ ] **Step 5: Commit**

```bash
git add cogstash.py test_cogstash.py
git commit -m "feat: parameterize parse_smart_tags and extract append_note_to_file"
```

---

### Task 3: Wire custom tags into autocomplete + browse window

**Files:**
- Modify: `cogstash.py` (lines 302-334: _on_key_release, lines 448-451: _open_browse)
- Modify: `cogstash_browse.py` (lines 14-15: imports, lines 21-84: __init__ + pills, lines 197-259: _render_card)
- Modify: `test_cogstash_browse.py`

This task wires the merged custom tags into the GUI: autocomplete filters from merged tags, and the browse window receives merged tags/colors as constructor parameters.

- [ ] **Step 1: Write failing test for browse with custom tags**

Add to `test_cogstash_browse.py`:

```python
@needs_display
def test_browse_custom_tag_pills(tk_root, tmp_path):
    """Custom tags appear as filter pills in the browse window."""
    from cogstash import CogStashConfig
    from cogstash_browse import BrowseWindow
    notes_file = tmp_path / "cogstash.md"
    notes_file.write_text("- [2026-03-27 10:00] meeting #work\n", encoding="utf-8")
    config = CogStashConfig(output_file=notes_file)
    custom_smart = {"todo": "☐", "work": "💼"}
    custom_colors = {"todo": "#7aa2f7", "work": "#4A90D9"}
    bw = BrowseWindow(tk_root, config, smart_tags=custom_smart, tag_colors=custom_colors)
    assert "work" in bw._pill_buttons
    bw.window.destroy()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest test_cogstash_browse.py::test_browse_custom_tag_pills -v`
Expected: FAIL (BrowseWindow doesn't accept smart_tags/tag_colors params)

- [ ] **Step 3: Implement the changes**

In `cogstash_browse.py`:

1. Update imports (line 14-15):
   ```python
   from cogstash import THEMES, DEFAULT_SMART_TAGS, CogStashConfig, platform_font
   from cogstash_search import parse_notes, search_notes, filter_by_tag, mark_done, DEFAULT_TAG_COLORS, Note
   ```

2. Update `BrowseWindow.__init__` to accept optional merged dicts:
   ```python
   def __init__(self, root: tk.Tk, config: CogStashConfig,
                smart_tags: dict[str, str] | None = None,
                tag_colors: dict[str, str] | None = None):
       self.root = root
       self.config = config
       self.theme = THEMES[config.theme]
       self.smart_tags = smart_tags or dict(DEFAULT_SMART_TAGS)
       self.tag_colors = tag_colors or dict(DEFAULT_TAG_COLORS)
       # ... rest unchanged
   ```

3. Update `_build_ui` tag pills loop (line 75-84) to use `self.smart_tags` and `self.tag_colors`:
   ```python
   for tag, emoji in self.smart_tags.items():
       color = self.tag_colors.get(tag, t["muted"])
       # ... rest unchanged
   ```

4. Update `_render_card` (lines 202-206) to use `self.tag_colors`:
   ```python
   border_color = t["muted"]
   for tag in note.tags:
       if tag in self.tag_colors:
           border_color = self.tag_colors[tag]
           break
   ```

5. Update tag pills in `_render_card` (line 255) to use `self.tag_colors`:
   ```python
   color = self.tag_colors.get(tag, t["muted"])
   ```

In `cogstash.py`:

1. Update `_on_key_release` autocomplete (line 325-328) to use merged tags:
   ```python
   smart_tags, _ = merge_tags(self.config)
   matches = [
       (name, emoji) for name, emoji in smart_tags.items()
       if name.startswith(fragment)
   ]
   ```

2. Update `_open_browse` (lines 448-451) to pass merged tags:
   ```python
   def _open_browse(self):
       """Open the Browse Notes window."""
       from cogstash_browse import BrowseWindow
       smart_tags, tag_colors = merge_tags(self.config)
       BrowseWindow(self.root, self.config, smart_tags, tag_colors)
   ```

- [ ] **Step 4: Run all tests**

Run: `python -m pytest test_cogstash.py test_cogstash_search.py test_cogstash_browse.py test_cogstash_cli.py -v`
Expected: All pass

- [ ] **Step 5: Commit**

```bash
git add cogstash.py cogstash_browse.py test_cogstash_browse.py
git commit -m "feat: wire custom tags into autocomplete and browse window"
```

---

### Task 4: Dynamic CLI tag colors with hex_to_ansi

**Files:**
- Modify: `cogstash_cli.py` (lines 21-26: ANSI_TAG, lines 29-47: format_note, lines 82-107: cmd_tags, lines 136-148: cli_main)
- Modify: `test_cogstash_cli.py`

This task makes the CLI's ANSI tag coloring dynamic. A new `hex_to_ansi()` helper maps hex colors to the nearest 8-color ANSI code. The hardcoded `ANSI_TAG` dict becomes a fallback default, and commands receive a dynamic map built from merged tag colors.

- [ ] **Step 1: Write failing tests**

Add to `test_cogstash_cli.py`:

```python
def test_hex_to_ansi():
    """hex_to_ansi maps hex colors to nearest ANSI codes."""
    from cogstash_cli import hex_to_ansi
    assert hex_to_ansi("#ff0000") == "\033[31m"  # red
    assert hex_to_ansi("#00ff00") == "\033[32m"  # green
    assert hex_to_ansi("#0000ff") == "\033[34m"  # blue
    assert hex_to_ansi("#ffff00") == "\033[33m"  # yellow


def test_format_note_custom_tag(tmp_path):
    """format_note colors custom tags when ansi_tag map provided."""
    from cogstash_cli import format_note
    from cogstash_search import Note
    from datetime import datetime
    note = Note(index=1, timestamp=datetime(2026, 3, 27, 10, 0),
                text="meeting #work", tags=["work"])
    ansi_map = {"work": "\033[34m"}
    result = format_note(note, use_color=True, ansi_tag=ansi_map)
    assert "\033[34m" in result  # blue for #work
    assert "#work" in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest test_cogstash_cli.py -k "hex_to_ansi or format_note_custom_tag" -v`
Expected: FAIL (hex_to_ansi doesn't exist, format_note doesn't accept ansi_tag)

- [ ] **Step 3: Implement the changes**

In `cogstash_cli.py`:

1. Rename `ANSI_TAG` → `DEFAULT_ANSI_TAG` (line 21) and keep as fallback:
   ```python
   DEFAULT_ANSI_TAG = {
       "urgent": "\033[31m",
       "important": "\033[33m",
       "idea": "\033[32m",
       "todo": "\033[36m",
   }
   ```

2. Add `hex_to_ansi()` helper after the ANSI constants:
   ```python
   def hex_to_ansi(hex_color: str) -> str:
       """Map a hex color to the nearest 8-color ANSI escape code."""
       r = int(hex_color[1:3], 16)
       g = int(hex_color[3:5], 16)
       b = int(hex_color[5:7], 16)
       # 8-color ANSI palette: map by dominant channel(s)
       ansi_map = [
           (0, 0, 0, "\033[30m"),       # black
           (255, 0, 0, "\033[31m"),     # red
           (0, 255, 0, "\033[32m"),     # green
           (255, 255, 0, "\033[33m"),   # yellow
           (0, 0, 255, "\033[34m"),     # blue
           (255, 0, 255, "\033[35m"),   # magenta
           (0, 255, 255, "\033[36m"),   # cyan
           (255, 255, 255, "\033[37m"), # white
       ]
       best = min(ansi_map, key=lambda c: (c[0]-r)**2 + (c[1]-g)**2 + (c[2]-b)**2)
       return best[3]
   ```

3. Add `build_ansi_tag_map()` helper:
   ```python
   def build_ansi_tag_map(tag_colors: dict[str, str]) -> dict[str, str]:
       """Build ANSI color map from hex tag colors. All tags converted from hex."""
       return {tag: hex_to_ansi(color) for tag, color in tag_colors.items()}
   ```
   Note: this converts ALL tags (including built-ins) from hex, so user overrides of built-in tag colors are reflected in CLI output too. The 8-color approximation is lossy but consistent with the browse window.

4. Update `format_note()` to accept optional `ansi_tag` parameter:
   ```python
   def format_note(note: Note, use_color: bool = True, ansi_tag: dict[str, str] | None = None) -> str:
       """Format a single note as one line of CLI output."""
       tag_map = ansi_tag if ansi_tag is not None else DEFAULT_ANSI_TAG
       # ... rest uses tag_map instead of ANSI_TAG
   ```

5. Update `cmd_tags()` to accept and use dynamic ansi_tag map. Update signature pattern — commands now receive `(args, config, ansi_tag)`:
   ```python
   def cmd_recent(args, config, ansi_tag=None):
       # ... uses format_note(note, use_color, ansi_tag)

   def cmd_search(args, config, ansi_tag=None):
       # ... uses format_note(note, use_color, ansi_tag)

   def cmd_tags(args, config, ansi_tag=None):
       tag_map = ansi_tag or DEFAULT_ANSI_TAG
       # ... uses tag_map.get(tag, "")
   ```

6. Update `cli_main()` to build and pass the ansi map:
   ```python
   def cli_main(argv: list[str]) -> None:
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
   ```

- [ ] **Step 4: Run all tests**

Run: `python -m pytest test_cogstash.py test_cogstash_search.py test_cogstash_browse.py test_cogstash_cli.py -v`
Expected: All pass. Existing format_note tests still pass because `ansi_tag=None` falls back to DEFAULT_ANSI_TAG.

- [ ] **Step 5: Commit**

```bash
git add cogstash_cli.py test_cogstash_cli.py
git commit -m "feat: dynamic CLI tag colors with hex_to_ansi mapping"
```

---

### Task 5: Implement `cogstash add` CLI command

**Files:**
- Modify: `cogstash_cli.py` (add cmd_add, update build_parser)
- Modify: `cogstash.py` (line 521: main() argv guard)
- Modify: `test_cogstash_cli.py`

This task adds the `cogstash add` subcommand that captures notes from the command line or stdin.

- [ ] **Step 1: Write failing tests**

Add to `test_cogstash_cli.py`:

```python
def test_cmd_add_argument(tmp_path):
    """cogstash add 'text' saves a note from argument."""
    from cogstash_cli import cmd_add
    from cogstash import CogStashConfig
    out = tmp_path / "cogstash.md"
    config = CogStashConfig(output_file=out)
    args = argparse.Namespace(text="hello world", func=cmd_add)
    cmd_add(args, config)
    content = out.read_text(encoding="utf-8")
    assert "hello world" in content
    assert content.startswith("- [")


def test_cmd_add_stdin(tmp_path, monkeypatch):
    """cogstash add reads from stdin when no argument given."""
    import io
    from cogstash_cli import cmd_add
    from cogstash import CogStashConfig
    out = tmp_path / "cogstash.md"
    config = CogStashConfig(output_file=out)
    monkeypatch.setattr("sys.stdin", io.StringIO("from stdin"))
    args = argparse.Namespace(text=None, func=cmd_add)
    cmd_add(args, config)
    content = out.read_text(encoding="utf-8")
    assert "from stdin" in content


def test_cmd_add_smart_tags(tmp_path):
    """cogstash add applies smart tag emojis."""
    from cogstash_cli import cmd_add
    from cogstash import CogStashConfig
    out = tmp_path / "cogstash.md"
    config = CogStashConfig(output_file=out)
    args = argparse.Namespace(text="buy milk #todo", func=cmd_add)
    cmd_add(args, config)
    content = out.read_text(encoding="utf-8")
    assert "☐" in content


def test_cmd_add_multiline_stdin(tmp_path, monkeypatch):
    """Multi-line stdin gets 2-space continuation."""
    import io
    from cogstash_cli import cmd_add
    from cogstash import CogStashConfig
    out = tmp_path / "cogstash.md"
    config = CogStashConfig(output_file=out)
    monkeypatch.setattr("sys.stdin", io.StringIO("line one\nline two"))
    args = argparse.Namespace(text=None, func=cmd_add)
    cmd_add(args, config)
    content = out.read_text(encoding="utf-8")
    assert "  line two\n" in content


def test_cmd_add_empty(tmp_path, monkeypatch, capsys):
    """Empty input prints error and exits with code 1."""
    import io
    from cogstash_cli import cmd_add
    from cogstash import CogStashConfig
    out = tmp_path / "cogstash.md"
    config = CogStashConfig(output_file=out)
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    args = argparse.Namespace(text=None, func=cmd_add)
    with pytest.raises(SystemExit) as exc_info:
        cmd_add(args, config)
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "no text" in captured.err.lower()
    assert not out.exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest test_cogstash_cli.py -k "cmd_add" -v`
Expected: FAIL (cmd_add doesn't exist)

- [ ] **Step 3: Implement the changes**

In `cogstash_cli.py`:

1. Add `cmd_add()` function (before `build_parser`):
   ```python
   def cmd_add(args, config, ansi_tag=None):
       """Add a note from argument or stdin."""
       from cogstash import append_note_to_file, merge_tags

       text = args.text if args.text else sys.stdin.read()

       if not text or not text.strip():
           print("Error: no text provided.", file=sys.stderr)
           sys.exit(1)

       smart_tags, _ = merge_tags(config)
       success = append_note_to_file(text, config.output_file, smart_tags)

       if success:
           print(f"✓ Note saved to {config.output_file}")
       else:
           print(f"Error: failed to write to {config.output_file}", file=sys.stderr)
           sys.exit(1)
   ```

2. Add `add` subcommand to `build_parser()` (after the `tags` parser):
   ```python
   # add
   p_add = sub.add_parser("add", help="Add a note from the command line")
   p_add.add_argument("text", nargs="?", help="Note text (reads stdin if omitted)")
   p_add.set_defaults(func=cmd_add)
   ```

In `cogstash.py`:

1. Update the argv guard (line 521):
   ```python
   if len(sys.argv) > 1 and sys.argv[1] in ("recent", "search", "tags", "add"):
   ```

- [ ] **Step 4: Run all tests**

Run: `python -m pytest test_cogstash.py test_cogstash_search.py test_cogstash_browse.py test_cogstash_cli.py -v`
Expected: All pass

- [ ] **Step 5: Commit**

```bash
git add cogstash_cli.py cogstash.py test_cogstash_cli.py
git commit -m "feat(cli): add 'cogstash add' command for CLI note capture"
```

---

## Task Dependency Graph

```
Task 1 (config + merge_tags)
  ├── Task 2 (parse_smart_tags + append_note_to_file)
  │     └── Task 5 (cogstash add)
  ├── Task 3 (autocomplete + browse)
  └── Task 4 (CLI colors)
        └── Task 5 (cogstash add)
```

Tasks 2, 3, and 4 can begin after Task 1. Task 5 requires both Task 2 and Task 4.
