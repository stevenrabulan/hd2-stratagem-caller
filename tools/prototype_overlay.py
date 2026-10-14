"""PROTOTYPE, throw away. Not part of the tool.

Answers three questions before the Overlay is built for real:
1. Can a click-through window sit on top of Helldivers 2 (borderless, HDR)
   without taking focus or clicks, and without hurting the game?
2. Which Key Cap style looks right next to the Stratagem Menu?
3. Does the reader still read the menu with the Overlay on screen?

    .venv\\Scripts\\python.exe tools\\prototype_overlay.py

Press the Call Key in-game. While the reader sees the Stratagem Menu open, Key
Caps and the ready heading show. A digit flashes its Key Cap red. F8 cycles
Key Cap styles. F7 saves what the reader sees to fixtures/raw/. Ctrl+Alt+Q
quits. Nothing is sent to the game and no key is swallowed (digits still switch
weapon). Run it without the tool itself the first time.
"""

import ctypes
import math
import sys
import threading
import time
from ctypes import wintypes
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from stratagem_caller import winkeys  # noqa: E402

winkeys.make_dpi_aware()

import cv2  # noqa: E402
import keyboard  # noqa: E402
import mss  # noqa: E402
import numpy as np  # noqa: E402

from stratagem_caller import reader  # noqa: E402
from stratagem_caller.reader import REFERENCE_HEIGHT, read_menu, region_size  # noqa: E402

CALL_KEY = "b"
TRIGGER_KEYS = {str(n % 10): n for n in range(1, 11)}  # "1".."9" -> 1..9, "0" -> 10
RAW_DIR = ROOT / "fixtures" / "raw"

# Two small windows instead of one big one, at 3840x2160: a column for the Key
# Caps, and a strip for the heading sized to its text.
CAPS_WINDOW_LEFT, CAPS_WINDOW_RIGHT, CAPS_WINDOW_HEIGHT = 40, 102, 1500
HEADING_PAD = 30

# Key Cap geometry at 3840x2160. The cap stays left of x=98 so the reader's
# Icon-edge check (which looks at x=101..104) never sees it.
CAP_LEFT, CAP_RIGHT = 46, 96
CAP_ABOVE, CAP_BELOW = 28, 18  # from the Icon's vertical centre
BAR_TOP, BAR_BOTTOM = 23, 26
CAP_RADIUS = 8
HEADING_LEFT, HEADING_MIDDLE = 410, 91
HEADING = "STRATAGEM CALLER READY"
PULSE_PERIOD = 1.2
PULSE_LOW, PULSE_HIGH = 110, 255  # the heading window's whole opacity
FLASH_STEP, FLASH_COUNT = 0.1, 3

# Colours are BGRA, premultiplied (what UpdateLayeredWindow expects).
OFF_WHITE = (205, 228, 232, 255)  # never pure white: min channel < reader.WHITE_THRESHOLD
DARK = (30, 30, 30, 255)
YELLOW = (0, 233, 255, 255)  # #FFE900
RED = (40, 40, 215, 255)
SMOKE = (6, 6, 6, 170)

STYLES = ("game hint (light, dark glyph, bar)", "outlined (dark glass, light glyph)", "yellow (filled, dark glyph, bar)")


# --- Win32 layered window -------------------------------------------------

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
kernel32 = ctypes.windll.kernel32

LRESULT = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
WS_POPUP = 0x80000000
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOPMOST = 0x00000008
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080
HWND_TOPMOST = wintypes.HWND(-1)
SWP_NOSIZE, SWP_NOMOVE, SWP_NOACTIVATE, SWP_SHOWWINDOW = 0x1, 0x2, 0x10, 0x40
SW_HIDE = 0
ULW_ALPHA = 2
PM_REMOVE = 1


class WNDCLASSEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.UINT), ("style", wintypes.UINT), ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int), ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON), ("hCursor", wintypes.HANDLE), ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR), ("lpszClassName", wintypes.LPCWSTR), ("hIconSm", wintypes.HICON),
    ]  # fmt: skip


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG), ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG), ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD), ("biClrImportant", wintypes.DWORD),
    ]  # fmt: skip


class BLENDFUNCTION(ctypes.Structure):
    _fields_ = [("BlendOp", ctypes.c_ubyte), ("BlendFlags", ctypes.c_ubyte),
                ("SourceConstantAlpha", ctypes.c_ubyte), ("AlphaFormat", ctypes.c_ubyte)]  # fmt: skip


user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.DefWindowProcW.restype = LRESULT
user32.RegisterClassExW.argtypes = [ctypes.POINTER(WNDCLASSEXW)]
user32.CreateWindowExW.argtypes = [
    wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_int, ctypes.c_int,
    ctypes.c_int, ctypes.c_int, wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID,
]  # fmt: skip
user32.CreateWindowExW.restype = wintypes.HWND
user32.GetDC.argtypes = [wintypes.HWND]
user32.GetDC.restype = wintypes.HDC
user32.UpdateLayeredWindow.argtypes = [
    wintypes.HWND, wintypes.HDC, ctypes.POINTER(wintypes.POINT), ctypes.POINTER(wintypes.SIZE), wintypes.HDC,
    ctypes.POINTER(wintypes.POINT), wintypes.DWORD, ctypes.POINTER(BLENDFUNCTION), wintypes.DWORD,
]  # fmt: skip
user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND] + [ctypes.c_int] * 4 + [wintypes.UINT]
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.PeekMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT, wintypes.UINT]
user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
gdi32.CreateCompatibleDC.restype = wintypes.HDC
gdi32.CreateDIBSection.argtypes = [
    wintypes.HDC, ctypes.POINTER(BITMAPINFOHEADER), wintypes.UINT, ctypes.POINTER(ctypes.c_void_p),
    wintypes.HANDLE, wintypes.DWORD,
]  # fmt: skip
gdi32.CreateDIBSection.restype = wintypes.HBITMAP
gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
gdi32.SelectObject.restype = wintypes.HGDIOBJ
kernel32.GetModuleHandleW.restype = wintypes.HMODULE


CLASS_NAME = "StratagemCallerOverlayPrototype"
_window_proc = WNDPROC(lambda h, m, w, l: user32.DefWindowProcW(h, m, w, l))
_class_registered = False


class OverlayWindow:
    """A topmost, click-through, never-focused window showing a premultiplied BGRA image."""

    def __init__(self, left: int, top: int, width: int, height: int):
        global _class_registered
        instance = kernel32.GetModuleHandleW(None)
        if not _class_registered:
            cls = WNDCLASSEXW(cbSize=ctypes.sizeof(WNDCLASSEXW), lpfnWndProc=_window_proc,
                              hInstance=instance, lpszClassName=CLASS_NAME)  # fmt: skip
            user32.RegisterClassExW(ctypes.byref(cls))
            _class_registered = True
        ex = WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOPMOST | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
        self.hwnd = user32.CreateWindowExW(ex, CLASS_NAME, "Stratagem Caller Overlay", WS_POPUP,
                                           left, top, width, height, None, None, instance, None)  # fmt: skip
        self.alpha = 255
        self._pos = wintypes.POINT(left, top)
        self._size = wintypes.SIZE(width, height)
        self._screen_dc = user32.GetDC(None)
        self._mem_dc = gdi32.CreateCompatibleDC(self._screen_dc)
        header = BITMAPINFOHEADER(ctypes.sizeof(BITMAPINFOHEADER), width, -height, 1, 32, 0, 0, 0, 0, 0, 0)
        self._bits = ctypes.c_void_p()
        bitmap = gdi32.CreateDIBSection(self._mem_dc, ctypes.byref(header), 0, ctypes.byref(self._bits), None, 0)
        gdi32.SelectObject(self._mem_dc, bitmap)
        self.shown = False

    def show(self, image: np.ndarray) -> None:
        ctypes.memmove(self._bits, image.ctypes.data, image.nbytes)
        blend = BLENDFUNCTION(0, 0, self.alpha, 1)  # AC_SRC_OVER, per-pixel alpha
        user32.UpdateLayeredWindow(self.hwnd, self._screen_dc, ctypes.byref(self._pos), ctypes.byref(self._size),
                                   self._mem_dc, ctypes.byref(wintypes.POINT(0, 0)), 0, ctypes.byref(blend),
                                   ULW_ALPHA)  # fmt: skip
        if not self.shown:
            user32.SetWindowPos(self.hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW)  # fmt: skip
            self.shown = True

    def set_alpha(self, alpha: int) -> None:
        """Fade the whole window without sending its picture again."""
        if alpha == self.alpha:
            return
        self.alpha = alpha
        if self.shown:
            blend = BLENDFUNCTION(0, 0, alpha, 1)
            user32.UpdateLayeredWindow(self.hwnd, None, None, None, None, None, 0, ctypes.byref(blend), ULW_ALPHA)

    def hide(self) -> None:
        if self.shown:
            user32.ShowWindow(self.hwnd, SW_HIDE)
            self.shown = False

    def pump(self) -> None:
        msg = wintypes.MSG()
        while user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, PM_REMOVE):
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))


