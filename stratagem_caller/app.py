"""Listen for the Call Key, Trigger Keys and Direct Keys, and make Calls."""

import os
import random
import threading
import time
import winsound
from collections.abc import Callable
from pathlib import Path

from . import winkeys

winkeys.make_dpi_aware()

import keyboard  # noqa: E402
import mss  # noqa: E402
import numpy as np  # noqa: E402

from .arming import ArmingWindow, Kind, Outcome  # noqa: E402
from .beep import DoubleBeep  # noqa: E402
from .eventlog import EventLog  # noqa: E402
from .marks import RecentRegions, save_mark  # noqa: E402
from . import overlay  # noqa: E402
from . import tray  # noqa: E402
from .reader import REFERENCE_HEIGHT, read_menu, region_size  # noqa: E402
from .router import KeyEvent, KeyRouter  # noqa: E402
from .settings import Settings, load  # noqa: E402
from .terminal_prompt import prompt_area, read_terminal_prompt  # noqa: E402
from .terminal_watch import READING_INTERVAL as TERMINAL_READING_INTERVAL, TerminalWatch  # noqa: E402
from .winkeys import Key  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LOG_PATH = ROOT / "logs" / "stratagem_caller.log"
# Screen regions saved by the Mark Key. Under fixtures/raw/, so not in version control.
MARKS_DIR = ROOT / "fixtures" / "raw" / "marks"
# Regions kept for a mark: about 1 to 3 s of watching (about 3.6 MB each at 4K).
RECENT_REGIONS = 16

# Reading the menu before it has started to slide in is wasted work.
FIRST_READING_DELAY = 0.15


