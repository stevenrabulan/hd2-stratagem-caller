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
