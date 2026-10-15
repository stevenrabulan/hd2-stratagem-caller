"""Cut the INTERACT and MOVE CURSOR words of the Terminal Prompt out of the Terminal fixtures
and write them as the templates the reader matches against.

Run it if the game changes how the prompt is drawn, after adding fixtures of the new look:

    .venv\Scripts\python.exe tools\make_prompt_templates.py

The templates are kept in the repo (stratagem_caller/assets/). The boxes below are in the
fixtures' own pixels (each fixture is the screen from x=1100, y=400; see its README).
"""

import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from stratagem_caller.reader import WHITE_THRESHOLD  # noqa: E402
from stratagem_caller.terminal_prompt import TEMPLATE_FILES  # noqa: E402

FIXTURES = ROOT / "fixtures" / "terminal"
ASSETS = ROOT / "stratagem_caller" / "assets"

# word -> (fixture it is cut from, x0, x1, y0, y1): the letters plus a few pixels around.
WORDS = {
    "interact": ("drill_code_pending_angle_a", 838, 1025, 1391, 1424),
    "move_cursor": ("drill_next_step_not_a_code_grid_move_cursor", 798, 1068, 1391, 1424),
}


def main() -> None:
    for word, (fixture, x0, x1, y0, y1) in WORDS.items():
        image = cv2.imread(str(FIXTURES / f"{fixture}.png"))
        white = image.min(axis=2)[y0:y1, x0:x1] >= WHITE_THRESHOLD
        path = ASSETS / TEMPLATE_FILES[word]
        cv2.imwrite(str(path), white.astype("uint8") * 255)
        print(f"wrote {path} ({x1 - x0}x{y1 - y0})")


if __name__ == "__main__":
    main()
