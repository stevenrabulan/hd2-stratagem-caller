"""The Overlay: Key Caps drawn over the game while the tool is ready to act on Trigger Keys.

This module decides nothing about when Key Caps show (the router does) and touches no
screen: it polls what to show, draws it when that changes, and tells a window to show
or hide the picture. The window is made by a factory the app passes in, so tests use a
fake and only Windows ever creates a real one (see layered_window.py).
"""

import threading
from collections.abc import Callable
from typing import Protocol

import numpy as np

from .keycaps import column_box, render_key_caps

# Seconds between looks at what the Overlay should show. Drawing happens only on change.
TICK = 1 / 30


class Window(Protocol):
    def show(self, image: np.ndarray) -> None: ...
    def hide(self) -> None: ...
    def pump(self) -> None: ...
    def close(self) -> None: ...


class Overlay:
    def __init__(
        self,
        key_caps: Callable[[], dict[int, str]],
        screen_height: int,
        make_window: Callable[[tuple[int, int, int, int]], Window],
    ):
        """`key_caps` says which Key Caps to show now (Slot -> key name; empty for none).
        `make_window` takes the Key Cap column's box (left, top, width, height, relative
        to the monitor) and returns a window."""
        self._key_caps = key_caps
        self._screen_height = screen_height
        self._make_window = make_window
        self._window: Window | None = None
        self._drawn: dict[int, str] = {}  # what the window shows now; empty when hidden

    def open(self) -> None:
        """Create the window. Call on the thread that will tick it."""
        self._window = self._make_window(column_box(self._screen_height))

    def tick(self) -> None:
        """Bring the window in line with what should show, drawing only on a change."""
        wanted = self._key_caps()
        if wanted == self._drawn:
            return
        if wanted:
            self._window.show(render_key_caps(wanted, self._screen_height))
        else:
            self._window.hide()
        self._drawn = dict(wanted)

    def close(self) -> None:
        if self._window is not None:
            self._window.close()
            self._window = None

    def run(self, stop: threading.Event, interval: float = TICK) -> None:
        """Own the window until `stop` is set: create it here, keep it alive, close it."""
        self.open()
        try:
            while not stop.is_set():
                self._window.pump()
                self.tick()
                stop.wait(interval)
        finally:
            self.close()


def _layered_window() -> type:
    """The real window class. Imported only when an Overlay is wanted, and only on Windows."""
    from .layered_window import LayeredWindow

    return LayeredWindow


def start_overlay(
    *,
    enabled: bool,
    key_caps: Callable[[], dict[int, str]],
    monitor: dict,
    stop: threading.Event,
    on_failure: Callable[[Exception], None],
    window_class: Callable[[], type] = _layered_window,
) -> threading.Thread | None:
    """Run an Overlay on its own thread over `monitor` (an mss monitor: left, top, height)
    until `stop` is set. With `enabled` false, nothing is created and None comes back.
    If the Overlay fails, `on_failure` hears of it and the thread ends; the caller's
    other work is not touched."""
    if not enabled:
        return None

    def make_window(box: tuple[int, int, int, int]) -> Window:
        left, top, width, height = box
        return window_class()(monitor["left"] + left, monitor["top"] + top, width, height)

    overlay = Overlay(key_caps, monitor["height"], make_window)

    def run() -> None:
        try:
            overlay.run(stop)
        except Exception as error:  # Losing the Overlay must not lose the keyboard.
            on_failure(error)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread
