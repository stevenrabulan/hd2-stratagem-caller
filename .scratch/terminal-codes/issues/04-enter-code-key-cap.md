# 04: The ENTER CODE Key Cap, with its red flash

**What to build:** While a Code is read, the Overlay shows a yellow Key Cap for the Terminal Key followed by ENTER CODE in the game's prompt style, just right of the Terminal Prompt at the same height. It hides when the Code is entered, when the Terminal Prompt goes, on focus loss and on pause. When the Terminal Key beeps because the Code can't be read, the Key Cap flashes red three times, as Trigger Key Key Caps do. It follows the Overlay's existing rules: redrawn only on change, never pure white, never over pixels the reader checks. See "Key Cap" in the spec.

**Blocked by:** 03

**Status:** resolved

- [x] Given scripted readings, the Key Cap shows exactly while a Code is read, and flashes on an unreadable-Code beep
- [x] The Key Cap shows the configured Terminal Key's name
- [x] Painting the Key Cap onto every Terminal fixture (normal and red) leaves the Terminal Prompt and Code readings unchanged
- [x] (player) In-game: the Key Cap appears beside INTERACT at a drill Terminal and goes once the Code is entered

## Comments

**Hand-back (2026-10-15).** Everything except the in-game box is done and tested (596 tests pass, up from 514; none plays a tone, hooks the keyboard, sends a key or shows a window). Not checked: the real game. The Key Cap has been drawn onto the 8 Terminal fixtures and looked at; it has not been seen over a live game.

What was built:
- `keycaps.py`: `TerminalKeyCap(name, red)`, `terminal_key_cap_box(h)`, `render_terminal_key_cap(cap, h)`: the same Key Cap drawing as a Slot's (yellow, or red fill, dark glyph, abbreviated long names) followed by ENTER CODE in light grey (215, never pure white) with a dark outline. `_draw_key_cap` now takes its position, so Slot and Terminal caps share it.
- `overlay.py`: a third window for the Terminal Key Cap (made after the column and the heading), drawn only when what it shows changes, hidden when none. The heading does not follow it. `close()` releases every window even if one will not close.
- `router.py`: `terminal_key_cap()` (what the Overlay polls) and `flash_terminal_key()`. `terminal_watch.py`: the watch holds the latest `CodeReading`, cleared when the prompt stops reading INTERACT. `app.py`: the Terminal watch worker reads the Code while the prompt reads INTERACT, and `_beep_for_code()` plays the Beep and starts the flash for every beep for want of a Code (unreadable, none, or the reading raising).
- README, GLOSSARY (Key Cap, Ready Heading, Flash) updated.

When the Key Cap shows: the prompt reads INTERACT, the latest Code reading is READ with directions left, the Stratagem Menu is not being watched, the tool is not typing, the game is focused, not paused. When a flash is running it shows red in each red step regardless of the reading.

Calls I made without asking:
- **Polling rate: the Code is read every 0.25 s (4 a second) while the prompt reads INTERACT**, on the existing Terminal watch worker, not at the prompt's 10 a second. A reading is about 40 ms at 4K (14 ms grab, about 25 ms read), so about 15% of one core while a Terminal waits for a Code, and the Key Cap is at most a quarter of a second behind the screen. Constant `CODE_READING_INTERVAL` in `terminal_watch.py`; a test pins 0.25 and that the worker does not read faster. Not read at all when `[overlay] enabled = false`, when the prompt is not INTERACT, or while the tool types. A reading that raises is logged once and stops Code reading for that watch; the prompt watch and the Terminal Key carry on.
- **Flash is twice, not "three times".** The ticket and spec say three times, but the Flash is two reds in 0.6 s since double-flash 01 (and the ticket says "as Trigger Key Key Caps do"). Used the shared schedule (`flash.is_red`, new, which `red_slots` now uses) so the reds match the Beep's two tones. The spec text still says three; left alone.
- **A flash shows the Key Cap even when no Code is read.** An unreadable Code is exactly when no Key Cap is up ("shown only while a Code is read"), so the flash itself shows it: red in each red step, nothing in the normal steps. If a Key Cap was up (a Code that read fine until the press), it goes red/yellow/red/yellow. Differs from a Slot beyond the menu's end, which only beeps.
- **Hidden when all directions are entered** (reading READ with nothing left), not just when the Code is gone: the key would type nothing, and the ticket's in-game check is that it goes once the Code is entered.
- **Hidden while the tool types, and the Code is forgotten at the Terminal Key press.** The pre-press reading is out of date once typing begins; it comes back only from a fresh reading (within 0.25 s), so a dropped key shows ENTER CODE again. A reading taken just before the press and delivered during typing is dropped.
- **Hidden while the Stratagem Menu is watched**: the Terminal Key is then a Trigger Key, so ENTER CODE would be wrong.
- **Position: x starts 10 px (at 4K) right of the Terminal Prompt reader's strip** (strip ends at x=2340, so the Key Cap starts at 2350, about 190 px right of the prompt's box edge at 2160), at the prompt's height (middle y=1805). "Just right" is bounded by the ticket's "never over pixels the reader checks". Narrowing the reader's strip (STRIP_WIDTH 840, the prompt is at most about 560 wide so there is slack) would bring it closer; I did not touch the reader. The window's rows (1760 to 1850) are clear of the Code area (y 560 to 1600). Tested for 2160, 1440 and 1080 high, normal and red.
- The glyph/words style is OpenCV's DUPLEX font like the other Key Caps, not the game's font; the dark outline keeps it readable on bright scenes. Look at it in-game and say if you want it thinner or closer.
- The Key Cap drawing has some edge pixels whose colour exceeds their alpha (the existing Slot caps do too, 94 pixels; the new one 46); I left that as is.

For Steven to verify in-game (the last box, left unticked): at a drill Terminal press `E`; within about a second of the Code appearing a yellow `1` Key Cap with ENTER CODE shows to the right of the INTERACT prompt. Type the whole Code by hand: it goes. At the CONFIRM DRILL POSITION grid (MOVE CURSOR) and the bar step it is not there. Put your hand or the pink circle over an arrow and press `1`: the Key Cap flashes red twice with the two tones (it may be absent before the press). Press `Call Key` at a Terminal: Slot Key Caps show and the ENTER CODE one does not. Pause (`Ctrl+Alt+P`) and alt-tab: it goes at once. Log lines to look for: `Terminal Key Cap shown: Code LURRDR, 2 entered` and `Terminal Key Cap hidden: ...` with the reason. If the game dips in frame rate at a Terminal, the 4 a second Code reading is the first suspect: raise `CODE_READING_INTERVAL`.

**In-game check (2026-10-16).** Passed. One finding: the Key Cap blinked too briefly to see well. The log showed why: single unreadable or no-Code readings hid it for 0.2 to 0.7 s at a time. Fixed: a Code with directions left is now held through such readings for `CODE_HOLD` (0.75 s), and the Key Cap blinks on purpose, on for 0.96 s and off for 0.24 s (off is 25% of on), from the moment the Code is first read. Red flash steps still show at any point in the blink. Not yet seen in-game.
