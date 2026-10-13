# 02: A Reading reports whether the Stratagem Menu is open

**What to build:** A Reading says whether the Stratagem Menu is open, separately from which Slots are callable. A menu in which every Stratagem is on cooldown is open with no callable Slots. A Reading of an open menu also lets its user tell a Slot beyond the end of the menu from one inside it only if that falls out naturally; both earn a beep, so it is not required. See "A Reading reports whether the menu is open" in the spec.

How the reader recognises an open menu is to be established against the fixtures; the menu's header and its column of Icons are the obvious candidates. It must hold up with bright scenery behind the menu.

A fixture for an open menu with nothing callable has to be found in the raw captures, cropped the same way as the existing fixtures, and saved with them. The raw captures are not in version control: they are only in the `fixtures/raw/` directory of the main checkout, not in a worktree. If no such frame exists there, say so in this ticket's comments and cover the case with the closest frame available.

**Blocked by:** 01

**Status:** resolved

- [ ] Every existing fixture of an open, settled menu reports open
- [ ] An open menu with nothing callable reports open, with no Codes
- [ ] The closed-menu-over-bright-sky fixture reports closed
- [ ] The glow fixture reports open
- [ ] What the reader reports for a menu still sliding in is decided, tested and written in this ticket's comments
- [ ] The detection is checked against the raw captures and the result (how many agree, any that do not) is written in this ticket's comments
- [ ] Every existing reader test still passes


## Comments

**How a Reading says the menu is open.** `Reading.menu_open` (bool, default False). It is true when four or more neighbouring Slots show their Icon square in its place (all four edges sharp against what is behind it), or when Slot 1 has a Code (a dead player's menu lists only Reinforce, with its Code). The header is not used: it is still partly visible while the menu closes over a bright sky. Icon squares are checked, not their art, so cooldown, dimmed and entered Slots all count.

**What the game shows when the menu is not open.** Besides "gone", the game shows a collapsed header with only the Reinforce Icon and its count, and flashes up single rows (a cooldown ending, "Ready", "Activating", a mission Stratagem such as Upload Data with its arrows) beside it without the menu being open. These are reported as not open. Fixture `closed_menu_one_row_showing` is one.

**Decision: a menu still sliding in reports `menu_open = False`.** Its Icons are not in place yet (rows slide in from the left), so the next ticket should treat "not open" right after the Call Key as "still opening", as the spec says. Settled-open is reported as soon as four neighbouring Icons are in place, which is about the same moment the Slots become readable. Tested with `menu_sliding_in` and `lone_arrow_while_sliding_in`.

**Fixtures added** (800x1500 top-left crops of raw captures): `open_menu_nothing_callable` (every Stratagem on cooldown, from press061 at 500 ms), `open_menu_only_reinforce` (dead player, from press053 at 250 ms), `closed_menu_one_row_showing` (from press144 at 500 ms). A real "open with nothing callable" frame existed in the raw captures; many did.

**Check against the raw captures (834 frames, not 835).** Reported open: 54 of 278 at 100 ms, 174 of 278 at 250 ms, 192 of 278 at 500 ms. No frame with two or more Codes is reported closed. I looked at every 500 ms frame that has fewer than two Codes (about 150 frames, as contact sheets) and judged them by eye:
- Reported open with no Code (32): all are genuinely open menus, nearly all with every Stratagem on cooldown.
- Reported closed with no Code (84): all correctly closed (collapsed header, a flashed row, loading screens, no menu), except:
  - press049 (500 ms), an open menu behind a large fire; the fire hides the Icon edges. Not detected: one open frame wrongly reported closed. The same press is open at 250 ms.
  - Three frames (times 014420, 015601, 015719) mid-animation, with rows a few pixels off their places as they slide in or out. Not open until the Icons settle.
  - A menu showing only a Reinforce row with "Ready" or "Activating" and no Code is reported closed. These look like the game's flashed rows, not the menu, so I believe that is right, but I could not prove it from stills.
- Reported closed with exactly one Code (2): both are flashed rows (Upload Data; Resupply). Correct.
- One 100 ms frame was falsely open with three neighbouring Icon-like edges from scenery; requiring four removed it, and nothing else changed.
Not checked frame by frame: the 100 ms and 250 ms frames with no Codes (only the 100 ms frames that were reported open).

All 108 tests pass, including every existing reader test.

**Resolved 2026-10-13.** Merged into `trigger-keys-while-menu-open` as 337c29e. Code review fixes that touch this ticket are in d003bd4; see "Code review fixes" in the spec. Not yet confirmed in-game.
