from pathlib import Path

import cv2
import numpy as np
import pytest

from stratagem_caller.terminal_prompt import TerminalPrompt, prompt_area, read_terminal_prompt

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "terminal"
# Each fixture is the screen from x=1100, y=400 (fixtures/terminal/README.md).
CROP_ORIGIN = (1100, 400)
SCREEN = {"left": 0, "top": 0, "width": 3840, "height": 2160}

CASES = {
    "drill_approaching_no_terminal": TerminalPrompt.NONE,  # "Press [key] to check map waypoint"
    "drill_code_pending_angle_a": TerminalPrompt.INTERACT,
    "drill_code_two_entered_angle_a": TerminalPrompt.INTERACT,
    "drill_code_two_entered_reticle_over_arrows": TerminalPrompt.INTERACT,
    "drill_code_five_entered_hand_over_first_arrow": TerminalPrompt.INTERACT,
    "drill_code_complete_fading": TerminalPrompt.INTERACT,  # the Code fades, the prompt does not yet
    "drill_next_step_not_a_code_bar": TerminalPrompt.INTERACT,  # the prompt itself is fading, still read
    "drill_next_step_not_a_code_grid_move_cursor": TerminalPrompt.MOVE_CURSOR,
}


def screen_with(name):
    """A black 3840x2160 screen with the fixture's crop pasted where it was taken."""
    crop = cv2.imread(str(FIXTURES / f"{name}.png"))
    screen = np.zeros((SCREEN["height"], SCREEN["width"], 3), np.uint8)
    x, y = CROP_ORIGIN
    screen[y : y + crop.shape[0], x : x + crop.shape[1]] = crop
    return screen


def grab(screen, area):
    return screen[area["top"] : area["top"] + area["height"], area["left"] : area["left"] + area["width"]]


@pytest.mark.parametrize("name", CASES)
def test_reads_the_terminal_prompt_on_every_fixture(name):
    region = grab(screen_with(name), prompt_area(SCREEN))
    assert read_terminal_prompt(region) is CASES[name]


def test_an_empty_region_has_no_terminal_prompt():
    region = np.zeros((prompt_area(SCREEN)["height"], prompt_area(SCREEN)["width"], 3), np.uint8)
    assert read_terminal_prompt(region) is TerminalPrompt.NONE


def test_a_bright_scene_behind_the_prompt_does_not_hide_it():
    # Gunfire or flames behind the prompt box: noise must not make INTERACT read as absent.
    screen = screen_with("drill_code_pending_angle_a")
    area = prompt_area(SCREEN)
    region = grab(screen, area).copy()
    noise = np.random.default_rng(1).integers(0, 40, region.shape, dtype=np.uint8)
    assert read_terminal_prompt(cv2.add(region, noise)) is TerminalPrompt.INTERACT


def test_the_prompt_area_scales_with_the_screen():
    full, half = prompt_area(SCREEN), prompt_area({"left": 0, "top": 0, "width": 1920, "height": 1080})
    assert (half["left"], half["top"], half["width"], half["height"]) == (
        full["left"] // 2,
        full["top"] // 2,
        full["width"] // 2,
        full["height"] // 2,
    )


def test_reads_at_a_smaller_screen_size_too():
    small = {"left": 0, "top": 0, "width": 1920, "height": 1080}
    for name in ("drill_code_pending_angle_a", "drill_next_step_not_a_code_grid_move_cursor"):
        shrunk = cv2.resize(screen_with(name), (1920, 1080), interpolation=cv2.INTER_AREA)
        region = grab(shrunk, prompt_area(small))
        assert read_terminal_prompt(region, 1080) is CASES[name]


def test_a_region_too_small_to_hold_the_words_is_an_error_not_a_quiet_no_prompt():
    with pytest.raises(ValueError, match="too small"):
        read_terminal_prompt(np.zeros((20, 100, 3), np.uint8))
