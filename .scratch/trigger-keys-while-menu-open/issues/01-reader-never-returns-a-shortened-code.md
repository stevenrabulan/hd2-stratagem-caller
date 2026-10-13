# 01: A Reading never contains a shortened Code

**What to build:** A Reading tells apart three states per Slot: callable with a Code, unreadable (something bright is on the Slot's arrow line that is not a recognisable arrow at a valid position), and everything else (not callable). When a Slot is unreadable the reader reports it as unreadable; it never returns the arrows it could recognise as if they were the whole Code. See "A Reading distinguishes three states per Slot" and "No shortened Codes" in the spec.

Existing callers of the reader keep working: they may ignore the unreadable state for now.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] The glow-behind-last-arrow fixture yields no Code for Resupply's Slot, and reports that Slot as unreadable
- [ ] The fixture of the same menu a quarter second later yields Resupply's full Code
- [ ] The lone-arrow-while-sliding-in fixture yields no Code for that Slot
- [ ] A Slot showing a status in place of arrows (cooldown, inbound) is not reported as unreadable
- [ ] Every existing reader test still passes
- [ ] Tests are fixture image in, Reading out; none depend on thresholds or pixel positions
