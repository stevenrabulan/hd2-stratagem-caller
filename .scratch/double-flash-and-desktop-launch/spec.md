# A missed Trigger Key flashes and beeps twice in step; the tool starts from a desktop shortcut

Status: ready-for-agent

## Problem Statement

When a Trigger Key cannot call its Slot, its Key Cap turns red three times in about 0.6 s while a single Beep tone sounds over the first part of it. The sound and the picture don't match, so the miss reads as two separate signals rather than one.

Starting the tool means opening a terminal, finding the repo, and typing a command, then leaving that terminal open for the whole session. Quitting means finding that terminal again and pressing Ctrl+C. Warnings, such as an untested screen height or the Overlay failing to start, only appear in that terminal.

## Solution

A Beep becomes two short tones, and the Flash becomes two reds. Each tone sounds as one red begins, so the player sees and hears one double pulse. Pressing the same Trigger Key again restarts the double pulse cleanly instead of stacking sounds.

The tool starts from a desktop shortcut named Stratagem Caller, with no terminal window. While it runs, a Tray Icon shows that it is running (greyed while paused). Its menu offers Pause/Resume, Open log, and Quit. Windows notifications say when the tool has started, when there is a startup warning, when it stopped because of an error, and when it was already running. Starting it from a terminal still works the same as today, and also shows the Tray Icon.

## User Stories

1. As a player, I want a Key Cap to turn red exactly twice when its Trigger Key can't call its Slot, so that the miss is easy to see without being drawn out.
2. As a player, I want to hear two short tones when a Trigger Key misses, so that I notice the miss without looking at the screen.
3. As a player, I want each tone to sound as a red step begins, so that the flash and the sound read as one signal.
4. As a player, I want the whole double pulse to take about 0.6 s, so that it is over before I try again.
5. As a player, I want a Slot on cooldown, inbound or empty to give the double pulse, so that every "can't call" looks and sounds the same.
6. As a player, I want a Slot the tool couldn't read in time to give the double pulse, so that I know my key was heard but not acted on.
7. As a player, I want a Trigger Key beyond the end of the menu to give the two tones even though it has no Key Cap to flash, so that the sound always means "can't call".
8. As a player, I want pressing the same Trigger Key again during a double pulse to restart the flash and the tones from the beginning, so that I never hear three or four tones stacked up.
9. As a player, I want any tone left over from an earlier press to be dropped when I press again, so that the tones I hear always belong to my latest press.
10. As a player, I want misses on two different Slots close together to each flash their own Key Cap, so that I can see which keys missed.
11. As a player, I want the pause beep and the mark beep to stay as they are, so that they stay distinct from a missed Trigger Key.
12. As a player, I want a Stratagem Caller shortcut on my desktop, so that I can start the tool with a double-click.
13. As a player, I want the shortcut to open no terminal window, so that nothing extra sits on my taskbar or over the game.
14. As a player, I want the shortcut to show a Key Cap icon in the Overlay's style, so that I can spot it on my desktop.
15. As a player, I want the shortcut to run my current code, so that changes I make take effect without a rebuild step.
16. As a player, I want a notification when the tool starts that says it is running and names my Call Key, so that I know the double-click worked.
17. As a player, I want a Tray Icon while the tool runs, so that I can see at a glance that it is active.
18. As a player, I want the Tray Icon greyed out while the tool is paused, so that I can tell paused from running without opening anything.
19. As a player, I want the Tray Icon's tooltip to say Running or Paused, so that hovering over it confirms the state.
20. As a player, I want Pause/Resume in the Tray Icon's menu, so that I can pause without remembering the pause hotkey.
21. As a player, I want the pause hotkey and the Tray Icon menu to stay in agreement, so that pausing either way updates both.
22. As a player, I want Open log in the Tray Icon's menu, so that I can read what happened without finding the logs folder.
23. As a player, I want Quit in the Tray Icon's menu, so that I can close the tool without a terminal.
24. As a player, I want quitting to remove the Overlay and the Tray Icon and give all my keys back to the game, so that nothing is left behind.
25. As a player, I want startup warnings (untested screen height, Overlay failed to start) shown as notifications, so that I still see them without a terminal.
26. As a player, I want an unexpected error to write the full details to the log, so that I can share the log when reporting it.
27. As a player, I want an unexpected error to show a "Stratagem Caller stopped: see log" notification and remove the Tray Icon, so that I know the tool is no longer acting on my keys.
28. As a player, I want a second launch while the tool is already running to show an "already running" notification, beep once, and exit, so that two copies never type every Call twice.
29. As a player, I want a launch after the tool has quit or crashed to start normally, so that a crash never blocks the next start.
30. As a player, I want the shortcut to run without asking for administrator rights, so that there is no UAC prompt on every start.
31. As a player, I want the README to tell me to tick "Run as administrator" on the shortcut if the game ignores the tool's keys, so that I have a fix ready.
32. As a developer, I want starting the tool from a terminal to print the same lines as today, so that my development workflow doesn't change.
33. As a developer, I want Ctrl+C to still quit the tool when it was started from a terminal, so that I can stop it the usual way.
34. As a developer, I want the Tray Icon to appear when the tool is started from a terminal too, so that it behaves the same however it's started.
35. As a developer, I want a script that creates or recreates the desktop shortcut, so that moving the repo or rebuilding the virtual environment doesn't leave me with a broken shortcut.
36. As a developer, I want the README to explain the shortcut, the Tray Icon and the shortcut script, so that the run instructions match how the tool is actually used.

