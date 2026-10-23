import dataclasses
import tempfile
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
import pytest
from test_terminal_prompt import grab, screen_with

from stratagem_caller import app as app_module
from stratagem_caller import startup, terminal_watch, winkeys
from stratagem_caller.app import ROOT, App
from stratagem_caller.settings import load
from stratagem_caller.keycaps import TerminalKeyCap
from stratagem_caller.terminal_code import CodeReading, CodeStatus, code_area, read_terminal_code
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
        self.failed_codes = Path(tempfile.mkdtemp())
        monkeypatch.setattr(app_module, "FAILED_CODES_DIR", self.failed_codes)
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


@pytest.mark.parametrize(
    "fixture", ["drill_code_five_entered_hand_over_first_arrow", "drill_next_step_not_a_code_bar"], ids=["unreadable", "none"]
)
def test_a_failed_read_saves_the_exact_region_it_looked_at(monkeypatch, fixture):
    screen = screen_with(fixture)
    terminal = Terminal(monkeypatch, screen)
    terminal.press_terminal_key()
    terminal.wait_until_typed(tones=2)
    assert wait_for(lambda: list(terminal.failed_codes.glob("*.png")))
    (saved,) = terminal.failed_codes.glob("*.png")
    area = code_area({"left": 0, "top": 0, "width": screen.shape[1], "height": screen.shape[0]})
    assert np.array_equal(cv2.imread(str(saved)), grab(screen, area))
    assert any(saved.name in line for line in terminal.lines)


def menu_screen(name):
    """A full 4K screen with a menu fixture (a top-left region) in its corner."""
    region = cv2.imread(str(ROOT / "fixtures" / "menu" / f"{name}.png"))
    screen = np.zeros((2160, 3840, 3), np.uint8)
    screen[: region.shape[0], : region.shape[1]] = region
    return screen, region


@pytest.mark.parametrize("after_a_reading", [False, True], ids=["before_any_reading", "after_a_reading"])
def test_a_slot_that_cannot_be_called_saves_the_menu_region_it_read(monkeypatch, tmp_path, after_a_reading):
    # The menu is open but nothing in it is callable, so Slot 3's Trigger Key beeps once the
    # watch reads the menu after the press, whether or not it had read it before.
    monkeypatch.setattr(app_module, "FAILED_CALLS_DIR", tmp_path)
    monkeypatch.setattr(app_module, "FIRST_READING_DELAY", 0)
    screen, region = menu_screen("open_menu_nothing_callable")
    monkeypatch.setattr(app_module.mss, "MSS", lambda: StillScreen(screen))
    settings = dataclasses.replace(load(ROOT / "settings.toml", ROOT / "codebook.toml"), keystroke_ms=(0, 0))
    monkeypatch.setattr(winkeys, "foreground_title", lambda: settings.window_title)
    monkeypatch.setattr(winkeys, "send", lambda key, down: None)
    lines = []
    app = App(settings, log=lines.append, tone=lambda hz, ms: None)
    trigger = winkeys.Key.named("3")
    app.on_event(Terminal.event(app.call_key, "down"))
    app.on_event(Terminal.event(app.call_key, "up"))
    if after_a_reading:
        assert wait_for(lambda: "menu open" in app.router.describe())
    app.on_event(Terminal.event(trigger, "down"))
    app.on_event(Terminal.event(trigger, "up"))
    try:
        # The PNG is written on its own thread: wait until it reads back whole.
        assert wait_for(lambda: [p for p in tmp_path.glob("*.png") if cv2.imread(str(p)) is not None])
        (saved,) = tmp_path.glob("*.png")
        assert np.array_equal(cv2.imread(str(saved)), region)
        assert any("cannot be called" in line and saved.name in line for line in lines)
    finally:
        app.stop()


