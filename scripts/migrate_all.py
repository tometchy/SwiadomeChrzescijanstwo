#!/usr/bin/env python3
"""Jednorazowa migracja własnych stron swch.pl i wswch.pl do Jekyll.

Całe treści HTML w `_artykuly`, oryginalne HTML w `_source_archive` (niepubliczne),
pliki pobieralne w `assets/legacy`, raport i manifest linków w `_data`.
Bez dostępu do internetu skrypt kończy się błędem zamiast deklarować sukces.

Użycie: python scripts/migrate_all.py --max-pages 3500 --max-assets 2500
"""
from __future__ import annotations
import argparse
import hashlib
import html
import json
import posixpath
import re
import shutil
import sys
import time
import unicodedata
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit, urlunsplit, quote
from bs4 import BeautifulSoup, UnicodeDammit
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import yaml

ROOT = Path(__file__).resolve().parents[1]
HOSTS = {'swch.pl': 'swch', 'www.swch.pl': 'swch', 'wswch.pl': 'wswch', 'www.wswch.pl': 'wswch'}
PAGE_SUFFIXES = {'', '.htm', '.html', '.shtml'}
FILE_SUFFIXES = {'.pdf', '.epub', '.mobi', '.azw3', '.zip', '.doc', '.docx', '.rtf', '.txt', '.odt', '.mp3', '.ogg', '.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.ico', '.mp4', '.xlsx', '.xls', '.pps', '.ppt', '.pptx', '.chm', '.conf', '.gz', '.bz2', '.mybible', '.bbl', '.css', '.js', '.woff', '.woff2', '.ttf', '.eot'}
SKIP_SUFFIXES = {'.exe', '.msi', '.apk', '.dmg', '.so', '.php', '.asp', '.aspx', '.cgi'}
SECTIONS = {
    'opowiadania': 'Opowiadania', 'ostrzezenia': 'Ostrzeżenia',
    'biografie': 'Biografie', 'autorzy': 'Znani pisarze', 'polemiki': 'Dyskusje, polemiki',
    'ksiazki': 'Książki', 'traktaty': 'Traktaty ewangelizacyjne',
    'historia': 'Historia Kościoła', 'teologia': 'Teologia',
    'programy': 'Oprogramowanie', 'fundacja': 'Fundacja', 'tnp': 'Przekład Toruński',
}
SEEDS = (
    ['https://swch.pl/']
    + [f'https://swch.pl/{section}/index.html' for section in SECTIONS]
    + ['https://swch.pl/copyright.html', 'https://www.wswch.pl/', 'https://www.wswch.pl/informator-wydawniczy.html']
)
LARGE_LIMIT = 88 * 1024 * 1024  # GitHub enforces 100 MB per tracked file
CHUNK_SIZE = 60 * 1024 * 1024  # safe, reproducible binary chunks

HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; SWCH-Migration/2.0; approved site owner migration)'}


def slug(value: str, maxlen=100) -> str:
    value = unicodedata.normalize('NFKD', value.lower().replace('ł', 'l'))
    value = ''.join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r'^-|-$', '', re.sub(r'[^a-z0-9]+', '-', value))[:maxlen].strip('-') or 'tekst'


def normalize_url(url: str, base: str = '') -> tuple[str, str] | None:
    """Return (site alias, canonical URL), accept only two owned sites and safe paths."""
    value = urljoin(base, html.unescape(url).strip())
    sp = urlsplit(value)
    if sp.scheme not in ('http', 'https') or not sp.hostname:
        return None
    alias = HOSTS.get(sp.hostname.lower())
    if not alias:
        return None
    # Collapse dot-segments, reject query-dependent pages (tracking, search, etc).
    path = unquote(sp.path or '/')
    if '\\' in path or '\x00' in path:
        return None
    path = '/' + posixpath.normpath(path).lstrip('/')
    if sp.path.endswith('/') and not path.endswith('/'):
        path += '/'
    if path == '/':
        path = '/index.html'
    elif path.endswith('/'):
        path += 'index.html'
    suff = Path(path).suffix.lower()
    if suff not in PAGE_SUFFIXES | FILE_SUFFIXES:
        return None
    if path.lower().startswith(('/cgi-bin/', '/.git/', '/wp-admin/')):
        return None
    # Normalize canonical HTTP to HTTPS and host to non-www.
    return alias, urlunsplit(('https', 'swch.pl' if alias == 'swch' else 'www.wswch.pl', quote(path, safe='/-_.~()%'), '', ''))


