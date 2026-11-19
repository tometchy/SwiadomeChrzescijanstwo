#!/usr/bin/env python3
"""Build front-cover WebP images from locally archived book photographs.

Never modifies originals; front images live under assets/img/books/fronts/.
Cropping can be adjusted per title below if a source photo is a full wrap.
Run before Jekyll build and optionally commit the deterministic output.
"""
from __future__ import annotations

import argparse
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]

# Normalized coordinates (left, top, right, bottom) of the true FRONT panel.
# The Oswald Smith file is a flattened back/spine/front spread.
FRONT_CROPS: dict[str, tuple[float, float, float, float]] = {
    "50-trylogia-zycie-w-duchowym-zwyciestwie.webp": (0.51, 0.015, 0.99, 0.985),
}


def crop_front(image: Image.Image, filename: str) -> Image.Image:
    image = ImageOps.exif_transpose(image)
    width, height = image.size
    if filename in FRONT_CROPS:
        left, top, right, bottom = FRONT_CROPS[filename]
    elif width > height * 1.14:
        # A wide, flat wrap usually has the back at left, spine centrally,
        # and its front at right. This never applies to portrait covers.
        left, top, right, bottom = (0.52, 0.01, 0.995, 0.99)
    else:
        return image.copy()
    box = (
        round(left * width), round(top * height),
        round(right * width), round(bottom * height),
    )
    if box[2] <= box[0] or box[3] <= box[1]:
        raise ValueError(f"Invalid cover crop for {filename}: {box}")
    return image.crop(box)


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
            buffer = BytesIO()
            front.save(buffer, format="WEBP", quality=89, method=5)
            encoded = buffer.getvalue()
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