def call_slot_2(monkeypatch, tmp_path, after_typing, check_delay=0.05):
    """Open the menu (Resupply, DDUR, callable at Slot 2) and press Slot 2's Trigger Key. Once the
    tool has typed the Code the screen shows `after_typing`. Returns the app, its log lines, the
    keys it typed, and the region shown after typing."""
    monkeypatch.setattr(app_module, "FAILED_CALLS_DIR", tmp_path)
    monkeypatch.setattr(app_module, "FIRST_READING_DELAY", 0)
    monkeypatch.setattr(app_module, "CALL_CHECK_DELAY", check_delay)
    before, _ = menu_screen("cream_arrows_four_slots")
    after, after_region = menu_screen(after_typing)
    shown = StillScreen(before)
    monkeypatch.setattr(app_module.mss, "MSS", lambda: shown)
    settings = dataclasses.replace(load(ROOT / "settings.toml", ROOT / "codebook.toml"), keystroke_ms=(0, 0))
    monkeypatch.setattr(winkeys, "foreground_title", lambda: settings.window_title)
    typed = []

    def send(key, down):
        if down:
            typed.append(key.name)
            if len(typed) == len("DDUR"):
                shown.show(after)

    monkeypatch.setattr(winkeys, "send", send)
    lines = []
    app = App(settings, log=lines.append, tone=lambda hz, ms: None)
    for key in (app.call_key, winkeys.Key.named("2")):
        app.on_event(Terminal.event(key, "down"))
        if key is app.call_key:
            assert wait_for(lambda: "Slots 1,2,3,4" in app.router.describe())
        app.on_event(Terminal.event(key, "up"))
    return app, lines, typed, after_region


def test_a_call_the_game_did_not_take_saves_the_menu_region_and_logs_it(monkeypatch, tmp_path):
    # After the Code is typed the menu is still open, with Slot 2's Code still showing.
    app, lines, typed, after = call_slot_2(monkeypatch, tmp_path, "cream_arrows_four_slots")
    try:
        assert wait_for(lambda: [p for p in tmp_path.glob("*.png") if cv2.imread(str(p)) is not None])
        assert typed == ["down", "down", "up", "right"]
        (saved,) = tmp_path.glob("*.png")
        assert np.array_equal(cv2.imread(str(saved)), after)
        assert any("Call DDUR not taken" in line and saved.name in line for line in lines), lines
    finally:
        app.stop()


def test_a_call_that_closes_the_menu_saves_nothing(monkeypatch, tmp_path):
    app, lines, typed, _ = call_slot_2(monkeypatch, tmp_path, "menu_closed_bright_sky")
    try:
        assert wait_for(lambda: len(typed) == 4)
        time.sleep(1.0)  # well past the check
        assert list(tmp_path.iterdir()) == []
        assert not any("not taken" in line for line in lines)
    finally:
        app.stop()


def test_opening_the_menu_again_before_the_check_saves_nothing(monkeypatch, tmp_path):
    # A quick next Call: the menu shows open because the player opened it again, not because the
    # game refused the Code.
    app, lines, typed, _ = call_slot_2(monkeypatch, tmp_path, "cream_arrows_four_slots", check_delay=0.3)
    try:
        assert wait_for(lambda: len(typed) == 4 and not app._sending.is_set())
        app.on_event(Terminal.event(app.call_key, "down"))
        app.on_event(Terminal.event(app.call_key, "up"))
        time.sleep(1.5)  # well past the check, even with the new watch reading meanwhile
        assert not any("not taken" in line for line in lines)
        assert not list(tmp_path.glob("*-not-taken.png"))
    finally:
        app.stop()


def test_a_direct_key_call_the_game_did_not_take_is_logged_too(monkeypatch, tmp_path):
    # The screen shows an open menu throughout, so the Direct Key's Code did not close it.
    monkeypatch.setattr(app_module, "FAILED_CALLS_DIR", tmp_path)
    monkeypatch.setattr(app_module, "CALL_CHECK_DELAY", 0.05)
    screen, _ = menu_screen("cream_arrows_four_slots")
    monkeypatch.setattr(app_module.mss, "MSS", lambda: StillScreen(screen))
    settings = dataclasses.replace(load(ROOT / "settings.toml", ROOT / "codebook.toml"), keystroke_ms=(0, 0))
    monkeypatch.setattr(winkeys, "foreground_title", lambda: settings.window_title)
    monkeypatch.setattr(winkeys, "send", lambda key, down: None)
    lines = []
    app = App(settings, log=lines.append, tone=lambda hz, ms: None)
    key = next(iter(app.router.direct_keys))
    code = app.router.direct_keys[key]
    app.on_event(Terminal.event(key, "down"))
    app.on_event(Terminal.event(key, "up"))
    try:
        assert wait_for(lambda: any(f"Call {code} not taken" in line for line in lines)), lines
    finally:
        app.stop()


