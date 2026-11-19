#!/usr/bin/env python3
"""Cache authentic photos from individually verified book-edition product pages.

Only known, explicitly reviewed retailer pages are accepted. The page must
match the expected title and identify Fundacja Świadome Chrześcijaństwo.
Original catalog title/author, links and prices are never touched.
A download error is non-fatal: do not fabricate replacement imagery.
"""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
from urllib.parse import urljoin, urlsplit
import re
import unicodedata
import hashlib
import json
import time

from bs4 import BeautifulSoup
from PIL import Image, ImageOps
import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SWCH-OwnPublishingCatalog/1.0)"}
ALLOWED_HOSTS = {"szaron.pl", "www.szaron.pl", "bogulandia.pl", "www.bogulandia.pl"}
MAX_IMAGE_BYTES = 12 * 1024 * 1024
MAX_GALLERY = 3


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold())
    value = "".join(c for c in value if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", value)).strip()


def valid_url(url: str, page: str) -> bool:
    ref = urlsplit(page)
    target = urlsplit(url)
    return target.scheme == "https" and target.hostname in ALLOWED_HOSTS and ref.hostname in ALLOWED_HOSTS


def image_urls(soup: BeautifulSoup, page: str) -> list[str]:
    candidates = []
    for selector in (".woocommerce-product-gallery__image a[href]",
                     ".woocommerce-product-gallery__image img",
                     "img.wp-post-image",
                     'meta[property="og:image"]'):
        for element in soup.select(selector):
            value = (element.get("data-large_image") or element.get("href")
                     or element.get("content") or element.get("src"))
            if value:
                url = urljoin(page, value)
                if valid_url(url, page) and url not in candidates:
                    candidates.append(url)
    return candidates


def photo(session: requests.Session, url: str, page: str) -> Image.Image:
    if not valid_url(url, page):
        raise ValueError("Untrusted image origin")
    response = session.get(url, timeout=22)
    response.raise_for_status()
    if len(response.content) > MAX_IMAGE_BYTES:
        raise ValueError("Oversized image")
    with Image.open(BytesIO(response.content)) as im:
        im.load()
        if im.width < 180 or im.height < 180:
            raise ValueError("Low-resolution thumbnail")
        return ImageOps.exif_transpose(im).convert("RGB")


def save_webp(image: Image.Image, target: Path) -> None:
    image.thumbnail((1100, 1600), Image.Resampling.LANCZOS)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".tmp")
    image.save(tmp, format="WEBP", quality=88, method=5)
    tmp.replace(target)


def append_frontmatter(markdown: Path, fields: dict) -> None:
    raw = markdown.read_text(encoding="utf-8")
    match = re.match(r"\A(---\r?\n.*?)(\r?\n---\r?\n)", raw, re.S)
    if not match:
        raise ValueError(f"Not a frontmatter document: {markdown}")
    front = match.group(1)
    lines = []
    for key, value in fields.items():
        if re.search(r"^" + re.escape(key) + r":", front, flags=re.M):
            continue
        lines.append(key + ": " + json.dumps(value, ensure_ascii=False))
    if lines:
        markdown.write_text(match.group(1) + "\n" + "\n".join(lines) + match.group(2) +
                            raw[match.end():], encoding="utf-8")


def run(root: Path = ROOT) -> tuple[int, int]:
    sources = yaml.safe_load((root / "scripts" / "verified_cover_sources.yml").read_text(encoding="utf-8"))
    session = requests.Session()
    session.headers.update(HEADERS)
    done = skipped = 0
    for source in sources:
        stem = source["book"]
        doc = root / "_ksiazki" / f"{stem}.md"
        target = root / "assets" / "img" / "books" / f"{stem}.webp"
        if not doc.is_file():
            print("SKIP missing catalog book", stem)
            skipped += 1
            continue
        if target.exists():
            print("KEEP existing original image", stem)
            skipped += 1
            continue
        page = source["page"]
        try:
            if urlsplit(page).hostname not in ALLOWED_HOSTS:
                raise ValueError("Untrusted product page")
            response = session.get(page, timeout=23)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            h1 = soup.find("h1")
            heading = normalize(h1.get_text(" ", strip=True) if h1 else "")
            if normalize(source["title"]) not in heading:
                raise ValueError("Product title does not match expected edition: " + heading)
            publisher = normalize(soup.get_text(" ", strip=True))
            if "fundacja swiadome chrzescijanstwo" not in publisher and "fundacja swiadome ch" not in publisher:
                raise ValueError("Publisher cannot be verified on the source page")
            urls = ([source["image"]] if source.get("image") else []) + image_urls(soup, page)
            imgs: list[Image.Image] = []
            signatures: set[bytes] = set()
            for url in urls:
                if len(imgs) >= MAX_GALLERY:
                    break
                try:
                    image = photo(session, url, page)
                    small = image.resize((40, 60)).convert("L")
                    signature = hashlib.sha256(small.tobytes()).digest()
                    if signature in signatures:
                        continue
                    imgs.append(image)
                    signatures.add(signature)
                except Exception as exc:
                    print("IMAGE SKIP", stem, str(exc)[:120])
            if not imgs:
                raise ValueError("No trustworthy usable product image")
            save_webp(imgs[0], target)
            extra = []
            for i, im in enumerate(imgs[1:], start=2):
                extra_path = target.with_name(f"{stem}-photo-{i}.webp")
                save_webp(im, extra_path)
                extra.append("/assets/img/books/" + extra_path.name)
            fields = {"cover_url": "/assets/img/books/" + target.name,
                      "cover_mode": "photo",
                      "cover_source_url": page}
            if extra:
                fields["gallery_images"] = extra
            append_frontmatter(doc, fields)
            print("CACHED", stem, "photos:", len(imgs))
            done += 1
        except Exception as exc:
            print("SKIP", stem, str(exc)[:240])
            skipped += 1
    print(f"New verified covers: {done}, skipped/unavailable: {skipped}")
    return done, skipped


if __name__ == "__main__":
    run()
