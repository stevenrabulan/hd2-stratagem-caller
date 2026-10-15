import threading

import numpy as np

from stratagem_caller.keycaps import column_box, render_key_caps
from stratagem_caller.overlay import Overlay, start_overlay


class FakeWindow:
    """Records what the Overlay asks of its window."""

    def __init__(self, box):
        self.box = box
        self.events = []
        self.pumped = 0

    def show(self, image):
        self.events.append(("show", image))

    def hide(self):
        self.events.append(("hide", None))

    def pump(self):
        self.pumped += 1

    def close(self):
        self.events.append(("close", None))


class Screen:
    """A scripted Overlay: what the router would report, and the window it draws on."""

    def __init__(self, height=2160):
        self.names = {}
        self.window = None
        self.overlay = Overlay(lambda: self.names, height, self._make_window)
        self.height = height

    def _make_window(self, box):
        self.window = FakeWindow(box)
        return self.window

    def tick(self, names=None):
        if names is not None:
            self.names = names
        self.overlay.tick()
        return [kind for kind, _ in self.window.events]


def shown_images(screen):
    return [image for kind, image in screen.window.events if kind == "show"]


def test_window_is_created_over_the_key_cap_column():
    screen = Screen(height=1440)
    screen.overlay.open()
    assert screen.window.box == column_box(1440)


def test_nothing_is_drawn_and_no_window_shown_while_there_are_no_key_caps():
    screen = Screen()
    screen.overlay.open()
    assert screen.tick() == []
    assert screen.tick() == []


def test_key_caps_are_drawn_when_they_appear():
    screen = Screen()
    screen.overlay.open()
    assert screen.tick({1: "1", 2: "2"}) == ["show"]
    assert np.array_equal(shown_images(screen)[0], render_key_caps({1: "1", 2: "2"}, 2160))


def test_key_caps_are_not_redrawn_while_what_they_show_is_unchanged():
    screen = Screen()
    screen.overlay.open()
    screen.tick({1: "1", 2: "2"})
    for _ in range(50):
        screen.tick({1: "1", 2: "2"})
    assert len(shown_images(screen)) == 1


def test_key_caps_are_redrawn_when_the_slots_change():
    screen = Screen()
    screen.overlay.open()
    screen.tick({1: "1", 2: "2"})
    screen.tick({1: "1", 2: "2", 3: "3"})
    assert len(shown_images(screen)) == 2
    assert np.array_equal(shown_images(screen)[1], render_key_caps({1: "1", 2: "2", 3: "3"}, 2160))


def test_key_caps_are_hidden_when_none_are_wanted_and_drawn_afresh_when_they_return():
    screen = Screen()
    screen.overlay.open()
    screen.tick({1: "1"})
    assert screen.tick({}) == ["show", "hide"]
    assert screen.tick({}) == ["show", "hide"]  # hiding is not repeated
    assert screen.tick({1: "1"}) == ["show", "hide", "show"]


def test_run_ticks_until_stopped_then_closes_the_window():
    stop = threading.Event()
    calls = []

    def names():
        calls.append(1)
        if len(calls) == 3:
            stop.set()
        return {}

    windows = []
    overlay = Overlay(names, 2160, lambda box: windows.append(FakeWindow(box)) or windows[-1])
    overlay.run(stop, interval=0)
    assert len(calls) == 3
    assert windows[0].pumped == 3
    assert windows[0].events[-1] == ("close", None)


def test_run_closes_the_window_even_when_reading_the_key_caps_fails():
    def names():
        raise RuntimeError("boom")

    windows = []
    overlay = Overlay(names, 2160, lambda box: windows.append(FakeWindow(box)) or windows[-1])
    try:
        overlay.run(threading.Event(), interval=0)
    except RuntimeError:
        pass
    assert windows[0].events[-1] == ("close", None)


# --- starting the Overlay ---

MONITOR = {"left": 100, "top": 50, "width": 3840, "height": 2160}


class RecordingWindowClass:
    """Stands in for the Windows window class: records each window it is asked to make."""

    def __init__(self):
        self.made = []
        self.windows = []

    def __call__(self):
        return self._make

    def _make(self, left, top, width, height):
        self.made.append((left, top, width, height))
        window = FakeWindow((left, top, width, height))
        self.windows.append(window)
        return window


def test_overlay_that_is_off_creates_no_window_and_no_thread():
    def never():
        raise AssertionError("asked for a window class")

    started = start_overlay(
        enabled=False, key_caps=dict, monitor=MONITOR, stop=threading.Event(), on_failure=print, window_class=never
    )
    assert started is None


def test_overlay_that_is_on_makes_its_window_over_the_monitor_and_ends_on_stop():
    windows, stop = RecordingWindowClass(), threading.Event()
    thread = start_overlay(
        enabled=True, key_caps=lambda: {1: "1"}, monitor=MONITOR, stop=stop, on_failure=print, window_class=windows
    )
    for _ in range(200):  # wait for the thread to have drawn
        if windows.windows and windows.windows[0].events:
            break
        thread.join(0.01)
    stop.set()
    thread.join(2)
    left, top, width, height = column_box(2160)
    assert windows.made == [(100 + left, 50 + top, width, height)]
    assert [kind for kind, _ in windows.windows[0].events] == ["show", "close"]


def test_overlay_that_fails_reports_it_and_stops_without_raising():
    failures = []

    def broken():
        raise RuntimeError("no window for you")

    thread = start_overlay(
        enabled=True, key_caps=dict, monitor=MONITOR, stop=threading.Event(), on_failure=failures.append, window_class=broken
    )
    thread.join(2)
    assert not thread.is_alive()
    assert [str(f) for f in failures] == ["no window for you"]
