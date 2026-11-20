#!/usr/bin/env python3
"""Generate a covered, navigable EPUB from the HTML that Jekyll built from _piesni/*.md.

Source of song text remains the Jekyll Markdown collection, not an EPUB copy.
The original cover is a checked-in image asset (assets/img/spiewnik/okladka.jpg).
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from html import escape
from pathlib import Path
import re
import unicodedata
from uuid import NAMESPACE_URL, uuid5
from xml.etree import ElementTree
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile

from bs4 import BeautifulSoup, NavigableString, Tag

TITLE = "Śpiewnik zborowy — Toruń"
SLUG = "Spiewnik-Torun.epub"
IDENTIFIER = "urn:uuid:" + str(uuid5(NAMESPACE_URL, "https://wswch.pl/spiewnik/torun"))
XHTML_NS = "http://www.w3.org/1999/xhtml"
ROOT = Path(__file__).resolve().parents[1]
COVER_SOURCE = ROOT / "assets/img/spiewnik/okladka.jpg"
ALLOWED = {"p", "br", "strong", "b", "em", "i", "blockquote", "ul", "ol", "li", "h2", "h3", "hr", "sup", "sub"}
VOID = {"br", "hr"}
POLISH_ALPHABET = "AĄBCĆDEĘFGHIJKLŁMNŃOÓPRSŚTUWYZŹŻ"
POLISH_POS = {c: i for i, c in enumerate(POLISH_ALPHABET)}


def convert_html(node) -> str:
    """Preserve Markdown formatting from Jekyll while excluding UI markup."""
    if isinstance(node, NavigableString):
        return escape(str(node), quote=False)
    if not isinstance(node, Tag):
        return ""
    if node.name in {"script", "style", "svg", "iframe", "form", "button"}:
        return ""
    inner = "".join(convert_html(child) for child in node.children)
    if node.name not in ALLOWED:
        return inner
    return f"<{node.name} />" if node.name in VOID else f"<{node.name}>{inner}</{node.name}>"


def xhtml(title: str, body: str, *, nav: bool = False, body_class: str = "") -> str:
    nav_ns = ' xmlns:epub="http://www.idpf.org/2007/ops"' if nav else ""
    class_attr = f' class="{body_class}"' if body_class else ""
    return (f'<?xml version="1.0" encoding="utf-8"?>\n'
            f'<html xmlns="{XHTML_NS}"{nav_ns} xml:lang="pl" lang="pl">'
            f'<head><title>{escape(title)}</title>'
            '<meta charset="utf-8"/><link rel="stylesheet" type="text/css" href="style.css"/>'
            f'</head><body{class_attr}>{body}</body></html>')


def extract(site: Path, expected_count: int = 449) -> list[tuple[int, str, str]]:
    pages = sorted((site / "spiewnik" / "piesni").glob("[0-9][0-9][0-9]/index.html"))
    if len(pages) != expected_count:
        raise ValueError(f"Expected {expected_count} Jekyll song pages, got {len(pages)}")
    result = []
    for number, path in enumerate(pages, 1):
        source_number = int(path.parent.name)
        if source_number != number:
            raise ValueError(f"Song number mismatch: {source_number} != {number}")
        soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
        entry = soup.select_one("[data-epub-song]")
        if not entry or entry.get("data-epub-song") != str(number):
            raise ValueError(f"Missing or wrong song marker: {path}")
        title_el = entry.select_one("h1")
        lyrics = entry.select_one("[data-epub-lyrics]")
        if not title_el or not lyrics:
            raise ValueError(f"Missing song title or lyrics: {path}")
        title = title_el.get_text(" ", strip=True)
        content = "".join(convert_html(child) for child in lyrics.children).strip()
        if not content or not re.search(r"[\wĄĆĘŁŃÓŚŹŻąćęłńóśźż]", BeautifulSoup(content, "html.parser").get_text()):
            raise ValueError(f"Empty song {number}: {path}")
        result.append((number, title, content))
    return result


def polish_key(title: str):
    normalized = unicodedata.normalize("NFC", title.upper())
    return tuple((POLISH_POS.get(char, 100 + ord(char)), char) for char in normalized)


def alphabetical_index(songs: list[tuple[int, str, str]]) -> str:
    """A readable, one-column index in the book body; navigable by letter."""
    by_initial = {}
    for number, title, _ in sorted(songs, key=lambda s: polish_key(s[1])):
        first_letter = next((c for c in unicodedata.normalize("NFC", title.upper()) if c.isalpha()), "#")
        by_initial.setdefault(first_letter, []).append((number, title))
    groups = sorted(by_initial, key=lambda c: (POLISH_POS.get(c, 100 + ord(c)), c))
    letter_links = " ".join(f'<a href="#letter-{ord(letter)}">{escape(letter)}</a>' for letter in groups)
    rows = []
    for letter in groups:
        entries = ''.join(
            f'<p class="index-entry"><a href="{number:03}.xhtml">{escape(title)}'
            f' <span class="index-number">— {number}</span></a></p>'
            for number, title in by_initial[letter]
        )
        rows.append(f'<section><h2 class="index-letter" id="letter-{ord(letter)}">{escape(letter)}</h2>{entries}</section>')
    return ('<h1>Spis pieśni</h1>'
            '<p class="index-intro">Alfabetyczny spis 449 pieśni. Wybierz tytuł, aby przejść do tekstu.</p>'
            f'<p class="index-letters">{letter_links}</p>' + "".join(rows))


def navigation(songs: list[tuple[int, str, str]]) -> str:
    """Hierarchical machine-readable TOC, grouped in 50-song ranges."""
    groups = []
    for start in range(1, len(songs) + 1, 50):
        subset = songs[start - 1:start + 49]
        end = subset[-1][0]
        links = ''.join(f'<li><a href="{number:03}.xhtml">{number}. {escape(title)}</a></li>' for number, title, _ in subset)
        groups.append(f'<li><span>Pieśni {start}–{end}</span><ul>{links}</ul></li>')
    body = ('<nav epub:type="toc" id="toc"><h1>Spis pieśni</h1>'
            f'<ul class="nav-groups">{"".join(groups)}</ul></nav>'
            '<nav epub:type="landmarks" hidden="hidden">'
            '<h2>Najważniejsze strony</h2><ol>'
            '<li><a epub:type="cover" href="cover.xhtml">Okładka</a></li>'
            '<li><a epub:type="toc" href="index.xhtml">Spis alfabetyczny</a></li>'
            '</ol></nav>')
    return xhtml("Spis pieśni — nawigacja", body, nav=True)


def build_ncx(songs: list[tuple[int, str, str]]) -> str:
    """EPUB2-compatible navigation, grouped like EPUB3 nav for older readers."""
    order = 4
    groups = []
    for start in range(1, len(songs) + 1, 50):
        subset = songs[start - 1:start + 49]
        end = subset[-1][0]
        label = f"Pieśni {start}–{end}"
        # Group entry uses the first song as target; all songs are nested children.
        parts = [f'<navPoint id="range-{start}" playOrder="{order}"><navLabel><text>{escape(label)}</text></navLabel>'
                 f'<content src="{start:03}.xhtml"/>']
        order += 1
        for number, title, _ in subset:
            parts.append(f'<navPoint id="song-{number:03}" playOrder="{order}"><navLabel><text>{number}. {escape(title)}</text></navLabel>'
                         f'<content src="{number:03}.xhtml"/></navPoint>')
            order += 1
        parts.append('</navPoint>')
        groups.append(''.join(parts))
    return (f'<?xml version="1.0" encoding="utf-8"?>'
            '<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">'
            f'<head><meta name="dtb:uid" content="{IDENTIFIER}"/></head>'
            f'<docTitle><text>{escape(TITLE)}</text></docTitle><navMap>'
            '<navPoint id="cover" playOrder="1"><navLabel><text>Okładka</text></navLabel><content src="cover.xhtml"/></navPoint>'
            '<navPoint id="title" playOrder="2"><navLabel><text>Strona tytułowa</text></navLabel><content src="title.xhtml"/></navPoint>'
            '<navPoint id="contents" playOrder="3"><navLabel><text>Alfabetyczny spis pieśni</text></navLabel><content src="index.xhtml"/></navPoint>'
            f'{"".join(groups)}</navMap></ncx>')


STYLE = '''
body { font-family: Georgia,serif; line-height:1.5; margin:5%; color:#29251e; }
h1 { font-size:1.55em; line-height:1.3; margin:0 0 1em; text-align:center; color:#513047; }
h2 { font-size:1.2em; }
a, a:link, a:visited { color:#343038; text-decoration:none; }
a:hover { text-decoration:underline; }
p { margin:.65em 0 1.2em; }
.song { page-break-before:always; }
.song h1 { text-align:left; color:#29251e; font-size:1.35em; }
.song-number { font-size:.7em; color:#7c685e; font-weight:normal; display:block; margin-bottom:.3em; }
.title-page { text-align:center; margin-top:24%; }
.title-page h2 { color:#7c685e; }
.cover-page { margin:0 !important; padding:0 !important; text-align:center; }
.cover-page .cover { margin:0; padding:0; text-align:center; }
.cover-page .cover img { display:block; width:100%; max-width:100%; height:auto; margin:0 auto; }
.index-intro { font-size:.9em; text-align:center; font-style:italic; color:#58514f; margin:0 0 1.3em; }
.index-letters { text-align:center; line-height:2.2; margin:1em 0 2em; }
.index-letters a { display:inline-block; padding:0 .28em; text-decoration:underline; }
.index-letter { border-bottom:1px solid #d2c9bd; color:#74455a; margin:1.35em 0 .6em; padding-bottom:.15em; page-break-after:avoid; }
.index-entry { padding:.28em 0; margin:.12em 0; border-bottom:1px solid #eee9e2; page-break-inside:avoid; }
.index-number { color:#774d5d; font-weight:bold; white-space:nowrap; }
.nav-groups { list-style:none; padding:0; margin:0; }
.nav-groups > li { margin:1.1em 0; }
.nav-groups > li > span { font-weight:bold; color:#774d5d; }
.nav-groups ul { padding-left:1em; list-style:none; }
.nav-groups ul li { padding:.15em 0; margin:.1em 0; }
'''


def build(site: Path, output: Path, expected_count: int = 449) -> Path:
    songs = extract(site, expected_count)
    if not COVER_SOURCE.is_file():
        raise FileNotFoundError(f"Original hymnbook cover missing: {COVER_SOURCE}")
    cover_bytes = COVER_SOURCE.read_bytes()
    if not cover_bytes.startswith(b"\xff\xd8\xff"):
        raise ValueError("Hymnal cover must be a JPEG image")

    nav = navigation(songs)
    index = xhtml("Spis pieśni — alfabetycznie", alphabetical_index(songs))
    cover = xhtml("Okładka", '<section class="cover"><img src="cover.jpg" alt="Okładka śpiewnika zborowego Toruń"/></section>', body_class="cover-page")
    titlepage = xhtml(TITLE, '<section class="title-page"><h1>Śpiewnik zborowy</h1><h2>Toruń</h2><p>449 pieśni zborowych</p></section>')
    manifest = [
        '<item id="css" href="style.css" media-type="text/css"/>',
        '<item id="toc" href="toc.ncx" media-type="application/x-dtbncx+xml"/>',
        '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
        '<item id="cover-image" href="cover.jpg" media-type="image/jpeg" properties="cover-image"/>',
        '<item id="cover-page" href="cover.xhtml" media-type="application/xhtml+xml"/>',
        '<item id="title" href="title.xhtml" media-type="application/xhtml+xml"/>',
        '<item id="index" href="index.xhtml" media-type="application/xhtml+xml"/>',
    ] + [f'<item id="song{n:03}" href="{n:03}.xhtml" media-type="application/xhtml+xml"/>' for n, _, _ in songs]
    # The machine-readable nav.xhtml is deliberately excluded from the reading spine:
    # its 449 links otherwise consume many e-reader pages before the first song.
    spine = ('<itemref idref="cover-page"/><itemref idref="title"/>'
             '<itemref idref="index"/>' +
             ''.join(f'<itemref idref="song{n:03}"/>' for n, _, _ in songs))
    modified = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    opf = ('<?xml version="1.0" encoding="utf-8"?>'
           '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid" xml:lang="pl">'
           '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
           f'<dc:identifier id="bookid">{IDENTIFIER}</dc:identifier>'
           f'<dc:title>{escape(TITLE)}</dc:title><dc:language>pl</dc:language>'
           '<meta name="cover" content="cover-image"/>'
           f'<meta property="dcterms:modified">{modified}</meta>'
           f'</metadata><manifest>{"".join(manifest)}</manifest><spine toc="toc">{spine}</spine></package>')
    entries = {
        "META-INF/container.xml": ('<?xml version="1.0" encoding="utf-8"?>'
            '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
            '<rootfiles><rootfile full-path="OEBPS/package.opf" media-type="application/oebps-package+xml"/>'
            '</rootfiles></container>'),
        "OEBPS/package.opf": opf,
        "OEBPS/nav.xhtml": nav,
        "OEBPS/index.xhtml": index,
        "OEBPS/cover.xhtml": cover,
        "OEBPS/cover.jpg": cover_bytes,
        "OEBPS/title.xhtml": titlepage,
        "OEBPS/toc.ncx": build_ncx(songs),
        "OEBPS/style.css": STYLE,
    }
    for number, title, content in songs:
        entries[f"OEBPS/{number:03}.xhtml"] = xhtml(
            f"{number}. {title}",
            f'<section class="song"><h1><span class="song-number">Pieśń {number}</span>'
            f'{escape(title)}</h1>{content}</section>')
    for name, contents in entries.items():
        if name.endswith((".xml", ".xhtml", ".opf", ".ncx")):
            ElementTree.fromstring(contents)
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w") as zipfile:
        zipfile.writestr("mimetype", "application/epub+zip", compress_type=ZIP_STORED)
        for name, contents in entries.items():
            data = contents if isinstance(contents, bytes) else contents.encode("utf-8")
            zipfile.writestr(name, data, compress_type=ZIP_DEFLATED, compresslevel=9)
    print(f"EPUB created: {output} ({len(songs)} songs, original cover and formatted alphabetical index)")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", type=Path, default=Path("_site"))
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    build(args.site, args.output or args.site / "spiewnik" / SLUG)