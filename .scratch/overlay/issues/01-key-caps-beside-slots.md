# 01: Key Caps show beside each Slot while the Arming Window is open

**What to build:** The Overlay, end to end, with Key Caps only. While the tool has confirmed the Stratagem Menu open, a yellow Key Cap showing each Slot's Trigger Key sits left of that Slot's Icon. Every Slot with an Icon in place gets one, callable or not. The Key Caps hide when a Call starts typing, when the Call Key is pressed to close the menu, on focus loss, on pause, when the safety limit ends the watch, and when the menu is confirmed closed. They stay up while the watch is in doubt. `[overlay] enabled = true` in `settings.toml` turns it on; off means no window is created and Trigger Keys work as before. See "Implementation Decisions" in the spec, and user stories 1 to 5, 7 to 9 and 12 to 16.

The Overlay is a click-through, always-on-top window that never takes focus, drawn with per-pixel transparency through Win32 and OpenCV. The prototype on branch `prototype/overlay` (`tools/prototype_overlay.py`) has working window code, the Key Cap drawing (style "yellow") and the geometry. In-game it showed no focus loss and no stutter once it redrew only on change. Reuse what fits; it is not production code.

The reader has to report which Slots show an Icon, not just the callable ones: today a Reading only carries Icons for Slots with a Code.

**Blocked by:** none

**Status:** ready-for-agent

- [ ] A Reading reports every Slot whose Icon is in place, including Slots on cooldown; tested on the menu fixtures
- [ ] Given scripted Readings and key presses, the router/Arming Window says when Key Caps show and on which Slots, covering each show/hide rule above
- [ ] A Key Cap shows the configured Trigger Key's name (Slot 10 shows `0` by default); a Slot without a Trigger Key gets none
- [ ] Key Caps are redrawn only when what they show changes
- [ ] Test, run with the normal suite: Key Caps painted on every menu fixture leave each Reading unchanged
- [ ] No Overlay pixel is pure white, and nothing is drawn at x >= 98 (at 3840x2160) in the Key Cap column
- [ ] `[overlay] enabled = false` creates no window
- [ ] README: the Overlay is built, with its setting; the Status line no longer says it is not built
- [ ] (player) Confirmed in-game with the tool alone: Key Caps visible, game keeps focus, no stutter
