"""Marks: the player presses the Mark Key when something unexpected happens, and the
tool saves the screen regions it last read so the moment can be examined later."""

from collections import deque
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np


class RecentRegions:
    """The last few screen regions read, oldest first. The reading thread adds to it
    while the Mark Key's thread takes a copy."""

    def __init__(self, keep: int):
        self._regions: deque[tuple[float, np.ndarray]] = deque(maxlen=keep)

    def add(self, when: float, region: np.ndarray) -> None:
        self._regions.append((when, region))

    def snapshot(self) -> list[tuple[float, np.ndarray]]:
        return list(self._regions)


def save_mark(
    folder: Path,
    number: int,
    marked_at: float,
    regions: list[tuple[float, np.ndarray]],
    at_mark: np.ndarray | None,
) -> Path:
    """Write one folder per mark: each recent region named by how long before the
    mark it was read, and the region read at the moment of the mark."""
    out = folder / f"{datetime.now():%Y%m%d-%H%M%S}_mark{number:02d}"
    out.mkdir(parents=True, exist_ok=True)
    for when, region in regions:
        cv2.imwrite(str(out / f"before_{marked_at - when:06.2f}s.png"), region)
    if at_mark is not None:
        cv2.imwrite(str(out / "at_mark.png"), at_mark)
    return out
