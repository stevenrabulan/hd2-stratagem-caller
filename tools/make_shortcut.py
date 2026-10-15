r"""Create (or replace) the Stratagem Caller shortcut on the desktop.

    .venv\Scripts\python.exe tools\make_shortcut.py

The shortcut runs this repo's virtual environment's windowless Python (pythonw.exe) on the
package, with the repo root as its working folder and the Key Cap icon, so double-clicking it
starts the current code with no terminal window. It does not ask for administrator rights. Run
this again after moving the repo or rebuilding the virtual environment; an existing shortcut
(including a broken one) is replaced.

    --path FILE.lnk   make the shortcut there instead of on the desktop
    --dry-run         say what would be made, and make nothing
"""

import argparse
import ctypes
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAME = "Stratagem Caller.lnk"
ARGUMENTS = "-m stratagem_caller"
CSIDL_DESKTOPDIRECTORY = 0x10

# The values come in through the environment, so no path needs quoting inside the script.
_CREATE = r"""
$link = (New-Object -ComObject WScript.Shell).CreateShortcut($env:SHORTCUT_PATH)
$link.TargetPath = $env:SHORTCUT_TARGET
$link.Arguments = $env:SHORTCUT_ARGUMENTS
$link.WorkingDirectory = $env:SHORTCUT_WORKDIR
$link.IconLocation = $env:SHORTCUT_ICON
$link.Description = 'Stratagem Caller'
$link.Save()
"""
_READ = r"""
$link = (New-Object -ComObject WScript.Shell).CreateShortcut($env:SHORTCUT_PATH)
@{ target = $link.TargetPath; arguments = $link.Arguments; working_directory = $link.WorkingDirectory; icon = $link.IconLocation } | ConvertTo-Json
"""


def desktop_path() -> Path:
    """The current user's desktop folder, wherever Windows keeps it (it may be redirected)."""
    buffer = ctypes.create_unicode_buffer(260)
    result = ctypes.windll.shell32.SHGetFolderPathW(None, CSIDL_DESKTOPDIRECTORY, None, 0, buffer)
    if result != 0:
        raise OSError(f"Windows could not say where the desktop is (SHGetFolderPathW returned {result})")
    return Path(buffer.value)


def _powershell(script: str, **environment: str) -> str:
    done = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
        env={**os.environ, **environment},
        capture_output=True,
        text=True,
        timeout=60,
    )
    if done.returncode != 0:
        raise RuntimeError(f"PowerShell failed ({done.returncode}): {done.stderr.strip() or done.stdout.strip()}")
    return done.stdout


def shortcut_fields(root: Path = ROOT) -> dict[str, str]:
    """What the shortcut runs. Raises if the virtual environment has no windowless Python."""
    pythonw = root / ".venv" / "Scripts" / "pythonw.exe"
    if not pythonw.is_file():
        raise FileNotFoundError(f"{pythonw} does not exist; set up the virtual environment first (see the README's Setup)")
    icon = root / "stratagem_caller" / "assets" / "stratagem_caller.ico"
    if not icon.is_file():
        raise FileNotFoundError(f"{icon} does not exist; run tools/make_icon.py")
    return {"target": str(pythonw), "arguments": ARGUMENTS, "working_directory": str(root), "icon": f"{icon},0"}


def create_shortcut(path: Path, root: Path = ROOT) -> None:
    """Make the shortcut at `path`, replacing whatever file is there."""
    fields = shortcut_fields(root)
    if path.is_dir():
        raise IsADirectoryError(f"{path} is a folder, not a shortcut file")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink(missing_ok=True)  # a broken shortcut can't be edited in place
    _powershell(
        _CREATE,
        SHORTCUT_PATH=str(path),
        SHORTCUT_TARGET=fields["target"],
        SHORTCUT_ARGUMENTS=fields["arguments"],
        SHORTCUT_WORKDIR=fields["working_directory"],
        SHORTCUT_ICON=fields["icon"],
    )
    assert path.is_file(), f"PowerShell reported success but {path} was not made"


def read_shortcut(path: Path) -> dict[str, str]:
    """What an existing shortcut runs: target, arguments, working_directory, icon."""
    return json.loads(_powershell(_READ, SHORTCUT_PATH=str(path)))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Create or replace the Stratagem Caller shortcut on the desktop.")
    parser.add_argument("--path", type=Path, help="make the shortcut here instead of on the desktop")
    parser.add_argument("--dry-run", action="store_true", help="say what would be made, and make nothing")
    args = parser.parse_args(argv)
    path = args.path or desktop_path() / NAME
    fields = shortcut_fields()
    if args.dry_run:
        print(f"Would make {path}")
    else:
        create_shortcut(path)
        print(f"Made {path}")
    print(f"  runs      {fields['target']} {fields['arguments']}")
    print(f"  start in  {fields['working_directory']}")
    print(f"  icon      {fields['icon']}")
    print("  no administrator rights (tick 'Run as administrator' on it if the game ignores the tool's keys)")


if __name__ == "__main__":
    main()
