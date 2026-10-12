"""Turn a screenshot of the Stratagem Menu into a Reading.

The reader looks only for the arrow glyphs the game draws under each callable
Stratagem. It never reads names, so it needs no list of known Stratagems.
"""

from dataclasses import dataclass, field

import cv2
import numpy as np

# Geometry measured on a 3840x2160 capture; everything scales with screen height.
REFERENCE_HEIGHT = 2160
# The menu sits in the top-left corner; this is the only part of the screen needed.
REGION_WIDTH = 800
REGION_HEIGHT = 1500

SLOT_PITCH = 104.4
FIRST_ARROW_TOP = 215.0
FIRST_ARROW_LEFT = 237.0
ARROW_PITCH = 43.3
ARROW_SIZE = 30.0
ICON_LEFT = 105.0
ICON_TOP = 162.0
ICON_SIZE = 86.0
MAX_SLOTS = 10

# Callable arrows are pure white; dimmed, entered (yellow) and background pixels fall below this.
WHITE_THRESHOLD = 225


@dataclass(frozen=True)
class Reading:
    """The Codes and Icons seen in the Stratagem Menu at one moment, by Slot.

    Only Slots whose Stratagem can be called right now appear: the game shows a
    status such as a cooldown timer in place of the arrows for the others.
    """

    codes: dict[int, str] = field(default_factory=dict)
    icons: dict[int, np.ndarray] = field(default_factory=dict)


def region_size(screen_height: int) -> tuple[int, int]:
    """Width and height of the top-left screen region read_menu needs."""
    scale = screen_height / REFERENCE_HEIGHT
    return round(REGION_WIDTH * scale), round(REGION_HEIGHT * scale)


def read_menu(region: np.ndarray, screen_height: int = REFERENCE_HEIGHT) -> Reading:
    """Read the top-left screen region (BGR, at least region_size big)."""
    scale = screen_height / REFERENCE_HEIGHT
    white = (region[:, :, :3].min(axis=2) >= WHITE_THRESHOLD).astype(np.uint8)
    _, labels, stats, _ = cv2.connectedComponentsWithStats(white, 8)

    # slot -> {arrow position in the Code: direction}
    found: dict[int, dict[int, str]] = {}
    rejected: set[int] = set()
    for label in range(1, len(stats)):
        x, y, w, h, _area = (int(v) for v in stats[label])
        slot_pos = (y / scale - FIRST_ARROW_TOP) / SLOT_PITCH
        slot = round(slot_pos) + 1
        if not 1 <= slot <= MAX_SLOTS or abs(slot_pos - round(slot_pos)) > 0.08:
            continue
        arrow_pos = (x / scale - FIRST_ARROW_LEFT) / ARROW_PITCH
        index = round(arrow_pos)
        if index < -1:
            continue
        direction = _direction(labels[y : y + h, x : x + w] == label, scale)
        on_grid = abs(arrow_pos - index) <= 0.15
        if direction is None or not on_grid or index < 0:
            # Something white where an arrow line should be clean: a menu still
            # sliding in, or a status text. An arrow left of the first position
            # means the whole line is shifted, so the Slot can't be trusted.
            if direction is not None:
                rejected.add(slot)
            continue
        found.setdefault(slot, {})[index] = direction

    codes = {}
    icons = {}
    for slot, arrows in sorted(found.items()):
        if slot in rejected or sorted(arrows) != list(range(len(arrows))):
            continue
        codes[slot] = "".join(arrows[i] for i in range(len(arrows)))
        top = round((ICON_TOP + (slot - 1) * SLOT_PITCH) * scale)
        left = round(ICON_LEFT * scale)
        size = round(ICON_SIZE * scale)
        icons[slot] = region[top : top + size, left : left + size].copy()
    return Reading(codes=codes, icons=icons)


def _direction(mask: np.ndarray, scale: float) -> str | None:
    """Classify a white blob as an arrow glyph pointing U, D, L or R, or None.

    A glyph is a triangle head on a rectangular stem. The stem's flat end fills
    about half of one bounding-box edge, while the other three edges hold only
    the tip and the two corners of the head.
    """
    h, w = mask.shape
    size = ARROW_SIZE * scale
    if not (0.8 * size <= w <= 1.25 * size and 0.8 * size <= h <= 1.25 * size):
        return None
    if not 0.38 <= mask.mean() <= 0.62:
        return None
    # Fullest line within a few pixels of each edge; the outermost line alone can
    # be lost to anti-aliasing.
    band = max(2, round(3 * scale))
    edges = {
        "D": mask[:band].mean(axis=1).max(),  # stem at the top, so it points down
        "U": mask[-band:].mean(axis=1).max(),
        "R": mask[:, :band].mean(axis=0).max(),
        "L": mask[:, -band:].mean(axis=0).max(),
    }
    direction = max(edges, key=edges.get)
    others = [v for k, v in edges.items() if k != direction]
    if not 0.3 <= edges[direction] <= 0.7 or max(others) > 0.25:
        return None
    return direction
