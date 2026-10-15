"""Draw the Key Caps: one per Slot, left of its Icon, in the look of the game's own key hints.

Pure drawing: no window, no screen, no clock. A frame is a premultiplied BGRA image,
which is what a layered window wants. The Key Caps must not disturb what the reader
checks, so they stay clear of pure white, of the arrow lines and of the Icons' edges.
"""

import cv2
import numpy as np

from . import reader

# Geometry measured on a 3840x2160 capture; everything scales with screen height.
# The Key Cap column is a thin window left of the Icons.
COLUMN_LEFT, COLUMN_RIGHT, COLUMN_HEIGHT = 40, 102, 1500
# A Key Cap ends left of x=98, so neither the reader's Icon-edge check (which looks
# from x=101) nor its arrow lines (from x=215) ever see it.
CAP_LEFT, CAP_RIGHT = 46, 96
CAP_ABOVE, CAP_BELOW = 28, 18  # from the Icon's vertical centre
BAR_TOP, BAR_BOTTOM = 23, 26  # the thin bar under the cap, in the cap's fill
CAP_RADIUS = 8
GLYPH_SCALE, GLYPH_THICKNESS = 1.1, 2.5
GLYPH_MARGIN = 6  # room kept between the glyph and each side of the cap

# Colours are BGRA, premultiplied (what UpdateLayeredWindow expects). Never pure white.
DARK = (30, 30, 30, 255)
RED = (40, 40, 215, 255)  # the fill of a Key Cap whose Trigger Key just beeped
YELLOW = (0, 233, 255, 255)  # #FFE900, the game's yellow

# Key names too long for a Key Cap.
SHORT_NAMES = {
    "page down": "PGDN",
    "page up": "PGUP",
    "caps lock": "CAPS",
    "insert": "INS",
    "delete": "DEL",
    "backspace": "BKSP",
    "escape": "ESC",
    "space": "SPACE",
}


def column_box(screen_height: int) -> tuple[int, int, int, int]:
    """Left, top, width and height of the Key Cap column, relative to the monitor."""
    s = screen_height / reader.REFERENCE_HEIGHT
    left = round(COLUMN_LEFT * s)
    return left, 0, round(COLUMN_RIGHT * s) - left, round(COLUMN_HEIGHT * s)


def cap_text(key_name: str) -> str:
    """What a Key Cap says for a key: its name, upper case, abbreviated if it is long."""
    return SHORT_NAMES.get(key_name.lower(), key_name.upper())


def render_key_caps(names: dict[int, str], screen_height: int, red: frozenset[int] = frozenset()) -> np.ndarray:
    """The Key Cap column with a Key Cap for each Slot in `names` (Slot -> key name), the
    fill red for those Slots also in `red`. A Slot in `red` without a Key Cap gets none."""
    s = screen_height / reader.REFERENCE_HEIGHT
    left, _, width, height = column_box(screen_height)
    img = np.zeros((height, width, 4), np.uint8)
    for slot, name in names.items():
        _draw_key_cap(img, slot, cap_text(name), RED if slot in red else YELLOW, s, origin_x=left)
    return img


# The icon is one Key Cap, in the same proportions, centred in a square of ICON_SPAN
# units with an up arrow where a Key Cap has its glyph. Cap units: x from CAP_LEFT, y
# from -CAP_ABOVE (relative to the middle a Slot's Key Cap would have).
ICON_SPAN = 60
ARROW_HEAD = ((71, -21), (84, -6), (58, -6))  # apex, then the two base corners
ARROW_SHAFT = (66, -7, 76, 9)  # left, top, right, bottom


def render_icon(size: int) -> np.ndarray:
    """The Key Cap with an up arrow, `size` pixels square, on a clear background (premultiplied
    BGRA, like a frame). Used for the Tray Icon and the desktop shortcut."""
    s = size / ICON_SPAN
    cap_w, cap_h = CAP_RIGHT - CAP_LEFT, CAP_ABOVE + BAR_BOTTOM
    shift_x, shift_y = (ICON_SPAN - cap_w) / 2 - CAP_LEFT, (ICON_SPAN - cap_h) / 2 + CAP_ABOVE

    def px(x: float, y: float) -> tuple[int, int]:
        return round((x + shift_x) * s), round((y + shift_y) * s)

    img = np.zeros((size, size, 4), np.uint8)
    x0, y0 = px(CAP_LEFT, -CAP_ABOVE)
    x1, y1 = px(CAP_RIGHT, CAP_BELOW)
    r = max(2, round(CAP_RADIUS * s))
    _rounded_rect(img, x0, y0, x1, y1, r, YELLOW)
    bar_y0, bar_y1 = px(0, BAR_TOP)[1], px(0, BAR_BOTTOM)[1]
    cv2.rectangle(img, (x0 + r, bar_y0), (x1 - r, bar_y1), YELLOW, -1, cv2.LINE_AA)
    head = np.array([px(*p) for p in ARROW_HEAD], np.int32)
    cv2.fillPoly(img, [head], DARK, cv2.LINE_AA)
    left, top = px(ARROW_SHAFT[0], ARROW_SHAFT[1])
    right, bottom = px(ARROW_SHAFT[2], ARROW_SHAFT[3])
    cv2.rectangle(img, (left, top), (right, bottom), DARK, -1, cv2.LINE_AA)
    return img


def _draw_key_cap(img: np.ndarray, slot: int, text: str, fill: tuple, s: float, origin_x: int) -> None:
    middle = reader.ICON_TOP + reader.ICON_SIZE / 2 + (slot - 1) * reader.SLOT_PITCH
    x0, x1 = round(CAP_LEFT * s) - origin_x, round(CAP_RIGHT * s) - origin_x
    y0, y1 = round((middle - CAP_ABOVE) * s), round((middle + CAP_BELOW) * s)
    r = max(2, round(CAP_RADIUS * s))
    _rounded_rect(img, x0, y0, x1, y1, r, fill)
    _glyph(img, text, (x0 + x1) / 2, (y0 + y1) / 2, s, room=x1 - x0 - 2 * round(GLYPH_MARGIN * s))
    bar_y0, bar_y1 = round((middle + BAR_TOP) * s), round((middle + BAR_BOTTOM) * s)
    cv2.rectangle(img, (x0 + r, bar_y0), (x1 - r, bar_y1), fill, -1, cv2.LINE_AA)


def _rounded_rect(img, x0, y0, x1, y1, r, colour):
    cv2.rectangle(img, (x0 + r, y0), (x1 - r, y1), colour, -1, cv2.LINE_AA)
    cv2.rectangle(img, (x0, y0 + r), (x1, y1 - r), colour, -1, cv2.LINE_AA)
    for cx, cy in ((x0 + r, y0 + r), (x1 - r, y0 + r), (x0 + r, y1 - r), (x1 - r, y1 - r)):
        cv2.circle(img, (cx, cy), r, colour, -1, cv2.LINE_AA)


def _glyph(img, text, cx, cy, s, room):
    """Centred dark text, shrunk if it would not fit in `room` pixels across."""
    scale = GLYPH_SCALE * s
    thickness = max(1, round(GLYPH_THICKNESS * s))
    (w, h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_DUPLEX, scale, thickness)
    if w > room:
        scale *= room / w
        thickness = max(1, round(thickness * room / w))
        (w, h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_DUPLEX, scale, thickness)
    origin = (round(cx - w / 2), round(cy + h / 2))
    cv2.putText(img, text, origin, cv2.FONT_HERSHEY_DUPLEX, scale, DARK, thickness, cv2.LINE_AA)
