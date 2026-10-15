# 01: A missed Trigger Key flashes and beeps twice, in step

**What to build:** When a Trigger Key earns a Beep, for any reason (not callable, unreadable too long, beyond the end of the menu), the player hears two short tones (330 Hz, about 120 ms each) and that Slot's Key Cap turns red twice: 150 ms red, 150 ms normal, 150 ms red, 150 ms normal. Each tone starts as a red step starts. The flash module owns this one schedule, both the red steps and the tone starts, so the two can't drift apart. A Slot with no Key Cap only hears the tones. Pressing again while a double pulse is running restarts the flash and the tones, and drops any tone left over from the earlier press. The pause and mark beeps are unchanged. See "Flash and Beep share one schedule", "Restart rule" and user stories 1 to 11 in the spec.

**Blocked by:** None (can start immediately)

**Status:** ready-for-human

- [x] The flash is red, normal, red, normal, then stays normal, with steps changing at multiples of 0.15 s (float-error guard kept)
- [x] The flash module says a Beep's tones start at 0 s and 0.3 s, and at no other time
- [x] Nothing is red and no tone is due before a flash begins; each Slot keeps its own clock; starting a Flash for a Slot restarts it
- [x] Every kind of Beep plays both tones, on a thread that never holds up the keyboard hook or the reading loop
- [x] A Beep that is no longer the latest one drops its second tone
- [x] The README's Overlay text says two reds in step with two tones
- [ ] (player) Confirmed in-game: pressing a Slot on cooldown gives two reds in step with two tones; pressing it twice quickly never gives more than two tones in a row

## Comments

**Hand-back (2026-10-15).** Everything except the in-game box is done and tested on Windows (346 tests pass, no real tones played: the tone player is faked). Two reds in step with two tones has not been heard or seen in-game.

What was built:
- `flash.py`: now 4 steps of 0.15 s (`FLASH_STEP`, `FLASH_COUNT = 2`), float-error guard kept. New `tone_starts(started)` returns the tone start times (0 s and 0.3 s after the start), derived from the same constants as the red steps.
- `beep.py` (new): `DoubleBeep(tone=...)`. `play()` returns at once; a thread sounds 330 Hz / 120 ms at each `tone_starts` time. A counter marks the latest Beep; before each tone a Beep checks it is still the latest and drops the tone if not. Clock, sleep, spawn and tone player are injectable.
- `app.py`: a BEEP outcome calls `DoubleBeep.play()` (real `winsound.Beep` as the player). Pause and mark beeps untouched.
- `router.py` needed no change: it still starts the Flash per Slot in `finish()` (restart per Slot, new watch drops it).
- README: Overlay text, Status line and the beep bullet describe two reds with two tones.
- Tests: `test_flash.py` (schedule, tone starts, float guard, per-Slot clocks), `test_beep.py` (new: two tones 0.3 s apart, restart drops the old second tone, tones never overlap, `play()` does not wait), `test_router.py` and `test_overlay.py` updated to two reds (four draws).

Judgement calls:
- Added `beep.py` as a small unit with injected sound so the restart rule is tested, rather than leaving it hand-checked as the spec allowed.
- Tones are serialised with a lock, so a restart during a tone waits for it to end (at most 120 ms) instead of two `winsound.Beep` calls overlapping. Cost: a restarted first tone can start up to ~120 ms late.
- The Beep's start time is taken when `play()` runs, a few ms after the router starts the Flash (not the same instant), per the spec's "within a few milliseconds".
- Tones left over are not dropped by a new watch (the spec only says a new press does it).

To check in-game (the unticked box): press a Trigger Key for a Slot on cooldown and confirm two reds with two tones in step over the game's audio; press it twice quickly and confirm never more than two tones in a row, the second press restarting from its own red. Also try a Slot beyond the end of the menu (two tones, no flash).
