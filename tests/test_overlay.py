import threading

import numpy as np
import pytest

from stratagem_caller.flash import red_slots
from stratagem_caller.heading import PULSE_PERIOD, heading_box, pulse_opacity, render_heading
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

    def set_opacity(self, opacity):
        self.events.append(("opacity", opacity))

    def pump(self):
        self.pumped += 1

    def close(self):
        self.events.append(("close", None))


class Screen:
    """A scripted Overlay: what the router would report, and the window it draws on."""

    def __init__(self, height=2160):
        self.names = {}
        self.red = frozenset()
        self.now = 100.0
        self.windows = []
        self.overlay = Overlay(lambda: self.names, lambda: self.red, height, self._make_window, clock=lambda: self.now)
        self.height = height

    def _make_window(self, box):
        window = FakeWindow(box)
        self.windows.append(window)
        return window

    @property
    def window(self):
        """The Key Cap column's window (made first)."""
        return self.windows[0]

    @property
    def heading(self):
        """The heading's window (made second)."""
        return self.windows[1]

    def tick(self, names=None, red=None, after=0.0):
        self.now += after
        if names is not None:
            self.names = names
        if red is not None:
            self.red = frozenset(red)
        self.overlay.tick()
        return [kind for kind, _ in self.window.events]


def shown_images(screen):
    return [image for kind, image in screen.window.events if kind == "show"]


def test_windows_are_created_over_the_key_cap_column_and_the_heading_strip():
    screen = Screen(height=1440)
    screen.overlay.open()
    assert [w.box for w in screen.windows] == [column_box(1440), heading_box(1440)]


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


def test_a_key_cap_is_redrawn_red_when_it_flashes_and_normal_when_it_ends():
    screen = Screen()
    screen.overlay.open()
    names = {1: "1", 2: "2"}
    screen.tick(names)
    screen.tick(red={2})
    screen.tick(red=set())
    images = shown_images(screen)
    assert len(images) == 3
    assert np.array_equal(images[1], render_key_caps(names, 2160, red=frozenset({2})))
    assert np.array_equal(images[2], images[0])


def test_a_red_key_cap_is_not_redrawn_while_it_stays_red():
    screen = Screen()
    screen.overlay.open()
    screen.tick({1: "1", 2: "2"}, red={2})
    for _ in range(50):
        screen.tick()
    assert len(shown_images(screen)) == 1


def test_red_for_a_slot_with_no_key_cap_changes_nothing():
    screen = Screen()
    screen.overlay.open()
    screen.tick({1: "1"})
    screen.tick(red={5})
    screen.tick(red=set())
    assert len(shown_images(screen)) == 1


def test_red_does_not_keep_key_caps_up_when_none_are_wanted():
    screen = Screen()
    screen.overlay.open()
    screen.tick({1: "1", 2: "2"}, red={2})
    assert screen.tick({}) == ["show", "hide"]


def test_a_flash_is_four_draws_red_normal_twice_then_nothing_more():
    clock = [10.0]
    names = {1: "1", 2: "2"}
    windows = []
    overlay = Overlay(
        lambda: names,
        lambda: red_slots({2: 10.0}, clock[0]) & names.keys(),
        2160,
        lambda box: windows.append(FakeWindow(box)) or windows[-1],
    )
    overlay.open()
    while clock[0] < 11.0:  # polled at 30 Hz, as in the app
        overlay.tick()
        clock[0] += 1 / 30
    images = [image for kind, image in windows[0].events if kind == "show"]
    red = render_key_caps(names, 2160, red=frozenset({2}))
    assert [np.array_equal(i, red) for i in images] == [True, False, True, False]


# --- the ready heading ---


def heading_events(screen, kind=None):
    return [event for event in screen.heading.events if kind is None or event[0] == kind]


def test_the_heading_is_drawn_once_when_the_key_caps_appear_and_not_before():
    screen = Screen()
    screen.overlay.open()
    screen.tick()
    assert heading_events(screen) == []
    screen.tick({1: "1"})
    shown = heading_events(screen, "show")
    assert len(shown) == 1
    assert np.array_equal(shown[0][1], render_heading(2160))


def test_the_heading_comes_in_at_full_opacity_before_its_picture():
    screen = Screen()
    screen.overlay.open()
    screen.tick({1: "1"})
    assert [kind for kind, _ in heading_events(screen)] == ["opacity", "show"]
    assert heading_events(screen)[0] == ("opacity", 255)


def test_the_heading_hides_in_the_same_tick_as_the_key_caps():
    screen = Screen()
    screen.overlay.open()
    screen.tick({1: "1"})
    screen.tick({})
    assert screen.window.events[-1] == ("hide", None)
    assert heading_events(screen)[-1] == ("hide", None)


def test_the_heading_stays_up_while_the_key_caps_change_and_flash():
    screen = Screen()
    screen.overlay.open()
    screen.tick({1: "1", 2: "2"})
    screen.tick({1: "1", 2: "2", 3: "3"}, after=0.03)
    screen.tick(red={2}, after=0.03)
    screen.tick(red=set(), after=0.03)
    assert [kind for kind, _ in heading_events(screen) if kind in ("show", "hide")] == ["show"]


