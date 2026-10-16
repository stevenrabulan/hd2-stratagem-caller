# A Reading takes about 110 ms, so the Arming Window reads about 3× slower than designed

Status: needs-triage

## Problem

Found while checking issue 01. `read_menu` on a 4K fixture takes about 110 ms (117 ms after issue 01). The worker loop sleeps `FAST_READING_INTERVAL` (50 ms) *after* each Reading, so the real fast rate is one Reading every ~160 ms, not every 50 ms. The worker also does a screen grab, not timed here.

Every timing rule in `arming.py` was tuned assuming ~50 ms Readings. With the real rate:

- `OPENING_GRACE` (0.75 s) covers about 4 Readings, not 12;
- a Trigger Key waits ~0.3 s for two agreeing Readings, not ~0.1 s;
- the doubt and closing rules count Readings that come 3× further apart.

This matters for issue 03's "menu not open" hand-backs.

## Where the time goes (cProfile, 20 Readings)

- `_icon_in_place` converts the **whole** region to int16 on each of its 10 calls (`region[:, :, :3].astype(np.int16)`): about 50 ms per Reading. Converting once, or only the Icon's neighbourhood, removes nearly all of that.
- The rest is numpy reductions: the white mask, and per-blob `_direction` on about 1000 blobs.

## Proposal

Convert the region once per Reading (or crop each Icon's neighbourhood before converting). Then re-measure, and log the Reading time in the event log so field timings are known.

## Comments
