# 01: A missed Trigger Key flashes and beeps twice, in step

**What to build:** When a Trigger Key earns a Beep, for any reason (not callable, unreadable too long, beyond the end of the menu), the player hears two short tones (330 Hz, about 120 ms each) and that Slot's Key Cap turns red twice: 150 ms red, 150 ms normal, 150 ms red, 150 ms normal. Each tone starts as a red step starts. The flash module owns this one schedule, both the red steps and the tone starts, so the two can't drift apart. A Slot with no Key Cap only hears the tones. Pressing again while a double pulse is running restarts the flash and the tones, and drops any tone left over from the earlier press. The pause and mark beeps are unchanged. See "Flash and Beep share one schedule", "Restart rule" and user stories 1 to 11 in the spec.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] The flash is red, normal, red, normal, then stays normal, with steps changing at multiples of 0.15 s (float-error guard kept)
- [ ] The flash module says a Beep's tones start at 0 s and 0.3 s, and at no other time
- [ ] Nothing is red and no tone is due before a flash begins; each Slot keeps its own clock; starting a Flash for a Slot restarts it
- [ ] Every kind of Beep plays both tones, on a thread that never holds up the keyboard hook or the reading loop
- [ ] A Beep that is no longer the latest one drops its second tone
- [ ] The README's Overlay text says two reds in step with two tones
- [ ] (player) Confirmed in-game: pressing a Slot on cooldown gives two reds in step with two tones; pressing it twice quickly never gives more than two tones in a row
