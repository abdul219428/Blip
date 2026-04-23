# Build And Installer Artifact Contracts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Centralize build, installer, and release artifact naming/path rules in one shared contract module and make the existing packaging scripts consume that contract instead of re-deriving conventions.

**Architecture:** Add a small `scripts/_artifacts.py` helper that owns artifact identities, output paths, archive names, and installer staging names. Refactor `scripts/build.py`, `scripts/build_installer.py`, and the naming-sensitive parts of `.github/workflows/release.yml` to consume that shared contract while preserving current external artifact names.

**Tech Stack:** Python, PyInstaller, Inno Setup, GitHub Actions YAML, `pytest`

---

## File Map

- Create: `scripts/_artifacts.py`
  Purpose: shared source of truth for artifact naming, expected output paths, archive names, and installer staging names.
- Modify: `scripts/build.py`
  Purpose: consume shared artifact naming helpers instead of local naming functions.
- Modify: `scripts/build_installer.py`
  Purpose: consume shared artifact naming/path helpers instead of duplicating naming/path rules.
- Modify: `.github/workflows/release.yml`
  Purpose: reduce inline rename/archive naming logic and rely on small Python helpers that apply the shared contract.
- Modify: `tests/test_build_installer.py`
  Purpose: add direct contract tests and update build/installer/release assertions to verify shared ownership.

### Task 1: Add red tests for the shared artifact contract

**Files:**
- Modify: `tests/test_build_installer.py`

- [ ] **Step 1: Add failing tests for artifact naming and lookup helpers**

```python
def _load_artifacts_module():
    import importlib.util
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[1]
    module_path = repo_root / "scripts" / "_artifacts.py"
    spec = importlib.util.spec_from_file_location("artifacts_contract", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_artifact_contract_build_names():
    module = _load_artifacts_module()

    assert module.get_executable_name(target="ui", bundle_mode="onefile", version="1.2.3") == "CogStash-1.2.3"
    assert module.get_executable_name(target="ui", bundle_mode="onedir", version="1.2.3") == "CogStash-1.2.3-onedir"
    assert module.get_executable_name(target="cli", bundle_mode="onefile", version="1.2.3") == "CogStash-CLI-1.2.3"


def test_artifact_contract_windows_paths(tmp_path):
    module = _load_artifacts_module()

    layout = module.windows_artifact_layout(version="1.2.3", dist_dir=tmp_path / "dist")

    assert layout.onedir_dir == tmp_path / "dist" / "CogStash-1.2.3-onedir"
    assert layout.onedir_exe == layout.onedir_dir / "CogStash-1.2.3-onedir.exe"
    assert layout.cli_exe == tmp_path / "dist" / "CogStash-CLI-1.2.3.exe"
    assert layout.staged_app_dirname == "CogStash"
    assert layout.staged_ui_exe_name == "CogStash.exe"
    assert layout.staged_cli_exe_name == "CogStash-CLI.exe"


def test_artifact_contract_release_archive_names():
    module = _load_artifacts_module()

    assert module.get_release_archive_name(tag="v1.2.3", platform_suffix="windows") == "CogStash-v1.2.3-windows.zip"
    assert module.get_release_archive_name(tag="v1.2.3", platform_suffix="macos") == "CogStash-v1.2.3-macos.zip"
    assert module.get_release_archive_name(tag="v1.2.3", platform_suffix="linux") == "CogStash-v1.2.3-linux.tar.gz"
```

- [ ] **Step 2: Run the new contract tests to verify they fail**

Run: `python -m pytest tests/test_build_installer.py -k "artifact_contract" -q`
Expected: FAIL with `FileNotFoundError`, `ModuleNotFoundError`, or missing helper attributes because `scripts/_artifacts.py` does not exist yet.

- [ ] **Step 3: Add a failing test that build/installer code imports the shared contract**

```python
def test_build_and_installer_import_shared_artifact_contract():
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[1]
    build_source = (repo_root / "scripts" / "build.py").read_text(encoding="utf-8")
    installer_source = (repo_root / "scripts" / "build_installer.py").read_text(encoding="utf-8")

    assert "from _artifacts import " in build_source or "import _artifacts" in build_source
    assert "from _artifacts import " in installer_source or "import _artifacts" in installer_source
```

- [ ] **Step 4: Run the import-ownership test to verify it fails**

Run: `python -m pytest tests/test_build_installer.py -k "shared_artifact_contract" -q`
Expected: FAIL because the scripts still own duplicated local naming helpers.

- [ ] **Step 5: Commit the red test checkpoint**

```bash
git add tests/test_build_installer.py
git commit -m "test: define artifact contract coverage"
```

### Task 2: Implement the shared artifact-contract module

