#!/usr/bin/env python3
"""Szybki test danych i spójności źródeł Jekyll.

Archiwalne pliki HTML mogą mieć oryginalne kodowanie inne niż UTF-8;
nie zmieniamy ich bajtów. Porównuje je osobno strict_audit.py.
"""
from pathlib import Path
from collections import Counter
from urllib.parse import urlsplit
import re
import sys
import yaml
ROOT = Path(__file__).resolve().parents[1]
errors, counts = [], Counter()
permalinks = {}
for collection in ['_ksiazki', '_broszury', '_artykuly']:
    for f in sorted((ROOT/collection).glob('*.md')):
        content=f.read_text(encoding='utf-8')
        fm=re.match(r'^---\s*\n(.*?)\n---\s*\n',content,re.S)
        if not fm:
            errors.append(f'{f}: brak prawidłowych YAML frontmatter');continue
        try:data=yaml.safe_load(fm.group(1))
        except Exception as e: errors.append(f'{f}: YAML: {e}');continue
        counts[collection]+=1
        if not isinstance(data,dict) or not data.get('title'):
            errors.append(f'{f}: brak tytułu');continue
        perma=data.get('permalink') or f"/{collection[1:]}/{f.stem}/"
        if perma in permalinks:
            errors.append(f'Podwójny permalink: {perma} w {f} i {permalinks[perma]}')
        perma and permalinks.setdefault(perma,f)
        for key in ('allegro_url','cover_url'):
            value=data.get(key)
            if value and key=='allegro_url' and not value.startswith('https://allegro.pl/'):
                errors.append(f'{f}: nieznany adres Allegro: {value}')
            if value and key=='cover_url' and value.startswith('/') and not (ROOT/value.lstrip('/')).is_file():
                errors.append(f'{f}: nieistniejąca okładka: {value}')
        if data.get('imported_from_legacy') and not data.get('source_url'):
            errors.append(f'{f}: brak adresu źródłowego starego artykułu')
for file in sorted(ROOT.rglob('*')):
    if not file.is_file() or any(x in file.parts for x in ('_source_archive', '_historical_sources', 'archiwum', '_large_parts', 'assets', '.git', '.venv', '_site', 'vendor', 'node_modules')):
        continue
    if file.suffix in ('.md','.html'):
        try:
            content=file.read_text(encoding='utf-8')
        except UnicodeDecodeError as exc:
            errors.append(f'{file}: niepoprawny UTF-8 w źródle Jekyll: {exc}')
            continue
        for m in re.finditer(r'(?:href|src)=["\'](/assets/[^"\']+)["\']',content):
            if not (ROOT / m.group(1).lstrip('/')).is_file():
                errors.append(f'{file}: brak lokalnego zasobu {m.group(1)}')
print('Kontrola danych:',dict(counts))
print('Liczba błędów:',len(errors))
for error in errors[:100]: print('ERR:',error)
if errors: sys.exit(1)
