# A Slot that flickers between readable and unreadable beeps instead of Calling

Status: needs-triage

## Problem

At 22:27:51.857 on 2026-10-13 Slot 3 beeped although the latest Reading showed its Code (`Slots 3,6`). The previous Reading had it unreadable. A Call needs two Readings in a row that agree on the Code (`ArmingWindow._resolve`). A Slot that is readable only on every other Reading never gets that, so `UNREADABLE_LIMIT` (0.75 s) fires a beep.

Reproduced with a scripted `ArmingWindow`: Readings alternating "Slot 3 = RRDLRD" and "Slot 3 unreadable" every 0.05 s after the Trigger Key beep at about 0.9 s after the press.

Issue 01 removes the main source of flicker (moving bright scenery behind the menu). Real clutter crossing the arrows (explosions, markers) can still flicker.

## Proposal

Once the menu is settled, accept a Code when the last two Readings that **showed a Code** for the Slot agree, even if unreadable Readings came between them. That is still two independent clean views of the same Code. A Reading where the Slot is "not callable" (no arrows, no clutter) resets it.

Needs a decision: is two non-consecutive agreeing Readings safe enough? The two-in-a-row rule guards against Codes caught mid-animation. That guard matters only before the menu is settled, and issue 01 stops clutter from shortening Codes.

## Comments
