# Trigger Keys work for as long as the Stratagem Menu is open

Status: ready-for-agent

## Problem Statement

Trigger Keys work most of the time, but sometimes pressing one does nothing useful: the Stratagem is not called and the digit may switch weapon instead. From the player's side there is no pattern to it, which makes the tool hard to trust in a fight.

Three causes are known:

- A Trigger Key only counts in the one second after the Call Key. Open the menu, look at it, decide, press a digit a moment too late, and it is ignored.
- When something bright is behind the Stratagem Menu (an explosion, an engine glow, a bright sky), the tool can fail to read a Slot's arrows. In one captured case it read a Code with its last direction missing.
- The menu sometimes takes longer than usual to open, and the tool gives up on a Slot before it becomes readable.

## Solution

A Trigger Key works at any time while the Stratagem Menu is open, not just in the first second. After the player presses the Call Key, the tool keeps watching the menu until it sees it close.

When the Slot's Code has already been read and confirmed, the Call starts the moment the Trigger Key is pressed. When the menu is still opening, the Call starts as soon as the Slot is confirmed.

A Slot that can't be called gives a beep. When the menu is closed, digits behave as ordinary keys.

The tool never types a Code it only partly read. A Slot whose arrows can't all be read is treated as unreadable until they can.

## User Stories

1. As a player, I want a Trigger Key to work however long the Stratagem Menu has been open, so that I can take my time choosing.
2. As a player, I want a Trigger Key pressed straight after the Call Key to still work, so that fast "b, 1" presses are not lost.
3. As a player, I want a Call to start immediately when the menu has been open for a while, so that there is no added delay once the tool has already read the menu.
4. As a player, I want a Trigger Key pressed while the menu is still sliding in to be held and acted on once the menu is readable, so that I don't have to time my press.
5. As a player, I want the tool to wait for a menu that opens slowly, so that a late-opening menu doesn't cause my Trigger Key to be dropped.
6. As a player, I want the digit swallowed whenever the Stratagem Menu is open, so that I never switch weapon while trying to call a Stratagem.
7. As a player, I want digits to pass through untouched when the Stratagem Menu is closed, so that weapon switching works normally.
8. As a player, I want a beep when I press a Trigger Key for a Slot that is on cooldown, inbound, or otherwise not callable, so that I know the tool heard me and why nothing happened.
9. As a player, I want a beep when I press a Trigger Key for a Slot number beyond the end of the menu, so that a wrong digit is obvious.
10. As a player, I want the beep to come promptly, so that I'm not left wondering for a second whether the key registered.
11. As a player, I want the tool to recognise that the menu is open even when no Stratagem in it can be called, so that digits are still swallowed and I get a beep, not a weapon switch.
12. As a player, I want the tool to stop acting on Trigger Keys as soon as I close the menu with the Call Key, so that my next digit switches weapon as normal.
13. As a player, I want the tool to stop acting on Trigger Keys after a Call completes and the game closes the menu, so that the following digit is an ordinary key.
14. As a player, I want the tool to notice when the menu closes for a reason it didn't cause (I typed a Code by hand, I was ragdolled, the mission ended), so that it doesn't keep swallowing digits.
15. As a player, I want one Trigger Key press to make at most one Call, so that a double tap doesn't call two Stratagems.
16. As a player, I want to press a second Trigger Key after a beep without reopening the menu, so that I can pick a different Slot when my first choice was on cooldown.
17. As a player, I want the tool to never type a shortened or wrong Code, so that I never call the wrong Stratagem or waste the input.
18. As a player, I want a Slot with something bright behind its arrows to be treated as not yet readable, so that the tool waits for a clean view.
19. As a player, I want a Slot that was unreadable for a moment to become callable as soon as the view clears, so that a passing explosion only costs a fraction of a second.
20. As a player, I want the tool to tell apart "this Slot is on cooldown" and "I can't read this Slot right now", so that I'm not told a Stratagem is unavailable when it is.
21. As a player who types part of a Code by hand, I want the tool to stay out of the way, so that my manual input isn't disturbed.
22. As a player, I want Slots to follow what the menu currently shows, so that when a mission Stratagem appears and shifts the list, my digit calls what I see at that position.
23. As a player, I want the tool to track the menu correctly across repeated Call Key presses (open, close, open), so that it never gets out of step with the game.
24. As a player, I want pausing the tool to stop it watching the menu, so that a paused tool does nothing at all.
25. As a player, I want the tool to stop watching when the game loses focus, so that it doesn't read or swallow anything while I'm in another window.
26. As a player, I want Direct Keys to behave exactly as before, so that this change doesn't affect them.
27. As a player, I want no noticeable lag on my own key presses while the tool is watching the menu, so that movement and aiming feel normal.
28. As a player, I want the time-limit setting removed from the settings file, so that there isn't a setting that no longer does anything.
29. As a maintainer, I want the misread screenshots kept as fixtures, so that the bright-background bug can't come back unnoticed.
30. As a maintainer, I want the Trigger Key decision logic testable with a scripted sequence of Readings and key presses, so that timing behaviour can be checked without the game.

## Implementation Decisions

