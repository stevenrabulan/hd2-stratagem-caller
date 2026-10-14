# Log Call Key presses and save the screen when a Trigger Key fails

Status: needs-triage

## Problem

Several times on 2026-10-13 a Trigger Key was taken and then handed back with "menu not open" 0.07 to 0.4 s later (21:18:31, 21:43:23, 22:14:34 for Slot 3; 14 hand-backs in the log against 63 Calls). The cause cannot be settled from the log. Two things are missing:

1. **Call Key presses are not logged**, nor whether the Arming Window took a press as opening or closing the menu.
2. **No screen is saved** when a Slot stays unreadable or a Trigger Key is handed back, so failures leave no fixtures behind.

## What the log does show

At 22:14:34.454 the Trigger Key was taken with no Reading yet since the last Call Key press, and handed back 0.24 s later. A fresh press has a 0.75 s opening grace, so that hand-back is only possible if `ArmingWindow.restart` took the Call Key press as **closing** an open menu (`CLOSING_GRACE` 0.05 s). That happens when the previous two Readings showed the menu open. So within about a second there were two Call Key presses, the first one seen as opening the menu.

Candidate causes (cannot be told apart without the data below):

- The game closed the menu on its own (sprint, dive, ragdoll, a Code typed by hand). The watch still believed it open when the player pressed the Call Key to reopen it, so the press was taken as closing. The doubt logic needs about 0.6 s of not-open Readings to notice.
- The reader called a closed or half-open screen "open" twice in a row. For example, the Reinforce row is in place first while sliding in, and `1 in codes` counts as open. The player then pressed the Call Key again because the menu had not appeared.
- The player really did press the Call Key twice.

The 2026-10-12 captures show no settled open menu read as closed. The "not open" frames inspected were menus mid-animation, so a reader fault on "open" is less likely than an Arming Window decision.

## Proposal

- One log line per Call Key press: `call key: watch started` / `call key: restarted, taken as opening|closing`, with the latest Reading.
- Keep the last few screen regions read (about 8, roughly 0.4 to 1.6 s). When a beep fires on `UNREADABLE_LIMIT`, or a held Trigger Key is handed back, write them to `fixtures/raw/failures/<time>_<slot>_<reason>_<n>.png` off the hot path. Region only (800×1500 at 4K, about 2 MB each), not the full screen, so no desktop content is captured. Cap the folder size (for example, the newest 200 files).

## Comments
