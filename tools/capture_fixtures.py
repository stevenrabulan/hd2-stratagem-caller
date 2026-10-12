"""Collect true-pixel screenshots of the Stratagem Menu to use as test fixtures.

Run it, play a mission, and every press of the Call Key saves a short burst of
screenshots to fixtures/raw/. Nothing is sent to the game.

    .venv\\Scripts\\python.exe tools\\capture_fixtures.py
    .venv\\Scripts\\python.exe tools\\capture_fixtures.py --selftest
"""

import ctypes
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

# Must run before anything asks Windows for screen sizes, or a display scaled to
# 150% reports 2560x1440 instead of 3840x2160 and captures come out wrong.
ctypes.windll.shcore.SetProcessDpiAwareness(2)

import keyboard  # noqa: E402
import mss  # noqa: E402
import mss.tools  # noqa: E402

CALL_KEY = "b"
MANUAL_KEY = "f9"
QUIT_KEY = "ctrl+alt+q"
# Several shots per press, so the fixtures show how long the menu takes to open.
DELAYS_MS = (100, 250, 500)

OUT_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "raw"
LOG_PATH = OUT_DIR / "captures.log"

_press_count = 0
_call_key_down = False
_lock = threading.Lock()


def foreground_title() -> str:
    user32 = ctypes.windll.user32
    hwnd = user32.GetForegroundWindow()
    buf = ctypes.create_unicode_buffer(256)
    user32.GetWindowTextW(hwnd, buf, 256)
    return buf.value


def capture_burst(label: str, delays_ms: tuple[int, ...]) -> None:
    title = foreground_title()
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    started = time.perf_counter()
    shots = []
    # mss handles are per-thread, so each burst opens its own.
    with mss.MSS() as sct:
        monitor = sct.monitors[1]
        for delay in delays_ms:
            remaining = delay / 1000 - (time.perf_counter() - started)
            if remaining > 0:
                time.sleep(remaining)
            shots.append((delay, sct.grab(monitor)))
    # Encode after the whole burst: a 4K PNG takes long enough to skew the timings.
    for delay, shot in shots:
        path = OUT_DIR / f"{stamp}_{label}_{delay:03d}ms.png"
        mss.tools.to_png(shot.rgb, shot.size, output=str(path))
        line = f"{path.name}\t{shot.size[0]}x{shot.size[1]}\tforeground={title!r}"
        with _lock, LOG_PATH.open("a", encoding="utf-8") as log:
            log.write(line + "\n")
        print("saved", line)


def on_call_key_down(_event) -> None:
    global _press_count, _call_key_down
    if _call_key_down:  # held key auto-repeating
        return
    _call_key_down = True
    _press_count += 1
    label = f"press{_press_count:03d}"
    threading.Thread(target=capture_burst, args=(label, DELAYS_MS), daemon=True).start()


def on_call_key_up(_event) -> None:
    global _call_key_down
    _call_key_down = False


def on_manual_key(_event) -> None:
    label = f"manual{datetime.now().strftime('%f')[:3]}"
    threading.Thread(target=capture_burst, args=(label, (0,)), daemon=True).start()


def selftest() -> None:
    with mss.MSS() as sct:
        shot = sct.grab(sct.monitors[1])
    print(f"capture ok: {shot.size[0]}x{shot.size[1]}")
    print(f"foreground window: {foreground_title()!r}")


def main() -> None:
    if "--selftest" in sys.argv:
        selftest()
        return
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with mss.MSS() as sct:
        monitor = sct.monitors[1]
    print(f"primary monitor: {monitor['width']}x{monitor['height']}")
    print(f"saving to {OUT_DIR}")
    print(f"[{CALL_KEY}] burst at {DELAYS_MS} ms   [{MANUAL_KEY}] single shot   [{QUIT_KEY}] quit")
    keyboard.on_press_key(CALL_KEY, on_call_key_down)
    keyboard.on_release_key(CALL_KEY, on_call_key_up)
    keyboard.on_press_key(MANUAL_KEY, on_manual_key)
    keyboard.wait(QUIT_KEY)


if __name__ == "__main__":
    main()
