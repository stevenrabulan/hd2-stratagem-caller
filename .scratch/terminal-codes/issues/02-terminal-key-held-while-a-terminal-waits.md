# 02: The Terminal Key is held while a Terminal waits for a Code

**What to build:** A Use Key press starts watching for a Terminal. The watch gives up if no Terminal Prompt appears within 5 s of the press, and otherwise lasts while any Terminal Prompt shows (INTERACT or MOVE CURSOR), ending about 1 s after none shows, or on focus loss, pause or a safety limit. The tool reads the Terminal Prompt at the bottom centre of the screen and tells INTERACT, MOVE CURSOR and no prompt apart. While the Terminal Prompt reads INTERACT, pressing the Terminal Key is swallowed, beeps, and is logged as "Code not read yet" (reading the Code is ticket 03). In every other situation the Terminal Key does exactly what it did before: a Trigger Key while the Stratagem Menu is watched, otherwise an ordinary key for the game. `use_key` (default `e`) and `terminal_key` (default `1`) are set in `settings.toml`. See "Decisions so far" in the spec.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] The Terminal Prompt is recognised as INTERACT, MOVE CURSOR or absent on every frame in `fixtures/terminal/` (the crop origin is in its README)
- [ ] Given scripted Terminal Prompt readings and key presses: the watch starts on the Use Key, gives up after 5 s with no Terminal Prompt, lasts while one shows, and ends about 1 s after it goes, on focus loss, on pause and at a safety limit
- [ ] While INTERACT shows, the Terminal Key is swallowed and beeps; its key-up is swallowed too
- [ ] With no Terminal Prompt, or MOVE CURSOR, the Terminal Key behaves as before (Trigger Key inside the Arming Window, otherwise passed to the game)
- [ ] The log records the watch starting and ending and each Terminal Key decision
- [ ] `settings.toml`, the settings loader and the README cover `use_key` and `terminal_key`
- [ ] (player) In-game: at a Terminal `1` beeps instead of switching weapon; away from one it switches weapon; with the Stratagem Menu open it calls Slot 1
