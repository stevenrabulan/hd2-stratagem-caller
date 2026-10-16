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


def test_icon_is_returned_for_each_slot_whose_icon_is_in_place():
    region = cv2.imread(str(FIXTURES / "some_on_cooldown.png"))
    reading = read_menu(region)
    # Seven Stratagems are listed; Slots 1-3 and 7 are on cooldown and still show an Icon.
    assert set(reading.icons) == set(range(1, 8))
    assert all(icon.shape == (86, 86, 3) for icon in reading.icons.values())


@pytest.mark.parametrize(
    "name, slots",
    [
        ("open_menu_nothing_callable", range(1, 8)),
        ("open_menu_only_reinforce", [1]),
        ("mission_stratagem_inserted", range(1, 9)),
        ("ping_over_last_arrow", range(1, 7)),
        ("menu_closed_bright_sky", []),
    ],
)
def test_reading_reports_every_slot_with_an_icon_in_place_callable_or_not(name, slots):
    assert set(_read(name).icons) == set(slots)


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


@pytest.mark.parametrize(
    "name, codes",
    [
        # Sky right of the menu: one bright blob whose extent spans Slots 1-5,
        # though none of its pixels touch an arrow line.
        ("bright_sky_beside_menu", {2: RESUPPLY, 6: AUTOCANNON_SENTRY}),
        # A light above and right of Slot 4's short Code, past its last arrow.
        ("bright_light_above_short_code", {4: "RDURD", 6: AUTOCANNON_SENTRY}),
    ],
)
def test_bright_scenery_off_the_arrows_leaves_codes_readable(name, codes):
    reading = _read(name)
    assert reading.codes == codes
    assert reading.unreadable == set()


def test_fog_over_the_last_arrows_gives_no_shortened_code():
    # White fog behind Resupply swallows its last two arrows; only DD is visible.
    reading = _read("fog_over_last_arrows")
    assert 2 not in reading.codes
    assert 2 in reading.unreadable
    assert reading.codes == {
        3: "RDUULDD",
        4: "RUUD",
        6: WARP_PACK,
        7: PATRIOT_EXOSUIT,
        8: "URLR",
    }


def test_marker_over_the_first_arrow_makes_the_slot_unreadable():
    # A map marker ("B2") hides Patriot Exosuit's first arrow: wait for a clean
    # view rather than treat the Slot as not callable.
    reading = _read("marker_over_first_arrow")
    assert 7 not in reading.codes
    assert reading.unreadable == {7}


def test_ping_over_the_last_arrow_makes_the_slot_unreadable():
    # A red map ping sits on Resupply's last arrow; its distance label sits
    # between Slots 2 and 3 and leaves Slot 3 readable. (The yellow digits left
    # of the Icons are an Overlay prototype, outside what the reader checks.)
    reading = _read("ping_over_last_arrow")
    assert 2 not in reading.codes
    assert reading.unreadable == {2}
    assert reading.codes == {3: "RRDLRD", 4: WARP_PACK, 5: "LDRURLU", 6: "DURDL"}


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
