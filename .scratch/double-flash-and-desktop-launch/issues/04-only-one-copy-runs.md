# 04: Only one copy of the tool runs at a time

**What to build:** On startup, the tool claims a machine-wide named lock before it hooks the keyboard. If another copy already holds the lock, the new launch shows an "already running" notification, beeps once, and exits without hooking anything. Two copies would otherwise type every Call twice. The OS releases the lock when the process ends, including after a crash, so a later launch starts normally. This lives in a new instance-guard unit, tested for real against the OS with a lock name unique to the test run. See "Single instance" and user stories 28 and 29 in the spec.

**Blocked by:** 02

**Status:** ready-for-human

- [x] A claim succeeds when nothing holds the lock
- [x] A second claim fails while the first is held
- [x] A claim succeeds again after the first is released
- [x] A second launch shows the "already running" notification, beeps once, and exits before hooking the keyboard
- [x] A launch after Quit, or after the process was killed, starts normally
- [ ] (player) Checked on Windows: double-clicking the shortcut twice leaves one Tray Icon, and a Call is typed once

## Comments

**Hand-back (2026-10-15).** Code, tests and README are done (514 tests pass, up from 502). One box is left for Steven: the in-game / shortcut check (it needs the real shortcut from ticket 03, which has not been made).

What was built:
- `stratagem_caller/instance_guard.py` (new): `claim(name=LOCK_NAME)` returns an `InstanceLock` (with `release()`, safe to repeat) or None when another copy holds the lock. A Win32 named mutex through ctypes, name `Global\StratagemCaller` (machine-wide, not per login session). If the OS answers "access denied" (the holder runs elevated, this copy does not), that also counts as held. Any other OS failure raises, so a broken guard stops the tool loudly rather than letting two copies run.
- `startup.py`: `refuse_second_launch(tray, beep, log, sleep)`: logs, shows "Stratagem Caller is already running", beeps once, waits 5 s for the notice to be read, removes the Tray Icon. The icon is removed even if the notification or the beep fails. `end_with_error` now shares the same closing-notice helper (behaviour unchanged).
- `app.py` `main()`: claims the lock first, before the settings, Tray Icon, Overlay or keyboard. On refusal it prints one line if there is a console, shows the notice on a bare Tray Icon (the pattern from ticket 03, renamed `_bare_tray_icon`), beeps one tone (330 Hz, 120 ms, the Beep's tone) and returns without hooking anything. The lock is released right after the keyboard is given back, before any stopped notice delay, so a relaunch is not refused during those seconds. The OS releases it anyway when the process ends.
- README: "Only one copy runs at a time" in the shortcut section.

Tests: `tests/test_instance_guard.py` runs against the real OS with a uuid lock name per test (skipped off Windows): free claim succeeds, second claim fails while held, claim succeeds after release, refused attempts do not free the holder's lock, double release is harmless, and a child process holding the lock is killed (its process tree, since the venv's python.exe starts a child) and the lock is claimable afterwards. `tests/test_startup.py` covers the refusal (notice, one beep, tray removed; also when the notice or the beep fails). `tests/test_app.py` runs the real `main()` with the lock, tray, beep and keyboard replaced: a refused launch notifies, beeps once, stops the tray and never touches the keyboard; a launch that holds the lock releases it when it ends.

Not tried: the access-denied path (needs an elevated holder and a non-elevated second launch), and the real second-launch toast and beep (not run here: it would show a toast on Steven's screen).

**What Steven must do:** after making the shortcut (see ticket 03), double-click it twice. Expect one Tray Icon, an "already running" toast and one beep from the second launch, and a Call typed once in-game. Then Quit from the Tray Icon and double-click again: it should start normally. Optional: kill the tool in Task Manager and double-click again; it should start normally. Then tick the last box and set the status to resolved. Until then, copies started from before this commit (like your current terminal ones) hold no lock and are not seen by the new guard: quit them first.
