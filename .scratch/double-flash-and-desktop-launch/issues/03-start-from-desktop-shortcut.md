# 03: The tool starts from a desktop shortcut with no terminal

**What to build:** A Stratagem Caller shortcut on the desktop starts the tool with no terminal window. The shortcut uses the project's virtual environment's windowless Python on the package, the repo root as its working folder, and ticket 02's Key Cap icon. It runs without elevation. It is created by a tools script that also replaces a broken shortcut; run the script once as part of this ticket. No PyInstaller or other frozen executable. On start, a notification says the tool is running and names the Call Key. Startup warnings (untested screen height, Overlay failed to start) appear as notifications. With no console, the other startup lines go to the event log. An unexpected error that ends the tool writes the full traceback to the event log, shows a "Stratagem Caller stopped: see log" notification, and removes the Tray Icon. The README's Running section explains the shortcut, the Tray Icon and the script. It also says to tick "Run as administrator" on the shortcut if the game ignores the tool's keys. See "No frozen executable", "Shortcut", "Notifications", "Errors" and user stories 12 to 16, 25 to 27, 30, 31, 35, 36 in the spec.

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] The tools script creates the Stratagem Caller desktop shortcut and replaces an existing one; it has been run once
- [ ] Double-clicking the shortcut opens no terminal window and shows the Tray Icon
- [ ] A "running" notification names the Call Key
- [ ] Startup warnings show as notifications; with no console, the startup lines are in the event log
- [ ] An unexpected error writes its traceback to the event log, shows the stopped notification, and removes the Tray Icon
- [ ] The README's Running section covers the shortcut, the Tray Icon, the script and the administrator fix
- [ ] (player) Confirmed in-game: started from the shortcut, Trigger Keys and Direct Keys reach the game
