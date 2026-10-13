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


def _read(name):
    return read_menu(cv2.imread(str(FIXTURES / f"{name}.png")))


def test_glow_behind_last_arrow_gives_no_shortened_code():
    reading = _read("glow_behind_last_arrow")
    resupply_slot = next(s for s in range(1, 11) if s in reading.unreadable)
    assert resupply_slot not in reading.codes
    assert reading.unreadable == {resupply_slot}


def test_same_menu_without_glow_yields_the_full_code():
    reading = _read("glow_gone_same_menu")
    assert RESUPPLY in reading.codes.values()
    assert reading.unreadable == set()


def test_lone_arrow_while_sliding_in_gives_no_code():
    reading = _read("lone_arrow_while_sliding_in")
    assert reading.codes == {}
    assert reading.unreadable


@pytest.mark.parametrize(
    "name", ["some_on_cooldown", "menu_closed_bright_sky", "menu_sliding_in", "one_direction_entered"]
)
def test_status_text_or_closed_menu_is_not_unreadable(name):
    assert _read(name).unreadable == set()


OPEN_MENUS = [
    "some_on_cooldown",
    "mission_stratagem_inserted",
    "resupply_available",
    "seven_arrow_code_at_slot_3",
    "one_direction_entered",
    "glow_behind_last_arrow",
    "glow_gone_same_menu",
    "open_menu_nothing_callable",
]


@pytest.mark.parametrize("name", OPEN_MENUS)
def test_settled_open_menu_reports_open(name):
    assert _read(name).menu_open


def test_open_menu_with_nothing_callable_is_open_with_no_codes():
    reading = _read("open_menu_nothing_callable")
    assert reading.menu_open
    assert reading.codes == {}
    assert reading.unreadable == set()


def test_closed_menu_over_bright_sky_reports_closed():
    assert not _read("menu_closed_bright_sky").menu_open


def test_menu_still_sliding_in_does_not_report_open_yet():
    # The rows are not in place, so the menu is not open yet; a user waiting for
    # an open menu keeps waiting.
    assert not _read("menu_sliding_in").menu_open
    assert not _read("lone_arrow_while_sliding_in").menu_open


def test_a_row_showing_without_the_menu_open_is_not_an_open_menu():
    # The game briefly shows a single row (here Resupply coming off cooldown)
    # beside the collapsed header while the menu is closed.
    assert not _read("closed_menu_one_row_showing").menu_open


def test_menu_with_only_reinforce_available_is_open():
    # A dead player's menu lists only Reinforce, with its Code.
    reading = _read("open_menu_only_reinforce")
    assert reading.menu_open
    assert reading.codes == {1: "UDRLU"}
