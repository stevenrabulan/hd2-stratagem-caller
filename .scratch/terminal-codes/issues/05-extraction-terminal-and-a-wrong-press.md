# 05: Extraction terminal and a wrong press

**What to build:** One more capture mission with `tools/capture_fixtures.py`, covering what the first one missed: an extraction terminal with its Code showing, and one deliberate wrong direction typed at any Terminal (what the game shows after it). Crop the useful frames into `fixtures/terminal/` the same way as the first set (same crop, README updated), add them to the reader's tests, and file a ticket for anything the reader gets wrong. The capture itself can happen any time; the tests need ticket 03.

**Blocked by:** 03

**Status:** ready-for-human

- [ ] (player) A capture mission with an extraction terminal and one wrong press
- [ ] Useful frames cropped into `fixtures/terminal/`, README updated; raw bursts deleted afterwards
- [ ] Reader tests cover the new frames; failures filed as tickets
- [ ] The spec notes what a wrong press looks like and whether the "no automatic retry" decision still holds
