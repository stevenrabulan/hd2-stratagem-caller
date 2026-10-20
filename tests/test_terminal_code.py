from pathlib import Path

import cv2
import numpy as np
import pytest
from test_terminal_prompt import SCREEN, grab, screen_with

from stratagem_caller.terminal_code import CodeStatus, code_area, read_terminal_code

SPEC_FOLDER = Path(__file__).resolve().parent.parent / ".scratch" / "terminal-codes"

# The Code the drill Terminal showed in every Code fixture: ← ↑ → → ↓ →
DRILL_CODE = "LURRDR"

# fixture name -> (Code, how many directions are entered). To add a fixture, add a line here.
CODES = {
    "drill_code_pending_angle_a": (DRILL_CODE, 0),
    "drill_code_two_entered_angle_a": (DRILL_CODE, 2),
    "drill_code_two_entered_reticle_over_arrows": (DRILL_CODE, 2),
    "drill_code_complete_fading": (DRILL_CODE, 6),
}
# Frames with no Code on the Terminal's screen (walking up, a bar, a grid).
NO_CODE = [
    "drill_approaching_no_terminal",
    "drill_next_step_not_a_code_bar",
    "drill_next_step_not_a_code_grid_move_cursor",
]


def read(screen, screen_height=SCREEN["height"]):
    monitor = {"left": 0, "top": 0, "width": screen.shape[1], "height": screen_height}
    return read_terminal_code(grab(screen, code_area(monitor)), screen_height)


def never_shortened(reading):
    """Whatever else, a Code that is returned is the whole Code."""
    assert reading.status is not CodeStatus.READ or reading.code == DRILL_CODE, reading


@pytest.mark.parametrize("name", CODES)
def test_reads_the_code_and_how_much_is_entered_on_every_fixture(name):
    code, entered = CODES[name]
    reading = read(screen_with(name))
    assert (reading.status, reading.code, reading.entered) == (CodeStatus.READ, code, entered)
    assert reading.remaining == code[entered:]


@pytest.mark.parametrize("name", NO_CODE)
def test_frames_with_no_code_give_no_code(name):
    assert read(screen_with(name)).status is CodeStatus.NONE


def test_five_entered_reads_too():
    # SYNTHETIC: no clear real frame has five entered (the hand frame is the only five). Here the
    # first five arrows of the pending frame are recoloured yellow, as the game draws entered ones.
    screen = screen_with("drill_code_pending_angle_a")
    left_of_sixth = 1100 + 1045  # the sixth arrow starts at x=1057 of the crop
    grey = (screen.min(axis=2) >= 140) & (screen.max(axis=2) - screen.min(axis=2) <= 30)
    grey[:, left_of_sixth:] = False
    grey[1700:] = False  # not the key glyphs of the prompt
    screen[grey] = (0, 170, 196)  # BGR, as the fixtures' yellow
    reading = read(screen)
    assert (reading.status, reading.code, reading.entered) == (CodeStatus.READ, DRILL_CODE, 5)
    assert reading.remaining == "R"


def test_a_hand_over_the_first_arrow_never_gives_a_shortened_code():
    reading = read(screen_with("drill_code_five_entered_hand_over_first_arrow"))
    never_shortened(reading)
    # The fixture shows only a yellow sliver of the first arrow: it can't be told what it was.
    assert reading.status is CodeStatus.UNREADABLE


def test_a_pink_circle_across_an_arrow_never_gives_a_shortened_code():
    # The 5th arrow is crossed by the pink circle; the Code is read whole.
    reading = read(screen_with("drill_code_two_entered_reticle_over_arrows"))
    never_shortened(reading)
    assert reading.status is CodeStatus.READ


def test_the_upload_data_login_screenshot_reads_as_up_down_left_up_down():
    # A Steam JPEG at 3840x2160 of another Terminal on another planet: light arrows on grey,
    # a reticle square over the middle arrow. A check, not the only proof.
    screen = cv2.imread(str(SPEC_FOLDER / "upload_data_login_steam.jpg"))
    reading = read(screen)
    assert (reading.status, reading.code, reading.entered) == (CodeStatus.READ, "UDLUD", 0)


def warped(name, degrees, shear=0.0):
    """The fixture's screen turned about its centre and sheared, as if the player stood elsewhere."""
    screen = screen_with(name)
    centre = (SCREEN["width"] / 2, SCREEN["height"] / 2)
    turn = cv2.getRotationMatrix2D(centre, degrees, 1.0)
    turn[0, 1] += shear
    turn[0, 2] -= shear * centre[1]
    return cv2.warpAffine(screen, turn, (SCREEN["width"], SCREEN["height"]))


