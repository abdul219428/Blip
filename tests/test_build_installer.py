"""Tests for Windows installer build helpers."""

from __future__ import annotations

import importlib.util
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
    assert 'if WizardIsTaskSelected(\'startup\') then' in content
    assert 'SaveStringToFile(ExpandConstant(\'{userstartup}\\CogStash.bat\')' in content
    assert 'ExpandConstant(\'{app}\\CogStash.exe\')' in content
    assert 'Type: files; Name: "{userstartup}\\CogStash.bat"' in content


def test_inno_setup_script_supports_optional_path_task():
    """Installer should expose an optional PATH task for CLI access."""
    repo_root = Path(__file__).resolve().parents[1]
    iss_path = repo_root / "installer" / "windows" / "CogStash.iss"

    content = iss_path.read_text(encoding="utf-8")

    assert 'Name: "addtopath"; Description: "Add CogStash to PATH' in content
    assert "RegisterPreviousData" in content
    assert "GetPreviousData" in content
    assert "SetPreviousData" in content
    assert "EnvAddPath" in content
    assert "EnvRemovePath" in content


def test_inno_setup_script_tracks_path_ownership_and_duplicates():
    """Installer PATH code should normalize duplicates and remove only owned entries."""
    repo_root = Path(__file__).resolve().parents[1]
    iss_path = repo_root / "installer" / "windows" / "CogStash.iss"

    content = iss_path.read_text(encoding="utf-8")

    assert "ExpandConstant('{app}')" in content
    assert "Result := LowerCase(Result);" in content
    assert "AddPathEntry" in content
    assert "RemovePathEntry" in content
    assert "StringChangeEx(Result, '%localappdata%', LowerCase(GetEnv('LOCALAPPDATA')), True);" in content
    assert "StringChangeEx(Result, '%userprofile%', LowerCase(GetEnv('USERPROFILE')), True);" in content
    assert "StringChangeEx" in content
    assert "Result := PreviouslyOwned;" in content


def test_inno_setup_script_makes_uninstall_path_cleanup_best_effort():
    """Optional PATH cleanup should log failures instead of aborting uninstall."""
    repo_root = Path(__file__).resolve().parents[1]
    iss_path = repo_root / "installer" / "windows" / "CogStash.iss"

    content = iss_path.read_text(encoding="utf-8")

    assert "Log('Could not remove the installer-managed PATH entry." in content
    assert "RaiseException('Could not remove the installer-managed PATH entry." not in content


def test_inno_setup_script_preserves_expandable_path_writes():
    """PATH rewrites should preserve expandable registry semantics."""
    repo_root = Path(__file__).resolve().parents[1]
    iss_path = repo_root / "installer" / "windows" / "CogStash.iss"

    content = iss_path.read_text(encoding="utf-8")

    assert "RegWriteExpandStringValue(HKEY_CURRENT_USER, UserEnvironmentSubkey, UserPathValueName, NewPath)" in content


def test_stage_windows_payload_copies_bundle_and_renames_exe(tmp_path):
    """Stage helper should normalize the app dir and executable name."""
    module = _load_build_installer_module()
    version = "1.2.3"
    bundle_dir = tmp_path / "dist" / f"CogStash-{version}-onedir"
    bundle_dir.mkdir(parents=True)
    (bundle_dir / f"CogStash-{version}-onedir.exe").write_text("exe", encoding="utf-8")
    (bundle_dir / "support.dll").write_text("dll", encoding="utf-8")
    (bundle_dir / "assets").mkdir()
    (bundle_dir / "assets" / "icon.png").write_text("png", encoding="utf-8")

    staged_dir = module.stage_windows_payload(
        bundle_dir=bundle_dir,
        version=version,
        staging_root=tmp_path / "build" / "installer",
    )

    assert staged_dir.name == "CogStash"
    assert (staged_dir / "CogStash.exe").read_text(encoding="utf-8") == "exe"
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