**Files:**
- Create: `scripts/_artifacts.py`
- Modify: `tests/test_build_installer.py`

- [ ] **Step 1: Create the contract module with explicit artifact helpers**

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

STAGED_APP_DIRNAME = "CogStash"
STAGED_UI_EXE_NAME = "CogStash.exe"
STAGED_CLI_EXE_NAME = "CogStash-CLI.exe"


def get_executable_name(*, target: str, bundle_mode: str, version: str) -> str:
    if target == "ui":
        return f"CogStash-{version}" if bundle_mode == "onefile" else f"CogStash-{version}-onedir"
    if target == "cli":
        return f"CogStash-CLI-{version}"
    raise ValueError(f"Unknown target: {target}")


def get_onedir_dir_name(version: str) -> str:
    return get_executable_name(target="ui", bundle_mode="onedir", version=version)


def get_onedir_exe_name(version: str) -> str:
    return f"{get_onedir_dir_name(version)}.exe"


def get_cli_exe_name(version: str) -> str:
    return f"{get_executable_name(target='cli', bundle_mode='onefile', version=version)}.exe"


def get_release_archive_name(*, tag: str, platform_suffix: str) -> str:
    if platform_suffix == "windows":
        return f"CogStash-{tag}-windows.zip"
    if platform_suffix == "macos":
        return f"CogStash-{tag}-macos.zip"
    if platform_suffix == "linux":
        return f"CogStash-{tag}-linux.tar.gz"
    raise ValueError(f"Unknown platform suffix: {platform_suffix}")


@dataclass(frozen=True)
class WindowsArtifactLayout:
    onedir_dir: Path
    onedir_exe: Path
    cli_exe: Path
    staged_app_dirname: str = STAGED_APP_DIRNAME
    staged_ui_exe_name: str = STAGED_UI_EXE_NAME
    staged_cli_exe_name: str = STAGED_CLI_EXE_NAME


def windows_artifact_layout(*, version: str, dist_dir: Path) -> WindowsArtifactLayout:
    onedir_dir = dist_dir / get_onedir_dir_name(version)
    return WindowsArtifactLayout(
        onedir_dir=onedir_dir,
        onedir_exe=onedir_dir / get_onedir_exe_name(version),
        cli_exe=dist_dir / get_cli_exe_name(version),
    )
```

- [ ] **Step 2: Run the new contract tests and make them pass**

Run: `python -m pytest tests/test_build_installer.py -k "artifact_contract" -q`
Expected: PASS

- [ ] **Step 3: Commit the new shared contract module**

```bash
git add scripts/_artifacts.py tests/test_build_installer.py
git commit -m "feat: add shared artifact contract"
```

### Task 3: Refactor build and installer scripts to consume the contract

**Files:**
- Modify: `scripts/build.py`
- Modify: `scripts/build_installer.py`
- Modify: `tests/test_build_installer.py`

- [ ] **Step 1: Replace duplicated naming helpers in `scripts/build.py`**

```python
from _artifacts import get_executable_name


def run_pyinstaller(
    *,
    target: str,
    bundle_mode: str,
    debug: bool,
    icon_path: str | None,
    version: str,
) -> None:
    entry = get_entrypoint(target)
    hidden_imports = get_hidden_imports(target)
    name = get_executable_name(target=target, bundle_mode=bundle_mode, version=version)
    ...
```

- [ ] **Step 2: Replace duplicated naming/path helpers in `scripts/build_installer.py`**

```python
from _artifacts import (
    STAGED_APP_DIRNAME,
    STAGED_CLI_EXE_NAME,
    STAGED_UI_EXE_NAME,
    windows_artifact_layout,
)


def find_windows_onedir_bundle(dist_dir: Path, version: str) -> Path:
    layout = windows_artifact_layout(version=version, dist_dir=dist_dir)
    if not layout.onedir_dir.is_dir():
        raise FileNotFoundError(f"Windows onedir bundle not found: {layout.onedir_dir}")
    if not layout.onedir_exe.is_file():
        raise FileNotFoundError(f"Expected bundle executable not found: {layout.onedir_exe}")
    return layout.onedir_dir


def find_windows_cli_binary(dist_dir: Path, version: str) -> Path:
    layout = windows_artifact_layout(version=version, dist_dir=dist_dir)
    if not layout.cli_exe.is_file():
        raise FileNotFoundError(f"Windows CLI binary not found: {layout.cli_exe}")
    return layout.cli_exe
```

- [ ] **Step 3: Update tests to assert shared-contract consumption**

```python
def test_build_and_installer_import_shared_artifact_contract():
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[1]
    build_source = (repo_root / "scripts" / "build.py").read_text(encoding="utf-8")
    installer_source = (repo_root / "scripts" / "build_installer.py").read_text(encoding="utf-8")

    assert "from _artifacts import " in build_source
    assert "from _artifacts import " in installer_source
    assert "def get_onedir_dir_name" not in installer_source