# --- drawing ---------------------------------------------------------------


def _rounded_rect(img, x0, y0, x1, y1, r, colour):
    cv2.rectangle(img, (x0 + r, y0), (x1 - r, y1), colour, -1, cv2.LINE_AA)
    cv2.rectangle(img, (x0, y0 + r), (x1, y1 - r), colour, -1, cv2.LINE_AA)
    for cx, cy in ((x0 + r, y0 + r), (x1 - r, y0 + r), (x0 + r, y1 - r), (x1 - r, y1 - r)):
        cv2.circle(img, (cx, cy), r, colour, -1, cv2.LINE_AA)


def _centred_text(img, text, cx, cy, scale, colour, thickness):
    (w, h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_DUPLEX, scale, thickness)
    cv2.putText(img, text, (round(cx - w / 2), round(cy + h / 2)), cv2.FONT_HERSHEY_DUPLEX, scale, colour,
                thickness, cv2.LINE_AA)  # fmt: skip


def draw_key_cap(img, slot: int, label: str, style: int, red: bool, s: float, origin_x: int = 0) -> None:
    middle = reader.ICON_TOP + reader.ICON_SIZE / 2 + (slot - 1) * reader.SLOT_PITCH
    x0, x1 = round(CAP_LEFT * s) - origin_x, round(CAP_RIGHT * s) - origin_x
    y0, y1 = round((middle - CAP_ABOVE) * s), round((middle + CAP_BELOW) * s)
    r = max(2, round(CAP_RADIUS * s))
    glyph_scale, glyph_thick = 1.1 * s, max(1, round(2.5 * s))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    if style == 1:
        edge = RED if red else OFF_WHITE
        t = max(1, round(3 * s))
        _rounded_rect(img, x0, y0, x1, y1, r, edge)
        _rounded_rect(img, x0 + t, y0 + t, x1 - t, y1 - t, max(1, r - t), SMOKE)
        _centred_text(img, label, cx, cy, glyph_scale, edge, glyph_thick)
        return
    fill = RED if red else (OFF_WHITE if style == 0 else YELLOW)
    _rounded_rect(img, x0, y0, x1, y1, r, fill)
    _centred_text(img, label, cx, cy, glyph_scale, DARK, glyph_thick)
    bar_y0, bar_y1 = round((middle + BAR_TOP) * s), round((middle + BAR_BOTTOM) * s)
    cv2.rectangle(img, (x0 + r, bar_y0), (x1 - r, bar_y1), fill, -1, cv2.LINE_AA)


