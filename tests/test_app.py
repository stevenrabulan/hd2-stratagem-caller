import dataclasses
import threading
import time
from types import SimpleNamespace

import numpy as np
import pytest
from test_terminal_prompt import grab, screen_with

from stratagem_caller import app as app_module
from stratagem_caller import terminal_watch, winkeys
from stratagem_caller.app import ROOT, App
from stratagem_caller.settings import load
from stratagem_caller.terminal_code import code_area
from stratagem_caller.terminal_prompt import TerminalPrompt, prompt_area


def make_app():
    tones = []
    app = App(load(ROOT / "settings.toml", ROOT / "codebook.toml"), tone=lambda hz, ms: tones.append(hz))
    return app, tones


def test_pausing_and_resuming_each_play_their_beep_and_tell_the_tray_icon():
    app, tones = make_app()
    told = []
    app.on_pause_change = lambda: told.append(app.router.paused)
    app.toggle_pause()
    app.toggle_pause()
    assert told == [True, False]  # the Tray Icon hears it each time, after the state has changed
    assert tones == [440, 880]  # low to pause, high to resume


def test_stop_is_how_quit_from_the_tray_ends_the_tool():
    app, _ = make_app()
    assert not app.quit_requested
    app.stop()
    assert app.quit_requested


def test_an_overlay_that_fails_to_start_is_a_warning_and_the_tool_carries_on(monkeypatch):
    warnings = []
    settings = load(ROOT / "settings.toml", ROOT / "codebook.toml")
    app = App(settings, tone=lambda hz, ms: None, warn=warnings.append)
    monkeypatch.setattr(app_module.overlay, "start_overlay", lambda **kwargs: kwargs["on_failure"](RuntimeError("no window")))
    app.start_overlay({"left": 0, "top": 0, "width": 3840, "height": 2160})
    assert len(warnings) == 1 and "Overlay" in warnings[0] and "no window" in warnings[0]
    assert not app.quit_requested


# --- the Terminal watch and the Terminal Key ---


class Terminal:
    """An App whose game window is focused, with a Terminal watch running that reads INTERACT. Keys
    the tool types are recorded, not sent. The screens it reads for a Code are `screens` (full-screen
    frames, one per press of the Terminal Key; none by default)."""

    def __init__(self, monkeypatch, *screens):
        self.monkeypatch = monkeypatch
        self.lines = []
        self.tones = []
        self.sent = []  # (key name, down?) in order
        self.areas = []
        self.gate = threading.Event()  # a screen grab waits for this; set from the start
        self.gate.set()
        settings = load(ROOT / "settings.toml", ROOT / "codebook.toml")
        settings = dataclasses.replace(settings, keystroke_ms=(0, 0))
        monkeypatch.setattr(winkeys, "foreground_title", lambda: settings.window_title)
        monkeypatch.setattr(winkeys, "send", lambda key, down: self.sent.append((key.name, down)))
        if screens:
            self.show(*screens)
        self.app = App(settings, log=self.lines.append, tone=lambda hz, ms: self.tones.append(hz))
        self.watch = self.app.router.handle(self.event(self.app.use_key, "down")).start_terminal_watch
        self.app.router.offer_terminal(self.watch, TerminalPrompt.INTERACT)

    def show(self, *screens):
        """The screens the Terminal Key's presses read, one per press."""
        frames = iter(screens)  # shared: each press takes the next one
        self.monkeypatch.setattr(app_module.mss, "MSS", lambda: FakeScreen(frames, self.areas, self.gate))

    def press_terminal_key(self):
        """Press the Terminal Key; returns the hook's answer (True: it goes on to the game)."""
        answer = self.app.on_event(self.event(self.app.terminal_key, "down"))
        self.app.on_event(self.event(self.app.terminal_key, "up"))
        return answer

    def wait_until_typed(self, tones=0):
        deadline = time.monotonic() + 5
        while (self.app._sending.is_set() or len(self.tones) < tones) and time.monotonic() < deadline:
            time.sleep(0.01)

    def typed(self):
        """The keys the tool pressed, in order (each was released again)."""
        downs = [name for name, down in self.sent if down]
        assert self.sent == [(name, down) for name in downs for down in (True, False)]
        return downs

    @staticmethod
    def event(key, kind):
        return SimpleNamespace(scan_code=key.scan_code, is_keypad=False, event_type=kind, time=time.monotonic())