## Implementation Decisions

- **Flash and Beep share one schedule.** The flash module keeps its pure functions of time and becomes the single owner of the double-pulse schedule: four steps of 0.15 s (red, normal, red, normal), 0.6 s in all. The same module says when each Beep tone starts (at the start of each red step, so 0 s and 0.3 s), so the red steps and the tones can't drift apart through separate constants.
- **Tones.** Each tone is 330 Hz for about 120 ms. Sound plays on its own thread so the keyboard hook and the reading loop never wait for it. Sync with the red steps is expected to be within a few milliseconds, not exact.
- **Restart rule.** The tool remembers when the latest Beep started. Before sounding its second tone, a Beep checks that it is still the latest Beep and drops the tone if not. The Flash already restarts per Slot (starting a Flash for a Slot replaces any it had), and that stays.
- **Every Beep kind is a double Beep.** Not callable, unreadable too long, and beyond the end of the menu all play both tones. Only Slots with a Key Cap flash, as today. Pause/resume and mark beeps are unchanged.
- **No frozen executable.** The tool is not packaged with PyInstaller or similar. The desktop shortcut runs the project's virtual environment's windowless Python on the package, so it always runs the current code. Rejected: a PyInstaller exe, which goes stale after each code change, is often flagged by antivirus, and may get more scrutiny from the game's anti-cheat as an unsigned packed binary that hooks the keyboard.
- **Shortcut.** It is named Stratagem Caller, placed on the desktop only (no Start Menu entry), uses the repo root as its working folder, runs without elevation, and uses a small icon file kept in the repo: a yellow Key Cap with an up arrow, in the Overlay's style. A tools script creates or replaces it, and is run once as part of this work.
- **Tray Icon.** It uses the same Key Cap image as the shortcut, drawn greyed while paused, with a Running or Paused tooltip. Its menu has Pause/Resume (the label follows the state), Open log (opens the log file in the default viewer), and Quit. The pause hotkey and the menu go through the same pause toggle, so the icon follows either. Quit performs the same shutdown as Ctrl+C. Adds the pystray and Pillow dependencies.
- **Notifications.** Shown through the Tray Icon: started (with the Call Key), startup warnings, stopped on error, and already running. The other startup lines (Direct Keys, log path, Overlay on/off) go to the log only when there is no console, and are printed as today when there is one.
- **Errors.** An unexpected error on the main path, or in a worker thread that ends the tool, writes the full traceback to the event log, shows the stopped notification, and removes the Tray Icon before exiting.
- **Single instance.** A new instance-guard unit claims a machine-wide named lock at startup. If the claim fails, the launch shows the already-running notification, beeps once, and exits before hooking the keyboard. The OS releases the lock when the process ends, including a crash, so a later launch can claim it.
- **Terminal launch.** Running the package from a terminal keeps today's printed output and Ctrl+C handling, and also starts the Tray Icon. Whether a console is attached decides only where the startup lines go.

## Testing Decisions

- A good test checks behaviour a player could observe (when a Key Cap is red, when a tone starts, whether a second launch is refused) through a module's public functions, with time passed in rather than slept through. It does not check internal step arithmetic or private state.
- **Flash module (existing seam).** Extend its tests to cover: red, normal, red, normal, then normal for good, with step changes at 0.15 s multiples (keeping the existing float-error guard); tone starts at 0 s and 0.3 s of a Beep and at no other time; nothing red or sounding before the start; independent clocks per Slot; restarting a Slot's Flash. Prior art: the existing flash tests, which already use pure time values with no sleeping.
- **Instance guard (new seam).** Tested for real against the OS: a claim succeeds when nothing holds it, a second claim fails while the first is held, and a claim succeeds again after release. Tests use a lock name unique to the test run so they never collide with a running copy of the tool.
- **Checked by hand, not unit-tested:** the tone thread and its restart rule (by ear, pressing a missed Trigger Key quickly twice), the Tray Icon and its menu, notifications, the error path, and the shortcut script. Like the Overlay, these depend on Windows UI and sound.
- Existing router tests that assert a Beep outcome need no change: the Beep stays one outcome, and only how it sounds changes.

## Out of Scope

- A standalone executable that runs without Python installed.
- A Start Menu entry, starting with Windows, or an installer.
- Running elevated by default.
- Changing the pause or mark beeps, or adding sound or flash to Direct Keys or the Terminal Key.
- Settings for flash timing, tone pitch or length, or turning the double pulse off.
- Showing Readings or Key Cap state in the Tray Icon.

## Further Notes

- The GLOSSARY.md entries for Beep and Flash (two tones, two reds, each tone sounding with a red step) and the new Tray Icon entry were written while this was grilled. The README's Overlay and Running sections still describe three reds and the terminal launch, and need updating.
- In-game checks still to do after the work is done: the two tones are heard in step with the reds over the game's audio, and keys still reach the game when started from the non-elevated shortcut.
