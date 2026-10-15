from pathlib import Path

import cv2
import numpy as np
import pytest

from stratagem_caller import reader
from stratagem_caller.keycaps import column_box, render_key_caps
from stratagem_caller.reader import WHITE_THRESHOLD, read_menu

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "menu"
ALL_SLOTS = {n: str(n % 10) for n in range(1, 11)}
YELLOW_BGRA = (0, 233, 255, 255)  # #FFE900, the game's yellow


def slot_rows(slot, s=1.0):
    """Rows of a rendered frame that belong to a Slot: its Icon's rows, as the reader sees them."""
    top = round((reader.ICON_TOP + (slot - 1) * reader.SLOT_PITCH) * s)
    return slice(top, top + round(reader.ICON_SIZE * s))


def drawn(frame, rows):
    return bool(frame[rows, :, 3].any())


def test_a_key_cap_is_drawn_for_exactly_the_given_slots():
    frame = render_key_caps({1: "1", 3: "3", 10: "0"}, 2160)
    assert [n for n in range(1, 11) if drawn(frame, slot_rows(n))] == [1, 3, 10]


def test_nothing_is_drawn_for_no_slots():
    assert not render_key_caps({}, 2160)[:, :, 3].any()


def test_key_cap_is_the_games_yellow_with_a_dark_glyph():
    frame = render_key_caps({2: "2"}, 2160)
    left, _, _, _ = column_box(2160)
    rows = slot_rows(2)
    middle = (rows.start + rows.stop) // 2
    corner_clear = tuple(frame[middle - 20, 46 + 8 - left])  # inside the fill, off the glyph
    assert corner_clear == YELLOW_BGRA
    body = frame[rows, :, :]
    dark = (body[:, :, :3].max(axis=2) < 80) & (body[:, :, 3] == 255)
    assert dark.sum() > 30  # the glyph


def test_key_cap_shows_the_given_name():
    one = render_key_caps({1: "1"}, 2160)
    zero = render_key_caps({1: "0"}, 2160)
    assert not np.array_equal(one, zero)
    assert np.array_equal(zero, render_key_caps({1: "0"}, 2160))


def test_key_cap_is_centred_on_its_icon_and_left_of_it():
    frame = render_key_caps({4: "4"}, 2160)
    left, _, _, _ = column_box(2160)
    rows = slot_rows(4)
    ys, xs = np.nonzero(frame[:, :, 3])
    icon_middle = (rows.start + rows.stop) / 2
    assert abs((ys.min() + ys.max()) / 2 - icon_middle) <= 4
    assert xs.max() + left < reader.ICON_LEFT


def test_no_pixel_is_pure_white():
    frame = render_key_caps(ALL_SLOTS, 2160)
    assert frame[:, :, :3].min(axis=2).max() < WHITE_THRESHOLD


@pytest.mark.parametrize("height", [2160, 1440, 1080])
def test_nothing_is_drawn_in_the_arrow_gutter_or_past_the_key_cap_column(height):
    s = height / 2160
    frame = render_key_caps({**ALL_SLOTS, 5: "page down"}, height)
    left, top, width, box_height = column_box(height)
    assert frame.shape == (box_height, width, 4)
    ys, xs = np.nonzero(frame[:, :, 3])
    slack = 0 if height == 2160 else 1  # rounding at other sizes
    assert xs.max() + left < 98 * s + slack  # ticket: nothing at x >= 98 (at 4K)
    assert xs.min() + left >= round(46 * s) - 1  # nor left of the column, even for a long name
    assert xs.min() > 0 and xs.max() < width - 1


@pytest.mark.parametrize("height", [1440, 1080])
def test_key_caps_scale_with_screen_height(height):
    s = height / 2160
    frame = render_key_caps({1: "1", 6: "6"}, height)
    assert [n for n in range(1, 11) if drawn(frame, slot_rows(n, s))] == [1, 6]


def test_a_long_key_name_is_shortened_to_fit_the_key_cap():
    frame = render_key_caps({1: "page down"}, 2160)
    left, _, _, _ = column_box(2160)
    ys, xs = np.nonzero(frame[:, :, 3])
    assert xs.min() + left >= 46 - 1 and xs.max() + left <= 96 + 1


# --- the Overlay cannot change a Reading ---


def paint(region, frame, left, top):
    """Composite a premultiplied BGRA frame onto a BGR region, as the screen does."""
    out = region.copy()
    height, width = frame.shape[:2]
    behind = out[top : top + height, left : left + width].astype(np.int32)
    alpha = frame[:, :, 3:4].astype(np.int32)
    out[top : top + height, left : left + width] = frame[:, :, :3] + (behind * (255 - alpha) + 127) // 255
    return out


def same_reading(a, b):
    return (
        a.codes == b.codes
        and a.unreadable == b.unreadable
        and a.menu_open == b.menu_open
        and a.icons.keys() == b.icons.keys()
        and all(np.array_equal(a.icons[n], b.icons[n]) for n in a.icons)
    )


MENU_FIXTURES = sorted(FIXTURES.glob("*.png"))


def test_there_are_menu_fixtures_to_paint_on():
    assert len(MENU_FIXTURES) >= 13


@pytest.mark.parametrize("path", MENU_FIXTURES, ids=lambda p: p.stem)
def test_key_caps_painted_on_a_menu_do_not_change_its_reading(path):
    region = cv2.imread(str(path))
    before = read_menu(region)
    left, top, _, _ = column_box(2160)
    listed = {n: str(n % 10) for n in before.icons}
    for names in (listed, ALL_SLOTS):  # what the Overlay would show, and every Slot at once
        painted = paint(region, render_key_caps(names, 2160), left, top)
        assert names is listed or not np.array_equal(painted, region)
        assert same_reading(before, read_menu(painted))
