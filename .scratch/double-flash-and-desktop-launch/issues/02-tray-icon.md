# 02: A Tray Icon shows the tool is running and can pause it or quit it

**What to build:** While the tool runs, a Tray Icon sits in the Windows notification area. It shows a yellow Key Cap with an up arrow, in the Overlay's style; the same image is kept in the repo as an icon file that ticket 03's shortcut also uses. The icon is greyed while the tool is paused, and its tooltip says Running or Paused. Its menu has Pause/Resume (the label follows the state), Open log (opens the event log in the default viewer), and Quit. The pause hotkey and the menu share one pause toggle, so the icon follows either one. Quit does the same shutdown as Ctrl+C: the Overlay and the Tray Icon go away and every key goes back to the game. Started from a terminal, the tool prints what it prints today and Ctrl+C still quits. Adds the pystray and Pillow dependencies. See "Tray Icon" and user stories 17 to 24, 32 to 34 in the spec.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] The Key Cap icon file is in the repo and the Tray Icon uses it
- [ ] Running from a terminal shows the Tray Icon; its tooltip says Running
- [ ] Pause/Resume from the menu or from the pause hotkey greys or restores the icon, updates the tooltip and the menu label, and plays the pause beep as today
- [ ] Open log opens the event log
- [ ] Quit and Ctrl+C both end the tool cleanly: no Tray Icon, no Overlay, no keyboard hook left behind
- [ ] pystray and Pillow are in the requirements; the existing tests still pass
- [ ] (player) Checked on Windows: every menu item works while the game is running
