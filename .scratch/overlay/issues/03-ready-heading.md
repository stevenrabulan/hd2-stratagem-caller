# 03: STRATAGEM CALLER READY heading pulses while the Key Caps show

**What to build:** STRATAGEM CALLER READY, uppercase, in the game's yellow (#FFE900) with a soft glow, on the line of the game's STRATAGEMS header just right of it. It shows and hides at exactly the same moments as the Key Caps. It is drawn once into its own small window, and the whole heading pulses by fading that window's opacity about once every 1.2 s, so nothing is redrawn per frame. See "Ready heading" in the spec, and user story 6.

The prototype on branch `prototype/overlay` has the heading drawing, its placement and the opacity pulse (`set_alpha`).

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] The heading shows and hides with the Key Caps
- [ ] Pulsing changes only the window's opacity; the picture is sent once per showing
- [ ] The Overlay-can't-change-a-Reading test covers the heading
- [ ] (player) Confirmed in-game: heading readable, no stutter
