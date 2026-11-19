"""Zapobiega powrotowi obcych zdjęć w galeriach i utracie cen katalogowych."""
import re
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
APPROVED_BACKS = {
    "02-zycie-przez-jego-smierc",
    "04-wszystko-z-laski",
    "13-radykalny-krzyz-uwielbienie-utracony-klejnot",
    "16-w-cieniu-wszechmogacego",
}


def test_verified_book_gallery_assets():
    books = sorted((ROOT / "_ksiazki").glob("*.md"))
    assert len(books) == 41
    for book in books:
        raw = book.read_text(encoding="utf-8")
        match = re.match(r"\A---\s*\n(.*?)\n---\s*\n", raw, re.S)
        assert match, book
        data = yaml.safe_load(match.group(1))
        assert data.get("historical_price"), f"Brak ceny z katalogu: {book}"
        assert data.get("catalog_status", "") in ("", "brak", "nowość"), book
        for photo in data.get("gallery_images", []):
            assert book.stem in APPROVED_BACKS, f"Niezweryfikowana galeria: {book}"
            assert photo == f"/assets/img/books/{book.stem}-photo-2.webp", f"Obce zdjęcie: {photo}"
            assert (ROOT / photo.lstrip("/")).is_file(), f"Brak pliku: {photo}"


def test_book_data_rendered_by_shared_templates():
    card = (ROOT / "_includes/book_card.html").read_text(encoding="utf-8")
    detail = (ROOT / "_layouts/book.html").read_text(encoding="utf-8")
    home = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "book.historical_price" in card
    assert "book.catalog_status" in card
    assert "page.historical_price" in detail
    assert "page.catalog_status" in detail
    assert "Zobacz wszystkie {{ site.ksiazki.size }} książek" in home
