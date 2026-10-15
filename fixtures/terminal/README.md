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
