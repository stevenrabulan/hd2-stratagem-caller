# 01: Capture screenshots of Terminals on each Use Key press

**What to build:** `tools/capture_fixtures.py` also saves a burst of screenshots on each Use Key press (`e`), timed to cover the walk-up to a Terminal and the Code appearing: for example 0.5, 1, 1.5, 2, 3 and 4 s after the press. Files are labelled so Use Key bursts can be told apart from Call Key bursts. The README's "Collecting fixtures" section lists the Terminal shots wanted.

Then the player plays one or two missions and uses as many kinds of Terminal as they meet. Shots wanted:

1. Each kind of Terminal with its Code showing (extraction, upload data log-in, ICBM, SEAF artillery, radar, any other).
2. A Code with some directions entered by hand.
3. A Code right after a wrong direction.
4. A Terminal whose next step is not a Code (digits, grid, dial).
5. The same kind of Terminal from two different approach angles.

**Blocked by:** none

**Status:** ready-for-agent

- [ ] A Use Key press saves a labelled burst; a held Use Key saves one burst, not one per repeat
- [ ] Call Key bursts work as before
- [ ] The README lists the Terminal shots wanted
- [ ] (player) Terminal bursts collected; the useful frames cropped into `fixtures/terminal/` as PNG before the raw captures are deleted
