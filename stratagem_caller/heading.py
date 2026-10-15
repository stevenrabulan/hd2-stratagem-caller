"""The ready heading: STRATAGEM CALLER READY, drawn once, pulsed by fading its window.

Pure drawing and timing: no window, no screen, no clock. The heading is a premultiplied
BGRA picture in the game's yellow with a soft glow. It pulses by changing the opacity of
the window that shows it, never by redrawing, so a pulse costs almost nothing. Like the
Key Caps it stays out of the reader's way: yellow only darkens what is behind it, so it
can never make a pixel pure white.
"""

import math

import cv2
import numpy as np

from . import reader
from .keycaps import YELLOW

HEADING = "STRATAGEM CALLER READY"
# Geometry measured on a 3840x2160 capture; everything scales with screen height.
# The text starts just right of the game's STRATAGEMS header, centred on its line.
TEXT_LEFT, TEXT_MIDDLE = 410, 91
PAD = 30  # room round the text for the glow
FONT_SCALE, FONT_THICKNESS = 1.15, 2
GLOW_THICKNESS, GLOW_BLUR = 6, 10

# The window's whole opacity (0 to 255) swings between these once every PULSE_PERIOD seconds.
PULSE_PERIOD = 1.2
PULSE_LOW, PULSE_HIGH = 110, 255


def _layout(screen_height: int) -> tuple[tuple[int, int, int, int], tuple[int, int], float, int]:
    """The heading's box (left, top, width, height relative to the monitor), where its text
    starts inside that box, and the font scale and thickness."""
    s = screen_height / reader.REFERENCE_HEIGHT
    scale, thickness = FONT_SCALE * s, max(1, round(FONT_THICKNESS * s))
    (text_width, text_height), _ = cv2.getTextSize(HEADING, cv2.FONT_HERSHEY_DUPLEX, scale, thickness)
    pad = round(PAD * s)
    baseline = round(TEXT_MIDDLE * s + text_height / 2)
    top = baseline - text_height - pad
    box = (round(TEXT_LEFT * s) - pad, top, text_width + 2 * pad, baseline + pad - top)
    return box, (pad, baseline - top), scale, thickness


def heading_box(screen_height: int) -> tuple[int, int, int, int]:
    """Left, top, width and height of the heading's window, relative to the monitor."""
    return _layout(screen_height)[0]


def render_heading(screen_height: int) -> np.ndarray:
    """The heading with its glow at full strength, sized to `heading_box`.

    Drawn as coverage (how much of each pixel is yellow) and turned into colour at the
    end, so the picture is properly premultiplied: no pixel's colour exceeds its alpha."""
    s = screen_height / reader.REFERENCE_HEIGHT
    (_, _, width, height), origin, scale, thickness = _layout(screen_height)
    font = cv2.FONT_HERSHEY_DUPLEX
    glow = np.zeros((height, width), np.uint8)
    cv2.putText(glow, HEADING, origin, font, scale, 255, max(2, round(GLOW_THICKNESS * s)), cv2.LINE_AA)
    glow = cv2.GaussianBlur(glow, (0, 0), GLOW_BLUR * s)
    text = np.zeros((height, width), np.uint8)
    cv2.putText(text, HEADING, origin, font, scale, 255, thickness, cv2.LINE_AA)
    # The text over its glow.
    alpha = text.astype(np.int32) + (glow.astype(np.int32) * (255 - text) + 127) // 255
    img = np.empty((height, width, 4), np.uint8)
    for channel, value in enumerate(YELLOW):
        img[:, :, channel] = (alpha * value + 127) // 255
    return img


def pulse_opacity(elapsed: float) -> int:
    """The window's opacity `elapsed` seconds after the heading appeared: full at first,
    dimming to PULSE_LOW and back once every PULSE_PERIOD."""
    wave = 0.5 + 0.5 * math.cos(2 * math.pi * elapsed / PULSE_PERIOD)
    return round(PULSE_LOW + (PULSE_HIGH - PULSE_LOW) * wave)
