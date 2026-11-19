#!/usr/bin/env python3
"""Build EPUB from Jekyll-rendered Markdown song pages; never maintain duplicate lyrics.

_piesni/*.md -> Jekyll HTML -> generated EPUB included in GitHub Pages output.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from html import escape
from pathlib import Path
import re
from uuid import NAMESPACE_URL, uuid5
from xml.etree import ElementTree
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile

from bs4 import BeautifulSoup, NavigableString, Tag

TITLE = "Śpiewnik zborowy — Toruń"
SLUG = "Spiewnik-Torun.epub"
IDENTIFIER = "urn:uuid:" + str(uuid5(NAMESPACE_URL, "https://wswch.pl/spiewnik/torun"))
XHTML_NS = "http://www.w3.org/1999/xhtml"
ALLOWED = {"p", "br", "strong", "b", "em", "i", "blockquote", "ul", "ol", "li", "h2", "h3", "hr", "sup", "sub"}
VOID = {"br", "hr"}


def convert_html(node) -> str:
    """Preserve Markdown formatting from Jekyll; omit website-specific HTML."""
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


def xhtml(title: str, body: str, *, nav: bool = False) -> str:
    nav_ns = ' xmlns:epub="http://www.idpf.org/2007/ops"' if nav else ""
    return (f'<?xml version="1.0" encoding="utf-8"?>\n'
            f'<html xmlns="{XHTML_NS}"{nav_ns} xml:lang="pl" lang="pl">'
            f'<head><title>{escape(title)}</title>'
            '<meta charset="utf-8"/><link rel="stylesheet" type="text/css" href="style.css"/>'
            f'</head><body>{body}</body></html>')


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


def build(site: Path, output: Path, expected_count: int = 449) -> Path:
    songs = extract(site, expected_count)
    toc_rows = "".join(f'<li><a href="{n:03}.xhtml">{n}. {escape(title)}</a></li>' for n, title, _ in songs)
    nav = xhtml("Spis pieśni", f'<nav epub:type="toc" id="toc"><h1>Spis pieśni</h1><ol>{toc_rows}</ol></nav>', nav=True)
    titlepage = xhtml(TITLE, '<section class="title-page"><h1>Śpiewnik zborowy</h1><h2>Toruń</h2><p>449 pieśni zborowych</p></section>')
    css = ('body{font-family:serif;line-height:1.6;margin:5%;color:#222}'
           'h1{font-size:1.5em;line-height:1.25;margin:0 0 1em}'
           'p{margin:.6em 0 1.15em}li{margin:.3em 0}'
           '.song{page-break-before:always}.title-page{text-align:center;margin-top:25%}'
           '.song-number{font-size:.85em;color:#666;font-weight:normal;display:block}'
           'nav ol{padding-left:2em}nav li{margin:.35em 0}')
    ncx_items = "".join(
        f'<navPoint id="song-{n:03}" playOrder="{n+2}"><navLabel><text>{n}. {escape(title)}</text></navLabel>'
        f'<content src="{n:03}.xhtml"/></navPoint>' for n, title, _ in songs
    )
    ncx = (f'<?xml version="1.0" encoding="utf-8"?>'
           f'<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">'
           f'<head><meta name="dtb:uid" content="{IDENTIFIER}"/></head>'
           f'<docTitle><text>{escape(TITLE)}</text></docTitle><navMap>'
           '<navPoint id="title" playOrder="1"><navLabel><text>Strona tytułowa</text></navLabel><content src="title.xhtml"/></navPoint>'
           '<navPoint id="contents" playOrder="2"><navLabel><text>Spis pieśni</text></navLabel><content src="nav.xhtml"/></navPoint>'
           f'{ncx_items}</navMap></ncx>')
    manifest = [
        '<item id="css" href="style.css" media-type="text/css"/>',
        '<item id="toc" href="toc.ncx" media-type="application/x-dtbncx+xml"/>',
        '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
        '<item id="title" href="title.xhtml" media-type="application/xhtml+xml"/>',
    ] + [f'<item id="song{n:03}" href="{n:03}.xhtml" media-type="application/xhtml+xml"/>' for n, _, _ in songs]
    spine = '<itemref idref="title"/><itemref idref="nav"/>' + ''.join(
        f'<itemref idref="song{n:03}"/>' for n, _, _ in songs)
    modified = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    opf = ('<?xml version="1.0" encoding="utf-8"?>'
           '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid" xml:lang="pl">'
           '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
           f'<dc:identifier id="bookid">{IDENTIFIER}</dc:identifier>'
           f'<dc:title>{escape(TITLE)}</dc:title><dc:language>pl</dc:language>'
           f'<meta property="dcterms:modified">{modified}</meta>'
           f'</metadata><manifest>{"".join(manifest)}</manifest><spine toc="toc">{spine}</spine></package>')
    entries = {
        "META-INF/container.xml": ('<?xml version="1.0" encoding="utf-8"?>'
            '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
            '<rootfiles><rootfile full-path="OEBPS/package.opf" media-type="application/oebps-package+xml"/>'
            '</rootfiles></container>'),
        "OEBPS/package.opf": opf,
        "OEBPS/nav.xhtml": nav,
        "OEBPS/title.xhtml": titlepage,
        "OEBPS/toc.ncx": ncx,
        "OEBPS/style.css": css,
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
            zipfile.writestr(name, contents.encode("utf-8"), compress_type=ZIP_DEFLATED, compresslevel=9)
    print(f"EPUB created: {output} ({len(songs)} songs)")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", type=Path, default=Path("_site"))
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    build(args.site, args.output or args.site / "spiewnik" / SLUG)
