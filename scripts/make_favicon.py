#!/usr/bin/env python3
"""Recolor the ORIGINAL SWCH favicon gray; remove its background.

Never uses the opaque gray favicon from wswch.pl. The original ICO remains
unchanged. Generated PNG is 64x64 RGBA with actual transparency.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from collections import deque

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("assets/legacy/swch/favicon.ico")
DESTINATION = Path("assets/img/favicon-gray-transparent.png")
GRAY = (82, 83, 80)


def transparent_gray(original: Image.Image, size: int = 64) -> Image.Image:
    pixels = original.convert("RGBA")
    w, h = pixels.size
    corners = [pixels.getpixel(point) for point in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1))]
    opaque_corners = [color for color in corners if color[3] > 200]
    background = None
    if len(opaque_corners) >= 3:
        ch = tuple(round(sum(px[i] for px in opaque_corners) / len(opaque_corners)) for i in range(3))
        if all(max(abs(color[i] - ch[i]) for i in range(3)) < 24 for color in opaque_corners):
            background = ch

    # Remove the continuous solid background connected to the corners.
    if background is not None:
        start = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
        queue = deque(start)
        seen = set()
        while queue:
            x, y = queue.popleft()
            if (x, y) in seen:
                continue
            seen.add((x, y))
            r, g, b, a = pixels.getpixel((x, y))
            if max(abs(r - background[0]), abs(g - background[1]), abs(b - background[2])) > 35:
                continue
            pixels.putpixel((x, y), (0, 0, 0, 0))
            if x > 0: queue.append((x - 1, y))
            if y > 0: queue.append((x, y - 1))
            if x + 1 < w: queue.append((x + 1, y))
            if y + 1 < h: queue.append((x, y + 1))

    result = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels.getpixel((x, y))
            if a == 0:
                continue
            # Transparent light fringe on an originally white background.
            if background is not None and min(background) > 225:
                diff = max(abs(r - background[0]), abs(g - background[1]), abs(b - background[2]))
                a = round(a * min(1, diff / 65))
            if a > 0:
                result.putpixel((x, y), (*GRAY, a))

    bbox = result.getchannel("A").getbbox()
    if not bbox:
        raise ValueError("Original favicon has no distinguishable symbol")
    symbol = result.crop(bbox)
    symbol.thumbnail((size - 8, size - 8), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.alpha_composite(symbol, ((size - symbol.width) // 2, (size - symbol.height) // 2))
    return canvas


def build(root: Path = ROOT) -> Path:
    source, dest = root / SOURCE, root / DESTINATION
    with Image.open(source) as image:
        icon = transparent_gray(image)
    dest.parent.mkdir(parents=True, exist_ok=True)
    icon.save(dest, format="PNG", optimize=True)
    print(f"Transparent gray favicon: {dest}")
    return dest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    build(args.root)
