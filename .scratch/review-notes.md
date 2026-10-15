# Review notes: ticket run of 2026-10-15

Branch `overlay`, not pushed. Four tickets built, each repo-complete and left `ready-for-human` because its last box is an in-game check. Tests: 176 at the start, **340 passed, 0 failed** at the end (macOS).

| Ticket | Commit | State |
| --- | --- | --- |
| (prep) test suite runs off Windows | `000f4b7` | done |
| overlay/01 Key Caps beside Slots | `328089e` | ready-for-human (in-game check) |
| terminal-codes/01 Use Key bursts | `7e1a48c` | ready-for-human (collect Terminal fixtures) |
| overlay/02 Key Cap flashes red on Beep | `9f1fdcb` | ready-for-human (in-game check) |
| overlay/03 Ready Heading pulses | `2080569` | ready-for-human (in-game check) |

No hard stops came up. Nothing was pushed.

## Needs your call

1. **Glossary additions.** Subagents added **Beep**, **Flash** (02) and **Ready Heading** (03) to `GLOSSARY.md`. Check the wording is how you want to talk about them.
2. **Spec edited.** `.scratch/overlay/spec.md`: the pulse "about once a second" now says 1.2 s to match ticket 03, and the spec's Status is `ready-for-human`.
3. **Terminal Codes built on `overlay`.** Its spec lives on this branch and no `terminal-codes` branch exists, so `7e1a48c` sits here. Cherry-pick it elsewhere if you want the features in separate PRs.
4. **`Reading.icons` changed meaning** (01). It now lists every Slot with an Icon in place, callable or not. A callable Slot whose Icon edge test fails no longer gets an Icon crop. Nothing but tests used it before.
5. **Key Caps are not latched** (01). One Reading that misses an Icon edge drops that Slot's Key Cap for a moment. If it flickers in-game, latch them.

## Decisions taken without you (reversible)

- `tests/conftest.py` stubs `ctypes.windll` off Windows so `test_router.py` runs on macOS. No effect on Windows.
- Key Cap names are upper case with short forms (`page down` shows `PGDN`); long names shrink to fit; two Trigger Keys on one Slot show the first in settings order.
- Key Caps hide at once on focus loss and pause, without waiting for the watch to end.
- A Call Key press while the watch is in doubt hides the Key Caps until the menu is confirmed open again.
- `[overlay] enabled` defaults to true; a missing section means on; a non-boolean raises `SettingsError`.
- If the Overlay thread fails it logs "Overlay stopped", prints a warning and ends. Trigger Keys carry on.
- The router owns the Flash clock; a second Beep restarts that Slot's Flash; a new watch drops any Flash.
- Flash red is the prototype's (BGRA 40, 40, 215).
- The Ready Heading shows exactly when there are Key Caps (same value, same tick). Its pulse is a cosine from the moment it appears (full opacity first), range 110 to 255, period 1.2 s.
- The Ready Heading is placed from the prototype: text at x=410, centred on y=91 at 4K (`TEXT_LEFT` / `TEXT_MIDDLE` in `heading.py`).
- Use Key bursts: `USE_KEY = "e"` constant in `tools/capture_fixtures.py`; shots at 0.5, 1, 1.5, 2, 3, 4 s; files `<stamp>_useNNN_0500ms.png`. Call Key file names are unchanged.
- Left for later, logged in the tickets: a `HeadingPane` split of `overlay.py`; up to one tick of skew between the two windows; 94 Key Cap edge pixels whose colour exceeds alpha (not a Reading risk); a rare older race where a Trigger Key pressed between a Beep being decided and reported flashes its own Slot.

## Unverified

Only a Windows run in the game can prove these. None of the Win32 code has ever run.

- The Overlay windows: visible, topmost, click-through, game keeps focus and mouse, no stutter.
- Key Caps line up left of each Icon; cooldown Slots get one; Slot 10 shows `0`.
- Key Caps and the Ready Heading vanish on a Call, on the Call Key closing the menu, on Alt+Tab, on pause, and shortly after the menu closes.
- Flash: a Slot on cooldown beeps and flashes red three times; `0` with fewer than ten Slots beeps and flashes nothing; the red looks right.
- Ready Heading: sits just right of STRATAGEMS, readable, fades about every 1.2 s (`LayeredWindow.set_opacity` is untested).
- Capture tool: E at a Terminal saves six `_use` shots, a held E saves one burst, B still saves three `_press` shots.

## To deploy

1. Push: `git push origin overlay` (left for you).
2. On Windows: `git pull`, then `.venv\Scripts\python.exe -m pip install -r requirements.txt` (no new dependencies).
3. Run `.venv\Scripts\python.exe -m pytest -q`: expect 340 passed.
4. Play a mission with `[overlay] enabled = true` and work through **Unverified** above. If nothing draws, check `logs/stratagem_caller.log` for "Overlay stopped".
5. Tick the in-game box in overlay 01, 02 and 03 and set them to `resolved`; then the spec.
6. Run `tools\capture_fixtures.py`, play one or two missions, crop Terminal frames into `fixtures/terminal/`, delete the raw captures, and resolve terminal-codes 01.

## Commits

`000f4b7`, `328089e`, `7e1a48c`, `9f1fdcb`, `2080569`, plus this file. Final suite: 340 passed, 0 failed.
