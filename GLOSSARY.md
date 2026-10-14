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
The ordered sequence of directions the game requires to call a Stratagem or to operate a Terminal.
_Avoid_: Key code, combo, arrow sequence

**Reading**:
What the tool observed on screen at one moment: the Codes and Icons in the Stratagem Menu, or the Code a Terminal is showing.
_Avoid_: Scan, screenshot, capture, OCR

**Icon**:
The picture the game shows beside a Stratagem in the Stratagem Menu.

**Call Key**:
The key the player has bound in-game to open the Stratagem Menu.
_Avoid_: Stratagem key, menu key, "b"

**Direction Keys**:
The four keys the player has bound in-game to enter the directions of a Code.
_Avoid_: Arrow keys, stratagem arrows

**Trigger Key**:
A key that chooses a Slot when pressed while the Stratagem Menu is open (inside the Arming Window), after the player has pressed the Call Key themselves. Digits by default.
_Avoid_: Hotkey, number key, bind

**Direct Key**:
A key that Calls one specific Stratagem in a single press, using a Code the player configured rather than one taken from a Reading. It needs no Call Key press from the player and no Arming Window.
_Avoid_: Hotkey, macro key, quick bind

**Code Book**:
The editable list of known Stratagem names and their Codes that Direct Keys can refer to by name.
_Avoid_: Hardcoded list, database, table

**Arming Window**:
The time from when the tool confirms the Stratagem Menu is open after a Call Key press until it confirms the menu has closed, however long that is, and so acts on Trigger Keys. Outside it, Trigger Keys behave as ordinary keys.
_Avoid_: Timeout, listen window, one-second window

**Call**:
Entering a Slot's Code on the player's behalf.
_Avoid_: Cast, fire, macro

**Terminal**:
A mission object that asks the player for a Code after they press the Use Key at it, such as the extraction terminal.
_Avoid_: Console, mission terminal

**Use Key**:
The key the player has bound in-game to interact with objects. E by default.
_Avoid_: Interact key, "E"

**Terminal Key**:
A key that enters the Code a Terminal is showing, on the player's behalf. Return by default.
_Avoid_: Enter key, return key

**Overlay**:
A display the tool draws over the game, showing Key Caps.
_Avoid_: HUD, window

**Key Cap**:
A drawing of a key in the Overlay, placed beside the thing that key acts on, such as a Trigger Key beside its Slot.
_Avoid_: Badge, label, key hint
