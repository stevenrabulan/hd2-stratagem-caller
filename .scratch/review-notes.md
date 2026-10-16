# Review notes: second ticket run of 2026-10-15

Branch `overlay`, not pushed. Six tickets built across two features, each repo-complete and left `ready-for-human` because its last box needs you (in-game, or the real Desktop). Run on Windows this time. Tests: 340 at the start, **596 passed, 0 failed** at the end (suite run three times, no flakes).

| Ticket | Commit | State |
| --- | --- | --- |
| double-flash 01 Double pulse on a miss | `5ef55e3` | ready-for-human (in-game) |
| double-flash 02 Tray Icon | `d8ff839` | ready-for-human (in-game) |
| terminal-codes 02 Terminal Key held while a Terminal waits | `767876d` | ready-for-human (in-game) |
| (fix) non-UTF-8 byte in README | `9f0aadd` | done |
| double-flash 03 Desktop shortcut | `10cd987` | ready-for-human (**hard stop**: shortcut not made; double-click; in-game) |
| terminal-codes 03 Terminal Key enters the Code | `1780640` | ready-for-human (in-game) |
| double-flash 04 Only one copy runs | `842c5b7` | ready-for-human (needs the shortcut) |
| terminal-codes 04 ENTER CODE Key Cap | `68610c5` | ready-for-human (in-game) |

Not touched: terminal-codes 05 (`ready-for-human`, needs a capture mission), trigger-key-misses 01 to 04 and trigger-keys-with-held-keys 01 (`needs-triage` / `ready-for-human`). Nothing was pushed.

## Needs your call

1. **Hard stop: the desktop shortcut was not made.** It writes to your Desktop, outside the repo. The script is built and tested into a temp folder. Run it yourself (step 3 of **To deploy**). Boxes 1 and 2 of double-flash 03 stay open until you do.
2. **Menu beats Terminal** (terminal-codes 02). If the Stratagem Menu is being watched and the prompt still reads INTERACT, `1` is a Trigger Key and calls Slot 1. The ticket did not say which wins.
3. **Hand-over-arrow frame reads as unreadable** (terminal-codes 03). The only real "five entered" frame has a yellow sliver for its first arrow, so it beeps instead of typing. Box 1 was ticked on a synthetic recoloured "five entered" frame. Say if a sliver should count as the same state as its neighbour.
4. **Terminal Key Cap flashes twice, not three times** (terminal-codes 04). It uses the shared double-pulse schedule so the reds match the two tones. `.scratch/terminal-codes/spec.md` line 26 and the ticket text still say three; left alone.
5. **Terminal Key Cap sits about 190 px right of the prompt box** (terminal-codes 04), at x=2350 at 4K, to stay off the prompt reader's strip. Narrowing `STRIP_WIDTH` in the prompt reader would close the gap.
6. **Single-instance lock:** `Global\StratagemCaller` (machine-wide). An elevated copy that a non-elevated launch cannot open counts as running, so that launch is refused. Matters if you tick "Run as administrator".
7. **Your running copies are old code.** `python -m stratagem_caller` (started 1:57 PM) and `tools/capture_fixtures.py` (2:34 PM) were left alone. They hold no lock, so the new guard cannot see them: quit them before starting the new code or Calls type twice.
8. **Blockers in `ready-for-human`.** double-flash 03 and 04 and terminal-codes 03 and 04 were built while their blockers waited only on in-game checks. If an in-game check fails, the later ticket may need a change too.

## Decisions taken without you (reversible)

Double pulse (double-flash 01)
- New `stratagem_caller/beep.py` (`DoubleBeep`), tone player injected so the restart rule is unit-tested.
- Tones take turns behind a lock; a restarted first tone can start up to about 120 ms late if the old one is still sounding.
- A new watch drops the Flash but not leftover tones (spec only says a new press drops them).

Tray Icon (double-flash 02)
- Icon at `stratagem_caller/assets/stratagem_caller.ico`, drawn by `tools/make_icon.py` from the Overlay's Key Cap constants; greyed at runtime to 60%.
- `pystray==0.19.5`, `Pillow==12.3.0` pinned (pystray pulls in `six`).
- `App.toggle_pause` is the one pause path for hotkey, menu and the Terminal watch.
- No default left-click action, so a stray click never pauses.
- Tray Icon failing to start logs and warns, tool carries on (as the Overlay does).
- Shutdown now unhooks the keyboard, joins the Overlay thread (2 s) and closes the log explicitly.

