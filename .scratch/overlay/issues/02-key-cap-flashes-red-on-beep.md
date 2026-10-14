# 02: A Key Cap flashes red when its Trigger Key beeps

**What to build:** Whenever a Trigger Key earns a beep, for any reason (not callable, unreadable too long, beyond the end of the menu), that Slot's Key Cap fill turns red three times in about 0.6 s (100 ms red, 100 ms normal). The beep sound is unchanged. A Slot with no Key Cap (beyond the end of the menu) gets the beep only. A second beep during a flash restarts it. See "Red flash" in the spec, and user stories 10 and 11.

The prototype on branch `prototype/overlay` has the flash timing and red drawing.

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] Given scripted Readings and key presses, a beep reports which Slot's Key Cap to flash
- [ ] The flash shows red, normal, red, normal, red, normal, then stays normal
- [ ] A beep for a Slot beyond the end of the menu flashes nothing
- [ ] The Overlay-can't-change-a-Reading test covers red Key Caps
- [ ] (player) Confirmed in-game: pressing a Slot on cooldown beeps and flashes its Key Cap