@pytest.mark.parametrize("degrees", [-40, -20, 0, 15, 35])
@pytest.mark.parametrize("shear", [-0.3, 0.0, 0.3])
def test_the_angle_and_skew_of_the_terminal_do_not_change_the_directions(degrees, shear):
    # The fixture is already tilted about 20 degrees; this tilts it further each way.
    reading = read(warped("drill_code_two_entered_angle_a", degrees, shear))
    never_shortened(reading)
    if reading.status is CodeStatus.READ:
        assert reading.entered == 2


def test_a_moderate_tilt_is_read_not_given_up():
    for degrees, shear in [(-20, 0.0), (15, 0.0), (0, 0.3)]:
        assert read(warped("drill_code_two_entered_angle_a", degrees, shear)).status is CodeStatus.READ


def test_an_arrow_hidden_in_the_middle_makes_the_code_unreadable():
    screen = screen_with("drill_code_pending_angle_a")
    cv2.circle(screen, (1100 + 838, 400 + 672), 60, (0, 0, 0), -1)  # a hand over the third arrow
    assert read(screen).status is CodeStatus.UNREADABLE


def test_a_pink_bar_cutting_an_arrow_in_two_never_gives_a_shortened_code():
    screen = screen_with("drill_code_pending_angle_a")
    cv2.line(screen, (1100 + 1008 - 50, 400 + 736 + 25), (1100 + 1008 + 50, 400 + 736 - 25), (137, 52, 255), 14)
    never_shortened(read(screen))


def test_a_sliver_of_an_arrow_beyond_the_last_one_makes_the_code_unreadable():
    screen = screen_with("drill_code_pending_angle_a")
    # Hide most of the last arrow: a stub is left where it was.
    cv2.rectangle(screen, (1100 + 1092 - 45, 400 + 772 - 45), (1100 + 1092 + 45, 400 + 772 + 8), (0, 0, 0), -1)
    assert read(screen).status is CodeStatus.UNREADABLE


def test_film_grain_and_a_glow_of_fire_behind_the_arrows_do_not_change_the_reading():
    screen = screen_with("drill_code_two_entered_angle_a")
    region = grab(screen, code_area(SCREEN)).copy()
    grain = np.random.default_rng(1).integers(0, 12, region.shape, dtype=np.uint8)
    glow = np.zeros_like(region)
    glow[:, :] = (0, 70, 110)  # orange, BGR: not grey and not the yellow of an entered arrow
    behind = region.max(axis=2, keepdims=True) < 100  # only what is behind the arrows, not the arrows
    reading = read_terminal_code(np.where(behind, cv2.add(cv2.add(region, grain), glow), region), SCREEN["height"])
    assert (reading.status, reading.code, reading.entered) == (CodeStatus.READ, DRILL_CODE, 2)


def test_the_code_area_is_the_screen_centre_and_scales_with_the_screen():
    full, half = code_area(SCREEN), code_area({"left": 0, "top": 0, "width": 1920, "height": 1080})
    assert (half["left"], half["top"], half["width"], half["height"]) == (
        full["left"] // 2,
        full["top"] // 2,
        full["width"] // 2,
        full["height"] // 2,
    )
    assert full["left"] + full["width"] // 2 == SCREEN["width"] // 2  # centred: the reticle is on the Terminal


def test_reads_at_a_smaller_screen_size_too():
    small = {"left": 0, "top": 0, "width": 1920, "height": 1080}
    for name, (code, entered) in CODES.items():
        shrunk = cv2.resize(screen_with(name), (1920, 1080), interpolation=cv2.INTER_AREA)
        reading = read_terminal_code(grab(shrunk, code_area(small)), 1080)
        assert (reading.status, reading.code, reading.entered) == (CodeStatus.READ, code, entered), name


def test_an_empty_region_has_no_code():
    area = code_area(SCREEN)
    assert read_terminal_code(np.zeros((area["height"], area["width"], 3), np.uint8)).status is CodeStatus.NONE


def test_a_region_that_cannot_hold_an_arrow_is_an_error_not_a_quiet_no_code():
    with pytest.raises(ValueError, match="too small"):
        read_terminal_code(np.zeros((40, 400, 3), np.uint8))
    with pytest.raises(ValueError, match="colour image"):
        read_terminal_code(np.zeros((500, 500), np.uint8))


# --- Code areas from 2026-10-17 and 2026-10-18 (ticket terminal-codes/06) ---
# Each is the region code_area gives at 3840x2160, so the screen's centre (where the weapon's
# reticle sits) is the image's centre. See fixtures/terminal/README.md.

CODE_AREA_FOLDER = Path(__file__).resolve().parent.parent / "fixtures" / "terminal" / "code_area"
EJECT_CODE = "RULUUDU"  # → ↑ ← ↑ ↑ ↓ ↑, typed by the tool at 15:33:51 once it read it