Terminal Key held (terminal-codes 02)
- Prompt read by template match of the words INTERACT and MOVE CURSOR (lowest colour channel, threshold 0.8, about 6 ms, 10 reads/s); templates cut by `tools/make_prompt_templates.py`.
- A fading INTERACT still reads INTERACT; the Code reader decides there is no Code.
- Safety limit 120 s from the last Use Key press (spec gave no number). Another Use Key press restarts the 5 s and the limit.
- A gap under 1 s is forgiven; gaps do not add up.
- Terminal Key presses are logged only while a watch runs.
- `use_key` / `terminal_key` default to `e` / `1` in the loader; equal values are a `SettingsError`.

Desktop shortcut (double-flash 03)
- `tools/make_shortcut.py` builds the `.lnk` through PowerShell's WScript.Shell (no new dependency); Desktop path from `SHGetFolderPathW` so a OneDrive Desktop works; `--dry-run` and `--path` added.
- No console means `sys.stdout is None` (pythonw).
- The started notification reads "Running. Call Key: B" and carries startup warnings in the same toast.
- Warnings are always written to the log now, even with a console.
- Worker-thread errors log their traceback via `threading.excepthook` but do not end the tool.
- An error before the Tray Icon exists shows a bare Tray Icon just to carry the "stopped" notice.

Code reader (terminal-codes 03)
- Each arrow fitted to a canonical arrow by an affine map; search area the middle 1840x1040 at 4K; shrunk to 1080 high (85 ms to 25 ms per read).
- Unreadable on uneven spacing, a stub at either end, a bright thing between arrows, a glyph score under 0.7, an ambiguous direction, a tilt over 60 degrees, or out-of-order entered arrows.
- Fewer than 3 arrows means no Code.
- All directions entered: no beep, logs "nothing left to type".
- Router addition `is_entering_code`: a second `1` and its release are swallowed while a Code is read and typed (otherwise it switched weapon).
- About 40 ms from press to first key (14 ms grab, 25 ms read).

Single instance (double-flash 04)
- Win32 named mutex via ctypes, claimed first in `main()`, released right after shutdown (before any 5 s notice wait).
- A refused launch logs, notifies "Stratagem Caller is already running", beeps once (330 Hz, 120 ms), waits 5 s, removes its icon; from a terminal it also prints one line.

ENTER CODE Key Cap (terminal-codes 04)
- Code read every 0.25 s while INTERACT shows (`CODE_READING_INTERVAL`, about 15% of one core); no reads with the Overlay off, without INTERACT, or while typing.
- A read that raises is logged once and stops Code reading for that watch; the Terminal Key still works.
- On an unreadable beep the cap shows red in the red steps even if no Code was read.
- Hidden when all directions are entered, while typing, and while the Stratagem Menu is watched.
- Own third Overlay window; the Ready Heading does not show for it (GLOSSARY updated).
- ENTER CODE drawn in OpenCV DUPLEX, light grey with a dark outline, not the game's font.

All code reviews were self-reviews by the implementing agent against the spec and `code-quality.md`; the code-review sub-agents were not run.

## Unverified

Only you, on this PC and in the game, can prove these.

- Double pulse: two reds in step with two tones on a cooldown Slot; a quick second press never gives more than two tones in a row.
- Tray Icon: every menu item while the game runs; icon greys on pause from both the menu and `Ctrl+Alt+P`. Real pystray menu clicks and Quit/Ctrl+C were smoke-tested by script.
- Toasts: notify calls ran without error, but no one saw a toast on screen. Check Focus Assist if none shows.
- Shortcut: double-click opens no terminal and shows the Tray Icon (a `pythonw` smoke run showed no console window); Trigger and Direct Keys reach the game from it.
- Terminal: `1` at INTERACT types the Code (whole, or the rest after two by hand); beeps with a hand or pink circle over an arrow; `1` still switches weapon at MOVE CURSOR and away from a Terminal; the ENTER CODE cap appears and goes. The readers have only seen the 8 drill fixtures plus one JPEG, all 3840x2160.
- Single instance: second double-click gives one Tray Icon, an "already running" toast, one beep; a Call types once. The access-denied (elevated holder) path is untested.
- Frame rate at a Terminal with the 4 reads/s Code polling.

## To deploy