def test_the_terminal_key_types_the_directions_not_yet_entered(monkeypatch):
    terminal = Terminal(monkeypatch, screen_with("drill_code_two_entered_angle_a"))  # two done, four left
    assert terminal.press_terminal_key() is False  # swallowed
    terminal.wait_until_typed()
    assert terminal.typed() == ["right", "right", "down", "right"]  # the Direction Keys, not the Terminal Key
    assert terminal.tones == []
    assert any("LURRDR" in line and "RRDR" in line for line in terminal.lines)


def test_with_nothing_entered_the_whole_code_is_typed(monkeypatch):
    terminal = Terminal(monkeypatch, screen_with("drill_code_pending_angle_a"))
    terminal.press_terminal_key()
    terminal.wait_until_typed()
    assert terminal.typed() == ["left", "up", "right", "right", "down", "right"]


def test_with_every_direction_entered_nothing_is_typed_and_there_is_no_beep(monkeypatch):
    terminal = Terminal(monkeypatch, screen_with("drill_code_complete_fading"))
    assert terminal.press_terminal_key() is False
    terminal.wait_until_typed()
    time.sleep(0.1)
    assert terminal.typed() == [] and terminal.tones == []
    assert any("nothing left to type" in line for line in terminal.lines)


def test_a_code_that_cannot_be_read_is_swallowed_and_beeps_and_types_nothing(monkeypatch):
    terminal = Terminal(monkeypatch, screen_with("drill_code_five_entered_hand_over_first_arrow"))
    assert terminal.press_terminal_key() is False
    terminal.wait_until_typed(tones=2)
    assert terminal.tones == [330, 330]  # the Beep's two tones; no Slot, so no Key Cap flash
    assert terminal.typed() == []
    assert any("Code unreadable" in line for line in terminal.lines)


def test_a_terminal_with_no_code_on_its_screen_beeps_too(monkeypatch):
    terminal = Terminal(monkeypatch, screen_with("drill_next_step_not_a_code_bar"))
    assert terminal.press_terminal_key() is False
    terminal.wait_until_typed(tones=2)
    assert terminal.tones == [330, 330] and terminal.typed() == []


def test_each_press_reads_the_code_afresh_and_nothing_is_retried(monkeypatch):
    # The first press finds the Code unreadable and beeps; nothing happens by itself after that. The
    # next press reads what is on screen then (two entered by hand meanwhile) and types the rest.
    terminal = Terminal(
        monkeypatch,
        screen_with("drill_code_five_entered_hand_over_first_arrow"),
        screen_with("drill_code_two_entered_angle_a"),
    )
    terminal.press_terminal_key()
    terminal.wait_until_typed(tones=2)
    time.sleep(0.2)
    assert terminal.typed() == [] and len(terminal.areas) == 1  # one grab, no retry
    terminal.press_terminal_key()
    terminal.wait_until_typed()
    assert terminal.typed() == ["right", "right", "down", "right"] and len(terminal.areas) == 2


def test_the_code_is_read_from_the_centre_of_the_screen(monkeypatch):
    terminal = Terminal(monkeypatch, screen_with("drill_code_pending_angle_a"))
    terminal.press_terminal_key()
    terminal.wait_until_typed()
    assert terminal.areas == [code_area({"left": 0, "top": 0, "width": 3840, "height": 2160})]


def test_the_tool_does_not_react_to_its_own_keys_while_it_reads_and_types(monkeypatch):
    terminal = Terminal(monkeypatch, screen_with("drill_code_pending_angle_a"))
    terminal.gate.clear()  # the screen grab waits
    terminal.press_terminal_key()
    assert terminal.app._sending.is_set()  # marked as typing from the moment the key was decided
    terminal.gate.set()
    terminal.wait_until_typed()
    assert not terminal.app._sending.is_set()


