# The Overlay shows a Key Cap beside each Slot while the Stratagem Menu is open

Status: needs-info

Waiting on the in-game check of the prototype (`tools/prototype_overlay.py`, see Further Notes). Tickets are cut after it.

## Problem Statement

Trigger Keys work, but nothing on screen says which key calls which Slot, or whether the tool is ready to act. When a Trigger Key beeps, the player hears it but can't see which key it was or that the tool heard them at all. In a fight that means looking away to count rows.

## Solution

A window drawn over the game, the Overlay, shows a Key Cap beside each Slot of the Stratagem Menu while the tool is ready to act on Trigger Keys, plus a pulsing heading that says so. A Key Cap that earns a beep flashes red. The Key Caps copy the look of the game's own key hints.

## User Stories

1. As a player, I want a Key Cap beside each Stratagem in the open menu, so that I can see which key calls it without counting rows.
2. As a player, I want each Key Cap to show the Trigger Key I configured for that Slot, so that remapped keys are shown correctly (Slot 10 shows `0` by default).
3. As a player, I want Key Caps beside Stratagems on cooldown too, so that the layout doesn't jump as Stratagems come and go.
4. As a player, I want the Key Caps to look like the game's own key hints, so that they feel part of the game.
5. As a player, I want the Key Caps to appear only once the tool is ready to act on Trigger Keys, so that what I see matches what a key press will do.
6. As a player, I want a heading reading STRATAGEM CALLER READY that pulses while the tool is ready, so that I know at a glance the tool is watching.
7. As a player, I want the Key Caps and heading gone the moment a Call starts, so that they don't cover the Code being entered.
8. As a player, I want them gone when I close the menu with the Call Key, when the game loses focus, and when I pause the tool.
9. As a player, I want them to stay steady when gunfire briefly hides the menu from the tool, so that they don't flicker.
10. As a player, I want the pressed Key Cap to flash red three times whenever a Trigger Key beeps, so that I can see which key was refused.
11. As a player, I want the beep to stay, so that I still hear it when I'm not looking at the menu.
12. As a player, I want no Overlay for Direct Keys, since they never look at the screen.
13. As a player, I want the Overlay never to take focus, keystrokes or mouse clicks from the game.
14. As a player, I want to turn the Overlay off in the settings and still have Trigger Keys work as before.
15. As a streamer, I want the Overlay to show in my captures and recordings like any other window.
16. As a maintainer, I want proof that the Overlay can't change a Reading, so that the reader seeing its own Overlay can never cause a wrong Call.

## Implementation Decisions

- **Visibility follows the Arming Window.** The Key Caps and heading show when the tool confirms the menu is open (the same moment Trigger Keys start to act) and hide when a Call starts typing, when the Call Key is pressed while the menu is confirmed open (closing), on focus loss, on pause, and when the safety limit ends the watch. While the watch is in doubt (gunfire hiding the menu) they stay up, so they can linger up to about 0.6 s after the menu really closes.
- **Which Slots get a Key Cap:** every Slot whose Icon is in place and that has a Trigger Key, callable or not, all drawn the same. A Slot beyond the end of the menu has no Key Cap; a Trigger Key for it beeps with no flash.
- **Placement:** left of the Icon, in the gutter between the menu's bracket and the Icon, vertically centred on the Icon. At 3840x2160 about 50 px square, ending left of x=98. Everything scales with screen height, as the reader does.
- **Look:** the shape of the game's own key hints (seen in a Terminal screenshot: `TAB`, `OPEN CHAT`), a filled rounded square with a dark glyph and a thin bar of the fill colour underneath, filled in the game's yellow (#FFE900). Chosen in-game over a light fill and an outlined style.
- **Red flash:** on any beep, the pressed Trigger Key's Key Cap fill turns red three times in about 0.6 s (100 ms red, 100 ms normal). The beep sound is unchanged.
- **Ready heading:** STRATAGEM CALLER READY, uppercase, in the game's yellow (#FFE900), on the line of the game's STRATAGEMS header, just right of it, with a soft glow. The whole heading pulses in opacity about once a second. Shown and hidden with the Key Caps.
- **The reader sees the Overlay.** The window is not excluded from screen capture, so it shows in streams and recordings. Instead the Overlay keeps out of every pixel the reader checks: nothing pure white, nothing on the arrow lines (x >= 215 at 4K on Slot rows), nothing within a few pixels of an Icon's edges. This was chosen over excluding the window from capture because players may want the Overlay in their recordings; it is easy to reverse.
- **The windows:** two small always-on-top, click-through windows that never take focus, one a column for the Key Caps and one a strip for the heading. The Key Caps are redrawn only when something changes (Slots, a flash step). The heading is drawn once and pulsed by fading its whole window, which costs almost nothing per frame. Both are drawn with per-pixel transparency through the Win32 calls the tool already uses and OpenCV. No new dependency. It runs on its own thread inside the tool's process.
- **Settings:** `[overlay] enabled = true` by default. Off means no window is created.
- **Direct Keys and Terminals** are untouched by this work. The Terminal Key's Key Cap belongs to the `terminal-codes` feature.
- **Modules affected:** a new Overlay module (window and drawing), the Arming Window / router (report when Key Caps should show and which Trigger Key beeped), the app (drives the Overlay from those reports), and the settings loader (one new setting).

## Testing Decisions

- A good test checks what the player would see: given this sequence of Readings and key presses, are Key Caps shown, on which Slots, and does one flash.
- **Overlay can't change a Reading:** paint the Key Caps (normal and mid-flash red) and the heading onto every menu fixture, and check each Reading is identical to the one without them. Runs with the normal test suite. A first version of this check passed against all 13 fixtures and three styles during prototyping.
- **When to show, what to flash:** scripted sequences of timestamps, Readings and key presses through the Arming Window / router, as the existing tests do. No window involved.
- **Drawing:** a rendered frame has a Key Cap for exactly the given Slots and the heading; no pixel is pure white.
- The window itself (topmost, click-through, no focus) is confirmed by playing.

## Out of Scope

- Terminals and the Terminal Key (feature `terminal-codes`).
- Key Caps for Direct Keys.
- Screen sizes other than 3840x2160 (the Overlay scales like the reader, untested elsewhere).
- Excluding the Overlay from capture.
- Showing which Stratagem is in a Slot by name.

## Further Notes

- **Prototype:** `tools/prototype_overlay.py`. Run it with the game in borderless + HDR, without the tool. It reads the menu after a Call Key press and draws Key Caps and the heading. Check:
  1. the Overlay is visible over the game and the game keeps focus (the console prints the foreground window);
  2. mouse and keys still go to the game;
  3. no stutter or frame-rate drop while it shows;
  4. which style looks right (F8 cycles; the prototype labels keys 1 to 0);
  5. F7 while the menu is open: the saved Reading matches the menu.
- **Results (2026-10-14):** 1 yes, 2 yes, 4 yellow. 5: the four F7 frames read correctly with the yellow Key Caps on screen (feedback is console-only, so it looked like nothing happened). 3: "stutters sometimes", not sure whether only while the Overlay showed. The prototype was then changed to the two-window, redraw-on-change design above; the stutter check is to be repeated with it.
- Once answered, the validated decisions go into the tickets, and the prototype moves to a throwaway branch with a pointer from the first ticket.