class StillScreen:
    """Stands in for mss: every grab is cut from the same full screen."""

    def __init__(self, screen):
        self.monitors = [None, {"left": 0, "top": 0, "width": screen.shape[1], "height": screen.shape[0]}]
        self._screen = screen

    def show(self, screen):
        """From now on every grab is cut from `screen`."""
        self._screen = screen

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def grab(self, area):
        frame = grab(self._screen, area)
        return np.concatenate([frame, np.full(frame.shape[:2] + (1,), 255, np.uint8)], axis=2)  # BGRA


def test_a_read_code_saves_nothing(monkeypatch):
    terminal = Terminal(monkeypatch, screen_with("drill_code_two_entered_angle_a"))
    terminal.press_terminal_key()
    terminal.wait_until_typed()
    time.sleep(0.1)
    assert list(terminal.failed_codes.iterdir()) == []


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


MONITOR = {"left": 0, "top": 0, "width": 3840, "height": 2160}
NO_CODE = CodeReading(CodeStatus.NONE, why="no row of arrows")


class LiveScreen:
    """Stands in for mss for the Terminal watch worker: every grab shows what `shown.frame` is now."""

    def __init__(self, shown, seen):
        self.monitors = [None, MONITOR]
        self._shown, self._seen = shown, seen

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def grab(self, area):
        self._seen.append(area)
        frame = grab(self._shown.frame, area)
        return np.concatenate([frame, np.full(frame.shape[:2] + (1,), 255, np.uint8)], axis=2)  # BGRA


def watch_in_thread(terminal):
    """Run the Terminal watch worker on its own thread, as the app does."""
    thread = threading.Thread(target=terminal.app._watch_terminal, args=(terminal.watch,), daemon=True)
    thread.start()
    return thread


def wait_for(condition, seconds=5):
    deadline = time.monotonic() + seconds
    while not condition() and time.monotonic() < deadline:
        time.sleep(0.005)
    return condition()


def quick_worker(monkeypatch, *, code_interval=0.01):
    monkeypatch.setattr(terminal_watch, "GONE_FOR", 0.05)
    monkeypatch.setattr(app_module, "TERMINAL_READING_INTERVAL", 0.01)
    monkeypatch.setattr(app_module, "CODE_READING_INTERVAL", code_interval)


def test_the_terminal_watch_worker_reads_the_prompt_until_it_has_gone(monkeypatch):
    quick_worker(monkeypatch)
    terminal = Terminal(monkeypatch)
    areas, shown = [], []
    screen = SimpleNamespace(frame=screen_with("drill_code_pending_angle_a"))
    monkeypatch.setattr(app_module.mss, "MSS", lambda: LiveScreen(screen, areas))
    # A router that tells what it was shown, to see the prompt was read while it showed.
    original = terminal.app.router.offer_terminal

    def offer(watch, prompt):
        shown.append(prompt)
        if len(shown) == 3:
            screen.frame = np.zeros_like(screen.frame)  # the prompt goes
        original(watch, prompt)

    terminal.app.router.offer_terminal = offer
    terminal.app._watch_terminal(terminal.watch)  # returns when the watch is over
    assert not terminal.app.router.terminal_is_current(terminal.watch)
    assert shown[:3] == [TerminalPrompt.INTERACT] * 3 and shown[-1] is TerminalPrompt.NONE
    assert set(map(str, areas)) == {str(prompt_area(MONITOR)), str(code_area(MONITOR))}
    assert any("Terminal watch ended: Terminal Prompt gone" in line for line in terminal.lines)


