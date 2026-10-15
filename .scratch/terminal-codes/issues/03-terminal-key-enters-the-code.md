# 03: The Terminal Key enters the Code

**What to build:** While the Terminal Prompt reads INTERACT, the tool reads the Code on the Terminal's own screen. The Code is drawn at an angle that depends on where the player stands, so the reader finds the arrows, puts them in order along their line, tells each direction despite the skew, and tells directions not yet entered (light grey) from entered ones (yellow). A pink circle or the character's hand may lie across the arrows: the reader either still reads every arrow or reports the Code unreadable, and never returns a shortened Code. Pressing the Terminal Key then types only the directions not yet entered, with the Direction Keys at `keystroke_ms` timing. An unreadable Code beeps, as in ticket 02. No automatic retry: the next press reads afresh. See "Decisions so far" and "What the fixtures show" in the spec.

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] Every Code frame in `fixtures/terminal/` reads as ← ↑ → → ↓ →, with the right directions marked entered (none, two, five, all six)
- [ ] The frame with the pink circle across an arrow and the frame with a hand over the first arrow give either the full Code or unreadable, never a shortened Code
- [ ] Frames with no Code (walking up, the bar step, the grid step) give no Code
- [ ] The Upload Data log-in screenshot in the spec's folder reads as ↑ ↓ ← ↑ ↓ (a JPEG, used as a check, not as the only proof)
- [ ] Given a read Code, the Terminal Key types only the directions not yet entered, and none when all are entered
- [ ] A Reading of a Terminal costs little enough that the Terminal Key does not feel delayed (measure it and note the number)
- [ ] (player) In-game at a drill Terminal: `1` enters the Code; after typing two directions by hand, `1` finishes it