def is_page(url: str) -> bool:
    return Path(urlsplit(url).path).suffix.lower() in PAGE_SUFFIXES


def stable_id(url: str) -> str:
    return hashlib.sha1(url.encode('utf-8')).hexdigest()[:9]


def relative_path(url: str) -> Path:
    p = unquote(urlsplit(url).path).lstrip('/')
    return Path(p or 'index.html')


def source_permalink(url: str) -> str:
    alias = normalize_url(url)[0]
    p = relative_path(url)
    name = '-'.join(p.with_suffix('').parts)
    return '/czytelnia/' + slug(alias + '-' + name, maxlen=95) + '-' + stable_id(url) + '/'


def decode(raw: bytes) -> str:
    # Some pages contain Windows-1250 content declared as ISO-8859-2 and vice versa.
    # UnicodeDammit uses both declarations and statistical detection; keep source for review.
    return UnicodeDammit(raw, is_html=True).unicode_markup or raw.decode('windows-1250', errors='replace')


def title_of(soup: BeautifulSoup, url: str, incoming: dict[str, str]) -> str:
    noise = {'czytelnia chrześcijanina', 'wydawnictwo świadome chrześcijaństwo', 'strona główna', 'czytelnia chrzescijanina'}
    for candidate in (soup.find('h1'), soup.find('h2'), soup.find('h3'), soup.find('title')):
        if candidate:
            text = re.sub(r'\s+', ' ', candidate.get_text(' ', strip=True)).strip()
            if text and text.lower() not in noise and not text.lower().startswith('czytelnia chrześcijanina -'):
                return text[:240]
    if incoming.get(url):
        return incoming[url][:240]
    return relative_path(url).stem.replace('_', ' ').replace('-', ' ').title()


def section_of(url: str) -> str:
    parts = relative_path(url).parts
    return SECTIONS.get(parts[0].lower(), 'Archiwum') if parts else 'Archiwum'


def content_node(soup: BeautifulSoup):
    body = soup.body or soup
    # Identify likely content before removing decorations; older layouts use TDs.
    main = body.find('article') or body.find('main') or body.find(id=re.compile(r'^(content|tresc|article)$', re.I))
    if main is None:
        cells = [x for x in body.find_all('td') if len(x.get_text(' ', strip=True)) >= 150]
        if cells:
            cells.sort(key=lambda x: len(x.get_text(' ', strip=True)), reverse=True)
            # Do not discard content in multiple independent cells.
            if len(cells[0].get_text(' ', strip=True)) >= .58 * max(1, len(body.get_text(' ', strip=True))):
                main = cells[0]
    node = BeautifulSoup(str(main or body), 'html.parser')
    for el in node.select('script,style,noscript,iframe,form,nav,header,footer'):
        el.decompose()
    for el in node.select('[id*=menu i], [class*=menu i]'):
        el.decompose()
    return node


def is_article(url: str, soup: BeautifulSoup) -> bool:
    if normalize_url(url)[0] != 'swch':
        return False
    parts = relative_path(url).parts
    if not parts or parts[0].lower() not in SECTIONS:
        return False
    if parts[0].lower() in {'fundacja', 'tnp'}:
        return False  # dedicated Jekyll sections, kept in separate manifests
    body = content_node(soup)
    text = body.get_text(' ', strip=True)
    if len(text) < 180:
        return False
    # Category and author indexes are link menus, not literature to be reproduced as articles.
    if relative_path(url).name.lower() == 'index.html':
        nav_chars = sum(len(a.get_text(' ', strip=True)) for a in body.find_all('a'))
        if nav_chars > len(text) * .29:
            return False
    return True


