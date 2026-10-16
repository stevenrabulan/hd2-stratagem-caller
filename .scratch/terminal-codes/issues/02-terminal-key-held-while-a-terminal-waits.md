# 02: The Terminal Key is held while a Terminal waits for a Code

**What to build:** A Use Key press starts watching for a Terminal. The watch gives up if no Terminal Prompt appears within 5 s of the press, and otherwise lasts while any Terminal Prompt shows (INTERACT or MOVE CURSOR), ending about 1 s after none shows, or on focus loss, pause or a safety limit. The tool reads the Terminal Prompt at the bottom centre of the screen and tells INTERACT, MOVE CURSOR and no prompt apart. While the Terminal Prompt reads INTERACT, pressing the Terminal Key is swallowed, beeps, and is logged as "Code not read yet" (reading the Code is ticket 03). In every other situation the Terminal Key does exactly what it did before: a Trigger Key while the Stratagem Menu is watched, otherwise an ordinary key for the game. `use_key` (default `e`) and `terminal_key` (default `1`) are set in `settings.toml`. See "Decisions so far" in the spec.

**Blocked by:** None (can start immediately)

**Status:** resolved

- [x] The Terminal Prompt is recognised as INTERACT, MOVE CURSOR or absent on every frame in `fixtures/terminal/` (the crop origin is in its README)
- [x] Given scripted Terminal Prompt readings and key presses: the watch starts on the Use Key, gives up after 5 s with no Terminal Prompt, lasts while one shows, and ends about 1 s after it goes, on focus loss, on pause and at a safety limit
- [x] While INTERACT shows, the Terminal Key is swallowed and beeps; its key-up is swallowed too
- [x] With no Terminal Prompt, or MOVE CURSOR, the Terminal Key behaves as before (Trigger Key inside the Arming Window, otherwise passed to the game)
- [x] The log records the watch starting and ending and each Terminal Key decision
- [x] `settings.toml`, the settings loader and the README cover `use_key` and `terminal_key`
- [x] (player) In-game: at a Terminal `1` beeps instead of switching weapon; away from one it switches weapon; with the Stratagem Menu open it calls Slot 1

## Comments

**Hand-back (2026-10-15).** Everything except the in-game box is done and tested (427 tests pass; no test plays a tone, hooks the keyboard or shows a window). Not checked: the real game. In particular the prompt reader has only seen the eight fixtures (one Prospecting Drill Terminal, 3840x2160), and `1` at a Terminal has not been pressed in a mission.

What was built:
- `terminal_prompt.py` (new): `TerminalPrompt` (NONE, INTERACT, MOVE_CURSOR), `prompt_area(monitor)` (the strip read, screen x 1500 to 2340, y 1740 to 1870 at 4K, scaled by height) and `read_terminal_prompt(region, height)`. It matches the words INTERACT and MOVE CURSOR against two templates (`assets/prompt_interact.png`, `assets/prompt_move_cursor.png`, cut from the fixtures by `tools/make_prompt_templates.py`). It reads the word, not the four key glyphs, because the glyphs are whatever Direction Keys the player has bound. On the fixtures the right word scores 0.96 or better (0.89 with the screen shrunk to 1080p) and anything else 0.27 or less; threshold 0.8. A region too small for the words raises rather than reading as "no prompt". Cost: about 6 ms per read at 10 reads a second.
- `terminal_watch.py` (new): `TerminalWatch`, pure like the Arming Window (readings and times in, a reason to end out). Gives up 5 s after the press with no prompt, lasts while INTERACT or MOVE CURSOR shows, ends 1 s after none shows (a gap shorter than that is forgiven, gaps do not add up), ends at 120 s since the last Use Key press. A second Use Key press restarts the 5 s and the limit.
- `router.py`: `use_key` and `terminal_key` constructor arguments. A Use Key press passes through and starts the watch (`Decision.start_terminal_watch`), or restarts the one running. A Terminal Key press while the latest reading is INTERACT is swallowed (its repeats and key-up too) and sets `Decision.enter_code`; otherwise it falls through to the Trigger Key rules or the game, exactly as before. `offer_terminal`, `terminal_is_current`, `end_terminal_watch` mirror the Arming Window's worker calls. The log gets: `use key e: Terminal watch started|restarted`, `terminal key 1: swallowed|not swallowed, <why>` (only while a watch runs), `Terminal watch ended: <why>`. A mark's description includes the Terminal watch.
- `app.py`: `_watch_terminal` worker (strip grab, read, offer, 0.1 s apart; ends cleanly on any error), `_enter_code` (**the seam for ticket 03**: today it logs `Code not read yet` and plays `DoubleBeep`), and `toggle_pause` also ends the Terminal watch.
- `settings.py`, `settings.toml`, README: `use_key` ("e") and `terminal_key` ("1"), defaulted in the loader so old settings files still load, must be non-empty strings and different keys.

