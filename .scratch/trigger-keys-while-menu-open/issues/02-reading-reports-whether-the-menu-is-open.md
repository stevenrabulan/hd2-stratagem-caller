# 02: A Reading reports whether the Stratagem Menu is open

**What to build:** A Reading says whether the Stratagem Menu is open, separately from which Slots are callable. A menu in which every Stratagem is on cooldown is open with no callable Slots. A Reading of an open menu also lets its user tell a Slot beyond the end of the menu from one inside it only if that falls out naturally; both earn a beep, so it is not required. See "A Reading reports whether the menu is open" in the spec.

How the reader recognises an open menu is to be established against the fixtures; the menu's header and its column of Icons are the obvious candidates. It must hold up with bright scenery behind the menu.

A fixture for an open menu with nothing callable has to be found in the raw captures, cropped the same way as the existing fixtures, and saved with them. The raw captures are not in version control: they are only in the `fixtures/raw/` directory of the main checkout, not in a worktree. If no such frame exists there, say so in this ticket's comments and cover the case with the closest frame available.

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] Every existing fixture of an open, settled menu reports open
- [ ] An open menu with nothing callable reports open, with no Codes
- [ ] The closed-menu-over-bright-sky fixture reports closed
- [ ] The glow fixture reports open
- [ ] What the reader reports for a menu still sliding in is decided, tested and written in this ticket's comments
- [ ] The detection is checked against the raw captures and the result (how many agree, any that do not) is written in this ticket's comments
- [ ] Every existing reader test still passes
