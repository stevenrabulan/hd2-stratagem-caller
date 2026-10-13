# Stratagem Caller

A companion tool for Helldivers 2 that reads the player's available stratagems off the screen and lets them call one with a single key instead of typing its arrow code.

## Language

**Stratagem**:
A call-in the player can request during a mission, whether chosen in the loadout or granted by the mission.
_Avoid_: Strategem, strat, call-in

**Stratagem Menu**:
The in-game list of currently available stratagems, shown when the player presses the Call Key.
_Avoid_: Stratagem list, HUD list, wheel

**Slot**:
A position in the Stratagem Menu counted from the top, starting at 1. A Slot is a position, not a particular Stratagem.
_Avoid_: Row, index, stratagem number

**Code**:
The ordered sequence of directions the game requires to call a Stratagem.
_Avoid_: Key code, combo, arrow sequence

**Reading**:
The Codes and Icons the tool observed in the Stratagem Menu at one moment.
_Avoid_: Scan, screenshot, capture

**Icon**:
The picture the game shows beside a Stratagem in the Stratagem Menu.

**Call Key**:
The key the player has bound in-game to open the Stratagem Menu.
_Avoid_: Stratagem key, menu key, "b"

**Direction Keys**:
The four keys the player has bound in-game to enter the directions of a Code.
_Avoid_: Arrow keys, stratagem arrows

**Trigger Key**:
A key that chooses a Slot when pressed inside the Arming Window, after the player has pressed the Call Key themselves. Digits by default.
_Avoid_: Hotkey, number key, bind

**Direct Key**:
A key that Calls one specific Stratagem in a single press, using a Code the player configured rather than one taken from a Reading. It needs no Call Key press from the player and no Arming Window.
_Avoid_: Hotkey, macro key, quick bind

**Code Book**:
The editable list of known Stratagem names and their Codes that Direct Keys can refer to by name.
_Avoid_: Hardcoded list, database, table

**Arming Window**:
The time during which the tool sees the Stratagem Menu open and so acts on Trigger Keys. Outside it, Trigger Keys behave as ordinary keys.
_Avoid_: Timeout, listen window, one-second window

**Call**:
Entering a Slot's Code on the player's behalf.
_Avoid_: Cast, fire, macro

**Overlay**:
An optional on-screen display showing which Icon belongs to which Trigger Key.