def test_the_heading_is_drawn_afresh_each_time_it_shows():
    screen = Screen()
    screen.overlay.open()
    screen.tick({1: "1"})
    screen.tick({})
    screen.tick({1: "1"})
    assert [kind for kind, _ in heading_events(screen) if kind != "opacity"] == ["show", "hide", "show"]


def test_pulsing_changes_only_the_opacity_never_the_picture():
    screen = Screen()
    screen.overlay.open()
    screen.tick({1: "1"})
    for _ in range(100):  # 3.3 s at 30 Hz, nearly three pulses
        screen.tick(after=1 / 30)
    assert len(heading_events(screen, "show")) == 1
    assert len(shown_images(screen)) == 1  # nor were the Key Caps redrawn
    opacities = [value for _, value in heading_events(screen, "opacity")]
    assert min(opacities) == pulse_opacity(PULSE_PERIOD / 2)
    assert max(opacities) == 255


def test_opacity_follows_time_since_the_heading_appeared():
    screen = Screen()
    screen.overlay.open()
    screen.tick({1: "1"})
    screen.tick(after=PULSE_PERIOD / 2)
    assert heading_events(screen, "opacity")[-1] == ("opacity", pulse_opacity(PULSE_PERIOD / 2))
    screen.tick({}, after=0.1)
    screen.tick({1: "1"}, after=5.0)  # a new showing starts the pulse over
    assert heading_events(screen, "opacity")[-1] == ("opacity", 255)


def test_opacity_is_not_sent_again_when_it_has_not_changed():
    screen = Screen()
    screen.overlay.open()
    screen.tick({1: "1"})
    count = len(heading_events(screen, "opacity"))
    screen.tick()
    screen.tick()
    assert len(heading_events(screen, "opacity")) == count


def test_no_window_is_touched_by_the_heading_while_hidden():
    screen = Screen()
    screen.overlay.open()
    for _ in range(30):
        screen.tick(after=1 / 30)
    assert heading_events(screen) == []


def test_run_ticks_until_stopped_then_closes_the_window():
    stop = threading.Event()
    calls = []

    def names():
        calls.append(1)
        if len(calls) == 3:
            stop.set()
        return {}

    windows = []
    overlay = Overlay(names, frozenset, 2160, lambda box: windows.append(FakeWindow(box)) or windows[-1])
    overlay.run(stop, interval=0)
    assert len(calls) == 3
    assert windows[0].pumped == 3
    assert windows[0].events[-1] == ("close", None)


def test_run_closes_the_window_even_when_reading_the_key_caps_fails():
    def names():
        raise RuntimeError("boom")

    windows = []
    overlay = Overlay(names, frozenset, 2160, lambda box: windows.append(FakeWindow(box)) or windows[-1])
    try:
        overlay.run(threading.Event(), interval=0)
    except RuntimeError:
        pass
    assert windows[0].events[-1] == ("close", None)


def test_the_first_window_is_closed_when_the_second_cannot_be_made():
    made = []

    def make_window(box):
        if made:
            raise RuntimeError("no second window")
        made.append(FakeWindow(box))
        return made[0]

    overlay = Overlay(dict, frozenset, 2160, make_window)
    with pytest.raises(RuntimeError, match="no second window"):
        overlay.run(threading.Event(), interval=0)
    assert made[0].events == [("close", None)]


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
        enabled=False, key_caps=dict, red_key_caps=frozenset, monitor=MONITOR, stop=threading.Event(), on_failure=print, window_class=never
    )
    assert started is None


def test_overlay_that_is_on_makes_its_window_over_the_monitor_and_ends_on_stop():
    windows, stop = RecordingWindowClass(), threading.Event()
    thread = start_overlay(
        enabled=True, key_caps=lambda: {1: "1"}, red_key_caps=frozenset, monitor=MONITOR, stop=stop, on_failure=print, window_class=windows
    )
    for _ in range(200):  # wait for the thread to have drawn
        if windows.windows and windows.windows[0].events:
            break
        thread.join(0.01)
    stop.set()
    thread.join(2)
    boxes = [column_box(2160), heading_box(2160)]
    assert windows.made == [(100 + left, 50 + top, width, height) for left, top, width, height in boxes]
    assert [kind for kind, _ in windows.windows[0].events] == ["show", "close"]
    heading_events = [kind for kind, _ in windows.windows[1].events]
    assert heading_events[:2] == ["opacity", "show"] and heading_events[-1] == "close"
    assert heading_events.count("show") == 1


def test_overlay_that_fails_reports_it_and_stops_without_raising():
    failures = []

    def broken():
        raise RuntimeError("no window for you")

    thread = start_overlay(
        enabled=True, key_caps=dict, red_key_caps=frozenset, monitor=MONITOR, stop=threading.Event(), on_failure=failures.append, window_class=broken
    )
    thread.join(2)
    assert not thread.is_alive()
    assert [str(f) for f in failures] == ["no window for you"]
