# 03: Trigger Keys work for as long as the Stratagem Menu is open

**What to build:** After a Call Key press the tool watches the Stratagem Menu until it sees it close, and a Trigger Key is acted on at any time in between. The Arming Window decision logic is rewritten around watching, and the keyboard-facing code routes Trigger Keys by its answer. This is the whole path: Readings in, key presses in, Call / beep / swallow / hand back out, wired through to the running tool. See "Watching replaces the time limit", "Confirmation rule stays", "Opening grace", "The Call Key no longer blindly toggles", "Trigger Key outcomes", "After a Call" and "After a beep" in the spec, and user stories 1 to 23.

The decision logic stays free of keyboard, screen capture and clock: it is driven by a scripted sequence of timestamps, Readings and key presses. The key-event tests added for the held-keys ticket are prior art for the keyboard-facing side and their held-key and missed key-up behaviour must not regress.

The Arming Window no longer takes a length. Stop using the length setting here; removing it from the settings file and loader is ticket 04. Ending the watch on pause, focus loss and the safety limit, and the Reading rate, are ticket 05; a simple fixed Reading rate is enough here.

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] Slot confirmed callable when the Trigger Key is pressed: the Call starts at once, with no wait for another Reading
- [ ] A Trigger Key works many seconds after the Call Key, as long as the menu is still open
- [ ] A Code is acted on only when two consecutive Readings agree on it for that Slot
- [ ] Menu open, Slot confirmed not callable or beyond the last Slot: beep, key swallowed, watch continues, and a second Trigger Key is accepted without reopening the menu
- [ ] Menu open, Slot unreadable: the key is held and the Call is made when the Slot becomes confirmed; beep if it has not within a short limit
- [ ] Menu still opening: the key is held and resolved once the menu is confirmed; it is handed back to the game if no menu appears
- [ ] A menu that takes 500 ms to become readable is still waited for
- [ ] Menu closed: the Trigger Key is not touched
- [ ] The menu is judged closed only when two consecutive Readings say so, and never during the opening grace
- [ ] After a Call the tool stops acting on Trigger Keys until the next Call Key press
- [ ] One Trigger Key press makes at most one Call
- [ ] Open, close, open with the Call Key stays in step with what is on screen; a menu closed for a reason the tool did not cause is noticed
- [ ] When a mission Stratagem shifts the list, the digit calls what is now shown at that Slot
- [ ] Direct Keys behave exactly as before
- [ ] The Trigger Key and Call log lines still explain each decision
- [ ] Decision-logic tests are scripted events in, one decision out; none depend on internal thresholds or timer names
