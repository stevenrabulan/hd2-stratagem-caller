# 06: Read the Code with any reticle over an arrow

**What to build:** The weapon's reticle sits at the centre of the screen, and at most Terminals that is on top of an arrow. Today the reader treats the pink reticle's disc as something to look past, so the arrow under it breaks into pieces too small to count. The Code then reads as unevenly spaced (a beep), even though nothing hides it from the player. Reticles differ by weapon (rings, dots, crosshairs, chevrons, in several colours), so the fix must not depend on the reticle's shape or colour: for example, treat a small zone at the screen's centre as unknown, join the pieces of an arrow across it, and look past it when fitting the arrow's shape. The same frames show a second problem: at a steep angle the nearest arrow is up to three times the area of the farthest, outside the 0.6 to 1.6 times the median that `AREA_SPREAD` allows, so the end arrows drop out. The rule stays: read every arrow or say unreadable, never a shortened or wrong Code.

**Found:** 2026-10-18, one Upload Data mission. Eight Terminal Key presses beeped at a log-in and an Eject Hard Drive Terminal (`logs/failed_codes/`); the ninth read the Code. A scratch prototype that bridges the pink reticle's disc and widens the area spread to 0.4 to 2.5 read four of the eight and changed no existing fixture.

**Blocked by:** none

**Status:** ready-for-agent

- [ ] The four `code_area/` fixtures in `NOT_READ_YET` read correctly (remove each from the set as it passes; the tests are strict xfails)
- [ ] `test_any_reticle_over_the_middle_arrow_still_reads` passes for every kind: grey crosshair, green dot, orange chevron, wide white ring (remove its xfail marks)
- [ ] A reticle below the row, or on an empty screen, changes nothing (tests already pass; keep them passing)
- [ ] The arm hiding the first arrow still gives unreadable, and no fixture gives a wrong or shortened Code
- [ ] Every existing fixture and test still passes, and a Reading still costs about what it does now (note the number)
- [ ] (player) In-game: `1` enters the Code at a log-in Terminal with the reticle on an arrow, with two different weapons

## Notes

- The finger frame refuses today because of a bright stub before the first arrow (the fingertip). Reading it is wanted but not at the cost of the hand rule: if it cannot be told apart from a hidden arrow, leave it unreadable and say why here.
- Not explained by this ticket: extraction terminals failed live on 2026-10-17 with "no row of arrows", yet Steam screenshots of the same moments read fine. Those reads came before failed frames were saved. The next live failure at an extraction terminal saves its frame; compare it with `extraction_*.png`.
