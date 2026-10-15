import threading

import pytest

from stratagem_caller.beep import DoubleBeep, TONE_HZ, TONE_MS


class Room:
    """A fake clock, a fake sleep that moves it, and a tone player that writes down what it was asked.
    Beeps run on the caller's thread, so a test can play again at any moment a beep waits."""

    def __init__(self):
        self.now = 10.0
        self.tones = []  # (time, hz, ms)
        self.on_wait = None
        self.beep = DoubleBeep(tone=self._tone, clock=lambda: self.now, sleep=self._sleep, spawn=lambda run: run())

    def _tone(self, hz, ms):
        self.tones.append((self.now, hz, ms))

    def _sleep(self, seconds):
        self.now += seconds
        if self.on_wait is not None:
            hook, self.on_wait = self.on_wait, None
            hook()


def test_a_beep_sounds_two_short_tones_0_3_seconds_apart():
    room = Room()
    room.beep.play()
    assert room.tones == [
        (pytest.approx(10.0), TONE_HZ, TONE_MS),
        (pytest.approx(10.3), TONE_HZ, TONE_MS),
    ]
    assert (TONE_HZ, TONE_MS) == (330, 120)


def test_playing_again_while_the_second_tone_is_due_restarts_the_beep_and_drops_the_old_second_tone():
    room = Room()
    room.on_wait = room.beep.play  # a second press while the first beep waits for its second tone
    room.beep.play()
    # The old beep's second tone (10.3) never sounds; the new beep's tones start from the second press.
    assert [at for at, _, _ in room.tones] == pytest.approx([10.0, 10.3, 10.6])


def test_the_next_beep_after_one_has_finished_sounds_both_its_tones():
    room = Room()
    room.beep.play()
    room.now += 5
    room.beep.play()
    assert len(room.tones) == 4


def test_play_returns_while_a_tone_still_sounds_and_tones_take_turns():
    # Real threads, fake sound: play() must not wait for the tones, and tones take turns.
    started, release = threading.Event(), threading.Event()
    sounding, overlaps = [], []

    def tone(hz, ms):
        if sounding:
            overlaps.append(True)
        sounding.append(True)
        started.set()
        release.wait(2)
        sounding.pop()

    threads = []

    def spawn(run):
        threads.append(threading.Thread(target=run, daemon=True))
        threads[-1].start()

    beep = DoubleBeep(tone=tone, clock=lambda: 0.0, sleep=lambda seconds: None, spawn=spawn)
    beep.play()
    assert started.wait(2)  # the first tone is playing and play() has already returned
    beep.play()
    release.set()
    for thread in threads:
        thread.join(2)
    assert overlaps == []