# --- the Key Cap for the Terminal Key ---


def test_the_overlay_is_given_the_terminal_key_cap(monkeypatch):
    app, _ = make_app()
    given = {}
    monkeypatch.setattr(app_module.overlay, "start_overlay", lambda **kwargs: given.update(kwargs))
    app.start_overlay(MONITOR)
    assert given["terminal_key_cap"] == app.router.terminal_key_cap


def test_the_worker_reads_the_code_while_the_prompt_reads_interact_and_the_key_cap_follows_the_screen(monkeypatch):
    quick_worker(monkeypatch)
    terminal = Terminal(monkeypatch)
    screen = SimpleNamespace(frame=screen_with("drill_code_two_entered_angle_a"))
    monkeypatch.setattr(app_module.mss, "MSS", lambda: LiveScreen(screen, []))
    router = terminal.app.router
    thread = watch_in_thread(terminal)
    assert wait_for(lambda: router.terminal_key_cap() == TerminalKeyCap("1"))  # a Code is read: a Key Cap
    screen.frame = screen_with("drill_code_complete_fading")  # all entered
    assert wait_for(lambda: router.terminal_key_cap() is None)
    screen.frame = screen_with("drill_code_pending_angle_a")  # a Code is wanted again
    assert wait_for(lambda: router.terminal_key_cap() == TerminalKeyCap("1"))
    screen.frame = screen_with("drill_next_step_not_a_code_grid_move_cursor")  # a grid: no Code, no INTERACT
    assert wait_for(lambda: router.terminal_key_cap() is None)
    screen.frame = np.zeros_like(screen.frame)
    thread.join(5)
    assert not thread.is_alive()
    assert any("Terminal Key Cap shown: Code LURRDR, 2 entered" in line for line in terminal.lines)


def test_an_unreadable_code_and_a_bar_show_no_key_cap(monkeypatch):
    quick_worker(monkeypatch)
    terminal = Terminal(monkeypatch)
    reads = []
    monkeypatch.setattr(
        app_module, "read_terminal_code", lambda region, height: reads.append(1) or read_terminal_code(region, height)
    )
    screen = SimpleNamespace(frame=screen_with("drill_code_five_entered_hand_over_first_arrow"))
    monkeypatch.setattr(app_module.mss, "MSS", lambda: LiveScreen(screen, []))
    thread = watch_in_thread(terminal)
    assert wait_for(lambda: len(reads) >= 3)  # kept reading, kept finding nothing it could trust
    assert terminal.app.router.terminal_key_cap() is None
    screen.frame = screen_with("drill_next_step_not_a_code_bar")
    assert wait_for(lambda: len(reads) >= 6)
    assert terminal.app.router.terminal_key_cap() is None
    screen.frame = np.zeros_like(screen.frame)
    thread.join(5)


def test_the_code_is_read_only_while_the_prompt_reads_interact(monkeypatch):
    quick_worker(monkeypatch)
    terminal = Terminal(monkeypatch)
    reads = []
    monkeypatch.setattr(app_module, "read_terminal_code", lambda region, height: reads.append(1) or NO_CODE)
    screen = SimpleNamespace(frame=screen_with("drill_next_step_not_a_code_grid_move_cursor"))
    monkeypatch.setattr(app_module.mss, "MSS", lambda: LiveScreen(screen, []))
    thread = watch_in_thread(terminal)
    time.sleep(0.2)  # many prompt readings, all MOVE CURSOR
    assert reads == []
    screen.frame = np.zeros_like(screen.frame)
    thread.join(5)
    assert reads == []


