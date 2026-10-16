# 05: Watching ends on pause, focus loss and a safety limit, and reads at a modest rate

**What to build:** Watching the Stratagem Menu stops when the player pauses the tool and when the game window loses focus, and a long safety limit ends it so a misdetected menu cannot leave the tool reading the screen for the rest of a session. Once the menu is confirmed the tool takes Readings at a modest rate; it reads fast only while the menu is opening or while a Trigger Key is waiting to be resolved. See "Watching ends" and "Reading rate while watching" in the spec, and user stories 24, 25 and 27.

Where the rule can be expressed without keyboard, screen capture or clock (when the watch ends, how long until the next Reading), it is covered by scripted tests. The capture loop itself is confirmed by playing.

**Blocked by:** 03

**Status:** resolved

- [ ] Pausing ends the watch; a Trigger Key pressed afterwards is not touched
- [ ] A Trigger Key being held when the watch ends is not lost silently: it is handed back to the game
- [ ] When the game window loses focus the watch ends and no further Readings are taken
- [ ] A watch that has run past the safety limit ends, and the next Call Key press starts a new one
- [ ] With the menu confirmed open and no Trigger Key waiting, Readings are taken at the modest rate
- [ ] While the menu is opening, or a Trigger Key is waiting, Readings are taken at the fast rate
- [ ] The log records why a watch ended

## Comments

**Judgement calls (implementer).**

- Safety limit is 60 s from the latest Call Key press (a second press restarts the count). The menu is rarely left open that long; the limit only has to bound a misdetection. A held Trigger Key is handed back when it fires; the log says "safety limit reached".
- Reading rates: 0.05 s while the menu is not yet confirmed open or a Trigger Key is waiting; 0.2 s once confirmed with nothing waiting. Cost: a menu closed by the game is noticed after about two modest Readings (~0.4 s), so a digit pressed in that gap is swallowed and beeps.
- Pause ends the watch (log: "watch ended: paused") and hands a held Trigger Key back to the game. Focus loss ends the watch from the worker's next Reading (<= 0.2 s) and does not tap a held key, since it would go to another window; the log says why.
- If reading throws an error, the worker ends the watch so the next Call Key press starts a fresh worker.
- The watch-ends logic and rates are scripted tests (`test_arming.py`, `test_router.py`). `app.py` (worker loop, pause hand back) is checked by reading and by import only.

**Resolved 2026-10-13.** Merged into `trigger-keys-while-menu-open` as 7e9bbe3. Code review fixes that touch this ticket are in d003bd4; see "Code review fixes" in the spec. Not yet confirmed in-game.
