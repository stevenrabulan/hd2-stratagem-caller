"""Windows glue: synthetic key presses, the focused window, and DPI awareness."""

import ctypes
from ctypes import wintypes
from dataclasses import dataclass

import keyboard

user32 = ctypes.windll.user32

INPUT_KEYBOARD = 1
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008

# Keys that share a scan code with a numpad key and are told apart by the extended flag.
EXTENDED_KEYS = {
    "up", "down", "left", "right", "page up", "page down",
    "home", "end", "insert", "delete", "right ctrl", "right alt",
}  # fmt: skip

ULONG_PTR = ctypes.c_size_t


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class _MOUSEINPUT(ctypes.Structure):
    # Never sent; present so the union has the size Windows expects.
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("ki", _KEYBDINPUT), ("mi", _MOUSEINPUT)]


class _INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]


@dataclass(frozen=True)
class Key:
    name: str
    scan_code: int
    extended: bool

    @classmethod
    def named(cls, name: str) -> "Key":
        name = name.lower()
        return cls(name, keyboard.key_to_scan_codes(name)[0], name in EXTENDED_KEYS)

    def matches(self, event: keyboard.KeyboardEvent) -> bool:
        return event.scan_code == self.scan_code and not event.is_keypad


def send(key: Key, down: bool) -> None:
    # Scan codes, not virtual keys: games read the hardware-level code.
    flags = KEYEVENTF_SCANCODE
    if key.extended:
        flags |= KEYEVENTF_EXTENDEDKEY
    if not down:
        flags |= KEYEVENTF_KEYUP
    event = _INPUT(INPUT_KEYBOARD, _INPUTUNION(ki=_KEYBDINPUT(0, key.scan_code, flags, 0, 0)))
    user32.SendInput(1, ctypes.byref(event), ctypes.sizeof(_INPUT))


def foreground_title() -> str:
    hwnd = user32.GetForegroundWindow()
    buf = ctypes.create_unicode_buffer(256)
    user32.GetWindowTextW(hwnd, buf, 256)
    return buf.value


def make_dpi_aware() -> None:
    # Without this a display scaled to 150% reports 2560x1440 instead of
    # 3840x2160 and every screen position is off.
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
