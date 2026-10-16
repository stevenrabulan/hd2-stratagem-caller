# A bright background makes clean Slots unreadable, or lets a shortened Code through

Status: ready-for-human

## Problem

Player report, mission on 2026-10-13 (evening): Trigger Key 3 for Slot 3 (Orbital 120mm HE Barrage, Code RRDLRD) failed "pretty consistently", while it worked at other times.

The log (`logs/stratagem_caller.log`, git-ignored) shows Slot 3, often with 4 and 5, reported unreadable on menus that were open and settled:

- 22:27:50.655 taken, latest Reading `Slots 6; unreadable 3`. Beep 1.2 s later, then a retry Called RRDLRD at 22:27:52.990. Slot 3 was flickering between readable and unreadable.
- 22:32:56 to 22:33:52: Readings `Slots 1,6; unreadable 3,4,5`.
- 22:35:08 to 22:35:15: beeps with `unreadable 3,4,5` or `unreadable 4`. At 22:35:11 the same menu read `Slots 2,3,4,5` cleanly.

No screenshots were saved during that mission, so its frames cannot be checked directly. The 834 captures from 2026-10-12 in `fixtures/raw/` (git-ignored) show the same failure: 35 frames of an open menu have unreadable Slots.

## Cause (confirmed on real captures)

`reader._slots_overlapped` decides which arrow lines a bright, non-arrow blob covers from the blob's **bounding box**, and skips the blob entirely if the box's **left edge** is left of the arrows. Bright scenery (sky, snow, fog, explosions) behind the semi-transparent menu forms one large irregular white blob. That causes two failures:

1. **Clean Slot reported unreadable.** A blob whose pixels sit to the right of the menu, or below the arrows, has a bounding box spanning several Slot lines. Every Slot in that span with a Code is marked unreadable, although no bright pixel touches its arrows. Examples:
   - `20261012-012244_press109_*`: sky right of the menu, box x 480–800, y 28–732. Resupply (DDUR, Slot 2) unreadable in all three shots.
   - `20261012-011934_press077_500ms`: light top right, box x 559–800, y 238–618. Orbital Laser (RDURD, Slot 4) unreadable.
   This fits "Slots 3, 4 and 5 unreadable together, depending on where the camera points".
2. **Shortened Code returned (worse).** When white fog swallows the last arrows of a Code and the fog reaches further left than the arrows, the blob is ignored and the visible arrows are returned as the full Code. `20261012-015556_press246_500ms`: Resupply read as `DD` instead of DDUR. A Call would type DD.

The 0.75 s `UNREADABLE_LIMIT` in `arming.py` is working as designed: the Slot really is reported unreadable for that long.

## Fix

Judge clutter by its **pixels on the arrow line**, not its bounding box. For a Slot with arrows, it is unreadable if any bright pixel that is not a recognised arrow (from a blob of at least 20 px at 4K) lies on its arrow line, from the left edge of arrow position 0 to the right edge of the position after its last arrow. Clutter further right cannot hide part of the Code, because a Code has no gaps. Clutter left of position 0 cannot either. The clutter check runs before the gap check, so an arrow hidden by a marker ("S1", "B2") makes the Slot unreadable (wait), not "not callable" (instant beep).

Checked on all 834 raw captures. Every changed result was inspected by eye:

- now read correctly: press048, 077, 108, 109 (×3), 193;
- now correctly unreadable instead of a shortened Code: press246 (Resupply `DD`);
- now unreadable instead of silently "not callable": press210/211 (a "B2" marker over Patriot's first arrow), press253 (a lightning bolt over Resupply's first arrow).

## Wanted

- [ ] Regression fixtures cut from the raw captures above, with tests: clean Code next to a bright blob is read; fog over the last arrows gives unreadable, never a shortened Code.
- [ ] All existing reader tests still pass.
- [ ] Confirmed by the player in a mission before merging.

## Comments

**Fixed on branch `claude/nifty-satoshi-15110e`, not merged (2026-10-13).** `reader._slots_overlapped` (bounding box) is replaced by `_cluttered` (pixels on the line, up to the position after the last arrow). Clutter needs at least `CLUTTER_PIXELS` (10 at 4K) on the line. One frame (press204, 100 ms) had 1–2 pixels of a blob grazing Slot 9's line; real clutter in the captures is 21 px or more, and an arrow is about 450.

- New fixtures: `bright_sky_beside_menu`, `bright_light_above_short_code`, `fog_over_last_arrows`, `marker_over_first_arrow`, cut from the 2026-10-12 raw captures. Their 4 tests failed before the fix (including Resupply read as `DD`) and pass after. Full suite: 165 passed.
- Across all 834 raw captures, the reader's output is identical to the output inspected frame by frame above.
- Reading time goes from ~110 ms to ~117 ms; see issue 04 for the 110.

**More evidence (2026-10-14, from the Overlay prototype session):** in `fixtures/raw/prototype_overlay_20261014-003908.png` and `-003912.png`, a red map ping sits on Resupply's 4th arrow (Slot 2). Both the old and the fixed reader report Slot 2 unreadable, which is correct: the arrow is hidden. Four seconds later (`-003922`) the ping is gone and Slot 2 reads DDUR. Slot 3 (RRDLRD) reads in all three frames; the ping's distance label sits between the lines. So pings and markers on an arrow line are a second, legitimate source of unreadable Slots. They last as long as the ping does, and a beep there is the right outcome. Added as fixture `ping_over_last_arrow` with a test: unreadable, never `DDU`.

**Merged 2026-10-14 into `trigger-keys-while-menu-open` without an in-mission test, at the player's request.** The in-mission check below is still open.

**Needs the player:** play a mission on a bright map (snow, desert, open sky behind the menu) and confirm Slots no longer go unreadable with nothing on their arrows. If a Slot still beeps, send the log time; issue 03 would make it leave a screenshot behind.
