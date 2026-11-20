"""Spójność jednego źródła Markdown, stron i pliku EPUB."""
from pathlib import Path
from zipfile import ZipFile, ZIP_STORED
from xml.etree import ElementTree
import pytest
import re
import yaml

ROOT = Path(__file__).resolve().parents[1]
EPUB = ROOT / "_site/spiewnik/Spiewnik-Torun.epub"


def test_449_numbered_markdown_songs():
    songs = sorted((ROOT / "_piesni").glob("*.md"))
    assert len(songs) == 449
    for expected, path in enumerate(songs, 1):
        assert path.stem == f"{expected:03}"
        content = path.read_text(encoding="utf-8")
        assert content.startswith("---\n")
        fm, lyrics = content.split("---", 2)[1:]
        meta = yaml.safe_load(fm)
        assert meta["number"] == expected
        assert meta["title"].strip()
        assert len(lyrics.strip()) > 30


def test_single_source_and_download_link():
    config = yaml.safe_load((ROOT / "_config.yml").read_text(encoding="utf-8"))
    assert config["collections"]["piesni"]["output"] is True
    assert config["collections"]["piesni"]["permalink"] == "/spiewnik/piesni/:name/"
    homepage = (ROOT / "spiewnik/index.html").read_text(encoding="utf-8")
    layout = (ROOT / "_layouts/song.html").read_text(encoding="utf-8")
    pages = (ROOT / ".github/workflows/pages.yml").read_text(encoding="utf-8")
    assert "Spiewnik-Torun.epub" in homepage
    assert "Spiewnik-Torun.epub" in layout
    assert "data-epub-lyrics" in layout
    assert "scripts/build_hymnal_epub.py" in pages


def test_generated_epub_package():
    if not EPUB.is_file():
        pytest.skip("EPUB is generated after Jekyll build")
    with ZipFile(EPUB) as z:
        names = set(z.namelist())
        assert z.namelist()[0] == "mimetype"
        assert z.infolist()[0].compress_type == ZIP_STORED
        assert z.read("mimetype") == b"application/epub+zip"
        assert len(re.findall(r"^OEBPS/\d{3}\.xhtml$", "\n".join(names), flags=re.M)) == 449
        assert "OEBPS/nav.xhtml" in names
        for number in (1, 100, 300, 449):
            page = z.read(f"OEBPS/{number:03}.xhtml").decode("utf-8")
            ElementTree.fromstring(page)
            meta = yaml.safe_load((ROOT / f"_piesni/{number:03}.md").read_text(encoding="utf-8").split("---", 2)[1])
            assert meta["title"] in page.replace("&amp;", "&")
        ElementTree.fromstring(z.read("OEBPS/package.opf"))
        ElementTree.fromstring(z.read("OEBPS/nav.xhtml"))



def test_cover_and_reader_friendly_toc():
    if not EPUB.is_file():
        pytest.skip("EPUB tests run after the Jekyll build")
    cover_source = ROOT / "assets/img/spiewnik/okladka.jpg"
    assert cover_source.is_file()
    with ZipFile(EPUB) as z:
        names = set(z.namelist())
        assert "OEBPS/cover.jpg" in names
        assert z.read("OEBPS/cover.jpg") == cover_source.read_bytes()
        assert "OEBPS/cover.xhtml" in names
        assert "OEBPS/index.xhtml" in names
        manifest_ns = "{http://www.idpf.org/2007/opf}"
        package = ElementTree.fromstring(z.read("OEBPS/package.opf"))
        manifest = package.find(manifest_ns + "manifest")
        items = {item.get("id"): item for item in manifest}
        assert "cover-image" in items["cover-image"].get("properties", "")
        assert items["cover-image"].get("href") == "cover.jpg"
        assert "nav" in items["nav"].get("properties", "")
        spine = package.find(manifest_ns + "spine")
        spine_ids = [item.get("idref") for item in spine]
        assert spine_ids[:3] == ["cover-page", "title", "index"]
        assert "nav" not in spine_ids, "Machine navigation should not consume book pages"
        index = ElementTree.fromstring(z.read("OEBPS/index.xhtml"))
        xhtml_ns = "{http://www.w3.org/1999/xhtml}"
        links = [a.get("href") for a in index.iter(xhtml_ns + "a")
                 if re.fullmatch(r"\d{3}\.xhtml", a.get("href") or "")]
        assert len(links) == 449
        assert len(set(links)) == 449
        assert len(list(index.iter(xhtml_ns + "h2"))) >= 20
        nav = ElementTree.fromstring(z.read("OEBPS/nav.xhtml"))
        assert len(list(nav.iter(xhtml_ns + "li"))) >= 449
        assert "Pieśni 1–50" in z.read("OEBPS/nav.xhtml").decode("utf-8")
        assert "nav li{margin:" not in z.read("OEBPS/style.css").decode("utf-8")
