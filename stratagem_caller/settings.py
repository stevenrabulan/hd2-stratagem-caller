"""Load settings.toml and the Code Book."""

import tomllib
from dataclasses import dataclass
from pathlib import Path


class SettingsError(Exception):
    pass


@dataclass(frozen=True)
class Settings:
    call_key: str
    direction_keys: dict[str, str]  # "U"/"D"/"L"/"R" -> key name
    trigger_keys: dict[str, int]  # key name -> Slot
    direct_keys: dict[str, str]  # key name -> Code
    window_title: str
    pause_key: str
    mark_key: str
    keystroke_ms: tuple[int, int]
    direct_key_pause_ms: tuple[int, int]


def load_code_book(path: Path) -> dict[str, str]:
    with path.open("rb") as f:
        sections = tomllib.load(f)
    return {name: code for section in sections.values() for name, code in section.items()}


def resolve_code(value: str, code_book: dict[str, str]) -> str:
    """A Direct Key's value is either a Code ("UDRLU") or a Code Book name."""
    if value and set(value) <= set("UDLR"):
        return value
    by_lower = {name.lower(): code for name, code in code_book.items()}
    try:
        return by_lower[value.lower()]
    except KeyError:
        raise SettingsError(
            f"Direct Key refers to {value!r}, which is neither a Code made of "
            "U, D, L, R nor a name in the Code Book"
        ) from None


def load(settings_path: Path, code_book_path: Path) -> Settings:
    with settings_path.open("rb") as f:
        raw = tomllib.load(f)
    code_book = load_code_book(code_book_path)
    directions = raw["direction_keys"]
    if set(directions) != set("UDLR"):
        raise SettingsError("[direction_keys] needs exactly U, D, L and R")
    return Settings(
        call_key=raw["call_key"],
        direction_keys=dict(directions),
        trigger_keys={key: int(slot) for key, slot in raw["trigger_keys"].items()},
        direct_keys={
            key: resolve_code(value, code_book)
            for key, value in raw.get("direct_keys", {}).items()
        },
        window_title=raw["window_title"],
        pause_key=raw["pause_key"],
        mark_key=raw["mark_key"],
        keystroke_ms=tuple(raw["keystroke_ms"]),
        direct_key_pause_ms=tuple(raw["direct_key_pause_ms"]),
    )
