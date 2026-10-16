import threading
from types import SimpleNamespace

import numpy as np
import pytest
from PIL import Image

from stratagem_caller.tray import ICON_PATH, TrayIcon, greyed, load_icon


class FakeIcon:
    """Stands in for pystray.Icon: remembers what it was given and what it was asked."""

    def __init__(self, name, icon, title, menu):
        self.name, self.icon, self.title, self.menu = name, icon, title, menu
        self.calls = []
        self.visible = False
        self.notices = []
        self.setup = None

    def run_detached(self, setup=None):
        self.calls.append("run_detached")
        self.setup = setup

    def show(self):
        """The icon's own thread getting as far as running the setup it was given."""
        self.setup(self)

    def notify(self, message, title=None):
        assert self.visible, "pystray cannot notify from an icon that is not shown yet"
        self.notices.append((message, title))

    def update_menu(self):
        self.calls.append("update_menu")

    def stop(self):
        self.calls.append("stop")


class FakeMenuItem:
    def __init__(self, text, action):
        self._text, self.action = text, action

    @property
    def text(self):
        return self._text(self) if callable(self._text) else self._text

    def click(self):
        self.action(None, self)


class Tool:
    """The tool as a Tray Icon sees it: a pause state, and what the menu did."""

    def __init__(self):
        self.paused = False
        self.clicked = []
        self.icons = []  # every icon the backend was asked to make

        def make_icon(*args, **kwargs):
            self.icons.append(FakeIcon(*args, **kwargs))
            return self.icons[-1]

        self.running, self.grey = Image.new("RGBA", (4, 4), (255, 233, 0, 255)), Image.new("RGBA", (4, 4), (90, 90, 90, 255))
        self.tray = TrayIcon(
            paused=lambda: self.paused,
            toggle_pause=lambda: self.clicked.append("pause"),
            open_log=lambda: self.clicked.append("log"),
            quit=lambda: self.clicked.append("quit"),
            running_image=self.running,
            paused_image=self.grey,
            backend=SimpleNamespace(Icon=make_icon, Menu=lambda *items: list(items), MenuItem=FakeMenuItem),
        )

    @property
    def icon(self):
        return self.icons[-1]

    def menu(self):
        return {item.text: item for item in self.icon.menu}


def test_it_shows_the_key_cap_with_a_tooltip_saying_running():
    tool = Tool()
    tool.tray.start()
    assert tool.icon.icon is tool.running
    assert "Running" in tool.icon.title and "Paused" not in tool.icon.title
    assert "run_detached" in tool.icon.calls


def test_notify_shows_a_notification_once_the_icon_is_in_the_notification_area():
    tool = Tool()
    tool.tray.start()
    tool.icon.show()
    tool.tray.notify("Running. Call Key: B")
    assert tool.icon.notices == [("Running. Call Key: B", "Stratagem Caller")]


def test_notify_waits_for_the_icon_to_be_shown_rather_than_failing_in_its_first_moments():
    tool = Tool()
    tool.tray.start()
    threading.Timer(0.05, tool.icon.show).start()  # the icon's thread is a moment slow
    tool.tray.notify("Running. Call Key: B")
    assert [message for message, _ in tool.icon.notices] == ["Running. Call Key: B"]


def test_notify_says_what_it_could_not_show_when_the_icon_never_appears():
    tool = Tool()
    tool.tray.start()
    with pytest.raises(RuntimeError, match="Stratagem Caller stopped: see log"):
        tool.tray.notify("Stratagem Caller stopped: see log", shown_within=0.05)


def test_notify_before_start_is_refused_loudly():
    tool = Tool()
    with pytest.raises(AssertionError, match="not started"):
        tool.tray.notify("too early")


def test_the_menu_offers_pause_open_log_and_quit_in_that_order():
    tool = Tool()
    tool.tray.start()
    assert [item.text for item in tool.icon.menu] == ["Pause", "Open log", "Quit"]


def test_each_menu_item_does_its_one_thing():
    tool = Tool()
    tool.tray.start()
    for label in ("Pause", "Open log", "Quit"):
        tool.menu()[label].click()
    assert tool.clicked == ["pause", "log", "quit"]


def test_once_paused_the_icon_is_greyed_the_tooltip_says_paused_and_the_menu_says_resume():
    tool = Tool()
    tool.tray.start()
    tool.paused = True
    tool.tray.refresh()
    assert tool.icon.icon is tool.grey
    assert "Paused" in tool.icon.title
    assert [item.text for item in tool.icon.menu] == ["Resume", "Open log", "Quit"]
    assert "update_menu" in tool.icon.calls


def test_resuming_restores_the_icon_the_tooltip_and_the_label():
    tool = Tool()
    tool.tray.start()
    tool.paused = True
    tool.tray.refresh()
    tool.paused = False
    tool.tray.refresh()
    assert tool.icon.icon is tool.running
    assert "Running" in tool.icon.title
    assert tool.menu().keys() >= {"Pause"}


def test_stop_removes_the_icon_and_may_be_repeated_or_come_before_start():
    tool = Tool()
    tool.tray.stop()  # nothing to remove yet
    tool.tray.start()
    tool.tray.stop()
    tool.tray.stop()
    assert tool.icon.calls.count("stop") == 1


def test_refresh_before_start_does_nothing():
    tool = Tool()
    tool.tray.refresh()  # no icon yet: must not raise


# --- the picture ---


def test_the_icon_file_is_in_the_repo_and_is_the_yellow_key_cap():
    assert ICON_PATH.is_file()
    image = load_icon(ICON_PATH, size=64)
    assert image.size == (64, 64) and image.mode == "RGBA"
    assert image.getpixel((12, 32)) == (255, 233, 0, 255)  # the cap, left of the arrow
    assert image.getpixel((0, 0))[3] == 0  # clear outside it


def test_greyed_keeps_the_shape_and_drops_the_colour():
    yellow = load_icon(ICON_PATH, size=64)
    grey = greyed(yellow)
    assert grey.size == yellow.size
    grey_pixels, yellow_pixels = np.asarray(grey), np.asarray(yellow)
    assert (grey_pixels[:, :, 3] == yellow_pixels[:, :, 3]).all()
    opaque = grey_pixels[grey_pixels[:, :, 3] == 255]
    assert len(opaque) > 0 and (opaque[:, 0] == opaque[:, 1]).all() and (opaque[:, 1] == opaque[:, 2]).all()
    assert grey.getpixel((12, 32))[0] < yellow.getpixel((12, 32))[0]  # and dimmer, so it reads as off
