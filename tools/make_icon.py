"""Draw the Key Cap icon (a yellow Key Cap with an up arrow) and write it as an .ico file.

Run it after changing the drawing in stratagem_caller/keycaps.py (render_icon):

    .venv\Scripts\python.exe tools\make_icon.py

The file is kept in the repo because the Tray Icon and the desktop shortcut both use it.
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from stratagem_caller.keycaps import render_icon  # noqa: E402

ICON_PATH = ROOT / "stratagem_caller" / "assets" / "stratagem_caller.ico"
SIZES = (16, 24, 32, 48, 64, 128, 256)


def to_image(bgra: np.ndarray) -> Image.Image:
    """A premultiplied BGRA frame as a straight-alpha RGBA picture."""
    alpha = bgra[:, :, 3:4].astype(np.float32)
    colour = bgra[:, :, :3].astype(np.float32)
    straight = np.where(alpha > 0, colour * 255 / np.maximum(alpha, 1), 0).clip(0, 255)
    rgba = np.concatenate([straight[:, :, ::-1], alpha], axis=2).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")


def main() -> None:
    pictures = [to_image(render_icon(size)) for size in SIZES]
    ICON_PATH.parent.mkdir(parents=True, exist_ok=True)
    pictures[-1].save(ICON_PATH, format="ICO", sizes=[p.size for p in pictures], append_images=pictures[:-1])
    print(f"wrote {ICON_PATH} ({', '.join(str(s) for s in SIZES)} px)")


if __name__ == "__main__":
    main()
