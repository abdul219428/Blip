from __future__ import annotations

import subprocess
import sys


def test_cogstash_cli_imports_without_gui_dependencies(tmp_path):
    script = tmp_path / "import_cli.py"
    script.write_text(
        "import builtins\n"
        "blocked = {'tkinter', 'pystray', 'PIL', 'Pillow'}\n"
        "orig = builtins.__import__\n"
        "def guarded(name, *args, **kwargs):\n"
        "    if name.split('.')[0] in blocked:\n"
        "        raise AssertionError(f'unexpected GUI import: {name}')\n"
        "    return orig(name, *args, **kwargs)\n"
        "builtins.__import__ = guarded\n"
        "import cogstash.cli\n",
        encoding="utf-8",
    )
    subprocess.run([sys.executable, str(script)], check=True)
