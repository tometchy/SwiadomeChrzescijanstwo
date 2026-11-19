"""Search-index coverage and domain aliases for the Jekyll book catalogue."""
from pathlib import Path
import re
import yaml

ROOT = Path(__file__).resolve().parents[1]

def book(number):
    for path in (ROOT / "_ksiazki").glob("*.md"):
        text = path.read_text(encoding="utf-8")
        data = yaml.safe_load(text.split("---", 2)[1])
        if data.get("catalog_number") == number:
            return data
    raise AssertionError(f"Missing book: {number}")

def test_search_indexes_all_publisher_fields():
    card = (ROOT / "_includes" / "book_card.html").read_text()
    for field in ("title", "display_title", "subtitle", "card_subtitle", "author",
                  "description", "tags", "search_aliases", "author_aliases",
                  "isbn", "publisher", "publication_year", "binding", "format",
                  "edition_note", "content"):
        assert f"book.{field}" in card
    assert 'data-search="{{ search_text | normalize_whitespace | escape }}"' in card

def test_biblia_synonyms_are_indexed_for_every_torun_bible():
    for number in (15, 21, 22, 35, 36):
        data = book(number)
        tokens = " ".join(data.get("tags", []) + data.get("search_aliases", [])).lower()
        for expected in ("biblia", "pismo święte", "tnp"):
            assert expected in tokens, (number, expected)

def test_all_41_books_have_specific_tags():
    all_books = sorted((ROOT / "_ksiazki").glob("*.md"))
    assert len(all_books) == 41
    for p in all_books:
        d = yaml.safe_load(p.read_text(encoding="utf-8").split("---", 2)[1])
        assert len(d.get("tags", [])) >= 2, p
        assert len(set(d["tags"])) == len(d["tags"]), p
        assert all(isinstance(t, str) and t.strip() for t in d["tags"]), p

def test_search_splits_terms_and_normalizes_diacritics():
    js = (ROOT / "assets" / "js" / "site.js").read_text()
    assert "terms.every(term => haystack.includes(term))" in js
    assert "normalize('NFKD')" in js
    assert ".replace(/ł/g, 'l')" in js
    assert "URLSearchParams(window.location.search)" in js

def test_tags_link_to_catalog_search():
    layout = (ROOT / "_layouts" / "book.html").read_text()
    assert "page.tags" in layout
    assert "?q={{ tag | url_encode }}" in layout

def test_all_local_product_images_exist_and_galleries_have_local_assets():
    all_books = [(p, yaml.safe_load(p.read_text(encoding="utf-8").split("---", 2)[1]))
                 for p in sorted((ROOT / "_ksiazki").glob("*.md"))]
    with_cover = 0
    extra_images = 0
    for path, data in all_books:
        cover = data.get("cover_url", "")
        if cover.startswith("/assets/img/books/"):
            assert (ROOT / cover.lstrip("/")).is_file(), (path, cover)
            with_cover += 1
        for image in data.get("gallery_images", []):
            assert isinstance(image, str)
            assert image.startswith("/assets/img/books/")
            assert (ROOT / image.lstrip("/")).is_file(), (path, image)
            extra_images += 1
    assert with_cover >= 35
    # Po usunięciu omyłkowo pobranych zdjęć innych tytułów
    # pozostaje pięć zweryfikowanych ujęć (w tym pełna obwoluta).
    assert extra_images == 5