class App:
    def __init__(
        self,
        settings: Settings,
        log: Callable[[str], None] = lambda text: None,
        tone: Callable[[int, int], None] = winsound.Beep,
    ):
        """`tone(hz, ms)` sounds one tone and returns when it ends."""
        self.settings = settings
        self._log = log
        self._tone = tone
        self.recent = RecentRegions(RECENT_REGIONS)
        self._marks = 0
        self._quit = threading.Event()  # ends the Overlay's thread and the tool's main loop
        self._overlay_thread: threading.Thread | None = None
        self._beep = DoubleBeep(tone=tone)
        self.on_pause_change: Callable[[], None] = lambda: None  # the Tray Icon follows the pause state
        self._pause_lock = threading.Lock()
        self.call_key = Key.named(settings.call_key)
        self.use_key = Key.named(settings.use_key)
        self.terminal_key = Key.named(settings.terminal_key)
        self.direction_keys = {d: Key.named(k) for d, k in settings.direction_keys.items()}

        # Set from the moment a send is decided until it has been typed, so the tool
        # never reacts to its own keys. Sends may overlap, so they are counted.
        self._sending = threading.Event()
        self._sends_pending = 0
        self._count_lock = threading.Lock()
        self._send_lock = threading.Lock()
        self.router = KeyRouter(
            call_key=self.call_key,
            use_key=self.use_key,
            terminal_key=self.terminal_key,
            direct_keys={Key.named(k): code for k, code in settings.direct_keys.items()},
            trigger_keys={Key.named(k): slot for k, slot in settings.trigger_keys.items()},
            window_title=settings.window_title,
            clock=time.monotonic,
            foreground_title=winkeys.foreground_title,
            is_sending=self._sending.is_set,
            log=log,
        )

    # --- Overlay ---

    def start_overlay(self, monitor: dict) -> None:
        """Run the Overlay on its own thread, unless the settings turn it off, in which
        case no window is created."""
        self._overlay_thread = overlay.start_overlay(
            enabled=self.settings.overlay_enabled,
            key_caps=self.router.key_caps,
            red_key_caps=self.router.red_key_caps,
            monitor=monitor,
            stop=self._quit,
            on_failure=self._overlay_failed,
        )

    def _overlay_failed(self, error: Exception) -> None:
        self._log(f"Overlay stopped: {error!r}")
        print(f"  Warning: the Overlay stopped ({error!r}); Trigger Keys still work.")

    def stop(self) -> None:
        """Ask the tool to end: the Overlay closes and the main loop returns. Called for
        Quit in the Tray Icon's menu; Ctrl+C reaches the same shutdown."""
        self._quit.set()

    @property
    def quit_requested(self) -> bool:
        return self._quit.is_set()

    def shutdown(self) -> None:
        """Everything the tool put in place goes away: the Overlay's windows, and the
        keyboard hook and hotkeys, so every key goes back to the game. Safe to repeat."""
        self.stop()
        if self._overlay_thread is not None:
            self._overlay_thread.join(timeout=2)  # it closes its windows on the way out
        keyboard.unhook_all()

    # --- keyboard hook (must return quickly; True lets the key through) ---

    def on_event(self, event: keyboard.KeyboardEvent) -> bool:
        decision = self.router.handle(
            KeyEvent(event.scan_code, event.is_keypad, event.event_type, event.time)
        )
        if decision.start_watching is not None:
            threading.Thread(
                target=self._watch_menu, args=(decision.start_watching,), daemon=True
            ).start()
        if decision.start_terminal_watch is not None:
            threading.Thread(
                target=self._watch_terminal, args=(decision.start_terminal_watch,), daemon=True
            ).start()
        if decision.enter_code:
            self._spawn(self._enter_code, sends=False)
        if decision.outcome is not None:
            # A Trigger Key decided at once from the Readings already taken.
            self._spawn(self._act, decision.outcome, sends=decision.outcome.sends_keys)
        if decision.direct_code is not None:
            self._spawn(self._direct_call, decision.direct_code, decision.direct_presses_call_key, sends=True)
        return decision.let_through

    def _spawn(self, target: Callable, *args, sends: bool) -> None:
        """Run `target` on its own thread. A send is marked as begun here, in the caller's
        thread, so no key of its own can arrive before the tool knows it is typing."""
        if sends:
            self._begin_send()
        threading.Thread(target=self._run, args=(target, args, sends), daemon=True).start()

    def _run(self, target: Callable, args: tuple, sends: bool) -> None:
        try:
            target(*args)
        finally:
            if sends:
                self._end_send()

    def _begin_send(self) -> None:
        with self._count_lock:
            self._sends_pending += 1
            self._sending.set()

    def _end_send(self) -> None:
        with self._count_lock:
            self._sends_pending -= 1
            if self._sends_pending == 0:
                self._sending.clear()

    # --- worker threads ---

    def _watch_menu(self, window: ArmingWindow) -> None:
        """Read the menu until the Arming Window ends: a Call, a hand back, the menu closing,
        the game losing focus, the safety limit, or a pause (which drops the window, so
        `is_current` turns false). Always returns when the watch is over."""
        try:
            with mss.MSS() as sct:
                monitor = sct.monitors[1]
                area = _menu_area(monitor)
                time.sleep(FIRST_READING_DELAY)
                while self.router.is_current(window):
                    region = np.asarray(sct.grab(area))[:, :, :3]
                    self.recent.add(time.monotonic(), region)
                    reading = read_menu(region, monitor["height"])
                    outcome = self.router.offer(window, reading)
                    if outcome is not None:
                        if outcome.sends_keys:
                            self._begin_send()  # before the watch ends and keys are free again
                        try:
                            trigger = self.router.finish(window, outcome)
                            if not outcome.ends_watch:
                                # A beep: keep reading while it sounds.
                                threading.Thread(target=self._act, args=(outcome,), daemon=True).start()
                            else:
                                self._act(outcome, trigger)
                                return
                        finally:
                            if outcome.sends_keys:
                                self._end_send()
                    time.sleep(self.router.reading_delay(window))
        finally:
            # An error must not leave a watch with no worker (the next Call Key press would
            # only restart it). A no-op when the watch already ended.
            self.router.end_watch("reading stopped", only=window)

    def _watch_terminal(self, watch: TerminalWatch) -> None:
        """Read the Terminal Prompt until the Terminal watch ends: no prompt within 5 s of the
        Use Key press, the prompt gone for about a second, the game losing focus, the safety
        limit, or a pause (which drops the watch, so `terminal_is_current` turns false). Always
        returns when the watch is over."""
        try:
            with mss.MSS() as sct:
                monitor = sct.monitors[1]
                area = prompt_area(monitor)
                while self.router.terminal_is_current(watch):
                    region = np.asarray(sct.grab(area))[:, :, :3]
                    self.router.offer_terminal(watch, read_terminal_prompt(region, monitor["height"]))
                    time.sleep(TERMINAL_READING_INTERVAL)
        finally:
            # An error must not leave a watch with no worker (the Terminal Key would stay held
            # on a stale reading). A no-op when the watch already ended.
            self.router.end_terminal_watch("reading stopped", only=watch)

    def _enter_code(self) -> None:
        """The Terminal Key was pressed while the Terminal Prompt reads INTERACT. Reading the Code
        on the Terminal's screen and typing it is the next ticket; until then the key is held
        back and the tool beeps (a Beep with no Slot, so only the tones, no Key Cap flash). That
        next ticket replaces this body: read the Code, type it, or beep when it cannot be read."""
        self._log("Code not read yet")
        self._beep.play()

    def _act(self, outcome: Outcome, trigger: Key | None = None) -> None:
        """Carry out what a Trigger Key came to. Once paused nothing is typed or tapped
        (a beep is only a sound). A key held when focus was lost, or a closed menu,
        needs nothing."""
        if outcome.kind is Kind.BEEP:
            self._beep.play()
        elif self.router.paused:
            return
        elif outcome.kind is Kind.CALL:
            self._type(outcome.code)
        elif outcome.hands_back and trigger is not None:
            self._hand_back(trigger)

    def _hand_back(self, trigger: Key) -> None:
        with self._send_lock:
            self._tap(trigger)

    def _direct_call(self, code: str, press_call_key: bool) -> None:
        with self._send_lock:
            if press_call_key:
                self._tap(self.call_key, gap=self.settings.direct_key_pause_ms)
            self._tap_code(code)
        self.router.close_window()

    def _type(self, code: str) -> None:
        with self._send_lock:
            self._tap_code(code, until_paused=True)

    def _tap_code(self, code: str, until_paused: bool = False) -> None:
        for direction in code:
            if until_paused and self.router.paused:
                return
            self._tap(self.direction_keys[direction])

    def _tap(self, key: Key, gap: tuple[int, int] | None = None) -> None:
        winkeys.send(key, down=True)
        time.sleep(random.uniform(*self.settings.keystroke_ms) / 1000)
        winkeys.send(key, down=False)
        time.sleep(random.uniform(*(gap or self.settings.keystroke_ms)) / 1000)

    # --- mark ---

    def mark(self) -> None:
        """The player saw something unexpected: log what the tool believes now, and save
        the regions it last read plus one taken now. Runs on the Mark Key's thread."""
        self._marks += 1
        number, marked_at = self._marks, time.monotonic()
        self._log(f"MARK {number}: {self.router.describe()}")
        regions = self.recent.snapshot()
        threading.Thread(target=self._save_mark, args=(number, marked_at, regions), daemon=True).start()
        self._tone(1200, 60)

    def _save_mark(self, number: int, marked_at: float, regions: list) -> None:
        with mss.MSS() as sct:
            at_mark = np.asarray(sct.grab(_menu_area(sct.monitors[1])))[:, :, :3]
        folder = save_mark(MARKS_DIR, number, marked_at, regions, at_mark)
        print(f"mark {number}: saved {len(regions) + 1} screen regions to {folder}")

    # --- pause ---

    def toggle_pause(self) -> None:
        """Pause or resume. The pause hotkey and the Tray Icon's menu both come here, on their
        own threads, so the two always agree and the Tray Icon follows either."""
        with self._pause_lock:
            self.router.paused = not self.router.paused
            held = None
            if self.router.paused:
                # The workers see their watch is gone and exit. A Trigger Key still held is
                # given back to the game.
                held = self.router.end_watch("paused")
                self.router.end_terminal_watch("paused")
            if held is not None:
                self._spawn(self._hand_back, held, sends=True)
            self._tone(440 if self.router.paused else 880, 120)
            print("paused" if self.router.paused else "resumed")
        self.on_pause_change()