# fixture name -> (Code, how many directions are entered)
AREA_CODES = {
    "login_reticle_on_third_arrow": ("RLLUL", 0),
    "eject_reticle_on_fourth_arrow": (EJECT_CODE, 0),
    "eject_steep_angle_reticle_on_fourth_arrow": (EJECT_CODE, 0),
    "eject_finger_near_first_arrow": (EJECT_CODE, 0),
    "extraction_nothing_entered": ("LDRDULLU", 0),
    "extraction_seven_entered": ("UDRLLDUL", 7),
}
# Read wrong today: the reticle cuts the arrow under it apart, and on a steep angle the near arrows
# are too big for the area filter. Remove a name here once ticket 06 reads it.
NOT_READ_YET = {
    "login_reticle_on_third_arrow",
    "eject_reticle_on_fourth_arrow",
    "eject_steep_angle_reticle_on_fourth_arrow",
    "eject_finger_near_first_arrow",
}
NOT_YET = pytest.mark.xfail(strict=True, reason="ticket terminal-codes/06")


def code_area_fixture(name):
    return cv2.imread(str(CODE_AREA_FOLDER / f"{name}.png"))


def read_area(region):
    return read_terminal_code(region, SCREEN["height"])


@pytest.mark.parametrize(
    "name", [pytest.param(n, marks=NOT_YET) if n in NOT_READ_YET else n for n in AREA_CODES]
)
def test_reads_the_code_on_every_code_area_fixture(name):
    code, entered = AREA_CODES[name]
    reading = read_area(code_area_fixture(name))
    assert (reading.status, reading.code, reading.entered) == (CodeStatus.READ, code, entered)


@pytest.mark.parametrize("name", AREA_CODES)
def test_a_code_area_fixture_never_gives_a_wrong_code(name):
    """Until a fixture is read, the reader may give up on it; it must never type a wrong Code."""
    code, _ = AREA_CODES[name]
    reading = read_area(code_area_fixture(name))
    assert reading.status is not CodeStatus.READ or reading.code == code, reading


def test_the_first_arrow_hidden_behind_the_arm_makes_the_code_unreadable():
    # The player's arm covers the → that starts the Code: six arrows show, and they are not the Code.
    reading = read_area(code_area_fixture("eject_first_arrow_behind_arm"))
    assert reading.status is CodeStatus.UNREADABLE, reading


def draw_reticle(region, kind):
    """Another weapon's reticle at the screen's centre, drawn over what is there. Sizes are at 4K."""
    out = region.copy()
    h, w = out.shape[:2]
    cx, cy = w // 2, h // 2
    if kind == "grey_crosshair":  # four pale grey ticks with a gap: the arrows' own grey
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            cv2.line(out, (cx + 14 * dx, cy + 14 * dy), (cx + 50 * dx, cy + 50 * dy), (200, 200, 200), 5)
    elif kind == "green_dot":
        cv2.circle(out, (cx, cy), 16, (60, 220, 60), -1)
    elif kind == "orange_chevron":
        cv2.polylines(out, [np.array([(cx - 36, cy + 10), (cx, cy + 40), (cx + 36, cy + 10)])], False, (0, 140, 255), 7)
    elif kind == "wide_white_ring":
        cv2.circle(out, (cx, cy), 60, (250, 250, 250), 6)
    return out


RETICLES = ["grey_crosshair", "green_dot", "orange_chevron", "wide_white_ring"]


@pytest.mark.parametrize(
    "kind", [k if k == "grey_crosshair" else pytest.param(k, marks=NOT_YET) for k in RETICLES]
)
def test_any_reticle_over_the_middle_arrow_still_reads(kind):
    # SYNTHETIC: different weapons draw different reticles at the screen's centre. Whatever its shape
    # or colour, the arrow under it is read. (The grey crosshair reads today only because its ticks
    # join the pieces the pink reticle cuts the arrow into.)
    reading = read_area(draw_reticle(code_area_fixture("login_reticle_on_third_arrow"), kind))
    assert (reading.status, reading.code) == (CodeStatus.READ, "RLLUL"), reading


@pytest.mark.parametrize("kind", RETICLES)
def test_any_reticle_below_the_row_does_not_change_the_reading(kind):
    # SYNTHETIC: on the extraction terminal the reticle sits under the row, not on an arrow.
    reading = read_area(draw_reticle(code_area_fixture("extraction_nothing_entered"), kind))
    assert (reading.status, reading.code) == (CodeStatus.READ, "LDRDULLU"), reading


@pytest.mark.parametrize("kind", RETICLES)
def test_any_reticle_on_an_empty_screen_is_no_code(kind):
    area = code_area(SCREEN)
    empty = np.full((area["height"], area["width"], 3), 25, np.uint8)
    assert read_area(draw_reticle(empty, kind)).status is CodeStatus.NONE
