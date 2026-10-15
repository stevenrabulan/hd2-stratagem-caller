# 04: The ENTER CODE Key Cap, with its red flash

**What to build:** While a Code is read, the Overlay shows a yellow Key Cap for the Terminal Key followed by ENTER CODE in the game's prompt style, just right of the Terminal Prompt at the same height. It hides when the Code is entered, when the Terminal Prompt goes, on focus loss and on pause. When the Terminal Key beeps because the Code can't be read, the Key Cap flashes red three times, as Trigger Key Key Caps do. It follows the Overlay's existing rules: redrawn only on change, never pure white, never over pixels the reader checks. See "Key Cap" in the spec.

**Blocked by:** 03

**Status:** ready-for-agent

- [ ] Given scripted readings, the Key Cap shows exactly while a Code is read, and flashes on an unreadable-Code beep
- [ ] The Key Cap shows the configured Terminal Key's name
- [ ] Painting the Key Cap onto every Terminal fixture (normal and red) leaves the Terminal Prompt and Code readings unchanged
- [ ] (player) In-game: the Key Cap appears beside INTERACT at a drill Terminal and goes once the Code is entered
