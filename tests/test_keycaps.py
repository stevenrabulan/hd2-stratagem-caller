from pathlib import Path

import cv2
import numpy as np
import pytest

from stratagem_caller import reader
from stratagem_caller.heading import PULSE_LOW, heading_box, render_heading
from stratagem_caller.keycaps import (
    TerminalKeyCap,
    column_box,
    render_icon,
    render_key_caps,
    render_terminal_key_cap,
    terminal_key_cap_box,
)
from stratagem_caller.reader import WHITE_THRESHOLD, read_menu
from stratagem_caller.terminal_code import code_area, read_terminal_code
from stratagem_caller.terminal_prompt import prompt_area, read_terminal_prompt

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "menu"
ALL_SLOTS = {n: str(n % 10) for n in range(1, 11)}
YELLOW_BGRA = (0, 233, 255, 255)  # #FFE900, the game's yellow
RED_BGRA = (40, 40, 215, 255)


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


def fill_at(frame, slot):
    """The colour of a Slot's Key Cap fill, sampled inside it and off the glyph."""
    left, _, _, _ = column_box(2160)
    rows = slot_rows(slot)
    middle = (rows.start + rows.stop) // 2
    return tuple(frame[middle - 20, 46 + 8 - left])


def test_a_red_key_cap_has_a_red_fill_and_the_others_stay_yellow():
    frame = render_key_caps({1: "1", 2: "2", 3: "3"}, 2160, red=frozenset({2}))
    assert [fill_at(frame, n) for n in (1, 2, 3)] == [YELLOW_BGRA, RED_BGRA, YELLOW_BGRA]


def test_a_red_key_cap_is_drawn_where_the_normal_one_is():
    normal = render_key_caps({2: "2"}, 2160)
    red = render_key_caps({2: "2"}, 2160, red=frozenset({2}))
    assert not np.array_equal(normal, red)
    assert np.array_equal(normal[:, :, 3], red[:, :, 3])  # same shape, only the colour changes


def test_a_red_slot_with_no_key_cap_draws_nothing():
    assert not render_key_caps({}, 2160, red=frozenset({4}))[:, :, 3].any()
    frame = render_key_caps({1: "1"}, 2160, red=frozenset({4}))
    assert [n for n in range(1, 11) if drawn(frame, slot_rows(n))] == [1]


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
    frame = render_key_caps(ALL_SLOTS, 2160, red=frozenset({2, 5}))
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


def paint(region, frame, left, top, clip=False):
    """Composite a premultiplied BGRA frame onto a BGR region, as the screen does. With
    `clip`, a frame reaching past the region is cut off (the reader never sees past it)."""
    out = region.copy()
    height, width = frame.shape[:2]
    if clip:
        height, width = min(height, out.shape[0] - top), min(width, out.shape[1] - left)
        frame = frame[:height, :width]
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
    # What the Overlay would show, and every Slot at once; normal, one mid-flash, and all red.
    for names in (listed, ALL_SLOTS):
        for red in (frozenset(), frozenset(list(names)[:1]), frozenset(names)):
            painted = paint(region, render_key_caps(names, 2160, red=red), left, top)
            assert names is listed or not np.array_equal(painted, region)
            assert same_reading(before, read_menu(painted))


@pytest.mark.parametrize("path", MENU_FIXTURES, ids=lambda p: p.stem)
def test_the_heading_painted_where_it_sits_does_not_change_a_menus_reading(path):
    region = cv2.imread(str(path))
    before = read_menu(region)
    left, top, _, _ = heading_box(2160)
    painted = paint(region, render_heading(2160), left, top, clip=True)
    assert not np.array_equal(painted, region)
    assert same_reading(before, read_menu(painted))


@pytest.mark.parametrize("path", MENU_FIXTURES, ids=lambda p: p.stem)
def test_the_heading_at_its_faintest_and_with_every_key_cap_does_not_change_a_menus_reading(path):
    """Everything the Overlay can have up at once, the heading at full strength and mid-fade."""
    region = cv2.imread(str(path))
    before = read_menu(region)
    key_caps_left, key_caps_top, _, _ = column_box(2160)
    heading_left, heading_top, _, _ = heading_box(2160)
    for opacity in (255, PULSE_LOW):
        heading = render_heading(2160).astype(np.int32) * opacity // 255  # a faded window, as the screen blends it
        painted = paint(region, render_key_caps(ALL_SLOTS, 2160, red=frozenset({3})), key_caps_left, key_caps_top)
        painted = paint(painted, heading.astype(np.uint8), heading_left, heading_top, clip=True)
        assert same_reading(before, read_menu(painted))


