# 02: A Tray Icon shows the tool is running and can pause it or quit it

**What to build:** While the tool runs, a Tray Icon sits in the Windows notification area. It shows a yellow Key Cap with an up arrow, in the Overlay's style; the same image is kept in the repo as an icon file that ticket 03's shortcut also uses. The icon is greyed while the tool is paused, and its tooltip says Running or Paused. Its menu has Pause/Resume (the label follows the state), Open log (opens the event log in the default viewer), and Quit. The pause hotkey and the menu share one pause toggle, so the icon follows either one. Quit does the same shutdown as Ctrl+C: the Overlay and the Tray Icon go away and every key goes back to the game. Started from a terminal, the tool prints what it prints today and Ctrl+C still quits. Adds the pystray and Pillow dependencies. See "Tray Icon" and user stories 17 to 24, 32 to 34 in the spec.

**Blocked by:** None (can start immediately)

**Status:** ready-for-human

- [x] The Key Cap icon file is in the repo and the Tray Icon uses it
- [x] Running from a terminal shows the Tray Icon; its tooltip says Running
- [x] Pause/Resume from the menu or from the pause hotkey greys or restores the icon, updates the tooltip and the menu label, and plays the pause beep as today
- [x] Open log opens the event log
- [x] Quit and Ctrl+C both end the tool cleanly: no Tray Icon, no Overlay, no keyboard hook left behind
- [x] pystray and Pillow are in the requirements; the existing tests still pass
- [ ] (player) Checked on Windows: every menu item works while the game is running

## Comments

**Hand-back (2026-10-15).** Everything except the in-game box is done and tested on Windows (363 tests pass). The real Tray Icon was smoke-run on this machine (script, not left running): icon shows, tooltip flips Running/Paused, menu items work through real pystray, Quit and Ctrl+C both return from `main()` with no tray icon, no keyboard handlers and no non-daemon threads left, process exit 0. Not checked: the icon against the game running, and how it looks on the taskbar (Windows may put it under the `^` overflow arrow).

What was built:
- `keycaps.py`: `render_icon(size)` draws the Key Cap with an up arrow from the Overlay's own constants (yellow `#FFE900`, dark glyph, bar under the cap, same proportions).
- `tools/make_icon.py` writes the icon file. **Icon file for ticket 03: `stratagem_caller/assets/stratagem_caller.ico`** (16 to 256 px, committed). `stratagem_caller.tray.ICON_PATH` points at it.
- `tray.py` (new): `TrayIcon(paused, toggle_pause, open_log, quit, running_image, paused_image, backend)` with `start()`, `refresh()`, `stop()`. Menu: Pause/Resume (label follows state), Open log, Quit. pystray is reached through a replaceable `backend`, imported lazily. `load_icon()` and `greyed()` make the two pictures from the one icon file (grey is dimmed to 60%).
- `app.py`: `App(tone=winsound.Beep)` now takes the tone player (pause, mark and Beep all use it, so tests stay silent). `toggle_pause` is the single pause path (hotkey and menu), under a lock, and calls `app.on_pause_change` (the tray's `refresh`) after the change. New `quit_requested`, and `shutdown()` (stop, join the Overlay thread, `keyboard.unhook_all()`). `main()` starts the Tray Icon after the Overlay, waits on `quit_requested`, and in `finally` stops the tray, shuts down and closes the log. Printed startup lines unchanged. A Tray Icon that fails to start logs and prints a warning and the tool carries on (like the Overlay).
- `requirements.txt`: `pystray==0.19.5`, `Pillow==12.3.0` (pystray also pulls in `six` 1.17.0).
- README: Tray Icon bullet under Running.
- Tests: `test_tray.py` (menu, labels, greying, stop, icon file, greyed picture, fake backend), `test_app.py` (pause toggle notifies the tray and plays its beeps, `stop` ends the main loop), `test_keycaps.py` (icon drawing).

Judgement calls:
- Seams (no one to confirm with): icon drawing, `TrayIcon` through a fake pystray, `App.toggle_pause`/`stop`. The real icon and `main()` wiring were checked by smoke script, not unit tests.
- Pillow and pystray pinned with `==` like `keyboard` and `mss`.
- Icon lives inside the package (`stratagem_caller/assets/`) so its path is stable whatever the working folder.
- No default (left-click) menu item, so a stray click never pauses.
- `Open log` that fails (no viewer, missing file) logs and prints a warning instead of raising on the tray's thread.
- Added `keyboard.unhook_all()` and `log.close()` to the shutdown, which the old Ctrl+C path left to process exit.
- No notifications yet (ticket 03 owns them); `TrayIcon` has no `notify` method for it to extend.

To check in-game (the unticked box): with the game running, pause and resume from the menu and from `Ctrl+Alt+P` (icon, tooltip and label follow both, pause beep plays), Open log opens the log, Quit removes the icon and Overlay and every key reaches the game.
