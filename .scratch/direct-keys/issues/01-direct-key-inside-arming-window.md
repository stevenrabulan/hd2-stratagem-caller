# Direct Key inside the Arming Window should not press the Call Key

Status: resolved

Not planned yet. Do only if it turns out to be cheap.

## Problem

A Direct Key always presses the Call Key before typing its Code, without looking at the screen. When the Call Key is bound as a toggle and the player has just opened the Stratagem Menu themselves, that extra press closes the menu and the Code is typed into nothing.

## Wanted

If a Direct Key is pressed while the Arming Window is open, skip the Call Key press and type the Code straight away. The Arming Window being open already tells the tool the Stratagem Menu is showing, so no Reading is needed.

## Out of scope

Any other case where the menu is already open (for example, opened more than a second ago). Direct Keys stay blind there by design; see [ADR 0001](../../../docs/adr/0001-read-codes-from-the-screen.md).

## Comments

Done on branch `direct-key-in-arming-window`. `ArmingWindow.is_open(now)` decides it; the key hook checks it, closes the Arming Window (so a pending Trigger Key is dropped), and skips the Call Key press. Covered by a unit test on `is_open`; the hook wiring needs a check in a mission on Windows.

**2026-10-15, merged into `overlay`.** `main` had this change on the old one-second Arming Window. In the newer watching model it lives in the router: a Direct Key skips the Call Key while the tool is watching a menu that is open or opening (`ArmingWindow.menu_shown()`), but not while the player's latest Call Key press is closing it or after a Call. It still ends the watch, dropping a held Trigger Key. Covered by arming and router tests; still needs a check in a mission.