@dataclass
class Response:
    raw: bytes
    content_type: str
    status: int


class Retriever:
    def __init__(self, delay, offline_dir=None, max_file_bytes=60_000_000, max_total_bytes=450_000_000):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.session.mount('https://', HTTPAdapter(max_retries=Retry(total=3, backoff_factor=1, status_forcelist=(429, 500, 502, 503, 504), allowed_methods=['GET'])))
        self.delay = delay
        self.offline_dir = Path(offline_dir) if offline_dir else None
        self.max_file_bytes = max_file_bytes
        self.max_total_bytes = max_total_bytes
        self.downloaded_bytes = 0
        self.last = 0

    def get(self, url: str, asset=False) -> Response:
        site, _ = normalize_url(url)
        if self.offline_dir:
            path = self.offline_dir / site / relative_path(url)
            if not path.is_file():
                raise FileNotFoundError(str(path))
            raw = path.read_bytes()
            return Response(raw, 'text/html' if is_page(url) else 'application/octet-stream', 200)
        waiting = self.delay - (time.monotonic() - self.last)
        if waiting > 0: time.sleep(waiting)
        self.last = time.monotonic()
        with self.session.get(url, timeout=(10, 40), stream=True, allow_redirects=True) as r:
            r.raise_for_status()
            # Prevent redirect to unrelated hosts or untrusted resources.
            if normalize_url(r.url) is None:
                raise ValueError('Redirect poza migrowane domeny: ' + r.url)
            ctype = r.headers.get('content-type', '')
            estimated = int(r.headers.get('content-length') or '0')
            if estimated > self.max_file_bytes or (asset and self.downloaded_bytes + estimated > self.max_total_bytes):
                raise ValueError('Przekroczony limit wielkości pliku lub archiwum')
            chunks, size = [], 0
            for chunk in r.iter_content(chunk_size=128 * 1024):
                if not chunk: continue
                size += len(chunk)
                if size > self.max_file_bytes or (asset and self.downloaded_bytes + size > self.max_total_bytes):
                    raise ValueError('Przekroczony limit wielkości pliku lub archiwum')
                chunks.append(chunk)
            if asset:
                self.downloaded_bytes += size
            return Response(b''.join(chunks), ctype, r.status_code)


def scan_links(soup, current_url: str, page_queue, asset_queue, seen, asset_seen, names, asset_titles):
    for a in soup.find_all(['a', 'img', 'source', 'link', 'script'], href=True) + soup.find_all(['img', 'source', 'script'], src=True):
        attribute = 'href' if a.has_attr('href') else 'src'
        href = (a.get(attribute) or '').strip()
        target = normalize_url(href, current_url)
        if not target: continue
        _, norm = target
        if is_page(norm):
            if norm not in seen:
                page_queue.append(norm)
            label = a.get_text(' ', strip=True)
            if label and norm not in names and label.lower() not in ('więcej', 'czytaj', 'kliknij', 'strona główna'):
                names[norm] = label[:240]
        elif norm not in asset_seen:
            asset_queue.append(norm)
        if not is_page(norm) and a.name == 'a' and a.get_text(' ', strip=True):
            asset_titles.setdefault(norm, a.get_text(' ', strip=True)[:240])


