#!/usr/bin/env python3
"""Cache authentic cover photos from the seller's links and crop front panels.
Run locally with Internet access. Existing local assets are preserved.
"""
from pathlib import Path
from io import BytesIO
import re,sys
import yaml,requests
from PIL import Image, ImageOps
ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'assets'/'img'/'books';DEST.mkdir(parents=True,exist_ok=True)
s=requests.Session();s.headers['User-Agent']='Mozilla/5.0 (compatible; publication asset archival)'
ok=0;errors=0
for path in sorted((ROOT/'_ksiazki').glob('*.md')):
    content=path.read_text(encoding='utf-8');match=re.match(r'^---\n(.*?)\n---\n',content,re.S)
    if not match:continue
    meta=yaml.safe_load(match.group(1));src=meta.get('cover_url','')
    if not src or src.startswith('/'):continue
    target=DEST/(path.stem+'.webp')
    if target.exists():print('SKIP',target.name);continue
    try:
        response=s.get(src,timeout=25);response.raise_for_status()
        im=ImageOps.exif_transpose(Image.open(BytesIO(response.content))).convert('RGB')
        if meta.get('cover_mode')=='wrap':
            w,h=im.size
            # Book cover spread: front panel is on the right-hand side.
            x0=int(w*.55);x1=int(w*.985);y0=int(h*.06);y1=int(h*.95)
            im=im.crop((x0,y0,x1,y1))
        im.thumbnail((760,1100),Image.Resampling.LANCZOS)
        im.save(target,format='WEBP',quality=85,method=5)
        meta['cover_url']='/assets/img/books/'+target.name
        meta['cover_mode']='photo'
        new='---\n'+yaml.safe_dump(meta,allow_unicode=True,sort_keys=False,width=240)+'---\n'
        path.write_text(new+content[match.end():],encoding='utf-8')
        print('OK',target.name);ok+=1
    except Exception as e:
        print('ERROR',path.name,str(e),file=sys.stderr);errors+=1
print(f'Cached: {ok}, errors: {errors}. Unavailable images retain remote URL / fallback typography.')
