# 03: STRATAGEM CALLER READY heading pulses while the Key Caps show

**What to build:** STRATAGEM CALLER READY, uppercase, in the game's yellow (#FFE900) with a soft glow, on the line of the game's STRATAGEMS header just right of it. It shows and hides at exactly the same moments as the Key Caps. It is drawn once into its own small window, and the whole heading pulses by fading that window's opacity about once every 1.2 s, so nothing is redrawn per frame. See "Ready heading" in the spec, and user story 6.

The prototype on branch `prototype/overlay` has the heading drawing, its placement and the opacity pulse (`set_alpha`).

**Blocked by:** 01

**Status:** ready-for-human

- [x] The heading shows and hides with the Key Caps
- [x] Pulsing changes only the window's opacity; the picture is sent once per showing
- [x] The Overlay-can't-change-a-Reading test covers the heading
- [ ] (player) Confirmed in-game: heading readable, no stutter

## Comments

**Hand-back (2026-10-15).** Everything except the in-game box is done and tested here (macOS; 340 tests pass). The heading window and its fade have never run on Windows.

What was built:
- `heading.py` (new, pure): `render_heading(height)` draws STRATAGEM CALLER READY in #FFE900 with a soft glow, once, as a premultiplied BGRA picture; `heading_box(height)` gives its window box (text starts at x=410, centred on y=91 at 4K, as in the prototype; everything scales with screen height); `pulse_opacity(elapsed)` gives the window opacity (110 to 255, one cycle every 1.2 s, full when it appears). No clock, no window.
- `overlay.py`: the Overlay now owns two windows (Key Cap column, then heading strip) and takes an injectable `clock`. The heading shows exactly when there are Key Caps (the same `key_caps()` value, same tick, no second rule). On appearing it sets opacity, then sends the picture once; after that each tick only calls `set_opacity` (and only when the value changed). Hiding hides both in the same tick. If the second window cannot be made, the first is closed.
- `layered_window.py`: `LayeredWindow.set_opacity(0..255)` fades the whole window with a blend-only `UpdateLayeredWindow` (no picture, no position); the value is kept for the next `show`.
- Tests: `tests/test_heading.py`; overlay tests (picture sent once per showing, opacity only while pulsing, no Key Cap redraws from the pulse, hide in step, fresh pulse per showing, no calls while hidden); the Reading-safety test now paints the heading at its real position, and with every Key Cap (one red) plus the heading at full and faintest opacity, on every menu fixture.
- README, GLOSSARY (Ready Heading), settings.toml comment, startup text; spec Status set to ready-for-human (not resolved).

Judgement calls:
- Pulse is a cosine from the moment the heading appears (full opacity first, dips at 0.6 s), not the prototype's sine of absolute time, so each showing starts the same.
- Opacity swings 110 to 255 (the prototype's values). Spec text said "about once a second"; changed to 1.2 s to match this ticket.
- The heading is drawn as coverage and turned into colour at the end, so no pixel's colour exceeds its alpha. (Drawing text straight onto a BGRA image with OpenCV gave edge pixels brighter than their alpha, which Windows would render too bright.)
- The heading shows iff there are Key Caps, so a confirmed-open menu with no listed Slot shows neither.
- The heading box runs past the reader's 800 px region (to about x=910) and sits entirely above the first Icon row (y<162), so the safety test crops it to the region; it touches no pixel the reader checks.
- One `pump` per tick serves both windows (Windows queues messages per thread).
- Shared `YELLOW` from `keycaps.py`.
- Review applied: `pytest.raises`, tuple-compare bug in a test, `paint` clips only when asked, renamed `_window` to `_key_cap_window`, second window closed even if the first close fails, dead `max(0, ...)` removed, constant-restating test dropped.
- Review points left: the two windows are separate Win32 calls, so up to one tick of skew between Key Caps and heading is possible. Overlay now holds two small state machines (a `HeadingPane` collaborator is a later tidy). `screen_height <= 0` is not validated (same as keycaps). Existing, not touched: 94 Key Cap anti-aliased edge pixels have colour above alpha (from `cv2` drawing on BGRA); not a Reading risk (blue channel stays low), but could be redrawn the way the heading now is.

To check on Windows (the unticked box): run the tool in-game (borderless, HDR), open the menu with the Call Key, and confirm STRATAGEM CALLER READY appears just right of the STRATAGEMS header in yellow with a soft glow, fades down and up about once every 1.2 s, is readable, and causes no stutter. It must vanish together with the Key Caps (Call starts, Call Key closes the menu, Alt+Tab, pause). If it sits on the wrong line or overlaps the header, adjust `TEXT_LEFT` / `TEXT_MIDDLE` in `stratagem_caller/heading.py`. If the fade does not show, the blend-only `UpdateLayeredWindow` call in `LayeredWindow.set_opacity` is the place to look; the terminal warns and the log has an "Overlay stopped" line if a Win32 call fails.
