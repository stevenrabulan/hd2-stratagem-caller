# The Terminal Key enters the Code a Terminal is showing

Status: needs-info

Behaviour settled in two grilling rounds (2026-10-13 and 2026-10-15, after the fixtures in issue 01). Reader tickets are still to be cut.

## Problem Statement

Mission Terminals (log-ins, the extraction terminal, uploads) ask the player to type a Code of directions shown on the Terminal's screen. It's the same chore as a Stratagem Code, done while exposed, and the tool can't help with it yet.

## Solution

Each Use Key press makes the tool look for a Terminal's Code. While one is on screen and read, the Overlay shows a Key Cap for the Terminal Key (`1` by default), and pressing it enters the Code with the Direction Keys at the same timing as a Call.

## Decisions so far

- **Start:** every Use Key press (E by default; the game treats it as a hold bind, the tool starts on key-down). The Use Key is also used for samples, ammo and pods, so the tool gives up if no Code appears within 5 s of the press (covers the walk-up animation).
- **When a Code is read:** only while the Terminal Prompt reads INTERACT with the four Direction Keys. The prompt is flat and fixed, so it gates the slower search for the angled Code on the Terminal's screen.
- **End:** the tool keeps watching while any Terminal Prompt shows (INTERACT or MOVE CURSOR), so a later Code step of the same Terminal works without another Use Key press. The watch ends about 1 s after no Terminal Prompt shows, or on focus loss, pause or a safety limit.
- **Terminal Key while a Code is read:** swallowed; the Code is typed with the Direction Keys at `keystroke_ms` timing.
- **Terminal Key:** `1` by default, set by `terminal_key` in `settings.toml`. Return was the first idea but was dropped (2026-10-15, player's choice). `1` is also the default Trigger Key for Slot 1 and the game's weapon-switch key, so it is a Terminal Key only while a Terminal's Code is read (or a Terminal is seen but its Code can't be read).
- **Terminal Key with no Terminal seen:** behaves as it otherwise would: a Trigger Key while the tool is watching the Stratagem Menu, otherwise it goes to the game untouched.
- **Partly entered Code:** the tool types only the directions not yet entered (grey); the game keeps the entered (yellow) ones. If the two can't be told apart, the Code is unreadable.
- **Wrong or dropped key:** no automatic retry. The next Terminal Key press reads the Code afresh and types what is left.
- **Key Cap:** a yellow Key Cap for the Terminal Key, followed by ENTER CODE in the game's prompt style, just right of the Terminal Prompt at the same height. Shown only while a Code is read.
- **Terminal seen but Code unreadable:** the Terminal Key is swallowed, the tool beeps, and the Terminal Key's Key Cap flashes red three times.
- **One press, one Code.** Terminals that chain steps (Launch ICBM, Retrieve Valuable Data, Emergency Evacuation) need one press per Code. Steps that are not arrow Codes (digit codes, grid targets, dials, dish alignment, valves) are out of scope.
- **Direction Keys:** Terminals appear to use the Stratagem direction binds. The screenshot's HUD prompt shows the arrow keys, which are this player's Direction Keys. Confirm with the fixtures.

## What the fixtures show (2026-10-15)

- While a Code is wanted, the HUD shows a flat prompt at bottom centre, `[▲][◀][▼][▶] INTERACT`, at a fixed position (about x=1680 to 2160, y=1760 to 1850 at 4K). Its key glyphs are the player's Direction Keys. It reads `MOVE CURSOR` for a grid step, fades out when a Code is complete, and is replaced by other prompts while walking up.
- The Code is drawn on the Terminal's own screen at an angle that depends on where the player stands, so its position and skew vary. Directions not yet entered are light grey; entered ones turn yellow. A complete Code turns all yellow and fades.
- A pink circle (and small pink markers) is often drawn across the arrows, and the character's hand can cover the first arrow.
- The Prospecting Drill Terminal counts its steps (`1/9`, `2/9`); step 1 is a Code, step 2 is a bar, and CONFIRM DRILL POSITION is a grid.
- The Code appears about 1 s after the Use Key press.

## Still open

- How the angled Code is read (finding the arrows, ordering them, telling direction under skew, grey from yellow, with the pink circle or a hand in the way). An implementation question, designed against `fixtures/terminal/`.
- What a wrong press looks like. Before the reader ticket is closed, capture one more mission with an extraction terminal and one deliberate wrong press.

## Further Notes

- `upload_data_login_steam.jpg` (in this folder): a Steam screenshot of the Upload Data log-in Terminal at 3840x2160, Code ↑ ↓ ← ↑ ↓. JPEG, so it is for design only, not a test fixture.
- Research notes (2026-10-13): Arrowhead's input doc lists Use as `E`, Hold, and Open Chat as `Enter`, Press. It has no separate terminal bind group.
