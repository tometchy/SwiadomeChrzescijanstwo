"""Front-cover cropping, gallery metadata and project-relative file URLs."""
from pathlib import Path

from PIL import Image
from scripts.generate_book_fronts import crop_front, build

ROOT = Path(__file__).resolve().parents[1]


def test_manual_full_wrap_crops_to_front():
    source = Image.new("RGB", (1000, 1000), "blue")
    source.paste(Image.new("RGB", (500, 1000), "red"), (500, 0))
    front = crop_front(source, "50-trylogia-zycie-w-duchowym-zwyciestwie.webp")
    assert front.width < source.width
    assert front.getpixel((front.width // 2, front.height // 2)) == (255, 0, 0)


def test_portrait_image_keeps_entire_front():
    source = Image.new("RGB", (600, 900), "green")
    front = crop_front(source, "sample.webp")
    assert front.size == source.size


def test_wide_image_uses_right_hand_panel():
    source = Image.new("RGB", (1400, 900), "blue")
    source.paste(Image.new("RGB", (700, 900), "red"), (700, 0))
    front = crop_front(source, "sample.webp")
    assert front.getpixel((front.width // 2, front.height // 2)) == (255, 0, 0)


def test_generator_is_repeatable_and_does_not_change_original(tmp_path):
    book_dir = tmp_path / "assets" / "img" / "books"
    book_dir.mkdir(parents=True)
    input_file = book_dir / "sample.webp"
    Image.new("RGB", (600, 900), "red").save(input_file)
    original = input_file.read_bytes()
    assert build(tmp_path) == (1, 0)
    assert build(tmp_path) == (0, 1)
    assert input_file.read_bytes() == original
    assert (book_dir / "fronts" / "sample.webp").exists()


def test_all_download_links_are_relative_to_pages_baseurl():
    source = (ROOT / "przeklad-torunski" / "index.html").read_text()
    assert 'href="{{ doc.url | relative_url }}"' in source
    assert 'href="{{ doc.url }}"' not in source


def test_original_favicon_is_selected():
    source = (ROOT / "_layouts" / "default.html").read_text()
    assert "/assets/legacy/swch/favicon.ico" in source
    assert '<link rel="icon" href="{{ \'/assets/img/favicon.svg\'' not in source


def test_book_cards_have_no_duplicate_link():
    source = (ROOT / "_includes" / "book_card.html").read_text()
    assert "Zobacz książkę" not in source
    assert 'class="book-card__image"' in source
    assert "<h3><a" in source


def test_gallery_has_front_original_and_extra_photo_support():
    layout = (ROOT / "_layouts" / "book.html").read_text()
    cover = (ROOT / "_includes" / "cover.html").read_text()
    script = (ROOT / "assets" / "js" / "site.js").read_text()
    assert "assets/img/books/fronts/" in layout
    assert "assets/img/books/fronts/" in cover
    assert "page.gallery_images" in layout
    assert "data-gallery-prev" in layout
    assert "data-gallery-next" in layout
    assert "data-gallery-image" in layout
    assert "ArrowRight" in script and "ArrowLeft" in script
