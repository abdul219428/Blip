#!/usr/bin/env python3
"""Build CogStash UI and CLI artifacts with PyInstaller."""

from __future__ import annotations

import argparse
import os
import platform
import subprocess
import sys
from pathlib import Path

from _artifacts import get_executable_name

ROOT = Path(__file__).resolve().parent.parent
ICON_SRC = ROOT / "assets" / "cogstash_icon.png"
BUILD_DIR = ROOT / "build"
DIST_DIR = ROOT / "dist"
UI_ENTRY = ROOT / "src" / "cogstash" / "ui" / "__main__.py"
CLI_ENTRY = ROOT / "src" / "cogstash" / "cli" / "__main__.py"

UI_HIDDEN_IMPORTS = [
    "pynput.keyboard._win32",
    "pynput.keyboard._darwin",
    "pynput.keyboard._xorg",
    "pynput.mouse._win32",
    "pynput.mouse._darwin",
    "pynput.mouse._xorg",
    "pystray._win32",
    "pystray._darwin",
    "pystray._xorg",
    "pystray._appindicator",
    "pystray._gtk",
]
CLI_HIDDEN_IMPORTS: list[str] = []

TARGET_CHOICES = ("ui", "cli", "both")


def get_entrypoint(target: str) -> Path:
    """Return the PyInstaller entrypoint for the given target."""
    if target == "ui":
        return UI_ENTRY
    if target == "cli":
        return CLI_ENTRY
    raise ValueError(f"Unknown target: {target}")


def get_hidden_imports(target: str) -> list[str]:
    """Return hidden imports for the given target."""
    if target == "ui":
        return UI_HIDDEN_IMPORTS
    if target == "cli":
        return CLI_HIDDEN_IMPORTS
    raise ValueError(f"Unknown target: {target}")


def get_build_plan(target: str) -> list[tuple[str, str]]:
    """Return the list of target/bundle combinations to build."""
    if target == "ui":
        return [("ui", "onefile"), ("ui", "onedir")]
    if target == "cli":
        return [("cli", "onefile")]
    if target == "both":
        return [("ui", "onefile"), ("ui", "onedir"), ("cli", "onefile")]
    raise ValueError(f"Unknown target: {target}")


def get_version() -> str:
    """Get version from setuptools-scm metadata."""
    from importlib.metadata import version
    return version("cogstash")


def convert_icon() -> str | None:
    """Convert PNG icon to platform-appropriate format. Returns path or None."""
    if not ICON_SRC.exists():
        print(f"Warning: icon not found at {ICON_SRC}", file=sys.stderr)
        return None

    from PIL import Image

    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    img = Image.open(ICON_SRC)

    if sys.platform == "win32":
        ico_path = BUILD_DIR / "cogstash.ico"
        sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        img.save(str(ico_path), format="ICO", sizes=sizes)
        return str(ico_path)
    elif sys.platform == "darwin":
        icns_path = BUILD_DIR / "cogstash.icns"
        img.save(str(icns_path), format="ICNS")
        return str(icns_path)
    else:
        return str(ICON_SRC)


def run_pyinstaller(
    *,
    target: str,
    bundle_mode: str,
    debug: bool,
    icon_path: str | None,
    version: str,
) -> None:
    """Run PyInstaller with the given configuration."""
    entry = get_entrypoint(target)
    hidden_imports = get_hidden_imports(target)
    name = get_executable_name(target=target, bundle_mode=bundle_mode, version=version)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        str(entry),
        f"--{bundle_mode}",
        "--name", name,
        "--copy-metadata", "cogstash",
        "--distpath", str(DIST_DIR),
        "--workpath", str(BUILD_DIR / f"{target}-{bundle_mode}"),
        "--specpath", str(BUILD_DIR),
        "--clean",
    ]

    if target == "ui":
        cmd.extend(["--add-data", f"{ICON_SRC}{os.pathsep}assets"])

    if target == "ui" and not debug:
        cmd.append("--noconsole")

    if icon_path:
        cmd.extend(["--icon", icon_path])

    for imp in hidden_imports:
        cmd.extend(["--hidden-import", imp])

    print(f"\n{'='*60}")
    print(f"Building {target} {bundle_mode}...")
    print(f"{'='*60}")
    subprocess.run(cmd, check=True)
    print(f"[OK] {target} {bundle_mode} build complete -> dist/")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build CogStash executables")
    parser.add_argument("--target", choices=TARGET_CHOICES, default="both", help="Which artifact target to build")
    parser.add_argument("--debug", action="store_true", help="Enable console window")
    args = parser.parse_args()

    version = get_version()
    print(f"CogStash version: {version}")
    print(f"Platform: {platform.system()} ({sys.platform})")
    print(f"Target: {args.target}")

    icon_path = convert_icon()

    for target, bundle_mode in get_build_plan(args.target):
        run_pyinstaller(
            target=target,
            bundle_mode=bundle_mode,
            debug=args.debug,
            icon_path=icon_path,
            version=version,
        )

    print("\nAll builds complete!")


if __name__ == "__main__":
    main()
