#!/usr/bin/env python3
"""Build CogStash with PyInstaller — onefile and/or onedir."""

from __future__ import annotations

import argparse
import os
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ICON_SRC = ROOT / "assets" / "cogstash_icon.png"
BUILD_DIR = ROOT / "build"
DIST_DIR = ROOT / "dist"
ENTRY = ROOT / "src" / "cogstash" / "__main__.py"

HIDDEN_IMPORTS = [
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


def run_pyinstaller(*, onefile: bool, debug: bool, icon_path: str | None, version: str) -> None:
    """Run PyInstaller with the given configuration."""
    mode = "onefile" if onefile else "onedir"
    name = f"CogStash-{version}" if onefile else f"CogStash-{version}-onedir"

    cmd = [
        sys.executable, "-m", "PyInstaller",
        str(ENTRY),
        f"--{'onefile' if onefile else 'onedir'}",
        "--name", name,
        "--copy-metadata", "cogstash",
        "--add-data", f"{ICON_SRC}{os.pathsep}assets",
        "--distpath", str(DIST_DIR),
        "--workpath", str(BUILD_DIR / mode),
        "--specpath", str(BUILD_DIR),
        "--clean",
    ]

    if not debug:
        cmd.append("--noconsole")

    if icon_path:
        cmd.extend(["--icon", icon_path])

    for imp in HIDDEN_IMPORTS:
        cmd.extend(["--hidden-import", imp])

    print(f"\n{'='*60}")
    print(f"Building {mode}...")
    print(f"{'='*60}")
    subprocess.run(cmd, check=True)
    print(f"[OK] {mode} build complete -> dist/")


def main():
    parser = argparse.ArgumentParser(description="Build CogStash executables")
    parser.add_argument("--onefile", action="store_true", help="Build only onefile")
    parser.add_argument("--onedir", action="store_true", help="Build only onedir")
    parser.add_argument("--debug", action="store_true", help="Enable console window")
    args = parser.parse_args()

    # Default: build both
    build_onefile = args.onefile or (not args.onefile and not args.onedir)
    build_onedir = args.onedir or (not args.onefile and not args.onedir)

    version = get_version()
    print(f"CogStash version: {version}")
    print(f"Platform: {platform.system()} ({sys.platform})")

    icon_path = convert_icon()

    if build_onefile:
        run_pyinstaller(onefile=True, debug=args.debug, icon_path=icon_path, version=version)

    if build_onedir:
        run_pyinstaller(onefile=False, debug=args.debug, icon_path=icon_path, version=version)

    print("\nAll builds complete!")


if __name__ == "__main__":
    main()
