"""Shared artifact naming and path contract for CogStash packaging."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

APP_NAME = "CogStash"
CLI_NAME = "CogStash-CLI"

STAGED_APP_DIRNAME = APP_NAME
STAGED_UI_EXE_NAME = f"{APP_NAME}.exe"
STAGED_CLI_EXE_NAME = f"{CLI_NAME}.exe"
STAGED_CLI_BIN_DIRNAME = "bin"
STAGED_CLI_SHIM_NAME = "cogstash.cmd"


def get_executable_name(*, target: str, bundle_mode: str, version: str) -> str:
    """Return the canonical versioned executable name for a build target."""
    if target == "ui":
        if bundle_mode == "onefile":
            return f"{APP_NAME}-{version}"
        if bundle_mode == "onedir":
            return f"{APP_NAME}-{version}-onedir"
        raise ValueError(f"Unknown bundle mode: {bundle_mode}")
    if target == "cli":
        return f"{CLI_NAME}-{version}"
    raise ValueError(f"Unknown target: {target}")


def get_onedir_dir_name(version: str) -> str:
    """Return the canonical versioned onedir directory name."""
    return get_executable_name(target="ui", bundle_mode="onedir", version=version)


def get_onedir_exe_name(version: str) -> str:
    """Return the executable name inside a versioned onedir bundle."""
    return f"{get_onedir_dir_name(version)}.exe"


def get_cli_exe_name(version: str) -> str:
    """Return the canonical Windows CLI executable name."""
    return f"{get_executable_name(target='cli', bundle_mode='onefile', version=version)}.exe"


def get_staged_app_dirname() -> str:
    """Return the versionless installer staging directory name."""
    return STAGED_APP_DIRNAME


def get_windows_installer_app_dirname() -> str:
    """Compatibility name for the installer staging directory contract."""
    return get_staged_app_dirname()


def get_staged_ui_exe_name() -> str:
    """Return the UI executable name inside the installer staging directory."""
    return STAGED_UI_EXE_NAME


def get_windows_installer_exe_name() -> str:
    """Compatibility name for the staged Windows UI executable."""
    return get_staged_ui_exe_name()


def get_staged_cli_exe_name() -> str:
    """Return the CLI executable name inside the installer staging directory."""
    return STAGED_CLI_EXE_NAME


def get_staged_cli_bin_dirname() -> str:
    """Return the PATH-facing CLI bin directory inside the installer staging directory."""
    return STAGED_CLI_BIN_DIRNAME


def get_windows_installer_cli_bin_dirname() -> str:
    """Compatibility name for the staged Windows CLI bin directory."""
    return get_staged_cli_bin_dirname()


def get_staged_cli_shim_name() -> str:
    """Return the PATH-facing CLI shim filename inside the installer staging directory."""
    return STAGED_CLI_SHIM_NAME


def get_windows_installer_cli_shim_name() -> str:
    """Compatibility name for the staged Windows CLI shim filename."""
    return get_staged_cli_shim_name()


def get_windows_installer_cli_exe_name() -> str:
    """Compatibility name for the staged Windows CLI executable."""
    return get_staged_cli_exe_name()


def get_release_archive_name(
    *, tag: Optional[str] = None, ref_name: Optional[str] = None, platform_suffix: str
) -> str:
    """Return the release archive filename for a tag and platform."""
    release_ref = tag if tag is not None else ref_name
    if release_ref is None:
        raise TypeError("get_release_archive_name() requires tag or ref_name")
    if platform_suffix == "windows":
        return f"{APP_NAME}-{release_ref}-windows.zip"
    if platform_suffix == "macos":
        return f"{APP_NAME}-{release_ref}-macos.zip"
    if platform_suffix == "linux":
        return f"{APP_NAME}-{release_ref}-linux.tar.gz"
    raise ValueError(f"Unknown platform suffix: {platform_suffix}")


@dataclass(frozen=True)
class WindowsArtifactLayout:
    """Paths and staged names for Windows build and installer artifacts."""

    onedir_dir: Path
    onedir_exe: Path
    cli_exe: Path
    staged_app_dirname: str = STAGED_APP_DIRNAME
    staged_ui_exe_name: str = STAGED_UI_EXE_NAME
    staged_cli_exe_name: str = STAGED_CLI_EXE_NAME
    staged_cli_bin_dirname: str = STAGED_CLI_BIN_DIRNAME
    staged_cli_shim_name: str = STAGED_CLI_SHIM_NAME


def windows_artifact_layout(*, version: str, dist_dir: Path) -> WindowsArtifactLayout:
    """Return the expected Windows build layout under ``dist_dir``."""
    onedir_dir = dist_dir / get_onedir_dir_name(version)
    return WindowsArtifactLayout(
        onedir_dir=onedir_dir,
        onedir_exe=onedir_dir / get_onedir_exe_name(version),
        cli_exe=dist_dir / get_cli_exe_name(version),
    )
