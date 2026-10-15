# 01: Capture screenshots of Terminals on each Use Key press

**What to build:** `tools/capture_fixtures.py` also saves a burst of screenshots on each Use Key press (`e`), timed to cover the walk-up to a Terminal and the Code appearing: for example 0.5, 1, 1.5, 2, 3 and 4 s after the press. Files are labelled so Use Key bursts can be told apart from Call Key bursts. The README's "Collecting fixtures" section lists the Terminal shots wanted.

Then the player plays one or two missions and uses as many kinds of Terminal as they meet. Shots wanted:

1. Each kind of Terminal with its Code showing (extraction, upload data log-in, ICBM, SEAF artillery, radar, any other).
2. A Code with some directions entered by hand.
3. A Code right after a wrong direction.
4. A Terminal whose next step is not a Code (digits, grid, dial).
5. The same kind of Terminal from two different approach angles.

**Blocked by:** none

**Status:** resolved

- [x] A Use Key press saves a labelled burst; a held Use Key saves one burst, not one per repeat
- [x] Call Key bursts work as before
- [x] The README lists the Terminal shots wanted
- [x] (player) Terminal bursts collected; the useful frames cropped into `fixtures/terminal/` as PNG before the raw captures are deleted

## Comments

**Hand-back (2026-10-15).** Everything except the in-game box is done and tested here (macOS; 263 tests pass, 8 new). The capture tool has not been run on Windows, so the hook wiring is unconfirmed.

What was built:
- `tools/burst_plan.py` (pure, no hooks or screen code): `BurstKind` (label prefix, shot delays, file naming) with `CALL_KEY_BURST` (100, 250, 500 ms, files named as before) and `USE_KEY_BURST` (0.5, 1, 1.5, 2, 3, 4 s); `BurstTrigger` turns one key's down/up events into a label, returning nothing for a held key's auto-repeats. Tested in `tests/test_capture_burst.py`.
- `tools/capture_fixtures.py`: one `hook_burst_key(key, kind)` for both keys; `USE_KEY = "e"` at the top. Use Key files are named `<stamp>_useNNN_0500ms.png`, Call Key files stay `<stamp>_pressNNN_100ms.png`. Each key has its own counter.
- README "Collecting fixtures": both bursts, naming, the Terminal shots wanted, and the crop-then-delete step.

Judgement calls:
- Pure logic lives in a sibling module `tools/burst_plan.py` (tests add `tools/` to `sys.path`) rather than inside the script or the `stratagem_caller` package, so the tool's DPI/hook imports stay out of the tests and the package stays free of dev tooling.
- Use Key delay is zero-padded to 4 digits (`0500ms`) so the six shots sort in order; Call Key keeps 3 digits so its names do not change.
- `USE_KEY` is a constant in the script like `CALL_KEY`, not read from `settings.toml`.
- Overlapping Use Key bursts (E pressed again within 4 s) run as separate threads. A 4 s burst holds six raw 4K grabs in memory (about 200 MB) until it is encoded.
- Seams were not confirmed with Steven (away); chose `BurstTrigger` and `BurstKind` as the only tested interface, and left the hook and screen code untested.

To do (the unticked box): on Windows, run `.venv\Scripts\python.exe tools\capture_fixtures.py`, check the startup text lists both keys, press `E` at a Terminal and confirm six `_use001_` files appear (holding `E` still gives one burst) and that a `B` press still gives three `_press` files. Then play one or two missions, work through the five shots listed above, crop the useful frames into `fixtures/terminal/` as PNG, and delete the raw captures. Tick the box and set the status to resolved.

**Resolved 2026-10-15.** The capture tool ran on Windows: 44 Use Key bursts of six shots each (42 in-game). Eight frames cropped into `fixtures/terminal/` (see its README). The raw captures (about 17 GB in `fixtures/raw/`) are not deleted yet.

Coverage against the list above: 1 only partly (one Prospecting Drill Terminal, plus the Upload Data log-in screenshot in this folder; no extraction, ICBM, SEAF or radar Terminal); 2 yes (two and five directions entered); 3 no (no wrong direction); 4 yes (a bar step and a grid step); 5 yes (two angles of the same Terminal).