def mirror(args):
    retriever = Retriever(args.delay, args.offline_dir, args.max_asset_mb * 1024 * 1024, args.max_total_mb * 1024 * 1024)
    queue = deque(normalize_url(u)[1] for u in SEEDS)
    assets = deque()
    visited, asset_seen, pages, downloaded, errors, names, asset_titles = set(), set(), {}, {}, [], {}, {}
    large_files = []
    source_dir = ROOT / '_source_archive'
    for directory in (ROOT / '_artykuly', ROOT / 'assets' / 'legacy', ROOT / 'archiwum' / 'swch', ROOT / 'archiwum' / 'wswch', source_dir):
        directory.mkdir(parents=True, exist_ok=True)
    while queue and len(visited) < args.max_pages:
        url = queue.popleft()
        if url in visited: continue
        visited.add(url)
        alias = normalize_url(url)[0]
        if not is_page(url):
            if url not in asset_seen:
                assets.append(url)
            continue
        try:
            resp = retriever.get(url)
            if resp.content_type and 'html' not in resp.content_type.lower() and b'<html' not in resp.raw[:1000].lower():
                raise ValueError('Nie-HTML; nie przeniesiono jako artykuł: ' + resp.content_type)
            text = decode(resp.raw)
            soup = BeautifulSoup(text, 'html.parser')
            scan_links(soup, url, queue, assets, visited, asset_seen, names, asset_titles)
            pages[url] = soup
            dest = source_dir / alias / relative_path(url)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(resp.raw)
            # Publish a byte-identical HTML snapshot, not only a selected text fragment.
            published = ROOT / 'archiwum' / alias / relative_path(url)
            published.parent.mkdir(parents=True, exist_ok=True)
            published.write_bytes(resp.raw)
            if len(visited) % 50 == 0:
                print(f'Strony: {len(visited)}, poprawne: {len(pages)}, w kolejce: {len(queue)}', flush=True)
        except Exception as exc:
            errors.append({'url': url, 'type': 'page', 'error': str(exc)})
    if queue:
        errors.append({'type': 'limit', 'error': f'Limit stron {args.max_pages} osiągnięty; pozostało {len(queue)} adresów w kolejce'})
    # Discover linked files across the entire site (also PDF/EPUB, not just images).
    while assets and len(asset_seen) < args.max_assets:
        url = assets.popleft()
        if url in asset_seen: continue
        asset_seen.add(url)
        alias = normalize_url(url)[0]
        try:
            response = retriever.get(url, asset=True)
            path = ROOT / 'assets' / 'legacy' / alias / relative_path(url)
            path.parent.mkdir(parents=True, exist_ok=True)
            # Large assets (e.g. the ~126 MB TNP PDF) cannot be tracked as a
            # single file by GitHub. Store lossless chunks in git; reassemble
            # them only into the built _site during Pages deployment.
            if len(response.raw) > LARGE_LIMIT:
                chunkdir = ROOT / '_large_parts' / alias / stable_id(url)
                chunkdir.mkdir(parents=True, exist_ok=True)
                pieces = []
                for i, start in enumerate(range(0, len(response.raw), CHUNK_SIZE)):
                    piece = chunkdir / f'{i:04d}.part'
                    piece.write_bytes(response.raw[start:start + CHUNK_SIZE])
                    pieces.append(str(piece.relative_to(ROOT)).replace('\\', '/'))
                large_files.append({
                    'source_url': url, 'target': '/' + str(path.relative_to(ROOT)).replace('\\', '/'),
                    'size': len(response.raw), 'sha256': hashlib.sha256(response.raw).hexdigest(),
                    'parts': pieces,
                })
            else:
                # Assets are exact byte copies to avoid silent data corruption.
                path.write_bytes(response.raw)
            # Preserve original relative CSS/JS/image paths inside the published archive.
            if len(response.raw) <= LARGE_LIMIT:
                original_location = ROOT / 'archiwum' / alias / relative_path(url)
                original_location.parent.mkdir(parents=True, exist_ok=True)
                original_location.write_bytes(response.raw)
            downloaded[url] = '/' + str(path.relative_to(ROOT)).replace('\\', '/')
            if len(downloaded) % 75 == 0:
                print(f'Pliki: {len(downloaded)}, bajty: {retriever.downloaded_bytes:,}', flush=True)
        except Exception as exc:
            errors.append({'url': url, 'type': 'asset', 'error': str(exc)})
    if assets:
        errors.append({'type': 'limit', 'error': f'Limit plików {args.max_assets} osiągnięty; pozostało {len(assets)} plików w kolejce'})
    if not pages:
        raise RuntimeError('Nie pobrano żadnej strony: migracja nie może zostać uznana za wykonaną. ' + str(errors[:3]))
    write_content(pages, downloaded, errors, names, asset_titles, args, large_files)
    return len(pages), len(downloaded), len(errors)


