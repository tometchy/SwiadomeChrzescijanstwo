#!/usr/bin/env python3
"""Rebuild real front panels from original photographs without modifying originals.

Remove only narrow, near-uniform dark/light scan borders. Do not force an aspect
ratio: the catalogue and detail page display the front at its natural ratio.
"""
from __future__ import annotations

import argparse
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps, ImageStat

ROOT = Path(__file__).resolve().parents[1]

FRONT_CROPS: dict[str, tuple[float, float, float, float]] = {
    "50-trylogia-zycie-w-duchowym-zwyciestwie.webp": (0.51, 0.015, 0.99, 0.985),
}


def _flat_border(line: Image.Image) -> bool:
    """A removable border is narrow and nearly uniform, either dark or light."""
    small = line.resize((min(60, max(1, line.width)), min(60, max(1, line.height))))
    stats = ImageStat.Stat(small.convert("RGB"))
    brightness = sum(stats.mean) / 3
    variance = max(stats.stddev)
    return variance < 11 and (brightness < 48 or brightness > 225) and (max(stats.mean) - min(stats.mean) < 22)


def trim_flat_borders(image: Image.Image) -> Image.Image:
    """Trim monochrome bands, never more than 9% of either dimension per edge."""
    rgb = image.convert("RGB")
    width, height = rgb.size
    top, bottom, left, right = 0, height, 0, width
    max_y = int(height * 0.09)
    max_x = int(width * 0.09)
    for y in range(max_y):
        if not _flat_border(rgb.crop((0, y, width, y + 1))):
            break
        top = y + 1
    for y in range(max_y):
        if not _flat_border(rgb.crop((0, height - y - 1, width, height - y))):
            break
        bottom = height - y - 1
    for x in range(max_x):
        if not _flat_border(rgb.crop((x, top, x + 1, bottom))):
            break
        left = x + 1
    for x in range(max_x):
        if not _flat_border(rgb.crop((width - x - 1, top, width - x, bottom))):
            break
        right = width - x - 1
    if bottom <= top or right <= left:
        return image.copy()
    return image.crop((left, top, right, bottom))


def crop_front(image: Image.Image, filename: str) -> Image.Image:
    image = ImageOps.exif_transpose(image)
    width, height = image.size
    if filename in FRONT_CROPS:
        left, top, right, bottom = FRONT_CROPS[filename]
    elif width > height * 1.14:
        left, top, right, bottom = (0.52, 0.01, 0.995, 0.99)
    else:
        return trim_flat_borders(image)
    box = (
        round(left * width), round(top * height),
        round(right * width), round(bottom * height),
    )
    if box[2] <= box[0] or box[3] <= box[1]:
        raise ValueError(f"Invalid cover crop for {filename}: {box}")
    return trim_flat_borders(image.crop(box))


def build(root: Path = ROOT) -> tuple[int, int]:
    books = root / "assets" / "img" / "books"
    target_dir = books / "fronts"
    if not books.is_dir():
        raise FileNotFoundError(books)
    target_dir.mkdir(exist_ok=True)
    written, unchanged = 0, 0
    for original in sorted(books.glob("*.webp")):
        with Image.open(original) as image:
            front = crop_front(image, original.name)
            front.thumbnail((900, 1350), Image.Resampling.LANCZOS)
            front = front.convert("RGBA" if "A" in front.getbands() else "RGB")
            output_buffer = BytesIO()
            front.save(output_buffer, format="WEBP", quality=89, method=5)
            encoded = output_buffer.getvalue()
        output = target_dir / original.name
        if output.is_file() and output.read_bytes() == encoded:
            unchanged += 1
            continue
        tmp = output.with_suffix(".webp.tmp")
        tmp.write_bytes(encoded)
        tmp.replace(output)
        written += 1
        print(f"FRONT {original.name}: {image_dimensions(original)} -> {front.size}")
    print(f"Front covers: {written} generated, {unchanged} unchanged")
    return written, unchanged


def image_dimensions(path: Path) -> tuple[int, int]:
    with Image.open(path) as image:
        return image.size


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    build(args.root)