def _menu_area(monitor: dict) -> dict:
    """The top-left screen region the reader needs."""
    width, height = region_size(monitor["height"])
    return {"left": monitor["left"], "top": monitor["top"], "width": width, "height": height}


def _open_log(log: Callable[[str], None]) -> None:
    """Open the event log in the default viewer. Runs on the Tray Icon's thread."""
    try:
        os.startfile(LOG_PATH)
    except OSError as error:
        log(f"Open log failed: {error!r}")
        print(f"  Warning: could not open {LOG_PATH}: {error}")


def _start_tray(app: App, log: Callable[[str], None]) -> tray.TrayIcon | None:
    """Show the Tray Icon, or say why not: losing it must not lose the keyboard."""
    try:
        running = tray.load_icon()
        icon = tray.TrayIcon(
            paused=lambda: app.router.paused,
            toggle_pause=app.toggle_pause,
            open_log=lambda: _open_log(log),
            quit=app.stop,
            running_image=running,
            paused_image=tray.greyed(running),
        )
        icon.start()
    except Exception as error:
        log(f"Tray Icon failed to start: {error!r}")
        print(f"  Warning: the Tray Icon failed to start ({error!r}); Ctrl+C here still quits.")
        return None
    app.on_pause_change = icon.refresh
    return icon