def test_the_code_is_read_at_most_four_times_a_second_not_at_the_prompts_rate(monkeypatch):
    assert app_module.CODE_READING_INTERVAL == 0.25
    quick_worker(monkeypatch, code_interval=0.2)
    terminal = Terminal(monkeypatch)
    reads, prompts = [], []
    monkeypatch.setattr(app_module, "read_terminal_code", lambda region, height: reads.append(time.monotonic()) or NO_CODE)
    original = terminal.app.router.offer_terminal
    terminal.app.router.offer_terminal = lambda w, p: (prompts.append(p), original(w, p))
    screen = SimpleNamespace(frame=screen_with("drill_code_pending_angle_a"))
    monkeypatch.setattr(app_module.mss, "MSS", lambda: LiveScreen(screen, []))
    thread = watch_in_thread(terminal)
    time.sleep(0.5)
    screen.frame = np.zeros_like(screen.frame)
    thread.join(5)
    assert len(prompts) > 10  # the prompt was read every 10 ms or so, the Code far less often
    assert 2 <= len(reads) <= 4  # now, then every 0.2 s
    assert all(later - earlier >= 0.15 for earlier, later in zip(reads, reads[1:]))


def test_the_code_is_not_read_while_the_tool_is_typing_one(monkeypatch):
    quick_worker(monkeypatch)
    terminal = Terminal(monkeypatch)
    reads = []
    monkeypatch.setattr(app_module, "read_terminal_code", lambda region, height: reads.append(1) or NO_CODE)
    screen = SimpleNamespace(frame=screen_with("drill_code_pending_angle_a"))
    monkeypatch.setattr(app_module.mss, "MSS", lambda: LiveScreen(screen, []))
    terminal.app._entering_code.set()
    thread = watch_in_thread(terminal)
    time.sleep(0.2)
    assert reads == []
    terminal.app._entering_code.clear()
    assert wait_for(lambda: len(reads) >= 1)
    screen.frame = np.zeros_like(screen.frame)
    thread.join(5)


def test_the_code_is_not_read_for_a_key_cap_when_the_overlay_is_off(monkeypatch):
    quick_worker(monkeypatch)
    terminal = Terminal(monkeypatch)
    terminal.app.settings = dataclasses.replace(terminal.app.settings, overlay_enabled=False)
    reads = []
    monkeypatch.setattr(app_module, "read_terminal_code", lambda region, height: reads.append(1) or NO_CODE)
    screen = SimpleNamespace(frame=screen_with("drill_code_pending_angle_a"))
    monkeypatch.setattr(app_module.mss, "MSS", lambda: LiveScreen(screen, []))
    thread = watch_in_thread(terminal)
    time.sleep(0.2)
    assert reads == []  # nothing would show it, so it is not worth a screen grab ten times a second
    screen.frame = np.zeros_like(screen.frame)
    thread.join(5)
    assert not thread.is_alive()


def test_a_code_reading_that_fails_costs_the_key_cap_not_the_terminal_watch(monkeypatch):
    quick_worker(monkeypatch)
    terminal = Terminal(monkeypatch)
    monkeypatch.setattr(app_module, "read_terminal_code", lambda region, height: 1 / 0)
    screen = SimpleNamespace(frame=screen_with("drill_code_pending_angle_a"))
    monkeypatch.setattr(app_module.mss, "MSS", lambda: LiveScreen(screen, []))
    thread = watch_in_thread(terminal)
    assert wait_for(lambda: any("Code reading for the Key Cap failed" in line for line in terminal.lines))
    time.sleep(0.1)
    assert terminal.app.router.terminal_is_current(terminal.watch)  # the prompt is still read, the Terminal Key still held
    assert terminal.app.router.terminal_key_cap() is None
    failures = [line for line in terminal.lines if "Code reading for the Key Cap failed" in line]
    assert len(failures) == 1 and "ZeroDivisionError" in failures[0]  # said once, not ten times a second
    screen.frame = np.zeros_like(screen.frame)
    thread.join(5)
    assert not thread.is_alive()


# --- the Terminal Key's Key Cap flashes when the Terminal Key beeps ---


class FlashSpy:
    def __init__(self, terminal):
        self.count = 0
        terminal.app.router.flash_terminal_key = self._flash

    def _flash(self):
        self.count += 1


