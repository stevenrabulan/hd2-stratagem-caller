from pathlib import Path

import pytest

from stratagem_caller.settings import SettingsError, load, resolve_code

ROOT = Path(__file__).resolve().parent.parent
CODE_BOOK = {"Reinforce": "UDRLU", "Orbital Laser": "RDURD"}


def test_shipped_settings_load():
    settings = load(ROOT / "settings.toml", ROOT / "codebook.toml")
    assert settings.call_key == "b"
    assert settings.direction_keys == {"U": "up", "D": "down", "L": "left", "R": "right"}
    assert settings.trigger_keys["1"] == 1
    assert settings.trigger_keys["0"] == 10
    assert settings.direct_keys["page down"] == "UDRLU"
    assert settings.keystroke_ms == (31, 62)


def test_direct_key_accepts_a_code_book_name_in_any_case():
    assert resolve_code("orbital laser", CODE_BOOK) == "RDURD"


def test_direct_key_accepts_a_written_out_code():
    assert resolve_code("UUDDLR", CODE_BOOK) == "UUDDLR"


def test_unknown_stratagem_name_is_an_error():
    with pytest.raises(SettingsError, match="Orbital Lazer"):
        resolve_code("Orbital Lazer", CODE_BOOK)


def test_loaded_settings_have_no_arming_window_length():
    settings = load(ROOT / "settings.toml", ROOT / "codebook.toml")
    assert not hasattr(settings, "arming_window_ms")
    assert "arming_window_ms" not in (ROOT / "settings.toml").read_text(encoding="utf-8")


def test_settings_file_with_the_old_setting_still_loads(tmp_path):
    old = (ROOT / "settings.toml").read_text(encoding="utf-8")
    old = old.replace("call_key =", "arming_window_ms = 1000\ncall_key =", 1)
    path = tmp_path / "settings.toml"
    path.write_text(old, encoding="utf-8")
    assert load(path, ROOT / "codebook.toml").call_key == "b"


def test_overlay_is_enabled_by_default_in_the_shipped_settings():
    settings = load(ROOT / "settings.toml", ROOT / "codebook.toml")
    assert settings.overlay_enabled is True
    assert "[overlay]" in (ROOT / "settings.toml").read_text(encoding="utf-8")


def _with_overlay_section(tmp_path, section):
    """The shipped settings with their [overlay] section (the last one) replaced."""
    text = (ROOT / "settings.toml").read_text(encoding="utf-8")
    path = tmp_path / "settings.toml"
    path.write_text(text[: text.index("[overlay]")] + section, encoding="utf-8")
    return load(path, ROOT / "codebook.toml")


def test_overlay_can_be_turned_off(tmp_path):
    assert _with_overlay_section(tmp_path, "[overlay]\nenabled = false\n").overlay_enabled is False


def test_settings_file_without_an_overlay_section_still_loads_with_the_overlay_on(tmp_path):
    assert _with_overlay_section(tmp_path, "").overlay_enabled is True


def test_overlay_enabled_must_be_true_or_false(tmp_path):
    with pytest.raises(SettingsError, match="enabled"):
        _with_overlay_section(tmp_path, '[overlay]\nenabled = "yes"\n')


def test_shipped_settings_name_the_use_key_and_the_terminal_key():
    settings = load(ROOT / "settings.toml", ROOT / "codebook.toml")
    assert (settings.use_key, settings.terminal_key) == ("e", "1")
    text = (ROOT / "settings.toml").read_text(encoding="utf-8")
    assert 'use_key = "e"' in text and 'terminal_key = "1"' in text


def _with_line_after_call_key(tmp_path, line=""):
    """The shipped settings with their use_key and terminal_key lines dropped and `line` put in their place."""
    text = (ROOT / "settings.toml").read_text(encoding="utf-8")
    kept = [l for l in text.splitlines() if not l.startswith(("use_key", "terminal_key"))]
    path = tmp_path / "settings.toml"
    path.write_text("\n".join(kept).replace('call_key = "b"', 'call_key = "b"\n' + line, 1), encoding="utf-8")
    return path


def test_use_key_and_terminal_key_can_be_changed(tmp_path):
    path = _with_line_after_call_key(tmp_path, 'use_key = "f"\nterminal_key = "enter"')
    settings = load(path, ROOT / "codebook.toml")
    assert (settings.use_key, settings.terminal_key) == ("f", "enter")


def test_settings_file_without_them_loads_with_e_and_1(tmp_path):
    settings = load(_with_line_after_call_key(tmp_path), ROOT / "codebook.toml")
    assert (settings.use_key, settings.terminal_key) == ("e", "1")


@pytest.mark.parametrize("line", ["use_key = 5", 'use_key = ""', "terminal_key = true"])
def test_use_key_and_terminal_key_must_be_key_names(tmp_path, line):
    with pytest.raises(SettingsError, match=line.split(" ")[0]):
        load(_with_line_after_call_key(tmp_path, line), ROOT / "codebook.toml")


def test_use_key_and_terminal_key_must_differ(tmp_path):
    path = _with_line_after_call_key(tmp_path, 'use_key = "1"')
    with pytest.raises(SettingsError, match="use_key and terminal_key"):
        load(path, ROOT / "codebook.toml")