**For ticket 03:** replace the body of `App._enter_code` (it runs on its own thread when the router sets `Decision.enter_code`; the router has already swallowed the key and `router._terminal.prompt` says INTERACT). Reading the Code needs the Terminal's screen, which is not in the prompt strip; grab it in `_enter_code` with `mss` the way `_watch_terminal` does. Typing needs `sends=True` in the `_spawn` call in `on_event` (so the tool ignores its own Direction Keys). An unreadable Code keeps the current `self._beep.play()`. The Terminal Key beep is the tones only: the Key Cap flash is started by the router's `finish()` for a Slot, and a Terminal Key beep never goes through it. Ticket 04's red flash will need its own start point.

Judgement calls:
- Seams (no one to confirm with): the prompt reader against every fixture (screen built from the crop origin in the fixtures README), `TerminalWatch` through scripted readings and times, `KeyRouter` through key events, `App` through `on_event`, `toggle_pause` and the worker with a fake screen.
- If the Stratagem Menu is being watched (Call Key pressed, Arming Window open) and the Terminal Prompt still reads INTERACT, the Terminal Key is a Trigger Key, not a Terminal Key: the player just opened the menu to call a Slot, which is what the in-game box says `1` does with the menu open. Logged as `not swallowed, Stratagem Menu watched`.
- A prompt that is fading (the 2/9 bar frame) still reads INTERACT; `drill_code_complete_fading` has a full-brightness prompt, so it reads INTERACT too. In both the Code reader (ticket 03) is what says there is no Code.
- A Terminal Key press with no watch running is not logged (nothing was decided); with a watch running every press is.
- Safety limit 120 s from the last Use Key press (the spec gave none). Reading every 0.1 s.
- Use Key presses while paused, not focused or while the tool is typing start nothing.
- `use_key` and `terminal_key` equal is a settings error (it would make the Terminal Key start its own watch).
- Self-review against the spec and `~/.agents/docs/code-quality.md` in place of the sub-agent review: fixed three findings (a region too small for the words read quietly as "no prompt", now a ValueError; `REFERENCE_HEIGHT` and `WHITE_THRESHOLD` were copied from the menu reader, now imported; the first draft logged a line for every ordinary `1` press, which broke the existing one-line log tests and is noise, now only while a watch runs).

To check in-game (the unticked box): at a drill Terminal press `E`, then `1` once the prompt reads INTERACT: a low double beep, no weapon switch, and the log shows `Terminal watch started`, `terminal key 1: swallowed, Terminal Prompt reads INTERACT`, `Code not read yet`. On the grid step (`MOVE CURSOR`) and away from a Terminal `1` switches weapon; with the Stratagem Menu open it calls Slot 1. Also look for `Terminal watch ended: Terminal Prompt gone` about 1 s after leaving, and `gave up` 5 s after an `E` at a sample or ammo box. If `1` does not beep at a Terminal, press `F9` there and share the mark: the log line will say what the watch believed.