def replace_hrefs(node: BeautifulSoup, base: str, published_articles: set[str], assets: dict[str, str]):
    for a in node.find_all(['a', 'img', 'source']):
        for attr in ('href', 'src'):
            value = a.get(attr)
            if not value: continue
            low = value.strip().lower()
            if low.startswith(('javascript:', 'data:')):
                if attr == 'href': a[attr] = '#'
                else: del a[attr]
                continue
            normalized = normalize_url(value, base)
            if normalized:
                _, url = normalized
                fragment = urlsplit(urljoin(base, value)).fragment
                if url in published_articles:
                    a[attr] = source_permalink(url) + ('#' + fragment if fragment else '')
                elif url in assets:
                    a[attr] = assets[url] + ('#' + fragment if fragment else '')
                else:
                    a[attr] = url + ('#' + fragment if fragment else '')
            elif value.startswith('/') and not value.startswith('//'):
                a[attr] = urljoin(base, value)
        # Avoid transferring deprecated markup or inline event handlers.
        for attribute in list(a.attrs):
            if attribute.lower().startswith('on'):
                del a[attribute]
    return node


def exact_text(node):
    """Exact visible character stream in HTML DOM; preserves whitespace and Unicode.

    Script/style not visible text; no stripping of page content, forms, tables or notes.
    """
    clone = BeautifulSoup(str(node), 'html.parser')
    for tag in clone.find_all(['script', 'style', 'template']):
        tag.decompose()
    return ''.join(clone.strings)


def safe_body_html(soup, url=None, all_pages=None, assets=None):
    """Use the COMPLETE body. Never guess a main TD or omit additional paragraphs."""
    body = soup.body or soup
    # Only eliminate active scripts to prevent executable third-party code in new layout.
    node = BeautifulSoup(str(body), 'html.parser')
    for tag in node.find_all(['script', 'style', 'template']):
        tag.decompose()
    for tag in node.find_all(True):
        for attr in list(tag.attrs):
            if attr.lower().startswith('on'):
                del tag[attr]
        # Only rewrite link ATTRIBUTES; all textual characters remain unchanged.
        if url and all_pages:
            for attr in ('href','src'):
                value=tag.get(attr)
                if not isinstance(value,str):continue
                target=normalize_url(value,url)
                if not target:continue
                alias,canonical=target
                fragment=urlsplit(urljoin(url,value)).fragment
                if canonical in assets or canonical in (assets or {}):
                    destination=assets[canonical]
                elif canonical in all_pages:
                    destination=source_permalink(canonical) if is_article(canonical,all_pages[canonical]) else '/archiwum/'+alias+'/'+str(relative_path(canonical)).replace('\\','/')
                else:
                    # Keep original link to a page/file which could not be downloaded;
                    # strict import has already logged unavailable resources.
                    destination=canonical
                # Every generated article lives at /czytelnia/<slug>/.
                # Relative links keep working both under GitHub Pages /<repo>/
                # and later under the final root domain (baseurl: '').
                if destination.startswith('/') and not destination.startswith('//'):
                    destination='../../'+destination.lstrip('/')
                tag[attr]=destination+('#'+fragment if fragment else '')
    # Keep full body text, including nav, footer, tables, copyright and form labels.
    inner = node.body.decode_contents() if node.body else node.decode_contents()
    result = BeautifulSoup(inner, 'html.parser')
    before, after = exact_text(body), exact_text(result)
    if before != after:
        import difflib
        snippet = '\n'.join(list(difflib.unified_diff(before.splitlines(), after.splitlines()))[:20])
        raise ValueError('RÓŻNICA W TEKŚCIE PRZED/PO KONWERSJI HTML: ' + snippet)
    return inner, hashlib.sha256(before.encode('utf-8')).hexdigest(), len(before)