def main() -> None:
    settings = load(ROOT / "settings.toml", ROOT / "codebook.toml")
    log = EventLog(LOG_PATH)
    app = App(settings, log.write)
    with mss.MSS() as sct:
        monitor = dict(sct.monitors[1])
    height = monitor["height"]
    print(f"Stratagem Caller running. Screen height {height}.")
    if height != REFERENCE_HEIGHT:
        print(f"  Warning: only tested at {REFERENCE_HEIGHT}; Trigger Keys may not read the menu.")
    print(f"  Call Key [{settings.call_key}] then {', '.join(settings.trigger_keys)} for Slots")
    print(f"  Use Key [{settings.use_key}] at a Terminal, then Terminal Key [{settings.terminal_key}] (beeps for now: the Code is not read yet)")
    for key, code in settings.direct_keys.items():
        print(f"  Direct Key [{key}] -> {code}")
    print(f"  [{settings.pause_key}] pause/resume, [{settings.mark_key}] mark something unexpected, Ctrl+C here to quit")
    print(f"  Logging Trigger Keys and Calls to {LOG_PATH}")
    print(f"  Overlay (Key Caps beside each Slot and a ready heading while the menu is open): {'on' if settings.overlay_enabled else 'off'}")
    app.start_overlay(monitor)
    tray_icon = _start_tray(app, log.write)
    try:
        keyboard.hook(app.on_event, suppress=True)
        keyboard.add_hotkey(settings.pause_key, app.toggle_pause)
        keyboard.add_hotkey(settings.mark_key, app.mark)
        # Ctrl+C here and Quit in the Tray Icon's menu both end up in the shutdown below.
        while not app.quit_requested:
            time.sleep(0.2)
    except KeyboardInterrupt:
        pass
    finally:
        if tray_icon is not None:
            tray_icon.stop()
        app.shutdown()
        log.close()