# --- the Key Cap with an up arrow, drawn for the Tray Icon and the shortcut ---


@pytest.mark.parametrize("size", [16, 32, 64, 256])
def test_icon_is_a_square_of_the_asked_size(size):
    assert render_icon(size).shape == (size, size, 4)


def test_icon_is_a_yellow_key_cap_with_a_dark_up_arrow_on_nothing():
    icon = render_icon(256)
    assert icon[0, 0, 3] == 0 and icon[255, 255, 3] == 0  # the corners are clear
    yellow = np.all(icon == YELLOW_BGRA, axis=2)
    dark = (icon[:, :, 3] == 255) & (icon[:, :, :3].max(axis=2) < 60)
    assert yellow.sum() > 0.3 * 256 * 256  # the cap fills most of the picture
    ys, xs = np.nonzero(dark)
    assert len(ys) > 0
    assert abs(xs.mean() - 128) < 8  # the arrow sits in the middle across
    assert ys.min() < ys.max() - 40  # and is tall


def test_icon_arrow_points_up():
    icon = render_icon(256)
    rows = ((icon[:, :, :3].max(axis=2) < 60) & (icon[:, :, 3] == 255)).sum(axis=1)
    first, last = np.nonzero(rows)[0][[0, -1]]
    widest = int(np.argmax(rows))
    assert rows[first + 4] < rows[widest - 4]  # a point at the top that widens into the head
    assert rows[widest + 8] < rows[widest] // 2  # then a narrow shaft
    assert rows[widest + 8] == rows[last - 4]  # which stays the same width to the bottom


# --- the Key Cap for the Terminal Key, beside the Terminal Prompt ---

TERMINAL_FIXTURES = sorted((Path(__file__).resolve().parent.parent / "fixtures" / "terminal").glob("*.png"))
SCREEN = {"left": 0, "top": 0, "width": 3840, "height": 2160}


def terminal_cap_pixels(frame, height):
    """The screen pixels (x0, y0, x1, y1, end-exclusive) a Terminal Key Cap frame draws on."""
    left, top, _, _ = terminal_key_cap_box(height)
    ys, xs = np.nonzero(frame[:, :, 3])
    return left + xs.min(), top + ys.min(), left + xs.max() + 1, top + ys.max() + 1


def test_the_terminal_key_cap_fills_its_window_exactly():
    for height in (2160, 1440, 1080):
        _, _, width, box_height = terminal_key_cap_box(height)
        assert render_terminal_key_cap(TerminalKeyCap("1"), height).shape == (box_height, width, 4)


def test_the_terminal_key_cap_is_a_yellow_key_cap_with_a_dark_glyph_then_enter_code():
    frame = render_terminal_key_cap(TerminalKeyCap("1"), 2160)
    assert frame[:, :, 3].any()
    assert (frame[:, :40] == YELLOW_BGRA).all(axis=2).sum() > 1000  # the cap's fill, on the left
    cap_columns = np.nonzero((frame[:, :, :3] == YELLOW_BGRA[:3]).all(axis=2).any(axis=0))[0]
    after_cap = frame[:, cap_columns.max() + 1 :]
    assert after_cap[:, :, 3].any()  # the words follow the cap
    assert not (after_cap[:, :, :3] == YELLOW_BGRA[:3]).all(axis=2).any()  # and are not yellow


def test_the_terminal_key_cap_says_the_configured_key():
    one = render_terminal_key_cap(TerminalKeyCap("1"), 2160)
    assert not np.array_equal(one, render_terminal_key_cap(TerminalKeyCap("0"), 2160))
    assert not np.array_equal(one, render_terminal_key_cap(TerminalKeyCap("enter"), 2160))
    # A long name is abbreviated as on any Key Cap.
    pgdn = render_terminal_key_cap(TerminalKeyCap("page down"), 2160)
    assert np.array_equal(pgdn, render_terminal_key_cap(TerminalKeyCap("pgdn"), 2160))


