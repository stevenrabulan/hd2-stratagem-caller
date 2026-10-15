# 02: A Key Cap flashes red when its Trigger Key beeps

**What to build:** Whenever a Trigger Key earns a beep, for any reason (not callable, unreadable too long, beyond the end of the menu), that Slot's Key Cap fill turns red three times in about 0.6 s (100 ms red, 100 ms normal). The beep sound is unchanged. A Slot with no Key Cap (beyond the end of the menu) gets the beep only. A second beep during a flash restarts it. See "Red flash" in the spec, and user stories 10 and 11.

The prototype on branch `prototype/overlay` has the flash timing and red drawing.

**Blocked by:** 01

**Status:** ready-for-human

- [x] Given scripted Readings and key presses, a beep reports which Slot's Key Cap to flash
- [x] The flash shows red, normal, red, normal, red, normal, then stays normal
- [x] A beep for a Slot beyond the end of the menu flashes nothing
- [x] The Overlay-can't-change-a-Reading test covers red Key Caps
- [ ] (player) Confirmed in-game: pressing a Slot on cooldown beeps and flashes its Key Cap

## Comments

**Hand-back (2026-10-15).** Everything except the in-game box is done and tested here (macOS; 284 tests pass). The red fill has never been seen on Windows.

What was built:
- `flash.py` (new, pure): `red_slots(flashes, now)` says which Slots are in a red step. Red, normal, red, normal, red, normal over 0.6 s, then normal. Time is passed in, so no test sleeps. Step edges are exact despite float error (0.3 / 0.1).
- `router.py`: `KeyRouter.finish` notes a flash for the Slot of a beeping Trigger Key, for both beep paths (a beep decided at once, and a Slot that stayed unreadable too long). Only a Slot that has a Key Cap flashes, so a Trigger Key beyond the end of the menu beeps and flashes nothing. A second beep restarts that Slot's flash. `KeyRouter.red_key_caps()` reports the red Slots now, only among Key Caps that are showing. A new watch starts with no flashes.
- `keycaps.py`: `render_key_caps(names, height, red=...)` fills the red Slots' Key Caps red (never pure white); shape, glyph and bar unchanged.
- `overlay.py`: `Overlay` and `start_overlay` take `red_key_caps`; "what to draw" is now (Key Caps, red Slots among them), redrawn only when that changes. One flash is six redraws.
- `app.py`: passes `router.red_key_caps` to the Overlay. The beep (`winsound.Beep(330, 150)`) is untouched.
- README: Overlay text mentions the flash. GLOSSARY: added Beep and Flash.
- Tests: `tests/test_flash.py`; router (both beep paths, beyond the menu's end, restart, two Slots, hidden, no carry-over to the next watch); keycaps (red fill, same shape, no white); overlay (redraw on change only, a flash is six draws); the Overlay-can't-change-a-Reading test now also paints one red and all-red Key Caps on every menu fixture.

Judgement calls:
- The router owns the flash clock (its injected clock), so the Overlay only polls "which Slots are red now" and needs no clock.
- A flash is dropped when a new watch starts; a second Call Key press inside one watch does not clear it (the Key Caps are hidden then anyway).
- The flash is noted when the beep is reported to the router (`finish`), a moment before the sound thread starts; no deliberate delay.
- Red fill is (R 215, G 40, B 40), from the prototype.
- Review (standards and spec axes) applied: `start_flash` in `flash.py` owns adding and pruning flashes; the flash length is derived from step and count; a tautological duration test was dropped.
- Review points left as they are: `red_key_caps` returns Slots, though its name says Key Caps (follows the spec's wording); "only a shown Key Cap flashes" is checked in the router, the Overlay and the drawing, deliberately redundant because each is a separate seam; `key_caps` and `red_key_caps` stay two callables (a small state type is a later tidy). A Trigger Key pressed in the instant between a beep being decided and reported would flash its own Slot instead (an old race in `finish`, rare and cosmetic).

To check on Windows (the unticked box): run the tool in-game, open the menu with the Call Key, press the Trigger Key of a Slot on cooldown, and confirm it beeps and that Slot's Key Cap flashes red three times, about 0.6 s in all. Also press the Trigger Key `0` when the menu has fewer than ten Slots: it beeps and nothing flashes. Press the same key twice quickly: the second press restarts the flash.
