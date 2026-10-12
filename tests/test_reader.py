from pathlib import Path

import cv2
import pytest

from stratagem_caller.reader import read_menu

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "menu"

WARP_PACK = "DLRDLR"
PATRIOT_EXOSUIT = "LDRULDD"
AUTOCANNON_SENTRY = "DURULU"
RESUPPLY = "DDUR"

# Each fixture is the top-left 800x1500 of a 3840x2160 capture.
CASES = {
    # Slots 1-3 and 7 show "Ready" or a cooldown timer instead of arrows.
    "some_on_cooldown": {4: "RDURD", 5: WARP_PACK, 6: PATRIOT_EXOSUIT},
    # A mission Stratagem (Upload Data) appeared at Slot 3 and pushed the rest down.
    "mission_stratagem_inserted": {
        3: "LRUUU",
        6: WARP_PACK,
        7: PATRIOT_EXOSUIT,
        8: AUTOCANNON_SENTRY,
    },
    "resupply_available": {
        2: RESUPPLY,
        5: WARP_PACK,
        6: PATRIOT_EXOSUIT,
        7: AUTOCANNON_SENTRY,
    },
    "seven_arrow_code_at_slot_3": {2: RESUPPLY, 3: "RDUULDD", 5: WARP_PACK},
    "menu_closed_bright_sky": {},
    # 100 ms after the Call Key: rows are still sliding in from the left.
    "menu_sliding_in": {},
}


@pytest.mark.parametrize("name", CASES)
def test_reads_codes_by_slot(name):
    region = cv2.imread(str(FIXTURES / f"{name}.png"))
    assert read_menu(region).codes == CASES[name]


def test_partly_entered_code_is_not_read():
    # The player has typed one direction: the first arrow of Slot 4 is yellow
    # and the Stratagems that no longer match are dimmed.
    region = cv2.imread(str(FIXTURES / "one_direction_entered.png"))
    assert read_menu(region).codes == {}


def test_icon_is_returned_for_each_readable_slot():
    region = cv2.imread(str(FIXTURES / "some_on_cooldown.png"))
    reading = read_menu(region)
    assert set(reading.icons) == set(reading.codes)
    assert all(icon.shape == (86, 86, 3) for icon in reading.icons.values())
