# Trigger Key is sometimes ignored while other keys are held

Status: ready-for-human

## Problem

In a mission, pressing the Call Key and then a Trigger Key did not always make a Call. The player believes it happened while running: movement keys (W, A, S, D, and probably Shift for sprint) were held down at the time.

A Trigger Key must act whenever the Arming Window is open, whatever other keys are held, pressed or released around it.

## What is known

- No cause has been confirmed. Nothing in the key handling refers to movement keys, and there is no automated test that presses a Trigger Key with other keys held, so the behaviour is unproven either way.
- The key handling lives inside the keyboard hook callback and cannot currently be tested without a real keyboard.
- One real defect has been found by reading the code: the tool decides a key-down is an auto-repeat if it believes the key is already held. If a key-up is ever missed (focus change, another hook swallowing it), the next genuine press of that key is treated as a repeat and ignored. This fits "ignored once, then works".
- When the report was made, two copies of the tool and the fixture capture script were running at the same time. That may explain some or all of it, and cannot be ruled out from the code.
- When a Trigger Key is ignored there is currently no record of why.

## Wanted

1. The decision "what happens to this key event" (let through, swallow, start watching, make a Call, hand to the Arming Window) is separated from the keyboard hook, so it can be driven by a scripted list of key events in tests. Behaviour does not otherwise change.
2. Tests that prove a Trigger Key is acted on:
   - with W, A, S, D and Shift held, alone and together;
   - with a held key auto-repeating before, between and after the Call Key and Trigger Key;
   - when a held key is released between the Call Key and the Trigger Key;
   - when the Trigger Key's previous key-up was never seen.
3. The missed key-up defect is fixed: a key-down is treated as an auto-repeat only if it could plausibly be one, so a stale "held" record cannot swallow or ignore a real press.
4. A plain-text log, off the hot path of the keyboard hook, with one line per Trigger Key press and per Call: the time, the Slot, what the latest Reading showed, and the decision (Call, beep, handed back, not in the Arming Window, ignored as repeat). The log must be enough to explain the next "it ignored me" report.

## Out of scope

- The one-second limit on the Arming Window. Removing it is covered by the spec in `.scratch/trigger-keys-while-menu-open/`.
- Changes to the screen reader.
- Direct Key behaviour, beyond keeping it working.

## Notes for whoever picks this up

- Do not start the tool or the capture script while working on this; the player may have a copy running, and a second keyboard hook changes the behaviour being investigated. Automated tests only.
- If the tests show the key handling is already correct with keys held, say so plainly in the ticket's comments. The log is then the route to the real cause.

## Comments

**Finding: movement keys do not break the routing.** The key-event decision now lives in `stratagem_caller/router.py` (`KeyRouter`) and is driven by scripted events in `tests/test_router.py`. With the original "held means repeat" rule in place, a Trigger Key was acted on in every scenario involving W, A, S, D and Shift (alone and together, auto-repeating before, between and after the Call Key and Trigger Key, and released between them). A Direct Key also worked with those keys held.

**The only failures were the missed key-up cases**, as suspected from reading the code: if a key's key-up was never seen, the next real press of that key (Trigger Key, Call Key or Direct Key) was treated as an auto-repeat and ignored. A stale swallowed record could also swallow the key-up of a later press that had been let through.

**Fix:** a key-down is a repeat only if the previous key-down for that key was at most `REPEAT_GAP` (1 second) earlier; each key-down refreshes that time, so a real repeat run stays chained. A key-down that is not a repeat clears any stale "swallowed" record. The Arming Window rules are unchanged.

**Left alone / caveats**
- A genuine press within 1 second of a key-down whose key-up was lost is still indistinguishable from the first auto-repeat and is ignored. It is logged as "ignored as repeat".
- Since movement keys are not at fault in the tests, the original report is more likely the two copies of the tool plus the fixture capture script running at once (two hooks), or this missed key-up case. The log should settle it: it is at `logs/stratagem_caller.log` (git-ignored), one line per Trigger Key press and per Call, with the latest Reading and the decision. No line is written for Trigger Keys pressed while another window is focused, so digits typed elsewhere are not recorded.

**Needs a human:** confirm in-game, with one copy of the tool running, that a Trigger Key now works while running with Shift held, and read the log after any miss.
