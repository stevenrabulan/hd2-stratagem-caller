import time
from types import SimpleNamespace

import numpy as np
from test_terminal_prompt import grab, screen_with

from stratagem_caller import app as app_module
from stratagem_caller import terminal_watch, winkeys
from stratagem_caller.app import ROOT, App
from stratagem_caller.settings import load
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
    """An App whose game window is focused, with a Terminal watch running that reads INTERACT."""

    def __init__(self, monkeypatch):
        self.lines = []
        self.tones = []
        settings = load(ROOT / "settings.toml", ROOT / "codebook.toml")
        monkeypatch.setattr(winkeys, "foreground_title", lambda: settings.window_title)
        self.app = App(settings, log=self.lines.append, tone=lambda hz, ms: self.tones.append(hz))
        self.watch = self.app.router.handle(self.event(self.app.use_key, "down")).start_terminal_watch
        self.app.router.offer_terminal(self.watch, TerminalPrompt.INTERACT)

    @staticmethod
    def event(key, kind):
        return SimpleNamespace(scan_code=key.scan_code, is_keypad=False, event_type=kind, time=time.monotonic())


def test_the_terminal_key_at_a_terminal_is_swallowed_and_beeps_for_now(monkeypatch):
    terminal = Terminal(monkeypatch)
    assert terminal.app.on_event(terminal.event(terminal.app.terminal_key, "down")) is False
    deadline = time.monotonic() + 3
    while len(terminal.tones) < 2 and time.monotonic() < deadline:
        time.sleep(0.02)
    assert terminal.tones == [330, 330]  # the Beep's two tones; no Slot, so no Key Cap flash
    assert any("Code not read yet" in line for line in terminal.lines)


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

    def __init__(self, frames, seen):
        self.monitors = [None, {"left": 0, "top": 0, "width": 3840, "height": 2160}]
        self._frames = iter(frames)
        self._seen = seen

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def grab(self, area):
        self._seen.append(area)
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
