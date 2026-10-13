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
MAX_ARROWS = 8

# An Icon is a square whose four edges are sharp against the menu behind it.
# Each edge counts when most of its length differs this much (summed over the
# colour channels) from the pixels just outside it.
ICON_EDGE_CONTRAST = 40
ICON_EDGE_SHARE = 0.6
# The menu counts as open when this many neighbouring Slots show an Icon in place.
ICONS_FOR_OPEN_MENU = 4

# Callable arrows are pure white; dimmed, entered (yellow) and background pixels fall below this.
WHITE_THRESHOLD = 225


@dataclass(frozen=True)
class Reading:
    """The Codes and Icons seen in the Stratagem Menu at one moment, by Slot.

    Each Slot is in one of three states:

    - callable: it appears in `codes` with its full Code (and in `icons`);
    - unreadable: it appears in `unreadable`. Something bright is on its arrow
      line that is not a recognisable arrow at a valid position, so the Code
      cannot be trusted. A shortened Code is never returned for such a Slot;
    - anything else: not callable. The game shows a status such as a cooldown
      timer in place of the arrows, and the Slot is in neither collection.

    `menu_open` says whether the Stratagem Menu is open, whatever the Slots
    are: a menu in which every Stratagem is on cooldown is open with no Codes.
    A menu still sliding in, or the single row the game flashes up beside the
    collapsed header while the menu is closed, is not open.
    """

    codes: dict[int, str] = field(default_factory=dict)
    unreadable: set[int] = field(default_factory=set)
    icons: dict[int, np.ndarray] = field(default_factory=dict)
    menu_open: bool = False


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
    other_bright: set[int] = set()
    for label in range(1, len(stats)):
        x, y, w, h, _area = (int(v) for v in stats[label])
        slot_pos = (y / scale - FIRST_ARROW_TOP) / SLOT_PITCH
        slot = round(slot_pos) + 1
        overlapped = _slots_overlapped(x, y, w, h, _area, scale)
        if not 1 <= slot <= MAX_SLOTS or abs(slot_pos - round(slot_pos)) > 0.08:
            # Not an arrow-shaped thing on a slot line, but if it still covers
            # part of a line (a glow merged with an arrow) that line is clutter.
            other_bright.update(overlapped)
            continue
        arrow_pos = (x / scale - FIRST_ARROW_LEFT) / ARROW_PITCH
        index = round(arrow_pos)
        direction = _direction(labels[y : y + h, x : x + w] == label, scale)
        if index < -1:
            if direction is not None:
                rejected.add(slot)  # an arrow far left of the line: still sliding in
            continue
        on_grid = abs(arrow_pos - index) <= 0.15
        if direction is None or not on_grid or index < 0:
            # Something white where an arrow line should be clean: a menu still
            # sliding in, or a status text. An arrow left of the first position
            # means the whole line is shifted, so the Slot can't be trusted.
            if direction is not None:
                rejected.add(slot)
            else:
                other_bright.update(overlapped)
            continue
        found.setdefault(slot, {})[index] = direction

    codes = {}
    icons = {}
    unreadable = set(rejected)
    for slot, arrows in sorted(found.items()):
        if slot in rejected:
            continue
        if slot in other_bright:
            # Some arrows recognised, but bright clutter on the line may hide
            # the rest of the Code: wait for a clean view.
            unreadable.add(slot)
            continue
        if sorted(arrows) != list(range(len(arrows))):
            continue  # a gap: the player has entered part of the Code by hand
        codes[slot] = "".join(arrows[i] for i in range(len(arrows)))
        top = round((ICON_TOP + (slot - 1) * SLOT_PITCH) * scale)
        left = round(ICON_LEFT * scale)
        size = round(ICON_SIZE * scale)
        icons[slot] = region[top : top + size, left : left + size].copy()
    return Reading(
        codes=codes,
        unreadable=unreadable,
        icons=icons,
        menu_open=_menu_open(region, scale, codes),
    )


def _menu_open(region: np.ndarray, scale: float, codes: dict[int, str]) -> bool:
    """An open menu is a column of Icons in their places. Rows that are still
    sliding in have no Icon in place yet, and a closed menu shows at most a few
    separate rows, as they come off cooldown. The only open menu that small is a
    dead player's, which lists Reinforce (Slot 1) alone, with its Code."""
    run = longest = 0
    for slot in range(1, MAX_SLOTS + 1):
        run = run + 1 if _icon_in_place(region, slot, scale) else 0
        longest = max(longest, run)
    return longest >= ICONS_FOR_OPEN_MENU or 1 in codes


def _icon_in_place(region: np.ndarray, slot: int, scale: float) -> bool:
    """Whether all four edges of the Icon square of this Slot are sharp."""
    top = round((ICON_TOP + (slot - 1) * SLOT_PITCH) * scale)
    left = round(ICON_LEFT * scale)
    size = round(ICON_SIZE * scale)
    near = max(1, round(scale))  # first pixel off the edge, either side
    band = max(3, round(3 * scale))
    inset = max(2, round(6 * scale))
    bottom, right = top + size, left + size
    if top - near - band < 0 or bottom + near + band > region.shape[0] or right + near + band > region.shape[1]:
        return False
    img = region[:, :, :3].astype(np.int16)

    def sharp(inside: np.ndarray, outside: np.ndarray) -> bool:
        return (np.abs(inside - outside).sum(axis=-1) > ICON_EDGE_CONTRAST).mean() >= ICON_EDGE_SHARE

    across = slice(left + inset, right - inset)
    down = slice(top + inset, bottom - inset)
    edges = (
        (img[top + near : top + near + band, across], img[top - near - band : top - near, across], 0),
        (img[bottom - near - band : bottom - near, across], img[bottom + near : bottom + near + band, across], 0),
        (img[down, left + near : left + near + band], img[down, left - near - band : left - near], 1),
        (img[down, right - near - band : right - near], img[down, right + near : right + near + band], 1),
    )
    return all(sharp(a.mean(axis=e), b.mean(axis=e)) for a, b, e in edges)


def _slots_overlapped(x: int, y: int, w: int, h: int, area: int, scale: float) -> set[int]:
    """Slots whose arrow line a bright blob covers, ignoring specks and anything
    left of the arrows (Icons, key hints)."""
    left = x / scale
    arrows_right = FIRST_ARROW_LEFT + MAX_ARROWS * ARROW_PITCH
    if left < FIRST_ARROW_LEFT - ARROW_PITCH / 2 or left > arrows_right or area < 20 * scale * scale:
        return set()
    top, bottom = y / scale, (y + h) / scale
    covered = set()
    for slot in range(1, MAX_SLOTS + 1):
        line_top = FIRST_ARROW_TOP + (slot - 1) * SLOT_PITCH
        overlap = min(bottom, line_top + ARROW_SIZE) - max(top, line_top)
        if overlap >= 0.3 * ARROW_SIZE:
            covered.add(slot)
    return covered


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