- **Watching replaces the time limit.** The Arming Window is no longer one second long. It opens when the tool confirms the Stratagem Menu is open after a Call Key press and stays open until the tool confirms the menu has closed. The glossary definition of Arming Window is updated to match.
- **A Reading reports whether the menu is open**, separately from which Slots are callable. A menu in which every Stratagem is on cooldown is open with no callable Slots. How the reader recognises an open menu is to be established against the fixtures; the menu's header and its column of Icons are the obvious candidates. It must hold up with bright scenery behind the menu.
- **A Reading distinguishes three states per Slot:** callable with a Code, not callable (the game shows a status in place of arrows), and unreadable (something is on the arrow line that the reader can't fully make sense of). Only "not callable" earns a beep; "unreadable" means keep waiting.
- **No shortened Codes.** If anything on a Slot's arrow line is bright but is not a recognisable arrow at a valid position, the reader reports the Slot as unreadable. It never returns the arrows it could recognise as if they were the whole Code.
- **Confirmation rule stays.** A Code is acted on only when two consecutive Readings agree on it for that Slot. The same rule applies to deciding the menu has closed, so one bad Reading cannot end the watch.
- **Opening grace.** After the Call Key, the menu not being visible yet does not count as closed for a short opening period. The captures show the menu readable by about 250 ms in most presses and by 500 ms in the rest.
- **The Call Key no longer blindly toggles the tool's idea of the menu.** Each Call Key press starts or continues watching; whether the menu is open is decided by what is on screen.
- **Trigger Key outcomes:**
  - Slot confirmed callable: Call now.
  - Menu open, Slot confirmed not callable or beyond the last Slot: beep, swallow the key, keep watching.
  - Menu open, Slot unreadable: hold the key and resolve when the Slot becomes confirmed; beep if it has not within a short limit.
  - Menu still opening: hold the key and resolve once the menu is confirmed, or hand the key back to the game if no menu appears.
  - Menu closed: the key is not touched.
- **After a Call**, the tool expects the game to close the menu and stops acting on Trigger Keys until the next Call Key press.
- **After a beep**, the watch continues and another Trigger Key is accepted.
- **Watching ends** on confirmed menu close, on pause, and when the game window loses focus. A long safety limit also ends it so a misdetected menu cannot leave the tool reading the screen for the rest of a session.
- **Reading rate while watching** is modest once the menu is confirmed, since a Reading costs about 30 ms. It is fast only while opening or while a Trigger Key is waiting to be resolved.
- **Settings.** The Arming Window length setting is removed. No new setting is required.
- **Direct Keys are unchanged**, as recorded in ADR 0001. The open ticket about a Direct Key pressed inside the Arming Window is not part of this work, though the new definition of the Arming Window makes it more useful.
- **Modules affected:** the screen reader (new menu-open answer, three-state Slots, no shortened Codes), the Arming Window decision logic (rewritten around watching), the settings loader (one setting removed), and the keyboard-facing application code (starts and stops watching, routes Trigger Keys by the decision logic's answer).

## Testing Decisions

- A good test here checks what the player would observe: given these screenshots or this sequence of events, is a Code called, is there a beep, is the key swallowed or handed back. Tests must not depend on internal thresholds, pixel positions or timer names.
- **Screen reader**, tested as now with fixture images in and a Reading out. New cases: the frame with a glow behind Resupply's last arrow must not yield a Code for that Slot; the frame taken a quarter second later must yield the full Code; the frame with a lone arrow during slide-in must yield nothing for that Slot; an open menu with nothing callable must report open; a closed menu over a bright sky must report closed. The existing reader tests are the prior art and must keep passing.
- **Arming Window decision logic**, tested as now with a scripted sequence of timestamps, Readings and key presses in, and one decision out. No keyboard, screen capture or game is involved. The existing decision-logic tests are the prior art; most will be rewritten because the one-second rule they describe is going away.
- **Settings loader**: the shipped settings file still loads, and the removed setting is gone.
- Keyboard hooking, screen capture and key sending are not covered by automated tests. They are confirmed by playing.
- Fixtures already saved for this work: the glow frame, the same menu after the glow moved, and the lone-arrow frame. A fixture for an open menu with nothing callable still has to be found in the raw captures or captured.

## Out of Scope

- The Overlay.
- Direct Key behaviour, including the open ticket about Direct Keys inside the Arming Window.
- Screen sizes other than 3840x2160.
- Numpad keys and mouse buttons as Trigger Keys.
- Reading Stratagem names.
- Making arrows readable through a bright background. This spec requires that such a Slot is reported unreadable and retried, not that it is read anyway.

## Further Notes

- Evidence comes from 152 Call Key presses captured during one play session. The reader read the menu in 84 of them; 71 gave the same Reading at 250 ms and 500 ms, 6 were readable only at 500 ms, and 2 frames produced a wrong Code (one shortened by a glow behind the last arrow, one single arrow during slide-in).
- During that session two copies of the tool and the fixture capture script were all running at once. Some of the ignored Trigger Keys may have come from that, so the in-game check after this change should be done with one copy of the tool and no capture script.
- The raw captures are large and not in version control. Anything needed from them as a fixture should be cropped and saved before they are deleted.

## Comments

**Ticketing decisions (2026-10-12, made by the agent without a review round, at the player's request).**

- Five tickets in `issues/`. Graph: 01 → 02 → 03 → 04 and 05 (04 and 05 run side by side).
- The two screen reader tickets (01 unreadable Slots, 02 menu open) are in sequence, not side by side, because both change the shape of a Reading.
- The decision logic and the keyboard-facing wiring are one ticket (03), so the tool works end to end after every merge. Splitting them would have left the tool broken between the two.
- Removing the length setting, with the glossary and README wording, is its own small ticket (04) after 03, because 03 is what stops the setting being used.
- Ending the watch (pause, focus loss, safety limit) and the Reading rate are a separate ticket (05) to keep 03 to a size one agent can hold.
- The missing "open menu with nothing callable" fixture is part of 02. The raw captures exist only in the main checkout's `fixtures/raw/`.
- The uncommitted work for `.scratch/trigger-keys-with-held-keys/` (key routing split from the hook, the log, the missed key-up fix) is committed as the first commit of the integration branch, because 03 builds on it. That ticket stays `ready-for-human`.
- Tickets are closed by setting `Status: resolved` with a closing comment, since the triage labels have no "done" role.
