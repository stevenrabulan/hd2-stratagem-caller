"""Read the Code a Terminal shows on its own screen.

The Code is a row of arrows drawn on the Terminal, at an angle and skew that depend on where the
player stands. Light grey arrows are directions not yet entered, yellow ones are entered. A pink
circle or the character's hand can lie across them.

How an arrow's direction is told under skew: every arrow is the same glyph (a triangle head on a
stem) seen through the same affine map, so for each arrow the reader finds the map that carries a
canonical right-pointing arrow onto it (matching the shape's moments, then searching the one angle
left over). That map says where the arrow's tip points, and which way the arrow's own "down" lies.
Compared with the line the arrows sit on, those two vectors say whether the arrow points along the
row (left or right) or across it (up or down), and which way.

The reader never returns a shortened Code. Anything it cannot account for (a gap in the row, a
bright stub where a next arrow should be, an arrow that does not fit the glyph, entered and not
entered arrows mixed in the wrong order) makes the Code unreadable. One case it cannot see: an
end arrow hidden so completely that nothing of it shows.
"""

from dataclasses import dataclass
from enum import Enum

import cv2
import numpy as np

from .reader import REFERENCE_HEIGHT

# Geometry measured on a 3840x2160 capture (reader.REFERENCE_HEIGHT); everything scales with screen
# height. The player has the Terminal under the reticle, so its Code lies near the screen centre:
# on the fixtures the arrows' centres are within 300 px of it. The area is centred on the screen.
AREA_WIDTH = 1840
AREA_HEIGHT = 1040
# An arrow is about 60 to 95 px across and 1800 to 3300 px^2 on a 4K screen.
ARROW_AREA = (1000, 4500)
ARROW_SIDE = (35, 130)
# Fewest arrows in a Code (a row shorter than this is something else on screen).
MIN_ARROWS = 3

# Arrow colours (BGR pixels): light grey up to pure white (not entered; grey measured 175 to 190,
# but the game can draw them near white, about 245), yellow or pale yellow while it fades (entered).
GREY_MIN = 140  # the dimmest channel of a grey arrow; there is no upper limit
GREY_SPREAD = 30  # the channels of grey differ by less than this
YELLOW_RED = 140
YELLOW_GREEN = 125
YELLOW_SPREAD = 40  # red and green differ by less than this
ENTERED_BLUE_BELOW = 40  # blue is at least this far under red and green in yellow (pale yellow: 60)
# The reader looks past the pink circle and markers. A white reticle counts as arrow-coloured, but
# its ring is too thin to survive as part of an arrow (see THIN_FEATURE).

# Lines and rings thinner than this many pixels are not part of an arrow.
THIN_FEATURE = 9

# The arrows lie on one line, at about even gaps.
ROW_OFF_LINE = 0.45  # of an arrow's width: how far its centre may lie off the line
AREA_SPREAD = (0.6, 1.6)  # of the median arrow area
GAP_SPREAD = (0.7, 1.4)  # of the median gap between neighbouring arrows
MAX_TILT_DEGREES = 60  # the row's slope from horizontal
# A bright stub this near (in gaps) to where the next arrow would be, at either end, is an arrow
# that something is in the way of.
STUB_NEAR = 0.8
STUB_MIN_AREA = 0.05  # of the median arrow area, at the ends
BETWEEN_MIN_AREA = 0.15  # the same between arrows, where the reticle leaves scraps

# How well an arrow must match the glyph (overlap over union, ignoring pink and white pixels).
# Measured on the fixtures: 0.87 to 0.91 for a clear arrow, 0.78 for one the reticle partly covers.
MATCH_MIN = 0.7
# How much more along the row than across it the tip or the arrow's own "down" must lie.
DIRECTION_MARGIN = 0.15

# A bigger screen is looked at shrunk to this height: arrows are still about 35 px across, and a
# Reading costs a quarter as much at 4K.
WORKING_HEIGHT = 1080

CANONICAL = 40  # side of the canonical arrow's square, in pixels
_ANGLE_STEP = 8
_REFINE_STEP = 2


class CodeStatus(Enum):
    NONE = "no Code on screen"
    UNREADABLE = "a Code that cannot be read"
    READ = "a Code read in full"


@dataclass(frozen=True)
class CodeReading:
    """What one look at a Terminal's screen showed. `code` (U, D, L, R) and `entered` (how many of
    its directions are already entered) are set only when `status` is READ, and then the Code is
    whole. `why` says in words what was seen or what stood in the way."""

    status: CodeStatus
    code: str = ""
    entered: int = 0
    why: str = ""

    @property
    def remaining(self) -> str:
        """The directions still to be typed."""
        return self.code[self.entered :]


