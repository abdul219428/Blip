"""Tests for Windows installer build helpers."""

from __future__ import annotations

import importlib.util
import re
import runpy
import sys
from pathlib import Path


def _load_build_installer_module():
    repo_root = Path(__file__).resolve().parents[1]
    module_path = repo_root / "scripts" / "build_installer.py"
    spec = importlib.util.spec_from_file_location("build_installer", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_build_module():
    repo_root = Path(__file__).resolve().parents[1]
    module_path = repo_root / "scripts" / "build.py"
    spec = importlib.util.spec_from_file_location("build_script", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_inno_setup_script_uses_per_user_defaults():
    """Installer script should target a per-user install with standard shortcuts."""
    repo_root = Path(__file__).resolve().parents[1]
    iss_path = repo_root / "installer" / "windows" / "CogStash.iss"

    content = iss_path.read_text(encoding="utf-8")

    assert 'DefaultDirName={localappdata}\\Programs\\CogStash' in content
    assert "PrivilegesRequired=lowest" in content
    assert "OutputBaseFilename=CogStash-v{#AppVersion}-setup" in content
    assert 'Name: "{group}\\CogStash"; Filename: "{app}\\CogStash.exe"' in content


def test_inno_setup_script_supports_optional_startup_task():
    """Installer should expose startup creation and remove that entry on uninstall."""
    repo_root = Path(__file__).resolve().parents[1]
    iss_path = repo_root / "installer" / "windows" / "CogStash.iss"

    content = iss_path.read_text(encoding="utf-8")

    assert 'Name: "startup"; Description: "Launch CogStash when I sign in"' in content
    assert "WizardIsTaskSelected('startup')" in content
    assert 'SaveStringToFile(ExpandConstant(\'{userstartup}\\CogStash.bat\')' in content
    assert 'ExpandConstant(\'{app}\\CogStash.exe\')' in content
    assert 'Type: files; Name: "{userstartup}\\CogStash.bat"' in content


def test_inno_setup_script_does_not_offer_path_task():
    """Installer should no longer offer PATH mutation tasks."""
    repo_root = Path(__file__).resolve().parents[1]
    iss_path = repo_root / "installer" / "windows" / "CogStash.iss"

    content = iss_path.read_text(encoding="utf-8")

    assert 'Name: "addtopath"; Description: "Add CogStash to PATH' not in content
    assert "EnvAddPath" not in content
    assert "EnvRemovePath" not in content
    assert "ChangesEnvironment=yes" not in content


def test_inno_setup_script_does_not_track_path_ownership():
    """Installer should not include PATH ownership or cleanup code."""
    repo_root = Path(__file__).resolve().parents[1]
    iss_path = repo_root / "installer" / "windows" / "CogStash.iss"

    content = iss_path.read_text(encoding="utf-8")

    assert "PathOwnershipMarkerPath" not in content
    assert "PathOwnershipMarkerExists" not in content
    assert "WritePathOwnershipMarker" not in content
    assert "RemovePathOwnershipMarker" not in content
    assert "AddPathEntry" not in content
    assert "RemovePathEntry" not in content
    assert "RegWriteExpandStringValue" not in content


def test_stage_windows_payload_copies_bundle_and_renames_exe(tmp_path):
    """Stage helper should normalize app names and include the CLI executable."""
    module = _load_build_installer_module()
    version = "1.2.3"
    bundle_dir = tmp_path / "dist" / f"CogStash-{version}-onedir"
    bundle_dir.mkdir(parents=True)
    (bundle_dir / f"CogStash-{version}-onedir.exe").write_text("exe", encoding="utf-8")
    (bundle_dir / "support.dll").write_text("dll", encoding="utf-8")
    (bundle_dir / "assets").mkdir()
    (bundle_dir / "assets" / "icon.png").write_text("png", encoding="utf-8")
    cli_binary = tmp_path / "dist" / f"CogStash-CLI-{version}.exe"
    cli_binary.write_text("cli", encoding="utf-8")

    staged_dir = module.stage_windows_payload(
        bundle_dir=bundle_dir,
        cli_binary=cli_binary,
        version=version,
        staging_root=tmp_path / "build" / "installer",
    )

    assert staged_dir.name == "CogStash"
    assert (staged_dir / "CogStash.exe").read_text(encoding="utf-8") == "exe"
    assert (staged_dir / "CogStash-CLI.exe").read_text(encoding="utf-8") == "cli"
    assert not (staged_dir / f"CogStash-{version}-onedir.exe").exists()
    assert (staged_dir / "support.dll").read_text(encoding="utf-8") == "dll"
    assert (staged_dir / "assets" / "icon.png").read_text(encoding="utf-8") == "png"


def test_compile_installer_invokes_iscc_with_expected_defines(monkeypatch, tmp_path):
    """ISCC should receive version, source, and output defines."""
    module = _load_build_installer_module()
    calls = []

    def fake_run(cmd, check):
        calls.append((cmd, check))

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    iss_path = tmp_path / "CogStash.iss"
    source_dir = tmp_path / "payload"
    output_dir = tmp_path / "dist"

    module.compile_installer(
        compiler="iscc.exe",
        iss_path=iss_path,
        version="2.0.0",
        source_dir=source_dir,
        output_dir=output_dir,
    )

    assert calls == [
        (
            [
                "iscc.exe",
                "/DAppVersion=2.0.0",
                "/DVersionInfoVersion=2.0.0.0",
                f"/DSourceDir={source_dir}",
                f"/DOutputDir={output_dir}",
                str(iss_path),
            ],
            True,
        )
    ]


def test_build_script_uses_noconsole_on_windows_when_not_debug(monkeypatch):
    """Windows release builds should use the GUI subsystem to avoid a persistent console window."""
    module = _load_build_module()
    calls = []

    def fake_run(cmd, check):
        calls.append((cmd, check))

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    monkeypatch.setattr(module.sys, "platform", "win32")

    module.run_pyinstaller(target="ui", bundle_mode="onefile", debug=False, icon_path=None, version="1.2.3")

    assert calls, "Expected PyInstaller to be invoked"
    cmd, check = calls[0]
    assert "--noconsole" in cmd
    assert check is True


def test_build_script_cli_target_uses_cli_entrypoint_without_gui_hidden_imports(monkeypatch):
    """CLI target should build from the CLI bootstrap without tray hidden imports."""
    module = _load_build_module()
    calls = []

    def fake_run(cmd, check):
        calls.append((cmd, check))

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    monkeypatch.setattr(module.sys, "platform", "win32")

    module.run_pyinstaller(target="cli", bundle_mode="onefile", debug=False, icon_path=None, version="1.2.3")

    assert calls, "Expected PyInstaller to be invoked"
    cmd, check = calls[0]
    assert str(module.CLI_ENTRY) in cmd
    assert "--name" in cmd
    assert "CogStash-CLI-1.2.3" in cmd
    assert "pystray._win32" not in cmd
    assert check is True


def test_cli_entrypoint_can_run_as_main_script(monkeypatch):
    """CLI bootstrap should work when PyInstaller executes it as __main__."""
    repo_root = Path(__file__).resolve().parents[1]
    src_dir = repo_root / "src"
    entry_path = src_dir / "cogstash" / "cli" / "__main__.py"
    calls: list[tuple[str, object]] = []

    monkeypatch.syspath_prepend(str(src_dir))

    import cogstash.cli
    import cogstash.cli.windows

    monkeypatch.setattr(cogstash.cli.windows, "prepare_windows_cli_console", lambda: calls.append(("prepare", None)))
    monkeypatch.setattr(cogstash.cli, "cli_main", lambda argv: calls.append(("cli", argv)))
    monkeypatch.setattr(sys, "argv", [str(entry_path), "--help"])

    runpy.run_path(str(entry_path), run_name="__main__")

    assert calls == [("prepare", None), ("cli", ["--help"])]


def test_build_script_main_builds_ui_and_cli_targets_for_both(monkeypatch):
    """Default target=both should build UI onefile+onedir and CLI onefile."""
    module = _load_build_module()
    calls = []

    monkeypatch.setattr(module, "get_version", lambda: "1.2.3")
    monkeypatch.setattr(module, "convert_icon", lambda: None)
    monkeypatch.setattr(
        module,
        "run_pyinstaller",
        lambda **kwargs: calls.append(kwargs),
    )
    monkeypatch.setattr(module.sys, "argv", ["build.py", "--target", "both"])

    module.main()

    assert calls == [
        {"target": "ui", "bundle_mode": "onefile", "debug": False, "icon_path": None, "version": "1.2.3"},
        {"target": "ui", "bundle_mode": "onedir", "debug": False, "icon_path": None, "version": "1.2.3"},
        {"target": "cli", "bundle_mode": "onefile", "debug": False, "icon_path": None, "version": "1.2.3"},
    ]


def test_make_version_info_version_normalizes_dev_versions():
    """Inno Setup version info should receive a numeric 4-part version."""
    module = _load_build_installer_module()

    assert module.make_version_info_version("0.1.1.dev0+gf8d42d1c6.d20260328") == "0.1.1.0"
    assert module.make_version_info_version("1.2.3") == "1.2.3.0"
    assert module.make_version_info_version("7") == "7.0.0.0"


def test_release_workflow_builds_and_uploads_windows_installer():
    """Release workflow should compile and publish the Windows setup executable."""
    repo_root = Path(__file__).resolve().parents[1]
    workflow_path = repo_root / ".github" / "workflows" / "release.yml"

    content = workflow_path.read_text(encoding="utf-8")

    assert "Install Inno Setup" in content
    assert "choco install innosetup" in content
    assert "Build Windows installer" in content
    assert "uv run python scripts/build_installer.py" in content
    assert "ProgramFiles(x86)" in content
    assert "dist/CogStash-v*-setup.exe" in content
    assert "Smoke test onedir (Windows)" in content
    assert "dist\\CogStash-*-onedir\\CogStash-*-onedir.exe" in content
    assert "--help output unexpectedly contained Traceback" in content
    assert "--version output unexpectedly contained Traceback" in content


def test_release_workflow_uploads_ui_and_cli_artifacts():
    repo_root = Path(__file__).resolve().parents[1]
    workflow_path = repo_root / ".github" / "workflows" / "release.yml"
    workflow = workflow_path.read_text(encoding="utf-8")

    upload_steps = {
        match["step"]: {"name": match["artifact"], "path": match["path"].strip()}
        for match in re.finditer(
            r"- name: Upload (?P<step>UI|CLI) artifacts\r?\n"
            r"[ \t]+uses: actions/upload-artifact@v\d+\r?\n"
            r"[ \t]+with:\r?\n"
            r"[ \t]+name: (?P<artifact>[^\r\n]+)\r?\n"
            r"[ \t]+path: \|\r?\n"
            r"[ \t]+(?P<path>[^\r\n]+)",
            workflow,
        )
    }

    assert set(upload_steps) == {"UI", "CLI"}
    assert upload_steps["UI"]["name"] == "cogstash-${{ matrix.artifact_suffix }}-ui"
    assert upload_steps["CLI"]["name"] == "cogstash-${{ matrix.artifact_suffix }}-cli"
    assert upload_steps["UI"]["name"] != upload_steps["CLI"]["name"]
    assert upload_steps["UI"]["path"] == "dist/CogStash-${{ github.ref_name }}-${{ matrix.artifact_suffix }}*"
    assert upload_steps["CLI"]["path"] == "dist/CogStash-CLI-${{ github.ref_name }}-${{ matrix.artifact_suffix }}*"
    assert "CLI" not in upload_steps["UI"]["path"]
    assert "CLI" in upload_steps["CLI"]["path"]


def test_release_workflow_smoke_tests_ui_and_cli_on_unix():
    """Release workflow should smoke-test both entrypoints on macOS/Linux too."""
    repo_root = Path(__file__).resolve().parents[1]
    workflow_path = repo_root / ".github" / "workflows" / "release.yml"

    content = workflow_path.read_text(encoding="utf-8")
    ui_smoke_step = re.search(
        r"- name: Smoke test UI onedir \(Unix\)\r?\n"
        r"(?P<body>(?:[ \t]+.*(?:\r?\n|$))+?)"
        r"[ \t]+shell: bash",
        content,
    )

    assert "Install Linux UI smoke-test dependencies" in content
    assert "sudo apt-get install -y xvfb" in content
    assert "if: matrix.os == 'ubuntu-latest'" in content
    assert ui_smoke_step is not None
    ui_smoke_step_body = ui_smoke_step.group("body")
    assert "if: matrix.os != 'windows-latest'" in ui_smoke_step_body
    assert "find dist -maxdepth 2 -path 'dist/CogStash-*-onedir/CogStash-*-onedir'" in ui_smoke_step_body
    assert 'xvfb-run --auto-servernum "$binary" &' in ui_smoke_step_body
    assert any(line.strip() == '"$binary" &' for line in ui_smoke_step_body.splitlines())
    assert 'kill -0 "$pid" 2>/dev/null' in ui_smoke_step_body
    assert 'kill "$pid"' in ui_smoke_step_body
    assert 'wait "$pid"' in ui_smoke_step_body
    assert "exit 1" in ui_smoke_step_body
    assert "Smoke test CLI onefile (Unix)" in content


def test_installer_script_installs_cli_binary_without_shortcut():
    repo_root = Path(__file__).resolve().parents[1]
    iss_path = repo_root / "installer" / "windows" / "CogStash.iss"

    iss = iss_path.read_text(encoding="utf-8")
    assert "CogStash-CLI.exe" in iss
    assert "CogStash CLI" not in iss
