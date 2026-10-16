# 03: The tool starts from a desktop shortcut with no terminal

**What to build:** A Stratagem Caller shortcut on the desktop starts the tool with no terminal window. The shortcut uses the project's virtual environment's windowless Python on the package, the repo root as its working folder, and ticket 02's Key Cap icon. It runs without elevation. It is created by a tools script that also replaces a broken shortcut; run the script once as part of this ticket. No PyInstaller or other frozen executable. On start, a notification says the tool is running and names the Call Key. Startup warnings (untested screen height, Overlay failed to start) appear as notifications. With no console, the other startup lines go to the event log. An unexpected error that ends the tool writes the full traceback to the event log, shows a "Stratagem Caller stopped: see log" notification, and removes the Tray Icon. The README's Running section explains the shortcut, the Tray Icon and the script. It also says to tick "Run as administrator" on the shortcut if the game ignores the tool's keys. See "No frozen executable", "Shortcut", "Notifications", "Errors" and user stories 12 to 16, 25 to 27, 30, 31, 35, 36 in the spec.

**Blocked by:** 02

**Status:** resolved

- [x] The tools script creates the Stratagem Caller desktop shortcut and replaces an existing one; it has been run once
- [x] Double-clicking the shortcut opens no terminal window and shows the Tray Icon
- [x] A "running" notification names the Call Key
- [x] Startup warnings show as notifications; with no console, the startup lines are in the event log
- [x] An unexpected error writes its traceback to the event log, shows the stopped notification, and removes the Tray Icon
- [x] The README's Running section covers the shortcut, the Tray Icon, the script and the administrator fix
- [x] (player) Confirmed in-game: started from the shortcut, Trigger Keys and Direct Keys reach the game

## Comments

**Hand-back (2026-10-15).** Code, tests and README are done (456 tests pass, up from 427). Three boxes are left for Steven: the real shortcut was NOT created (it writes to his Desktop), the windowless launch of the real tool was not tried (it would hook the keyboard a second time), and the in-game check is his.

What was built:
- `tools/make_shortcut.py` (new): makes `Stratagem Caller.lnk` on the Desktop (path from Windows, so a OneDrive-redirected Desktop works). Target `.venv\Scripts\pythonw.exe`, arguments `-m stratagem_caller`, start in the repo root, icon `stratagem_caller.ico`, no "Run as administrator". Replaces an existing or broken shortcut. Fails loudly if the venv has no pythonw.exe. `--dry-run` prints what it would make; `--path FILE.lnk` makes it elsewhere. Uses PowerShell's WScript.Shell, so no new dependency. Tests (`tests/test_make_shortcut.py`) run it for real, only into pytest's tmp_path, and read the .lnk back.
- `stratagem_caller/startup.py` (new): `Reporter` (startup lines printed with a console, logged without one; warnings always logged, notified, and printed when there is a console), `started_message` ("Running. Call Key: B", plus any startup warnings in the same notification so a warning does not replace the news that it started), `describe_startup` (same printed lines as before), `end_with_error` (traceback to the log, "Stratagem Caller stopped: see log" notification, 5 s to read it, Tray Icon removed), `log_thread_failure` (worker-thread tracebacks to the log).
- `tray.py`: `TrayIcon.notify(message)`. Waits (up to 3 s) for the icon to be in the notification area before notifying, because pystray cannot notify from an icon that is not shown yet.
- `app.py`: `App(warn=...)` (the Overlay failing now goes through it); `main()` starts the Tray Icon first, sends the started notification, then starts the Overlay and hooks the keyboard. An error anywhere in `main()` (including a bad `settings.toml`, which comes before the Tray Icon exists, so a bare icon is shown just to carry the notice) gives the keyboard back, logs, notifies, removes the icon, then re-raises (so a terminal still shows the traceback and the exit code is 1).
- README: Running section now has "From the desktop shortcut" (script, notifications, log, stopped notice, the "Run as administrator" fix) and "From a terminal"; Troubleshooting updated.

Proved here without touching the keyboard or the Desktop:
- A script run by the venv's `pythonw.exe` (the same one the shortcut uses): no console window (MainWindowHandle 0, `sys.stdout` is None), startup lines landed in the log file, the real Tray Icon and a real notification call ran without error, an error path wrote its traceback, and the process exited 0 with nothing left running.
- The real `app.main()` under pythonw with a broken settings.toml in a scratch folder (nothing hooked): traceback in the log, stopped notice path ran, process gone.
- Not seen: the toasts themselves (nobody was looking at the screen), and the real shortcut file launching the real tool.

Judgement calls:
- Seams (no one to confirm with): `TrayIcon.notify` through the fake pystray; `startup.py` through its public functions; the shortcut script run for real into tmp_path. `main()` wiring itself is checked by the smoke runs above, not unit tests.
- No `Icon.notify` calls from `Reporter` directly: it gets a `notify` callable that `main()` sets once the Tray Icon is up.
- Warnings are also written to the log with a console (new; they used to be terminal only). The printed startup lines are unchanged.
- Worker-thread errors do not end the tool today (each worker cleans up its own watch), so they are logged via `threading.excepthook` rather than treated as "stopped".
- If the Tray Icon cannot start, the tool still runs (ticket 02's rule), but with no console that means no notifications and no Quit; the log says so. Task Manager is then the only way to end it.
- Ticket 04 (single instance) is not built yet: **double-clicking the shortcut while another copy runs starts a second copy that also hooks the keyboard.**

**What Steven must run or click:**
1. Quit your running copies first (the Tray Icon's Quit, or Ctrl+C in their terminals, and the `capture_fixtures.py` one). Until ticket 04 is done a second copy would type every Call twice.
2. Make the shortcut (this writes to your Desktop; `--dry-run` first if you like): `.venv\Scripts\python.exe tools\make_shortcut.py` from the repo root. Then tick "it has been run once" in the first box.
3. Double-click "Stratagem Caller" on the Desktop. Check: no terminal window opens, the Key Cap Tray Icon appears (maybe under the `^` overflow), and a notification says "Running. Call Key: B". Tick the second and third boxes if so. If no toast shows, check Windows notification / Focus Assist settings first.
4. Open `logs\stratagem_caller.log`: the startup lines (Direct Keys, log path, Overlay on) should be there from this launch. Use the Tray Icon's Quit to end it.
5. Optional, error path: temporarily break `settings.toml` (for example delete the `call_key` line), double-click the shortcut, expect the "Stratagem Caller stopped: see log" notification and a traceback in the log. Restore `settings.toml` after.
6. In-game (the player box): start from the shortcut, confirm Trigger Keys and Direct Keys reach the game. If the game ignores them, tick "Run as administrator" on the shortcut (Properties, Advanced) and try again.
