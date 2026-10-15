"""The desktop shortcut script, run for real against Windows but only ever into pytest's tmp_path."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from make_shortcut import ROOT, create_shortcut, desktop_path, main, read_shortcut  # noqa: E402

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows shortcuts")


def test_the_shortcut_runs_the_virtual_environments_windowless_python_on_the_package_from_the_repo_root(tmp_path):
    shortcut = tmp_path / "Stratagem Caller.lnk"
    create_shortcut(shortcut)
    made = read_shortcut(shortcut)
    assert Path(made["target"]) == ROOT / ".venv" / "Scripts" / "pythonw.exe"
    assert made["arguments"] == "-m stratagem_caller"
    assert Path(made["working_directory"]) == ROOT
    assert Path(made["icon"].split(",")[0]) == ROOT / "stratagem_caller" / "assets" / "stratagem_caller.ico"


def test_it_does_not_ask_for_administrator_rights(tmp_path):
    shortcut = tmp_path / "Stratagem Caller.lnk"
    create_shortcut(shortcut)
    data = shortcut.read_bytes()
    # The shell link header's flags: SLDF_RUNAS_USER (0x2000) is what "Run as administrator" sets.
    link_flags = int.from_bytes(data[0x14:0x18], "little")
    assert link_flags & 0x2000 == 0


def test_it_replaces_an_existing_shortcut(tmp_path):
    shortcut = tmp_path / "Stratagem Caller.lnk"
    create_shortcut(shortcut)
    create_shortcut(shortcut)
    assert read_shortcut(shortcut)["arguments"] == "-m stratagem_caller"


def test_it_replaces_a_broken_shortcut(tmp_path):
    shortcut = tmp_path / "Stratagem Caller.lnk"
    shortcut.write_bytes(b"not a shortcut at all")
    create_shortcut(shortcut)
    assert read_shortcut(shortcut)["arguments"] == "-m stratagem_caller"


def test_it_works_for_a_folder_with_a_quote_in_its_name(tmp_path):
    folder = tmp_path / "O'Brien's desktop"
    folder.mkdir()
    create_shortcut(folder / "Stratagem Caller.lnk")
    assert (folder / "Stratagem Caller.lnk").is_file()


def test_it_refuses_when_the_virtual_environment_has_no_windowless_python(tmp_path):
    with pytest.raises(FileNotFoundError, match="pythonw.exe"):
        create_shortcut(tmp_path / "x.lnk", root=tmp_path)
    assert not (tmp_path / "x.lnk").exists()


def test_a_dry_run_says_what_it_would_make_and_makes_nothing(tmp_path, capsys):
    target = tmp_path / "Stratagem Caller.lnk"
    main(["--path", str(target), "--dry-run"])
    said = capsys.readouterr().out
    assert str(target) in said and "pythonw.exe" in said and "-m stratagem_caller" in said
    assert not target.exists()


def test_main_makes_the_shortcut_at_the_path_it_is_given(tmp_path, capsys):
    target = tmp_path / "Stratagem Caller.lnk"
    main(["--path", str(target)])
    assert target.is_file()
    assert str(target) in capsys.readouterr().out


def test_the_desktop_folder_is_found_wherever_windows_keeps_it():
    assert desktop_path().is_dir()