```

- [ ] **Step 4: Run the script-level build/installer tests**

Run: `python -m pytest tests/test_build_installer.py -k "build or installer or artifact_contract or shared_artifact_contract" -q`
Expected: PASS

- [ ] **Step 5: Commit the script refactor**

```bash
git add scripts/build.py scripts/build_installer.py tests/test_build_installer.py
git commit -m "refactor: share artifact naming contracts"
```

### Task 4: Reduce workflow naming duplication

**Files:**
- Modify: `.github/workflows/release.yml`
- Modify: `tests/test_build_installer.py`

- [ ] **Step 1: Add a small Python helper step in the workflow for naming-sensitive rename/archive outputs**

```yaml
      - name: Rename onefile artifacts
        run: |
          from pathlib import Path
          import os

          from _artifacts import get_executable_name

          suffix = "${{ matrix.artifact_suffix }}"
          ext = "${{ matrix.exe_ext }}"
          version = os.environ["GITHUB_REF_NAME"]
          dist_dir = Path("dist")

          ui_source = dist_dir / f"{get_executable_name(target='ui', bundle_mode='onefile', version=version)}{ext}"
          cli_source = dist_dir / f"{get_executable_name(target='cli', bundle_mode='onefile', version=version)}{ext}"
          ui_target = dist_dir / f"CogStash-{version}-{suffix}{ext}"
          cli_target = dist_dir / f"CogStash-CLI-{version}-{suffix}{ext}"
          ui_source.replace(ui_target)
          cli_source.replace(cli_target)
        shell: python
```

- [ ] **Step 2: Keep workflow orchestration intact but remove duplicated artifact identity assumptions where practical**

```yaml
      - name: Archive onedir bundle (Windows)
        if: matrix.os == 'windows-latest'
        run: |
          import os
          import subprocess
          from _artifacts import get_release_archive_name

          archive_name = get_release_archive_name(tag=os.environ["GITHUB_REF_NAME"], platform_suffix="windows")
          subprocess.run(["powershell", "-Command", f"Compress-Archive -Path dist/CogStash-*-onedir -DestinationPath dist/{archive_name}"], check=True)
        shell: python
```

- [ ] **Step 3: Update workflow assertions in tests**

```python
def test_release_workflow_uses_shared_artifact_contract():
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[1]
    content = (repo_root / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

    assert "from _artifacts import get_executable_name" in content
    assert "from _artifacts import get_release_archive_name" in content
    assert "dist/CogStash-v*-setup.exe" in content
```

- [ ] **Step 4: Run the workflow-related tests**

Run: `python -m pytest tests/test_build_installer.py -k "release_workflow" -q`
Expected: PASS

- [ ] **Step 5: Commit the workflow contract cleanup**

```bash
git add .github/workflows/release.yml tests/test_build_installer.py
git commit -m "refactor: centralize release artifact naming"
```

### Task 5: Final verification and finish

**Files:**
- Verify: `scripts/_artifacts.py`
- Verify: `scripts/build.py`
- Verify: `scripts/build_installer.py`
- Verify: `.github/workflows/release.yml`
- Verify: `tests/test_build_installer.py`

- [ ] **Step 1: Run lint on the changed scripts and tests**

Run: `python -m ruff check scripts/_artifacts.py scripts/build.py scripts/build_installer.py tests/test_build_installer.py`
Expected: PASS

- [ ] **Step 2: Run the full focused packaging test suite**

Run: `python -m pytest tests/test_build_installer.py -q`
Expected: PASS

- [ ] **Step 3: Run targeted typing if the changed scripts are included in static checking**

Run: `python -m mypy scripts/_artifacts.py scripts/build.py scripts/build_installer.py`
Expected: PASS or, if scripts are intentionally outside mypy scope, document that clearly instead of guessing.

- [ ] **Step 4: Inspect the final diff**

Run: `git diff -- scripts/_artifacts.py scripts/build.py scripts/build_installer.py .github/workflows/release.yml tests/test_build_installer.py`
Expected: only shared artifact contract and related test/workflow changes.

- [ ] **Step 5: Commit any final verification fixes if needed**

```bash
git add scripts/_artifacts.py scripts/build.py scripts/build_installer.py .github/workflows/release.yml tests/test_build_installer.py
git commit -m "test: finalize artifact contract coverage"
```

- [ ] **Step 6: Prepare handoff notes**

```text
Summarize:
- shared artifact contract module added
- build and installer scripts now consume one source of truth
- release workflow uses less inline naming logic
- verification commands and results
```
