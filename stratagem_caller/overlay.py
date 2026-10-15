"""The Overlay: Key Caps and a pulsing ready heading drawn over the game while the tool
is ready to act on Trigger Keys, and the Key Cap for the Terminal Key while a Code is read.

This module decides nothing about when they show (the router does: the heading shows
exactly when there are Slot Key Caps) and touches no screen: it polls what to show, draws it
when that changes, and tells a window to show or hide the picture. There are three
windows: one for the Slot Key Caps, one for the heading and one for the Terminal Key's
Key Cap. They are made by a factory the app passes in, so tests use a fake and only Windows
ever creates a real one (see layered_window.py).
"""

import threading
import time
from collections.abc import Callable
from contextlib import ExitStack
from typing import Protocol

import numpy as np

from .heading import heading_box, pulse_opacity, render_heading
from .keycaps import TerminalKeyCap, column_box, render_key_caps, render_terminal_key_cap, terminal_key_cap_box

# Seconds between looks at what the Overlay should show. Drawing happens only on change.
TICK = 1 / 30


class Window(Protocol):
    def show(self, image: np.ndarray) -> None: ...
    def hide(self) -> None: ...
    def set_opacity(self, opacity: int) -> None: ...
    def pump(self) -> None: ...
    def close(self) -> None: ...


class Overlay:
    def __init__(
        self,
        key_caps: Callable[[], dict[int, str]],
        red_key_caps: Callable[[], frozenset[int]],
        screen_height: int,
        make_window: Callable[[tuple[int, int, int, int]], Window],
        clock: Callable[[], float] = time.monotonic,
        terminal_key_cap: Callable[[], TerminalKeyCap | None] = lambda: None,
    ):
        """`key_caps` says which Key Caps to show now (Slot -> key name; empty for none).
        The heading shows whenever there are Key Caps and not otherwise.
        `red_key_caps` says which Slots are in a red step of a flash; one with no Key Cap
        shown is ignored. `make_window` takes a window's box (left, top, width, height,
        relative to the monitor) and returns a window; it is called for the Key Cap
        column, then for the heading, then for the Terminal Key's Key Cap. `clock` times the
        heading's pulse. `terminal_key_cap` says what that Key Cap shows now (None for none)."""
        self._key_caps = key_caps
        self._red_key_caps = red_key_caps
        self._screen_height = screen_height
        self._make_window = make_window
        self._clock = clock
        self._terminal_key_cap = terminal_key_cap
        self._key_cap_window: Window | None = None
        self._heading_window: Window | None = None
        self._terminal_window: Window | None = None
        self._heading_image = render_heading(screen_height)  # drawn once, shown as often as needed
        # What the window shows now: Key Caps and which are red; empty when hidden.
        self._drawn: tuple[dict[int, str], frozenset[int]] = ({}, frozenset())
        self._terminal_drawn: TerminalKeyCap | None = None  # what the Terminal Key Cap's window shows now
        self._heading_since: float | None = None  # when the heading appeared; None when hidden
        self._opacity: int | None = None  # what the heading's window is set to

    def open(self) -> None:
        """Create the windows. Call on the thread that will tick them."""
        self._key_cap_window = self._make_window(column_box(self._screen_height))
        self._heading_window = self._make_window(heading_box(self._screen_height))
        self._terminal_window = self._make_window(terminal_key_cap_box(self._screen_height))

    def tick(self) -> None:
        """Bring the windows in line with what should show, drawing only on a change."""
        names = dict(self._key_caps())
        self._tick_key_caps(names)
        self._tick_heading(showing=bool(names))
        self._tick_terminal_key_cap(self._terminal_key_cap())

    def _tick_key_caps(self, names: dict[int, str]) -> None:
        wanted = (names, frozenset(self._red_key_caps()) & names.keys())
        if wanted == self._drawn:
            return
        if names:
            self._key_cap_window.show(render_key_caps(names, self._screen_height, red=wanted[1]))
        else:
            self._key_cap_window.hide()
        self._drawn = wanted

    def _tick_terminal_key_cap(self, wanted: TerminalKeyCap | None) -> None:
        if wanted == self._terminal_drawn:
            return
        if wanted is None:
            self._terminal_window.hide()
        else:
            self._terminal_window.show(render_terminal_key_cap(wanted, self._screen_height))
        self._terminal_drawn = wanted

    def _tick_heading(self, showing: bool) -> None:
        """Send the heading's picture once per showing; after that only fade its window."""
        if not showing:
            if self._heading_since is not None:
                self._heading_window.hide()
                self._heading_since = self._opacity = None
            return
        now = self._clock()
        appearing = self._heading_since is None
        if appearing:
            self._heading_since = now
        opacity = pulse_opacity(now - self._heading_since)
        if opacity != self._opacity:
            self._heading_window.set_opacity(opacity)
            self._opacity = opacity
        if appearing:
            self._heading_window.show(self._heading_image)

    def close(self) -> None:
        windows = (self._key_cap_window, self._heading_window, self._terminal_window)
        self._key_cap_window = self._heading_window = self._terminal_window = None
        with ExitStack() as stack:  # every window is released even if one will not close
            for window in reversed(windows):  # (closed in the order they were made)
                if window is not None:
                    stack.callback(window.close)

    def run(self, stop: threading.Event, interval: float = TICK) -> None:
        """Own the windows until `stop` is set: create them here, keep them alive, close them."""
        try:
            self.open()
            while not stop.is_set():
                self._key_cap_window.pump()  # messages are per thread, so one pump serves both windows
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
    red_key_caps: Callable[[], frozenset[int]],
    terminal_key_cap: Callable[[], TerminalKeyCap | None] = lambda: None,
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

    overlay = Overlay(key_caps, red_key_caps, monitor["height"], make_window, terminal_key_cap=terminal_key_cap)

    def run() -> None:
        try:
            overlay.run(stop)
        except Exception as error:  # Losing the Overlay must not lose the keyboard.
            on_failure(error)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread
