# 01: Key Caps show beside each Slot while the Arming Window is open

**What to build:** The Overlay, end to end, with Key Caps only. While the tool has confirmed the Stratagem Menu open, a yellow Key Cap showing each Slot's Trigger Key sits left of that Slot's Icon. Every Slot with an Icon in place gets one, callable or not. The Key Caps hide when a Call starts typing, when the Call Key is pressed to close the menu, on focus loss, on pause, when the safety limit ends the watch, and when the menu is confirmed closed. They stay up while the watch is in doubt. `[overlay] enabled = true` in `settings.toml` turns it on; off means no window is created and Trigger Keys work as before. See "Implementation Decisions" in the spec, and user stories 1 to 5, 7 to 9 and 12 to 16.

The Overlay is a click-through, always-on-top window that never takes focus, drawn with per-pixel transparency through Win32 and OpenCV. The prototype on branch `prototype/overlay` (`tools/prototype_overlay.py`) has working window code, the Key Cap drawing (style "yellow") and the geometry. In-game it showed no focus loss and no stutter once it redrew only on change. Reuse what fits; it is not production code.

The reader has to report which Slots show an Icon, not just the callable ones: today a Reading only carries Icons for Slots with a Code.

**Blocked by:** none

**Status:** ready-for-human

- [x] A Reading reports every Slot whose Icon is in place, including Slots on cooldown; tested on the menu fixtures
- [x] Given scripted Readings and key presses, the router/Arming Window says when Key Caps show and on which Slots, covering each show/hide rule above
- [x] A Key Cap shows the configured Trigger Key's name (Slot 10 shows `0` by default); a Slot without a Trigger Key gets none
- [x] Key Caps are redrawn only when what they show changes
- [x] Test, run with the normal suite: Key Caps painted on every menu fixture leave each Reading unchanged
- [x] No Overlay pixel is pure white, and nothing is drawn at x >= 98 (at 3840x2160) in the Key Cap column
- [x] `[overlay] enabled = false` creates no window
- [x] README: the Overlay is built, with its setting; the Status line no longer says it is not built
- [ ] (player) Confirmed in-game with the tool alone: Key Caps visible, game keeps focus, no stutter

## Comments

**Hand-back (2026-10-15).** Everything except the in-game box is done and tested here (macOS; 255 tests pass). The Win32 window has never been run: it is a port of the prototype's window code, so it needs a check on Windows.

What was built:
- `reader.py`: `Reading.icons` now holds every Slot whose Icon is in place (cooldown Slots included), not just callable ones. Tested on the fixtures.
- `arming.py`: `ArmingWindow.key_cap_slots()`; `router.py`: `KeyRouter.key_caps()` (Slot -> Trigger Key name; empty when hidden). Hidden at once on focus loss and pause, not only when the watch ends.
- `keycaps.py`: pure drawing (yellow style from the prototype) to a premultiplied BGRA frame. `overlay.py`: polls `key_caps()` at 30 Hz, redraws only on change; `start_overlay` creates nothing when disabled. `layered_window.py`: the Win32 window, imported only when the Overlay is on.
- `[overlay] enabled` in `settings.toml` (default true; a missing section means on).
- Overlay-can't-change-a-Reading test: caps for the listed Slots and for all ten Slots painted on every menu fixture; codes, unreadable, menu_open and Icon pixels unchanged.

Judgement calls:
- Key Caps come from the latest confirmed-open Reading's Icons and are kept unchanged while the watch is in doubt. A Slot whose Icon edge fails for one Reading drops its Key Cap and returns; not latched. Revisit if it flickers in-game.
- A Call Key press while the watch is in doubt hides the Key Caps until the menu is confirmed open again (the press resets what was trusted).
- Long key names are shortened (`page down` shows `PGDN`, a few others) and shrunk to fit; every name is upper case.
- Two Trigger Keys for one Slot: the first in settings order is shown.
- If the Overlay thread fails, it logs, prints a warning and stops; Trigger Keys carry on.
- Left for tickets 02 and 03: `Overlay.tick` compares one "what to draw" value (add red Slots there); the heading needs a second window and a per-window fade, which `LayeredWindow.show` does not have yet (alpha fixed at 255); the router reports no beeps yet.

To check on Windows (the unticked box): run the tool alone in-game with borderless fullscreen and HDR, open the menu with the Call Key, and confirm Key Caps appear left of each Icon (cooldown Slots too, Slot 10 shows `0`), the game keeps focus and mouse, no stutter, and Key Caps vanish on a Call, on the Call Key closing the menu, on Alt+Tab and on pause (`Ctrl+Alt+P`). If the window does not appear, the terminal warns and the log has an "Overlay stopped" line naming the Win32 call that failed.
