"""Gray cat sprite — frame 0 from cute_grey_cat_rotations_8dir.gif."""

from __future__ import annotations

import os
from PIL import Image

from draw import W, H

_GIF_PATH = os.path.join(os.path.dirname(__file__), "..", "Assets", "gray-cat", "cute_grey_cat_rotations_8dir.gif")
_FRAME_INDEX = 0


def render_gray_cat() -> bytes:
    img = Image.open(_GIF_PATH)
    img.seek(_FRAME_INDEX)
    frame = img.convert("RGBA")

    bbox = frame.getbbox()
    if bbox:
        frame = frame.crop(bbox)

    fw, fh = frame.size
    scale = min(W // fw, H // fh)
    if scale < 1:
        scale = 1
    frame = frame.resize((fw * scale, fh * scale), Image.NEAREST)
    nw, nh = frame.size

    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    x = W - nw
    y = H - nh
    canvas.paste(frame, (x, y), frame)

    return canvas.tobytes()
