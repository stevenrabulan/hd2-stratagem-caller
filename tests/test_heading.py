import numpy as np
import pytest

from stratagem_caller import reader
from stratagem_caller.heading import PULSE_PERIOD, heading_box, pulse_opacity, render_heading
from stratagem_caller.reader import WHITE_THRESHOLD

YELLOW_BGR = (0, 233, 255)  # #FFE900, the game's yellow


def test_the_picture_fills_the_heading_box():
    left, top, width, height = heading_box(2160)
    assert render_heading(2160).shape == (height, width, 4)
    assert left >= 0 and top >= 0


def test_the_heading_is_the_games_yellow_with_a_glow_around_it():
    frame = render_heading(2160)
    solid = frame[:, :, 3] == 255
    assert solid.any()
    assert (frame[solid][:, :3] == YELLOW_BGR).all()
    glow = (frame[:, :, 3] > 0) & ~solid
    assert glow.sum() > solid.sum()  # soft light round the letters, more than the letters
    assert frame[:, :, 3].max() == 255


def test_the_picture_is_premultiplied_yellow():
    frame = render_heading(2160)
    alpha = frame[:, :, 3].astype(int)
    assert (frame[:, :, 0] == 0).all()
    assert np.abs(frame[:, :, 1].astype(int) - 233 * alpha // 255).max() <= 1
    assert (frame[:, :, :3].max(axis=2) <= alpha).all()  # a colour above its alpha would glare
    assert (frame[:, :, 2] == alpha).all()


def test_no_pixel_is_pure_white():
    assert render_heading(2160)[:, :, :3].min(axis=2).max() < WHITE_THRESHOLD


def test_the_heading_sits_on_the_line_of_the_stratagems_header_right_of_it():
    left, top, width, height = heading_box(2160)
    ys, xs = np.nonzero(render_heading(2160)[:, :, 3] == 255)
    assert xs.min() + left >= 410 - 2  # right of the game's header, which ends before x=410
    middle = (ys.min() + ys.max()) / 2 + top
    assert abs(middle - 91) <= 4  # the header's line at 4K
    assert top + height < reader.ICON_TOP  # above the first Icon


@pytest.mark.parametrize("height", [1440, 1080])
def test_the_heading_scales_with_screen_height(height):
    s = height / 2160
    left, top, width, box_height = heading_box(height)
    full_left, full_top, full_width, full_height = heading_box(2160)
    assert abs(left - full_left * s) <= 2
    assert abs(width - full_width * s) <= 0.05 * full_width * s  # thinner strokes at lower heights
    assert abs(box_height - full_height * s) <= 4
    assert render_heading(height).shape == (box_height, width, 4)


def test_opacity_starts_at_full_and_dips_once_per_period():
    assert pulse_opacity(0) == 255
    low = pulse_opacity(PULSE_PERIOD / 2)
    assert 0 < low < 255
    assert pulse_opacity(PULSE_PERIOD) == 255
    samples = [pulse_opacity(PULSE_PERIOD * i / 20) for i in range(20)]
    assert min(samples) == low
    # One dip: falls to the low point, then rises back.
    assert samples.index(low) == 10
    assert samples[:11] == sorted(samples[:11], reverse=True)
    assert samples[10:] == sorted(samples[10:])


def test_the_pulse_repeats_every_period():
    assert pulse_opacity(5 * PULSE_PERIOD + 0.3) == pulse_opacity(0.3)


def test_the_heading_never_fades_out_entirely():
    assert min(pulse_opacity(t / 100) for t in range(240)) >= 100
