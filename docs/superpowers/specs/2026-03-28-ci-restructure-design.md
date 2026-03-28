# Phase 9: GitHub Actions CI + src/ Package Restructure — Design Spec

## Goal

Restructure CogStash from a flat-file layout into a proper `src/cogstash/` Python package, move tests into a `tests/` directory, and add GitHub Actions CI with pytest, ruff, and mypy across Python 3.9–3.13.

## Current State

- 4 source modules flat in root: `cogstash.py`, `cogstash_cli.py`, `cogstash_search.py`, `cogstash_browse.py`
- 4 test files flat in root: `test_cogstash.py`, `test_cogstash_cli.py`, `test_cogstash_search.py`, `test_cogstash_browse.py`
- `conftest.py` in root
- `pyproject.toml` uses `py-modules` (flat) layout
- No CI/CD configured
- No linter or type checker configured
- 98 tests passing

## Target State

### Package Structure

```
CogStash/
├── src/
│   └── cogstash/
│       ├── __init__.py      # Re-exports main() from app
│       ├── app.py           # Main tkinter app (was cogstash.py)
│       ├── browse.py        # Browse window (was cogstash_browse.py)
│       ├── cli.py           # CLI commands (was cogstash_cli.py)
│       └── search.py        # Data layer (was cogstash_search.py)
├── tests/
│   ├── conftest.py
│   ├── test_app.py
│   ├── test_browse.py
│   ├── test_cli.py
│   └── test_search.py
├── .github/
│   └── workflows/
│       └── ci.yml
├── pyproject.toml
├── requirements.txt
├── README.md
├── LICENSE
└── docs/
```

### File Mapping

| Old path | New path |
|---|---|
| `cogstash.py` | `src/cogstash/app.py` |
| `cogstash_search.py` | `src/cogstash/search.py` |
| `cogstash_browse.py` | `src/cogstash/browse.py` |
| `cogstash_cli.py` | `src/cogstash/cli.py` |
| (new) | `src/cogstash/__main__.py` |
| `conftest.py` | `tests/conftest.py` |
| `test_cogstash.py` | `tests/test_app.py` |
| `test_cogstash_search.py` | `tests/test_search.py` |
| `test_cogstash_browse.py` | `tests/test_browse.py` |
| `test_cogstash_cli.py` | `tests/test_cli.py` |

### Import Rewiring

All cross-module imports change from flat (`from cogstash_search import ...`) to package (`from cogstash.search import ...`).

| Old import | New import |
|---|---|
| `from cogstash_search import parse_notes, ...` | `from cogstash.search import parse_notes, ...` |
| `from cogstash import THEMES, CogStashConfig, ...` | `from cogstash.app import THEMES, CogStashConfig, ...` |
| `import cogstash as cogstash_mod` (in tests) | `import cogstash.app as cogstash_mod` |
| `from cogstash_search import compute_stats` (lazy) | `from cogstash.search import compute_stats` |
| `from cogstash import load_config, merge_tags` (lazy) | `from cogstash.app import load_config, merge_tags` |
| `from cogstash_cli import cmd_recent, ...` (in tests) | `from cogstash.cli import cmd_recent, ...` |
| `from cogstash_browse import BrowseWindow` (in tests) | `from cogstash.browse import BrowseWindow` |

The `__init__.py` uses a lazy wrapper to avoid importing tkinter/pynput when only submodules are needed:
```python
def main():
    from cogstash.app import main as _main
    _main()
```

A `__main__.py` enables `python -m cogstash`:
```python
from cogstash import main
main()
```

This preserves the entry point `cogstash = "cogstash:main"` in pyproject.toml.

**Note:** The import rewiring table below is representative. Implementers must grep for all `from cogstash` and `from cogstash_` imports in both source and test files.

### pyproject.toml Changes

```toml
[tool.setuptools.packages.find]
where = ["src"]

[project.scripts]
cogstash = "cogstash:main"

[project.optional-dependencies]
dev = ["pytest>=7.0", "ruff>=0.4", "mypy>=1.10"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

**Note:** `requirements.txt` stays runtime-only (pynput, pystray, Pillow). Dev dependencies are installed via `pip install -e ".[dev]"`.

## CI Pipeline

### Workflow: `.github/workflows/ci.yml`

- **Trigger:** push to `main` + pull requests to `main`
- **Matrix:** Python 3.9, 3.10, 3.11, 3.12, 3.13 on `ubuntu-latest`
- **Steps:**
  1. Checkout code
  2. Setup Python (matrix version)
  3. Install dependencies (`pip install -e ".[dev]"`)
  4. Run ruff (`ruff check src/ tests/`)
  5. Run mypy (`mypy src/cogstash/`)
  6. Run pytest (`xvfb-run pytest tests/ -v` — xvfb for tkinter headless)

### Ruff Configuration

Added to `pyproject.toml`:
```toml
[tool.ruff]
target-version = "py39"
line-length = 120

[tool.ruff.lint]
select = ["E", "F", "W", "I"]
```

Rules: E (pycodestyle errors), F (pyflakes), W (warnings), I (isort import ordering).

### Mypy Configuration

Added to `pyproject.toml`:
```toml
[tool.mypy]
python_version = "3.9"
warn_return_any = true
warn_unused_configs = true
ignore_missing_imports = true
```

`ignore_missing_imports` is necessary because pynput, pystray, and Pillow lack complete type stubs.

### requirements.txt Update

Keep runtime dependencies only:
```
pynput>=1.7
pystray>=0.19
Pillow>=9.0
```

Dev tools (pytest, ruff, mypy) are declared in `[project.optional-dependencies]` and installed via `pip install -e ".[dev]"`.

## Testing Notes

- Tests that require a display (tkinter GUI tests) use the `@needs_display` marker
- On CI (Ubuntu), `xvfb-run` provides a virtual display so these tests can run
- The `conftest.py` shared Tk root pattern remains unchanged
- After restructuring, run `pip install -e .` so package imports resolve correctly
- Target: 98 tests passing on all Python versions

## Scope Exclusions

- No PyInstaller packaging (future phase)
- No coverage reporting (can add later)
- No pre-commit hooks (can add later)
- No Windows/macOS CI runners (tests use Linux + xvfb only)
