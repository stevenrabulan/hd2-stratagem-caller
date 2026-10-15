# The Terminal Key enters the Code a Terminal is showing

Status: needs-info

Partial spec. The behaviour is settled; how the tool reads a Terminal and where the Terminal Key's Key Cap goes wait on fixtures (issue 01), followed by a second grilling round.

## Problem Statement

Mission Terminals (log-ins, the extraction terminal, uploads) ask the player to type a Code of directions shown on the Terminal's screen. It's the same chore as a Stratagem Code, done while exposed, and the tool can't help with it yet.

## Solution

Each Use Key press makes the tool look for a Terminal's Code. While one is on screen and read, the Overlay shows a Key Cap for the Terminal Key (`1` by default), and pressing it enters the Code with the Direction Keys at the same timing as a Call.

## Decisions so far

- **Start:** every Use Key press (E by default; the game treats it as a hold bind, the tool starts on key-down). The Use Key is also used for samples, ammo and pods, so the tool gives up if no Code appears within 5 s of the press (covers the walk-up animation).
- **End:** once a Code has been seen, the tool keeps watching until the Code leaves the screen, the game loses focus, the tool is paused, or a safety limit passes.
- **Terminal Key while a Code is read:** swallowed; the Code is typed with the Direction Keys at `keystroke_ms` timing.
- **Terminal Key:** `1` by default, set by `terminal_key` in `settings.toml`. Return was the first idea but was dropped (2026-10-15, player's choice). `1` is also the default Trigger Key for Slot 1 and the game's weapon-switch key, so it is a Terminal Key only while a Terminal's Code is read (or a Terminal is seen but its Code can't be read).
- **Terminal Key with no Terminal seen:** behaves as it otherwise would: a Trigger Key while the tool is watching the Stratagem Menu, otherwise it goes to the game untouched.
- **Terminal seen but Code unreadable:** the Terminal Key is swallowed, the tool beeps, and the Terminal Key's Key Cap flashes red three times.
- **One press, one Code.** Terminals that chain steps (Launch ICBM, Retrieve Valuable Data, Emergency Evacuation) need one press per Code. Steps that are not arrow Codes (digit codes, grid targets, dials, dish alignment, valves) are out of scope.
- **Direction Keys:** Terminals appear to use the Stratagem direction binds. The screenshot's HUD prompt shows the arrow keys, which are this player's Direction Keys. Confirm with the fixtures.

## Open until fixtures exist

- How the tool recognises that a Terminal is showing a Code. The flat HUD prompt `[▲][◀][▼][▶] INTERACT` at bottom centre may be easier to detect than the Terminal's own screen.
- How the Code is read: in the screenshot it is drawn at an angle on the in-game screen, white arrows on dark grey, with a red marker between arrows.
- Whether directions already entered look different (by hand, or after a wrong press), and what the tool does then.
- Whether the camera, and so the Code's position, is the same for every Terminal of a type.
- Where the Terminal Key's Key Cap goes (candidate: beside the game's INTERACT prompt).

## Further Notes

- `upload_data_login_steam.jpg` (in this folder): a Steam screenshot of the Upload Data log-in Terminal at 3840x2160, Code ↑ ↓ ← ↑ ↓. JPEG, so it is for design only, not a test fixture.
- Research notes (2026-10-13): Arrowhead's input doc lists Use as `E`, Hold, and Open Chat as `Enter`, Press. It has no separate terminal bind group.