@pytest.mark.parametrize(
    "fixture", ["drill_code_five_entered_hand_over_first_arrow", "drill_next_step_not_a_code_bar"], ids=["unreadable", "none"]
)
def test_the_terminal_key_cap_flashes_when_the_terminal_key_beeps_for_want_of_a_code(monkeypatch, fixture):
    terminal = Terminal(monkeypatch, screen_with(fixture))
    spy = FlashSpy(terminal)
    terminal.press_terminal_key()
    terminal.wait_until_typed(tones=2)
    assert terminal.tones == [330, 330] and spy.count == 1  # one flash for the one Beep


def test_the_terminal_key_cap_flashes_when_reading_the_code_fails(monkeypatch):
    terminal = Terminal(monkeypatch, screen_with("drill_code_pending_angle_a"))
    spy = FlashSpy(terminal)
    monkeypatch.setattr(app_module, "read_terminal_code", lambda region, height: 1 / 0)
    terminal.app._entering_code.set()
    with pytest.raises(ZeroDivisionError):
        terminal.app._enter_code()
    terminal.wait_until_typed(tones=2)
    assert terminal.tones == [330, 330] and spy.count == 1


@pytest.mark.parametrize("fixture", ["drill_code_two_entered_angle_a", "drill_code_complete_fading"])
def test_the_terminal_key_cap_does_not_flash_when_a_code_was_read(monkeypatch, fixture):
    terminal = Terminal(monkeypatch, screen_with(fixture))
    spy = FlashSpy(terminal)
    terminal.press_terminal_key()
    terminal.wait_until_typed()
    time.sleep(0.1)
    assert terminal.tones == [] and spy.count == 0


def test_the_terminal_key_cap_flash_is_red_for_real_after_a_beep(monkeypatch):
    # Through the real router, with no spy: the Key Cap is red at the moment of the Beep.
    terminal = Terminal(monkeypatch, screen_with("drill_next_step_not_a_code_bar"))
    assert terminal.app.router.terminal_key_cap() is None
    terminal.press_terminal_key()
    terminal.wait_until_typed(tones=1)
    assert terminal.app.router.terminal_key_cap() == TerminalKeyCap("1", red=True)


# --- only one copy runs ---


class FakeLock:
    def __init__(self):
        self.released = False

    def release(self):
        self.released = True


class LaunchRoom:
    """main() with the OS, the screen, the keyboard, sound and the Tray Icon replaced."""

    def __init__(self, monkeypatch, tmp_path, lock):
        self.events = []
        events = self.events

        class Tray:
            def notify(self, message):
                events.append(("notify", message))

            def stop(self):
                events.append(("tray stopped",))

        class Keyboard:
            def __getattr__(self, name):
                events.append(("keyboard", name))  # any use at all is a failure for these tests
                raise AssertionError(f"the keyboard was used: {name}")

        monkeypatch.setattr(app_module, "LOG_PATH", tmp_path / "log.txt")
        monkeypatch.setattr(app_module, "claim", lambda: lock)
        monkeypatch.setattr(app_module, "_make_tray", lambda *args, **kwargs: Tray())
        monkeypatch.setattr(app_module, "_beep_once", lambda: events.append(("beep",)))
        monkeypatch.setattr(app_module, "keyboard", Keyboard())
        monkeypatch.setattr(startup, "STOPPED_NOTICE_SECONDS", 0)
        monkeypatch.setattr(threading, "excepthook", threading.excepthook)  # main() replaces it


def test_a_second_launch_notifies_beeps_once_and_exits_without_touching_the_keyboard(monkeypatch, tmp_path):
    room = LaunchRoom(monkeypatch, tmp_path, lock=None)  # another copy holds the lock
    app_module.main()  # returns instead of running
    assert room.events == [("notify", "Stratagem Caller is already running"), ("beep",), ("tray stopped",)]


def test_a_launch_that_holds_the_lock_lets_go_of_it_when_it_ends(monkeypatch, tmp_path):
    lock = FakeLock()
    LaunchRoom(monkeypatch, tmp_path, lock=lock)
    monkeypatch.setattr(app_module, "load", lambda *paths: (_ for _ in ()).throw(ValueError("settings.toml is broken")))
    with pytest.raises(ValueError, match="settings.toml is broken"):
        app_module.main()
    assert lock.released