def code_area(monitor: dict) -> dict:
    """The screen region (in mss's terms) that read_terminal_code needs."""
    scale = monitor["height"] / REFERENCE_HEIGHT
    width, height = round(AREA_WIDTH * scale), round(AREA_HEIGHT * scale)
    return {
        "left": monitor["left"] + (monitor["width"] - width) // 2,
        "top": monitor["top"] + (monitor["height"] - height) // 2,
        "width": width,
        "height": height,
    }


def _canonical_arrow() -> np.ndarray:
    """A right-pointing arrow: a stem on the left, a triangle head on the right."""
    size = CANONICAL
    shape = np.zeros((size, size), np.uint8)
    half = size // 2
    cv2.fillPoly(shape, [np.array([(0, size // 4), (half, size // 4), (half, 3 * size // 4), (0, 3 * size // 4)])], 1)
    cv2.fillPoly(shape, [np.array([(half, 0), (size - 1, half), (half, size - 1)])], 1)
    return shape


def _moments(points: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    centre = points.mean(axis=0)
    return centre, np.cov((points - centre).T)


def _matrix_power(cov: np.ndarray, power: float) -> np.ndarray:
    values, vectors = np.linalg.eigh(cov)
    return vectors @ np.diag(values**power) @ vectors.T


_ARROW = _canonical_arrow()
_ARROW_CENTRE, _ARROW_COV = _moments(np.argwhere(_ARROW)[:, ::-1].astype(float))
_ARROW_WHITENER = _matrix_power(_ARROW_COV, -0.5)


@dataclass(frozen=True)
class _Fit:
    """How well a blob matches the arrow, and the map that carries the arrow onto it."""

    score: float
    tip: np.ndarray  # image of the arrow's right-pointing direction
    down: np.ndarray  # image of the arrow's own downward direction


def _fit_arrow(blob: np.ndarray, ignore: np.ndarray) -> _Fit:
    """`blob` is the arrow's mask (cropped) and `ignore` marks pixels in the same crop to look past.
    Returns the best map found; its score is what overlap that map gives."""
    points = np.argwhere(blob)[:, ::-1].astype(float)
    centre, cov = _moments(points)
    root = _matrix_power(cov, 0.5)
    both = np.dstack([blob, ignore]).astype(np.float32)  # warped together: the arrow and what to look past
    template = _ARROW.astype(bool)

    def overlap(degrees: float) -> tuple[float, np.ndarray]:
        turn = np.radians(degrees)
        rotation = np.array([[np.cos(turn), -np.sin(turn)], [np.sin(turn), np.cos(turn)]])
        # blob point = centre + a @ (canonical point - canonical centre). With the canonical arrow
        # and the blob both whitened (same second moments), only a rotation is left to find.
        a = root @ rotation @ _ARROW_WHITENER
        shift = centre - a @ _ARROW_CENTRE
        matrix = np.hstack([a, shift[:, None]]).astype(np.float32)
        size = (CANONICAL, CANONICAL)
        flags = cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP
        warped = cv2.warpAffine(both, matrix, size, flags=flags) > 0.5
        valid = ~warped[:, :, 1]
        seen = warped[:, :, 0]
        union = np.count_nonzero((seen | template) & valid)
        return (np.count_nonzero(seen & template & valid) / union if union else 0.0), a

    best_score, best_degrees = -1.0, 0.0
    for degrees in np.arange(0, 360, _ANGLE_STEP):
        score, _ = overlap(degrees)
        if score > best_score:
            best_score, best_degrees = score, degrees
    for degrees in np.arange(best_degrees - _ANGLE_STEP, best_degrees + _ANGLE_STEP + 0.01, _REFINE_STEP):
        score, _ = overlap(degrees)
        if score > best_score:
            best_score, best_degrees = score, degrees
    score, a = overlap(best_degrees)
    return _Fit(score, a[:, 0].copy(), a[:, 1].copy())


@dataclass(frozen=True)
class _Blob:
    width: int
    height: int
    area: int
    centre: np.ndarray  # (x, y) in the region
    origin: tuple[int, int]  # (x, y) of the corner of the crop below
    mask: np.ndarray  # cropped to the blob's box, with a margin
    ignore: np.ndarray  # pixels in that crop to look past
    entered: bool


def _masks(region: np.ndarray, scale: float) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Which pixels are arrow-coloured, the same without thin features, which are yellow, and which
    to look past."""
    blue, green, red = (region[:, :, i].astype(np.int16) for i in range(3))
    lowest = np.minimum(np.minimum(blue, green), red)
    highest = np.maximum(np.maximum(blue, green), red)
    grey = (lowest >= GREY_MIN) & (highest - lowest <= GREY_SPREAD)
    yellow = (
        (red >= YELLOW_RED)
        & (green >= YELLOW_GREEN)
        & (np.abs(red - green) <= YELLOW_SPREAD)
        & (blue <= np.minimum(red, green) - ENTERED_BLUE_BELOW)
    )
    pink = (red >= 160) & (green * 2 <= red) & (blue * 7 >= red)
    ignore = cv2.dilate(pink.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    coloured = grey | yellow
    # The reticle's pale ring and the letters and lines of the Terminal's screen are thin, an arrow is
    # not: open them away, then give back the pixels around what is left (an arrow's sharp tip).
    thin = max(3, round(THIN_FEATURE * scale)) | 1
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (thin, thin))
    opened = cv2.morphologyEx(coloured.astype(np.uint8), cv2.MORPH_OPEN, kernel)
    body = cv2.dilate(opened, kernel).astype(bool) & coloured
    return coloured, body, yellow, ignore


def _components(mask: np.ndarray, yellow: np.ndarray, ignore: np.ndarray) -> list[_Blob]:
    count, labels, stats, centres = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=8)
    blobs = []
    for label in range(1, count):
        x, y, width, height, area = (int(v) for v in stats[label])
        left, top = max(x - 6, 0), max(y - 6, 0)
        right, bottom = min(x + width + 6, mask.shape[1]), min(y + height + 6, mask.shape[0])
        mine = labels[top:bottom, left:right] == label
        blobs.append(
            _Blob(
                width=width, height=height, area=area, centre=centres[label],
                origin=(left, top), mask=mine, ignore=ignore[top:bottom, left:right] & ~mine,
                entered=float(yellow[top:bottom, left:right][mine].mean()) > 0.5,
            )
        )
    return blobs


def _row_of_arrows(candidates: list[_Blob]) -> list[_Blob]:
    """The candidates that lie on one line, the most of them; when several lines tie, the one with
    the biggest total area. Empty if none have three on a line."""
    if len(candidates) < MIN_ARROWS:
        return []
    centres = np.array([c.centre for c in candidates])
    side = float(np.median([max(c.width, c.height) for c in candidates]))
    best: list[int] = []
    areas = np.array([c.area for c in candidates])
    for i in range(len(candidates)):
        for j in range(i + 1, len(candidates)):
            along = centres[j] - centres[i]
            length = np.hypot(*along)
            if length < side * 0.6:
                continue
            normal = np.array([-along[1], along[0]]) / length
            off_line = np.abs((centres - centres[i]) @ normal)
            members = [k for k in range(len(candidates)) if off_line[k] <= ROW_OFF_LINE * side]
            if (len(members), areas[members].sum()) > (len(best), areas[best].sum()):
                best = members
    return [candidates[k] for k in best] if len(best) >= MIN_ARROWS else []


def read_terminal_code(region: np.ndarray, screen_height: int = REFERENCE_HEIGHT) -> CodeReading:
    """Read the Code on the Terminal in `region` (BGR, the area code_area gives)."""
    if region.ndim != 3 or region.shape[2] < 3:
        raise ValueError(f"region must be a colour image (height, width, 3 or more channels), not shape {region.shape}")
    if min(region.shape[:2]) < ARROW_SIDE[1] * screen_height / REFERENCE_HEIGHT:
        raise ValueError(
            f"region {region.shape[1]}x{region.shape[0]} is too small to hold an arrow at screen height {screen_height}"
        )
    if screen_height > WORKING_HEIGHT:
        shrink = WORKING_HEIGHT / screen_height
        region = cv2.resize(region, None, fx=shrink, fy=shrink, interpolation=cv2.INTER_AREA)
        screen_height = WORKING_HEIGHT
    scale = screen_height / REFERENCE_HEIGHT
    coloured, body, yellow, ignore = _masks(region[:, :, :3], scale)
    arrows = _components(body, yellow, ignore)
    candidates = [
        b
        for b in arrows
        if ARROW_AREA[0] * scale**2 <= b.area <= ARROW_AREA[1] * scale**2
        and ARROW_SIDE[0] * scale <= b.width <= ARROW_SIDE[1] * scale
        and ARROW_SIDE[0] * scale <= b.height <= ARROW_SIDE[1] * scale
    ]
    if candidates:
        typical = float(np.median([c.area for c in candidates]))
        candidates = [c for c in candidates if AREA_SPREAD[0] * typical <= c.area <= AREA_SPREAD[1] * typical]
    row = _row_of_arrows(candidates)
    if not row:
        return CodeReading(CodeStatus.NONE, why="no row of arrows")

    centres = np.array([b.centre for b in row])
    line = np.linalg.svd(centres - centres.mean(axis=0))[2][0]
    if line[0] < 0:
        line = -line
    tilt = np.degrees(np.arctan2(line[1], line[0]))
    if abs(tilt) > MAX_TILT_DEGREES:
        return CodeReading(CodeStatus.UNREADABLE, why=f"the row of arrows lies {tilt:.0f} degrees from horizontal")
    row = sorted(row, key=lambda b: float(b.centre @ line))
    steps = np.diff(np.array([b.centre @ line for b in row]))
    gap = float(np.median(steps))
    if not all(GAP_SPREAD[0] * gap <= s <= GAP_SPREAD[1] * gap for s in steps):
        return CodeReading(CodeStatus.UNREADABLE, why="the arrows are unevenly spaced, one may be hidden")

    blocked = _what_hides_an_arrow(row, line, gap, coloured, body, yellow, ignore)
    if blocked is not None:
        return CodeReading(CodeStatus.UNREADABLE, why=blocked)

    letters = []
    for number, blob in enumerate(row, 1):
        fit = _fit_arrow(blob.mask, blob.ignore)
        if fit.score < MATCH_MIN:
            return CodeReading(CodeStatus.UNREADABLE, why=f"arrow {number} does not look like an arrow ({fit.score:.2f})")
        letter = _direction(fit, line)
        if letter is None:
            return CodeReading(CodeStatus.UNREADABLE, why=f"arrow {number} points no clear way")
        letters.append(letter)

    states = [b.entered for b in row]
    entered = sum(states)
    if states != [True] * entered + [False] * (len(row) - entered):
        return CodeReading(CodeStatus.UNREADABLE, why="entered and not entered arrows are not in order")
    return CodeReading(CodeStatus.READ, "".join(letters), entered, why=f"{len(row)} arrows")


def _what_hides_an_arrow(
    row: list[_Blob], line: np.ndarray, gap: float, coloured, body, yellow, ignore
) -> str | None:
    """Why the Code may be longer than the row, or have an arrow missing from it, or None. A bright
    stub where the next arrow would be, at either end, is an arrow something is in the way of; so is
    a bright thing between the arrows that is not one of them; so is the area ending there."""
    typical = float(np.median([b.area for b in row]))
    side = float(np.median([max(b.width, b.height) for b in row]))
    height, width = coloured.shape
    taken = np.zeros(coloured.shape, bool)
    for b in row:
        left, top = b.origin
        taken[top : top + b.mask.shape[0], left : left + b.mask.shape[1]] |= b.mask
    taken = cv2.dilate(taken.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    # What is left of the bright pixels once the row's own arrows are taken away. The ends look at
    # every bright pixel (a hand leaves a thin sliver); between the arrows thin things are not
    # looked at (the reticle's pale ring lies there).
    at_the_ends = [b for b in _components(coloured & ~taken, yellow, ignore) if b.area >= STUB_MIN_AREA * typical]
    between = [b for b in _components(body & ~taken, yellow, ignore) if b.area >= BETWEEN_MIN_AREA * typical]

    for end, direction, where in ((row[0], -1, "before the first arrow"), (row[-1], 1, "after the last arrow")):
        expected = end.centre + direction * gap * line
        if not (side / 2 <= expected[0] <= width - side / 2 and side / 2 <= expected[1] <= height - side / 2):
            return "the Code runs to the edge of the area looked at"
        if any(np.hypot(*(stub.centre - expected)) <= STUB_NEAR * gap for stub in at_the_ends):
            return f"something bright {where}, an arrow may be hidden"
    first, last = row[0].centre, row[-1].centre
    normal = np.array([-line[1], line[0]])
    for stub in between:
        along, across = (stub.centre - first) @ line, (stub.centre - first) @ normal
        if 0 <= along <= (last - first) @ line and abs(across) <= STUB_NEAR * gap:
            return "something bright between the arrows, an arrow may be hidden"
    return None


def _direction(fit: _Fit, line: np.ndarray) -> str | None:
    """U, D, L or R for an arrow whose tip and own "down" are the vectors in `fit`, on a row of
    arrows along `line` (unit, pointing right)."""
    along_tip = float(fit.tip @ line) / np.hypot(*fit.tip)
    along_down = float(fit.down @ line) / np.hypot(*fit.down)
    if abs(abs(along_tip) - abs(along_down)) < DIRECTION_MARGIN:
        return None
    if abs(along_tip) > abs(along_down):
        return "R" if along_tip > 0 else "L"
    return "U" if along_down > 0 else "D"