def caps_window_box(s: float) -> tuple[int, int, int, int]:
    """Left, top, width, height of the Key Cap column, relative to the monitor."""
    left = round(CAPS_WINDOW_LEFT * s)
    return left, 0, round(CAPS_WINDOW_RIGHT * s) - left, round(CAPS_WINDOW_HEIGHT * s)


def red_slots(flashes: dict[int, float], now: float) -> frozenset[int]:
    """Slots whose Key Cap is in a red step of its flash right now."""
    return frozenset(
        slot for slot, start in flashes.items()
        if 0 <= now - start < 2 * FLASH_STEP * FLASH_COUNT and int((now - start) / FLASH_STEP) % 2 == 0
    )  # fmt: skip


def render_caps(slots, red: frozenset[int], style: int, s: float) -> np.ndarray:
    left, _, width, height = caps_window_box(s)
    img = np.zeros((height, width, 4), np.uint8)
    for slot in slots:
        draw_key_cap(img, slot, str(slot % 10), style, slot in red, s, origin_x=left)
    return img


def render_heading(s: float) -> tuple[np.ndarray, int, int]:
    """The heading with its glow at full strength, drawn once; the window's opacity pulses it.
    Returns the picture and its left and top, relative to the monitor."""
    scale, thick = 1.15 * s, max(1, round(2 * s))
    (w, h), _ = cv2.getTextSize(HEADING, cv2.FONT_HERSHEY_DUPLEX, scale, thick)
    pad = round(HEADING_PAD * s)
    left = round(HEADING_LEFT * s) - pad
    baseline = round(HEADING_MIDDLE * s + h / 2)
    top = max(0, baseline - h - pad)
    img = np.zeros((baseline + pad - top, w + 2 * pad, 4), np.uint8)
    origin = (pad, baseline - top)
    cv2.putText(img, HEADING, origin, cv2.FONT_HERSHEY_DUPLEX, scale, YELLOW, max(2, round(6 * s)), cv2.LINE_AA)
    img = cv2.GaussianBlur(img, (0, 0), 10 * s)
    cv2.putText(img, HEADING, origin, cv2.FONT_HERSHEY_DUPLEX, scale, YELLOW, thick, cv2.LINE_AA)
    return np.ascontiguousarray(img), left, top


def pulse_alpha(now: float) -> int:
    wave = 0.5 + 0.5 * math.sin(2 * math.pi * now / PULSE_PERIOD)
    return round(PULSE_LOW + (PULSE_HIGH - PULSE_LOW) * wave)


# --- state and threads -------------------------------------------------------


class State:
    def __init__(self):
        self.lock = threading.Lock()
        self.quit = False
        self.armed = False
        self.armed_at = 0.0
        self.last_open = 0.0
        self.menu_open = False
        self.slots: list[int] = []
        self.flashes: dict[int, float] = {}
        self.style = 2  # yellow, chosen in-game
        self.region: np.ndarray | None = None


def watch(state: State, monitor: dict) -> None:
    """Read the menu while armed, the way the tool would, and note what to draw."""
    width, height = region_size(monitor["height"])
    area = {"left": monitor["left"], "top": monitor["top"], "width": width, "height": height}
    s = monitor["height"] / REFERENCE_HEIGHT
    last_line = None
    with mss.MSS() as sct:
        while not state.quit:
            if not state.armed:
                time.sleep(0.02)
                continue
            region = np.asarray(sct.grab(area))[:, :, :3]
            reading = read_menu(region, monitor["height"])
            slots = [n for n in range(1, reader.MAX_SLOTS + 1) if reader._icon_in_place(region, n, s)]
            now = time.monotonic()
            with state.lock:
                state.region = region
                state.menu_open = reading.menu_open
                state.slots = slots if reading.menu_open else []
                if reading.menu_open:
                    state.last_open = now
                elif now - state.armed_at > 0.75 and now - max(state.last_open, state.armed_at) > 1.0:
                    state.armed = False
                if now - state.armed_at > 60:
                    state.armed = False
                armed = state.armed
            line = (
                f"menu {'open' if reading.menu_open else 'not open'}; Key Caps on {slots if reading.menu_open else []}; "
                f"callable {sorted(reading.codes)}; unreadable {sorted(reading.unreadable)}"
                + ("" if armed else "; watch ended")
            )
            if line != last_line:
                print(f"{time.strftime('%H:%M:%S')} {line}; foreground {winkeys.foreground_title()!r}")
                last_line = line
            time.sleep(0.1)


