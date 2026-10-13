# 05: Watching ends on pause, focus loss and a safety limit, and reads at a modest rate

**What to build:** Watching the Stratagem Menu stops when the player pauses the tool and when the game window loses focus, and a long safety limit ends it so a misdetected menu cannot leave the tool reading the screen for the rest of a session. Once the menu is confirmed the tool takes Readings at a modest rate; it reads fast only while the menu is opening or while a Trigger Key is waiting to be resolved. See "Watching ends" and "Reading rate while watching" in the spec, and user stories 24, 25 and 27.

Where the rule can be expressed without keyboard, screen capture or clock (when the watch ends, how long until the next Reading), it is covered by scripted tests. The capture loop itself is confirmed by playing.

**Blocked by:** 03

**Status:** ready-for-agent

- [ ] Pausing ends the watch; a Trigger Key pressed afterwards is not touched
- [ ] A Trigger Key being held when the watch ends is not lost silently: it is handed back to the game
- [ ] When the game window loses focus the watch ends and no further Readings are taken
- [ ] A watch that has run past the safety limit ends, and the next Call Key press starts a new one
- [ ] With the menu confirmed open and no Trigger Key waiting, Readings are taken at the modest rate
- [ ] While the menu is opening, or a Trigger Key is waiting, Readings are taken at the fast rate
- [ ] The log records why a watch ended
