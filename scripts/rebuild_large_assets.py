#!/usr/bin/env python3
"""Restore byte-identical large legacy files in _site for Pages deployment.

GitHub has a 100 MB per-file repository limit. Migration saves original large
resources as safe 60 MiB chunks under _large_parts, and this script restores
those files only to the deployable site directory after Jekyll builds.
"""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]

def rebuild(root: Path, output: Path) -> int:
    manifest = root / '_data/large_assets.yml'
    if not manifest.is_file():
        return 0
    entries = yaml.safe_load(manifest.read_text(encoding='utf-8')) or []
    outroot = output.resolve()
    for entry in entries:
        rel = entry['target'].lstrip('/')
        dest = (outroot / rel).resolve()
        if not dest.is_relative_to(outroot):
            raise ValueError(f'Unsafe output path: {rel}')
        dest.parent.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256()
        size = 0
        # Binary concatenation without modifying the original bytes.
        with dest.open('wb') as result:
            for part in entry['parts']:
                chunkpath = (root / part).resolve()
                if not chunkpath.is_relative_to(root.resolve()) or not chunkpath.is_file():
                    raise ValueError(f'Missing or unsafe binary part: {part}')
                with chunkpath.open('rb') as source:
                    while data := source.read(1024 * 1024):
                        result.write(data)
                        digest.update(data)
                        size += len(data)
        if size != entry['size'] or digest.hexdigest() != entry['sha256']:
            dest.unlink(missing_ok=True)
            raise ValueError(f'Checksum or size mismatch for {rel}')
        print(f'Restored {rel}: {size:,} bytes SHA256={digest.hexdigest()}')
    return len(entries)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='_site')
    args = parser.parse_args()
    print('Total large assets restored:', rebuild(ROOT, (ROOT / args.output).resolve()))