def main() -> None:
    state = State()
    with mss.MSS() as sct:
        monitor = sct.monitors[1]
    s = monitor["height"] / REFERENCE_HEIGHT
    caps_left, caps_top, caps_width, caps_height = caps_window_box(s)
    caps = OverlayWindow(monitor["left"] + caps_left, monitor["top"] + caps_top, caps_width, caps_height)
    heading_img, heading_left, heading_top = render_heading(s)
    heading = OverlayWindow(monitor["left"] + heading_left, monitor["top"] + heading_top,
                            heading_img.shape[1], heading_img.shape[0])  # fmt: skip

    def on_call(_event):
        with state.lock:
            state.armed_at = time.monotonic()
            if not state.armed:
                state.armed, state.last_open = True, 0.0
        print(f"{time.strftime('%H:%M:%S')} Call Key: watching")

    def on_trigger(slot):
        def handler(_event):
            with state.lock:
                if state.armed and state.menu_open and slot in state.slots:
                    state.flashes[slot] = time.monotonic()
                    print(f"{time.strftime('%H:%M:%S')} flash Slot {slot}")

        return handler

    def on_style(_event):
        with state.lock:
            state.style = (state.style + 1) % len(STYLES)
        print(f"style: {STYLES[state.style]}")

    def on_save(_event):
        with state.lock:
            region = state.region
        if region is None:
            print("nothing read yet; press the Call Key first")
            return
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        path = RAW_DIR / f"prototype_overlay_{datetime.now():%Y%m%d-%H%M%S}.png"
        cv2.imwrite(str(path), region)
        reading = read_menu(region, monitor["height"])
        print(f"saved {path.name}: callable {reading.codes}, unreadable {sorted(reading.unreadable)}, "
              f"open {reading.menu_open}")  # fmt: skip

    def on_quit():
        state.quit = True

    keyboard.on_press_key(CALL_KEY, on_call)
    for key, slot in TRIGGER_KEYS.items():
        keyboard.on_press_key(key, on_trigger(slot))
    keyboard.on_press_key("f8", on_style)
    keyboard.on_press_key("f7", on_save)
    keyboard.add_hotkey("ctrl+alt+q", on_quit)
    threading.Thread(target=watch, args=(state, monitor), daemon=True).start()

    print(f"PROTOTYPE overlay on a {monitor['width']}x{monitor['height']} screen.")
    print(f"[{CALL_KEY}] watch the menu   [1-0] flash   [F8] style   [F7] save what the reader sees   [Ctrl+Alt+Q] quit")
    print(f"style: {STYLES[state.style]}")
    drawn = None  # what the Key Cap window shows now; redraw only when it changes
    redraws = 0
    while not state.quit:
        caps.pump()
        with state.lock:
            visible = state.armed and state.menu_open
            slots, flashes, style = tuple(state.slots), dict(state.flashes), state.style
        now = time.monotonic()
        if visible:
            wanted = (slots, red_slots(flashes, now), style)
            if wanted != drawn:
                caps.show(render_caps(*wanted, s))
                drawn = wanted
                redraws += 1
            heading.set_alpha(pulse_alpha(now))
            if not heading.shown:
                heading.show(heading_img)
        elif caps.shown:
            caps.hide()
            heading.hide()
            print(f"{time.strftime('%H:%M:%S')} hidden; Key Caps drawn {redraws} times while shown")
            drawn, redraws = None, 0
        time.sleep(1 / 30)


if __name__ == "__main__":
    main()