1. Push: `git push origin overlay` (left for you).
2. Quit your running copies (the tool from 1:57 PM and `capture_fixtures.py` from 2:34 PM), then `.venv\Scripts\python.exe -m pip install -r requirements.txt` (adds pystray, Pillow, six).
3. Make the shortcut: `.venv\Scripts\python.exe tools\make_shortcut.py` (try `--dry-run` first).
4. Double-click "Stratagem Caller" on the Desktop: no terminal, Tray Icon appears (maybe under `^`), toast "Running. Call Key: B". Double-click again: "already running" toast, one beep, still one icon.
5. Play a mission and work through **Unverified**. Logs are in `logs\stratagem_caller.log`. If the game ignores the keys, tick "Run as administrator" on the shortcut.
6. Tick the open boxes and set `resolved` in each ticket; the hand-back under `## Comments` in each lists exact checks.
7. Then the capture mission for terminal-codes 05 (extraction terminal, a wrong press); each new fixture is one line in `tests/test_terminal_code.py`.

## Commits

`5ef55e3`, `d8ff839`, `767876d`, `9f0aadd`, `10cd987`, `1780640`, `842c5b7`, `68610c5`, plus this file. Final suite: 596 passed, 0 failed.

---

## Earlier run: first ticket run of 2026-10-15 (Overlay)

Branch `overlay`, not pushed. Four tickets built, each repo-complete and left `ready-for-human` because its last box is an in-game check. Tests: 176 at the start, **340 passed, 0 failed** at the end (macOS).

| Ticket | Commit | State |
| --- | --- | --- |
| (prep) test suite runs off Windows | `000f4b7` | done |
| overlay/01 Key Caps beside Slots | `328089e` | ready-for-human (in-game check) |
| terminal-codes/01 Use Key bursts | `7e1a48c` | ready-for-human (collect Terminal fixtures) |
| overlay/02 Key Cap flashes red on Beep | `9f1fdcb` | ready-for-human (in-game check) |
| overlay/03 Ready Heading pulses | `2080569` | ready-for-human (in-game check) |

No hard stops came up. Nothing was pushed.

### Needs your call

1. **Glossary additions.** Subagents added **Beep**, **Flash** (02) and **Ready Heading** (03) to `GLOSSARY.md`. Check the wording is how you want to talk about them.
2. **Spec edited.** `.scratch/overlay/spec.md`: the pulse "about once a second" now says 1.2 s to match ticket 03, and the spec's Status is `ready-for-human`.
3. **Terminal Codes built on `overlay`.** Its spec lives on this branch and no `terminal-codes` branch exists, so `7e1a48c` sits here. Cherry-pick it elsewhere if you want the features in separate PRs.
4. **`Reading.icons` changed meaning** (01). It now lists every Slot with an Icon in place, callable or not. A callable Slot whose Icon edge test fails no longer gets an Icon crop. Nothing but tests used it before.
5. **Key Caps are not latched** (01). One Reading that misses an Icon edge drops that Slot's Key Cap for a moment. If it flickers in-game, latch them.

### Decisions taken without you (reversible)

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

### Unverified

Only a Windows run in the game can prove these. None of the Win32 code has ever run.

- The Overlay windows: visible, topmost, click-through, game keeps focus and mouse, no stutter.
- Key Caps line up left of each Icon; cooldown Slots get one; Slot 10 shows `0`.
- Key Caps and the Ready Heading vanish on a Call, on the Call Key closing the menu, on Alt+Tab, on pause, and shortly after the menu closes.
- Flash: a Slot on cooldown beeps and flashes red three times; `0` with fewer than ten Slots beeps and flashes nothing; the red looks right.
- Ready Heading: sits just right of STRATAGEMS, readable, fades about every 1.2 s (`LayeredWindow.set_opacity` is untested).
- Capture tool: E at a Terminal saves six `_use` shots, a held E saves one burst, B still saves three `_press` shots.

### To deploy

1. Push: `git push origin overlay` (left for you).
2. On Windows: `git pull`, then `.venv\Scripts\python.exe -m pip install -r requirements.txt` (no new dependencies).
3. Run `.venv\Scripts\python.exe -m pytest -q`: expect 340 passed.
4. Play a mission with `[overlay] enabled = true` and work through **Unverified** above. If nothing draws, check `logs/stratagem_caller.log` for "Overlay stopped".
5. Tick the in-game box in overlay 01, 02 and 03 and set them to `resolved`; then the spec.
6. Run `tools\capture_fixtures.py`, play one or two missions, crop Terminal frames into `fixtures/terminal/`, delete the raw captures, and resolve terminal-codes 01.

### Commits

`000f4b7`, `328089e`, `7e1a48c`, `9f1fdcb`, `2080569`, plus this file. Final suite: 340 passed, 0 failed.
