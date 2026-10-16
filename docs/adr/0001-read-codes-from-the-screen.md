# Read Codes from the screen; use the Code Book only for Direct Keys

Helldivers 2 sometimes adds temporary Stratagems or changes a Code, so a built-in table goes stale without warning. Trigger Keys therefore take their Codes from a Reading of the Stratagem Menu and never from a table, which also lets them address a Slot without knowing which Stratagem is in it. Direct Keys are the deliberate exception: they must work in one press without looking at the screen, so they use a Code the player configured, either written out or looked up by name in the editable Code Book.

## Consequences

- Trigger Keys depend on screen capture and image recognition working on the player's display setup (resolution, scaling, HDR). Direct Keys do not.
- A Direct Key types its Code blind. With a Call Key that toggles, pressing one while the Stratagem Menu is already open closes the menu instead of calling. The one exception is while the tool is watching a menu the player opened with the Call Key: it knows the menu is open or opening, so it skips the Call Key press.
- The Code Book needs manual upkeep; a wrong entry affects only Direct Keys that name it.
