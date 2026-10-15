"""Read the Terminal Prompt: the game's prompt at the bottom centre of the screen while a
Terminal waits for input. INTERACT wants a Code, MOVE CURSOR wants a grid step.

The prompt is flat, crisp and drawn at a fixed height, centred on the screen, so the reader
matches the two words against templates (cut from the fixtures by tools/make_prompt_templates.py)
along a strip of the screen. It looks at the word, not the four key glyphs before it, because
the glyphs are whatever Direction Keys the player has bound.
"""

from enum import Enum
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np

from .reader import REFERENCE_HEIGHT, WHITE_THRESHOLD

# Geometry measured on a 3840x2160 capture (reader.REFERENCE_HEIGHT); everything scales with screen height.
# The prompt box is centred on the screen and at most about 560 px wide; the words sit
# 1787 to 1821 px from the top. The strip is a little wider and taller than that.
STRIP_LEFT = 1500
STRIP_WIDTH = 840
STRIP_TOP = 1740
STRIP_HEIGHT = 130

# Correlation with a template. Measured on the fixtures: 0.96 or better for a word that is
# there (even half faded; 0.89 when the screen is shrunk to 1080p), 0.27 or less for anything else.
MATCH_THRESHOLD = 0.8

ASSETS = Path(__file__).resolve().parent / "assets"
TEMPLATE_FILES = {"interact": "prompt_interact.png", "move_cursor": "prompt_move_cursor.png"}


class TerminalPrompt(Enum):
    NONE = "no Terminal Prompt"
    INTERACT = "INTERACT"
    MOVE_CURSOR = "MOVE CURSOR"


_WORDS = {"interact": TerminalPrompt.INTERACT, "move_cursor": TerminalPrompt.MOVE_CURSOR}


def prompt_area(monitor: dict) -> dict:
    """The screen region (in mss's terms) that read_terminal_prompt needs."""
    scale = monitor["height"] / REFERENCE_HEIGHT
    return {
        "left": monitor["left"] + round(STRIP_LEFT * scale),
        "top": monitor["top"] + round(STRIP_TOP * scale),
        "width": round(STRIP_WIDTH * scale),
        "height": round(STRIP_HEIGHT * scale),
    }


@lru_cache(maxsize=None)
def _templates(scale_percent: int) -> dict[TerminalPrompt, np.ndarray]:
    templates = {}
    for word, prompt in _WORDS.items():
        path = ASSETS / TEMPLATE_FILES[word]
        template = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        if template is None:
            raise FileNotFoundError(f"Terminal Prompt template missing: {path}")
        if scale_percent != 100:
            size = (
                max(1, round(template.shape[1] * scale_percent / 100)),
                max(1, round(template.shape[0] * scale_percent / 100)),
            )
            template = cv2.resize(template, size, interpolation=cv2.INTER_AREA)
        templates[prompt] = template
    return templates


def read_terminal_prompt(region: np.ndarray, screen_height: int = REFERENCE_HEIGHT) -> TerminalPrompt:
    """Which Terminal Prompt `region` shows (BGR, the area prompt_area gives)."""
    templates = _templates(round(100 * screen_height / REFERENCE_HEIGHT))
    for prompt, template in templates.items():
        if region.shape[0] < template.shape[0] or region.shape[1] < template.shape[1]:
            raise ValueError(
                f"region {region.shape[1]}x{region.shape[0]} is too small to hold the {prompt.value} "
                f"word ({template.shape[1]}x{template.shape[0]}) at screen height {screen_height}"
            )
    # The lowest channel keeps white and drops the orange and yellow of fire and scenery.
    strip = region[:, :, :3].min(axis=2)
    best, best_score = TerminalPrompt.NONE, MATCH_THRESHOLD
    for prompt, template in templates.items():
        score = cv2.matchTemplate(strip, template, cv2.TM_CCOEFF_NORMED).max()
        if score >= best_score:
            best, best_score = prompt, score
    return best