def test_a_red_terminal_key_cap_is_the_same_shape_with_a_red_fill():
    normal = render_terminal_key_cap(TerminalKeyCap("1"), 2160)
    red = render_terminal_key_cap(TerminalKeyCap("1", red=True), 2160)
    assert np.array_equal(normal[:, :, 3], red[:, :, 3])
    assert not np.array_equal(normal, red)
    assert (red[:, :40] == RED_BGRA).all(axis=2).sum() == (normal[:, :40] == YELLOW_BGRA).all(axis=2).sum()
    assert not (red[:, :40] == YELLOW_BGRA).all(axis=2).any()


def test_the_terminal_key_cap_sits_right_of_the_terminal_prompt_at_the_same_height():
    left, top, _, _ = terminal_key_cap_box(2160)
    x0, y0, x1, y1 = terminal_cap_pixels(render_terminal_key_cap(TerminalKeyCap("1"), 2160), 2160)
    prompt = prompt_area(SCREEN)
    assert x0 >= prompt["left"] + prompt["width"]  # right of everything the Terminal Prompt reader looks at
    assert abs((y0 + y1) / 2 - (prompt["top"] + prompt["height"] / 2)) < 20  # at the prompt's height
    assert x0 < 2400  # and close to it


@pytest.mark.parametrize("height", [2160, 1440, 1080])
@pytest.mark.parametrize("red", [False, True])
def test_the_terminal_key_cap_stays_off_every_pixel_either_reader_looks_at(height, red):
    monitor = {"left": 0, "top": 0, "width": height * 16 // 9, "height": height}
    x0, y0, x1, y1 = terminal_cap_pixels(render_terminal_key_cap(TerminalKeyCap("page down", red), height), height)
    for area in (prompt_area(monitor), code_area(monitor)):
        apart = x1 <= area["left"] or x0 >= area["left"] + area["width"]
        apart = apart or y1 <= area["top"] or y0 >= area["top"] + area["height"]
        assert apart, (area, (x0, y0, x1, y1))


def test_the_terminal_key_cap_is_never_pure_white_and_scales_with_screen_height():
    for height in (2160, 1440, 1080):
        frame = render_terminal_key_cap(TerminalKeyCap("1", red=height == 1440), height)
        assert frame[:, :, :3].min(axis=2).max() < WHITE_THRESHOLD
    tall, small = terminal_key_cap_box(2160), terminal_key_cap_box(1080)
    assert all(abs(a - 2 * b) <= 2 for i, (a, b) in enumerate(zip(tall, small)) if i != 2)
    assert abs(tall[2] - 2 * small[2]) <= 0.06 * tall[2]  # the words' stroke rounds to whole pixels


def terminal_screen(name):
    crop = cv2.imread(str(Path(__file__).resolve().parent.parent / "fixtures" / "terminal" / f"{name}.png"))
    screen = np.zeros((SCREEN["height"], SCREEN["width"], 3), np.uint8)
    screen[400 : 400 + crop.shape[0], 1100 : 1100 + crop.shape[1]] = crop  # fixtures/terminal/README.md
    return screen


def reading_of(screen):
    def grab(area):
        return screen[area["top"] : area["top"] + area["height"], area["left"] : area["left"] + area["width"]]

    return read_terminal_prompt(grab(prompt_area(SCREEN))), read_terminal_code(grab(code_area(SCREEN)))


def test_there_are_terminal_fixtures_to_paint_on():
    assert len(TERMINAL_FIXTURES) == 8


@pytest.mark.parametrize("path", TERMINAL_FIXTURES, ids=lambda p: p.stem)
def test_the_terminal_key_cap_painted_on_a_terminal_does_not_change_its_readings(path):
    screen = terminal_screen(path.stem)
    before = reading_of(screen)
    left, top, _, _ = terminal_key_cap_box(2160)
    for red in (False, True):
        painted = paint(screen, render_terminal_key_cap(TerminalKeyCap("1", red), 2160), left, top)
        assert not np.array_equal(painted, screen)
        assert reading_of(painted) == before
