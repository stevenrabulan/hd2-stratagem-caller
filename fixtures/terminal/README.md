# Terminal fixtures

Crops of 3840x2160 captures from one mission on 2026-10-15 (Acquire Soil Scan Data), all at the same Prospecting Drill Terminal. Each crop is the screen from x=1100 to 2900 and y=400 to 1900, so a point (x, y) in a crop is (x + 1100, y + 400) on the screen. The crop keeps the Terminal's screen and the HUD prompt at bottom centre, and leaves out the chat and player names.

| File | What it shows |
| --- | --- |
| `drill_approaching_no_terminal.png` | 0.5 s after the Use Key: still walking up, no Terminal, a different HUD prompt |
| `drill_code_pending_angle_a.png` | INPUT ACTIVATION SEQUENCE 1/9, Code ← ↑ → → ↓ →, nothing entered, prompt `[▲][◀][▼][▶] INTERACT` |
| `drill_code_two_entered_angle_a.png` | Same Code, first two directions entered (yellow) |
| `drill_code_two_entered_reticle_over_arrows.png` | Same Code from a second angle, two entered, a pink circle crossing the 5th arrow |
| `drill_code_five_entered_hand_over_first_arrow.png` | Five entered; the character's hand covers part of the first arrow |
| `drill_code_complete_fading.png` | All six entered, the Code fading out |
| `drill_next_step_not_a_code_bar.png` | 2/9: a bar, not a Code; the INTERACT prompt is fading |
| `drill_next_step_not_a_code_grid_move_cursor.png` | CONFIRM DRILL POSITION grid; prompt reads `MOVE CURSOR`, not `INTERACT` |

## `code_area/`

Each file is exactly the region `code_area` gives at 3840x2160: the middle 1840x1040 of the screen (x=1000 to 2840, y=560 to 1600). The screen's centre, where the weapon's reticle sits, is the image's centre (920, 520). Read them with `read_terminal_code(image, 2160)`.

The first five are live grabs the tool saved after a failed Terminal Key read (`logs/failed_codes/`, 2026-10-18, Upload Data: a log-in Terminal, then Eject Hard Drive). The two extraction ones are cut from Steam JPEG screenshots (2026-10-17); the tool's live reads of those moments failed, so they are a check, not proof of the live case.

| File | What it shows |
| --- | --- |
| `login_reticle_on_third_arrow.png` | LOG IN 1/4, Code → ← ← ↑ ←, the pink reticle on the third arrow |
| `eject_reticle_on_fourth_arrow.png` | EJECT HARD DRIVE 4/4, Code → ↑ ← ↑ ↑ ↓ ↑, Terminal at a steep angle, reticle on the fourth arrow |
| `eject_steep_angle_reticle_on_fourth_arrow.png` | Same Code at a steeper angle: the nearest arrow is almost three times the area of the farthest |
| `eject_finger_near_first_arrow.png` | Same Code, square on; the character's fingertip just left of the first arrow |
| `eject_first_arrow_behind_arm.png` | Same Code; the player's arm hides the first arrow (→), six arrows show |
| `extraction_nothing_entered.png` | Extraction terminal, Code ← ↓ → ↓ ↑ ← ← ↑, nothing entered, reticle under the row |
| `extraction_seven_entered.png` | Extraction terminal, Code ↑ ↓ → ← ← ↓ ↑ ←, seven entered |
| `hellbomb_white_arrows_reticle_on_second.png` | Hellbomb arming Terminal (live grab, 2026-10-21), Code → ← ← ↑ ↓ ←, tilted about 30 degrees, the arrows near white (about 245) instead of light grey, a small reticle ring on the second arrow |
| `hellbomb_white_arrows_square_on.png` | Hellbomb arming Terminal (live grab, 2026-10-20), Code ← → ↑ ↓ → ↓, square on, the arrows near white |