def parse_publisher_catalog(soup):
    """Extract all 41 book rows and 39 brochure rows from actual publisher tables.
    Do not silently approximate titles from prewritten descriptions.
    """
    found=[]
    for tr in soup.find_all('tr'):
        cells=tr.find_all(['td','th'],recursive=False)
        if len(cells)<3: continue
        first=cells[0].get_text(' ',strip=True)
        if not re.fullmatch(r'\d{1,2}',first): continue
        n=int(first)
        author=cells[1].get_text(' ',strip=True)
        title=cells[2].get_text(' ',strip=True)
        if not title or not author: continue
        found.append({'number':n,'author':author,'title':title, 'edition': cells[3].get_text(' ',strip=True) if len(cells)>3 else '', 'price': cells[4].get_text(' ',strip=True) if len(cells)>4 else '', 'status': cells[5].get_text(' ',strip=True) if len(cells)>5 else ''})
    # In some markup the catalog number and label are inside nested elements; no guessing.
    starts=[i for i,row in enumerate(found) if row['number']==41]
    if len(starts)!=1: raise ValueError('Nie znaleziono dokładnie jednego katalogu 41 książek (wymagany odczyt tabel HTML)')
    i=starts[0]; book_rows=found[i:i+41]; brochure_rows=found[i+41:i+80]
    if [x['number'] for x in book_rows]!=list(range(41,0,-1)) or [x['number'] for x in brochure_rows]!=list(range(39,0,-1)):
        raise ValueError('Katalog wydawcy nie jest kompletny (41 książek + 39 broszur); odmowa deklaracji 1:1')
    return {'books': book_rows, 'brochures': brochure_rows}