def test_a_second_terminal_key_press_while_the_first_is_read_and_typed_is_held_back(monkeypatch):
    terminal = Terminal(monkeypatch, screen_with("drill_code_pending_angle_a"), screen_with("drill_code_pending_angle_a"))
    terminal.gate.clear()
    terminal.press_terminal_key()
    assert terminal.press_terminal_key() is False  # not a weapon switch for the game, and not a second Code
    terminal.gate.set()
    terminal.wait_until_typed()
    assert terminal.typed() == ["left", "up", "right", "right", "down", "right"] and len(terminal.areas) == 1
    assert not terminal.app._entering_code.is_set()


def test_a_reading_that_fails_beeps_logs_and_lets_the_terminal_key_go_free_again(monkeypatch):
    terminal = Terminal(monkeypatch, screen_with("drill_code_pending_angle_a"))
    monkeypatch.setattr(app_module, "read_terminal_code", lambda region, height: 1 / 0)
    terminal.app._entering_code.set()
    with pytest.raises(ZeroDivisionError):
        terminal.app._enter_code()
    terminal.wait_until_typed(tones=2)
    assert terminal.tones == [330, 330] and not terminal.app._entering_code.is_set()
    assert any("reading the Code failed" in line and "ZeroDivisionError" in line for line in terminal.lines)


def test_pausing_while_the_code_is_read_types_nothing(monkeypatch):
    terminal = Terminal(monkeypatch, screen_with("drill_code_pending_angle_a"))
    terminal.gate.clear()
    terminal.press_terminal_key()
    terminal.app.toggle_pause()
    terminal.gate.set()
    terminal.wait_until_typed()
    assert terminal.typed() == []


def test_pausing_ends_the_terminal_watch_through_the_same_path_as_the_menu_watch(monkeypatch):
    terminal = Terminal(monkeypatch)
    terminal.app.toggle_pause()
    assert not terminal.app.router.terminal_is_current(terminal.watch)
    assert any("Terminal watch ended: paused" in line for line in terminal.lines)


def test_resuming_does_not_start_a_terminal_watch(monkeypatch):
    terminal = Terminal(monkeypatch)
    terminal.app.toggle_pause()
    terminal.app.toggle_pause()
    assert not terminal.app.router.terminal_is_current(terminal.watch)
    assert terminal.app.router.describe().count("Terminal watch") == 0


def test_the_use_key_and_terminal_key_come_from_the_settings():
    app, _ = make_app()
    assert (app.use_key.name, app.terminal_key.name) == ("e", "1")


class FakeScreen:
    """Stands in for mss: each grab of the prompt strip returns the next scripted frame."""

    def __init__(self, frames, seen, gate=None):
        self.monitors = [None, {"left": 0, "top": 0, "width": 3840, "height": 2160}]
        self._frames = iter(frames)
        self._seen = seen
        self._gate = gate

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def grab(self, area):
        self._seen.append(area)
        if self._gate is not None:
            self._gate.wait(5)
        frame = grab(next(self._frames), area)
        return np.concatenate([frame, np.full(frame.shape[:2] + (1,), 255, np.uint8)], axis=2)  # BGRA


def test_the_terminal_watch_worker_reads_the_prompt_until_it_has_gone(monkeypatch):
    monkeypatch.setattr(terminal_watch, "GONE_FOR", 0.05)
    monkeypatch.setattr(app_module, "TERMINAL_READING_INTERVAL", 0.01)
    terminal = Terminal(monkeypatch)
    areas, shown = [], []
    interact = screen_with("drill_code_pending_angle_a")
    empty = np.zeros_like(interact)
    frames = [interact] * 3 + [empty] * 200  # the prompt shows, then goes
    monkeypatch.setattr(app_module.mss, "MSS", lambda: FakeScreen(frames, areas))
    # A router that tells what it was shown, to see the prompt was read while it showed.
    original = terminal.app.router.offer_terminal
    terminal.app.router.offer_terminal = lambda w, p: (shown.append(p), original(w, p))
    terminal.app._watch_terminal(terminal.watch)  # returns when the watch is over
    assert not terminal.app.router.terminal_is_current(terminal.watch)
    assert shown[:3] == [TerminalPrompt.INTERACT] * 3 and shown[-1] is TerminalPrompt.NONE
    assert all(area == prompt_area({"left": 0, "top": 0, "width": 3840, "height": 2160}) for area in areas)
    assert any("Terminal watch ended: Terminal Prompt gone" in line for line in terminal.lines)