def refresh_publisher_catalog(pages):
    home = 'https://www.wswch.pl/index.html'
    if home not in pages:
        raise ValueError('Nie pobrano strony głównej wydawnictwa: ' + home)
    source = parse_publisher_catalog(pages[home])
    changes=[]
    for collection,entries in (('_ksiazki',source['books']),('_broszury',source['brochures'])):
        by_num={item['number']: item for item in entries}
        files=list((ROOT / collection).glob('*.md'))
        if len(files)!=len(entries): raise ValueError('Nieprawidłowa liczba wpisów Jekyll '+collection)
        for file in files:
            raw=file.read_text(encoding='utf-8')
            parts=raw.split('---',2)
            meta=yaml.safe_load(parts[1])
            n=meta['catalog_number']
            if n not in by_num: raise ValueError(f'Brak numeru {n} w tabeli '+collection)
            row=by_num[n]
            old={key:meta.get(key) for key in ('title','author','edition_note','historical_price','catalog_status')}
            meta['title']=row['title'];meta['author']=row['author']
            meta['source_provenance']='original-downloaded-html'
            meta['source_text_verified']=True
            meta['catalog_status']=row['status']
            if row['edition']: meta['edition_note']=row['edition']
            else: meta.pop('edition_note',None)
            if row['price']: meta['historical_price']=row['price']
            else: meta.pop('historical_price',None)
            if old!={key:meta.get(key) for key in old}:
                changes.append({'file':str(file.relative_to(ROOT)),'before':old,'after':{key:meta.get(key) for key in old}})
            file.write_text('---\n'+yaml.safe_dump(meta,allow_unicode=True,sort_keys=False,width=250)+'---\n',encoding='utf-8')
    (ROOT / '_data' / 'publisher_catalog_verified.json').write_text(json.dumps(source,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return changes


def write_content(pages, assets, errors, names, asset_titles, args, large_files=None):
    large_files=large_files or []
    report={'source_html_pages':len(pages),'html_pages_archived':len(pages),'articles_discovered':0, 'articles_written':0,'assets_downloaded':len(assets),'errors':len(errors),'source_to_new_text_diffs':0,'books_verified':0,'brochures_verified':0}
    changes=[]
    try:
        changes=refresh_publisher_catalog(pages)
        report['books_verified']=41;report['brochures_verified']=39
    except Exception as exc:
        errors.append({'type':'catalog-verification','error':str(exc)})
    article_records=[]
    fallback_records=[]
    for url,soup in sorted(pages.items()):
        # Full old page HTML is already published byte-for-byte in /archiwum/<site>/.
        # Only editorial articles also become Jekyll collection documents.
        if not is_article(url,soup): continue
        try:
            body,source_hash,count=safe_body_html(soup, url, pages, assets)
            if not count: raise ValueError('Pusty tekst źródła')
            title=title_of(soup,url,names)
            if not title: raise ValueError('Brak źródłowego tytułu')
            permalink=source_permalink(url)
            dest=ROOT/'_artykuly'/(permalink.strip('/').split('/')[-1]+'.md')
            data={'title':title,'category':section_of(url),'permalink':permalink,'source_url':url,'imported_from_legacy':True,'source_text_sha256':source_hash,'source_char_count':count,'source_verified':True}
            # Jekyll document remains editable, with HTML markup retained in markdown.
            # Liquid RAW prevents any original {{...}} or {%...%} being evaluated.
            filetext='---\n'+yaml.safe_dump(data,allow_unicode=True,sort_keys=False,width=180)+'---\n\n{% raw %}\n'+body+'\n{% endraw %}\n'
            # Verification before writing: no substantive character added or removed.
            parsed=filetext.split('{% raw %}\n',1)[1].rsplit('\n{% endraw %}',1)[0]
            if hashlib.sha256(exact_text(BeautifulSoup(parsed,'html.parser')).encode('utf-8')).hexdigest()!=source_hash:
                raise ValueError('SHA256 tekstu niezgodny przed zapisem Jekyll')
            dest.parent.mkdir(parents=True,exist_ok=True)
            if dest.exists() and not args.overwrite:
                prior=dest.read_text(encoding='utf-8')
                if prior!=filetext:
                    raise ValueError('Istniejący wpis zmieniony względem źródła; uruchom ponownie z --overwrite po sprawdzeniu')
            else: dest.write_text(filetext,encoding='utf-8')
            report['articles_written']+=1
            article_records.append({'source_url':url,'path':str(dest.relative_to(ROOT)),'permalink':permalink,'sha256':source_hash,'source_char_count':count})
        except Exception as exc:
            errors.append({'url':url,'type':'article-text','error':str(exc)})
            alias=normalize_url(url)[0]
            fallback_records.append({'title':title_of(soup,url,names),'category':section_of(url),'source_url':url,'url':'/archiwum/'+alias+'/'+str(relative_path(url)).replace('\\','/')})
    report['articles_discovered']=len(article_records)+len(fallback_records)
    report['articles_archived_only']=len(fallback_records)
    (ROOT/'_data'/'fallback_articles.yml').write_text(yaml.safe_dump(fallback_records,allow_unicode=True,sort_keys=False,width=250),encoding='utf-8')
    docs,tnp=[],[]
    for url,soup in pages.items():
        alias,_=normalize_url(url)
        if alias!='swch':continue
        prefix=relative_path(url).parts[0]
        if prefix not in ('fundacja','tnp'):continue
        for a in soup.find_all('a',href=True):
            norm=normalize_url(a['href'],url)
            if not norm or is_page(norm[1]):continue
            result={'title':a.get_text(' ',strip=True) or relative_path(norm[1]).name,'url':assets.get(norm[1],norm[1]),'source_url':norm[1],'local':norm[1] in assets}
            if prefix=='fundacja':docs.append(result)
            else:tnp.append(result)
    for name,rows in (('fundacja_dokumenty.yml',docs),('tnp_pliki.yml',tnp)):
        unique={row['source_url']:row for row in rows}
        (ROOT/'_data'/name).write_text(yaml.safe_dump(list(unique.values()),allow_unicode=True,sort_keys=False),encoding='utf-8')
    (ROOT/'_data'/'large_assets.yml').write_text(yaml.safe_dump(large_files,allow_unicode=True,sort_keys=False),encoding='utf-8')
    # Text/content archive comparison, all HTML raw bytes are checked.
    archived=[]
    for url,soup in sorted(pages.items()):
        site,_=normalize_url(url)
        original=ROOT/'_source_archive'/site/relative_path(url)
        public=ROOT/'archiwum'/site/relative_path(url)
        if not original.is_file() or not public.is_file() or original.read_bytes()!=public.read_bytes():
            errors.append({'url':url,'type':'raw-source-checksum','error':'Archiwalna kopia HTML różni się od oryginału'})
        else:
            archived.append({'url':url,'path':'/'+str(public.relative_to(ROOT)),'sha256':hashlib.sha256(original.read_bytes()).hexdigest()})
    archive_index=[]
    for url,soup in sorted(pages.items()):
        alias,_=normalize_url(url)
        archive_index.append({'title':title_of(soup,url,names),'url':'/archiwum/'+alias+'/'+str(relative_path(url)),'source_url':url,'source_site':alias})
    (ROOT/'_data'/'legacy_pages.yml').write_text(yaml.safe_dump(archive_index,allow_unicode=True,sort_keys=False,width=250),encoding='utf-8')
    report['errors']=len(errors)
    report['source_to_new_text_diffs']=sum(x.get('type') == 'article-text' for x in errors)
    report['error_types']=dict(Counter(x.get('type', 'unknown') for x in errors))
    result={'status':'VERIFIED' if not errors and report['books_verified']==41 and report['brochures_verified']==39 else 'INCOMPLETE', 'summary':report, 'articles':article_records,'fallback_articles':fallback_records,'archived_html_pages':archived, 'assets':assets,'catalog_changes_from_online_source':changes,'errors':errors, 'limitations':['Unlinked URLs cannot be discovered automatically; verify source sitemap and backups','External-hosted assets are outside two domains']}
    (ROOT/'migration-report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    # Save partial captures without ever claiming they are verified.
    if result['status']!='VERIFIED':
        if not getattr(args,'allow_incomplete',False):
            raise RuntimeError('Odmowa oznaczenia migracji 1:1: '+str(len(errors))+' błędów; czytaj migration-report.json')
        print('IMPORT NIEKOMPLETNY: zapisano oryginalne pobrane bajty. Publikacja 1:1 pozostaje zablokowana.',flush=True)
    print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Migracja artykułów, dokumentów i zdjęć ze swch.pl/ wswch.pl')
    parser.add_argument('--max-pages', type=int, default=3500)
    parser.add_argument('--max-assets', type=int, default=2500)
    parser.add_argument('--delay', type=float, default=.25, help='Odstęp między żądaniami, w sekundach')
    parser.add_argument('--max-asset-mb', type=int, default=250)
    parser.add_argument('--max-total-mb', type=int, default=1400)
    parser.add_argument('--offline-dir', help='Folder archiwalnych plików: swch/... i wswch/... (dla testów/backupów)')
    parser.add_argument('--overwrite', action='store_true', help='Odtwórz wcześniej migrowane Markdown z oryginału')
    parser.add_argument('--allow-incomplete', action='store_true', help='Zapisz częściowy import do naprawy; raport nadal INCOMPLETE')
    parser.add_argument('--fail-on-errors', action='store_true', help='Tryb rygorystyczny (domyślny)')
    args = parser.parse_args()
    if args.allow_incomplete and args.fail_on_errors:
        parser.error('--allow-incomplete i --fail-on-errors wykluczają się')
    try:
        count = mirror(args)
        print(f'Gotowe: {count[0]} HTML, {count[1]} plików, {count[2]} błędów. Szczegóły w migration-report.json')
    except Exception as exc:
        print('BŁĄD MIGRACJI:', exc, file=sys.stderr)
        raise SystemExit(1)
