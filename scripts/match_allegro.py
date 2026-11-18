#!/usr/bin/env python3
"""Znajdź tylko jednoznaczne oferty katalogu u sprzedawcy Piotr448.

Uzupełnia puste `allegro_url`, nigdy nie zmienia wcześniej zweryfikowanych.
Nie wymyśla ofert, nie kieruje do innych sprzedawców. Sprawdza offerId.
Przy blokadzie Allegro pozostawia rekord bez linku bezpośredniego.
"""
import argparse
from difflib import SequenceMatcher
import json
from pathlib import Path
import re
import time
import unicodedata
from urllib.parse import urljoin, urlsplit, parse_qs
from bs4 import BeautifulSoup
import requests
import yaml

ROOT=Path(__file__).resolve().parents[1]
PROFILE='https://allegro.pl/uzytkownik/Piotr448'
HEADERS={'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36', 'Accept-Language':'pl-PL,pl;q=0.9'}

def normal(s):
    s=unicodedata.normalize('NFKD',str(s or '').lower().replace('ł','l'))
    s=''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'\s+',' ',re.sub(r'[^a-z0-9]+',' ',s)).strip()

def candidates_from_listing(html):
    soup=BeautifulSoup(html,'html.parser'); candidates={}
    for a in soup.select('a[href]'):
        href=urljoin('https://allegro.pl',a.get('href',''))
        p=urlsplit(href)
        if p.netloc not in ('allegro.pl','www.allegro.pl') or '/produkt/' not in p.path:
            continue
        offer=parse_qs(p.query).get('offerId',[])
        if not offer or not re.fullmatch(r'\d{8,20}', offer[0]):
            continue
        title=a.get_text(' ',strip=True)
        if len(title)<8:
            parent=a.find_parent(['h2','h3'])
            if parent:title=parent.get_text(' ',strip=True)
        if len(title)<8:
            title=a.get('aria-label','') or (a.find('img').get('alt','') if a.find('img') else '')
        if len(title)>8:
            key=(p.path,offer[0]);candidates[key]={'title':title,'url':href}
    return list(candidates.values())

def similarity(book, candidate):
    title=normal(book.get('title')); author=normal(book.get('author')); listed=normal(candidate['title'])
    if len(title)<9 or not listed:return 0
    # Book title must actually appear in offer; avoid false matches between editions.
    title_score=1 if title in listed else SequenceMatcher(None,title,listed).ratio()
    if title_score < .83:return 0
    words=set(author.split())-{'a','w','j','i','t','e','john','andrew'}
    if words and not (words & set(listed.split())):
        # Short descriptions sometimes omit author; no automatic mapping then.
        return 0
    # Extra caution for versions/sizes of Bible editions.
    if 'przeklad torunski' in title:
        for format in ('a4','b5'):
            if format in title and format not in listed:return 0
    return title_score

def read_frontmatter(path):
    raw=path.read_text(encoding='utf-8')
    match=re.match(r'\A---\n(.*?)\n---\n',raw,re.S)
    if not match:return None
    return yaml.safe_load(match.group(1)),raw,match

def run(max_pages,delay):
    books=[]
    for path in sorted((ROOT/'_ksiazki').glob('*.md')):
        r=read_frontmatter(path)
        if r and not r[0].get('allegro_url'):
            books.append((path,*r))
    session=requests.Session();session.headers.update(HEADERS)
    offers={};errors=[]
    for page in range(1,max_pages+1):
        try:
            resp=session.get(PROFILE,params={'p':page},timeout=30)
            resp.raise_for_status()
            found=candidates_from_listing(resp.text)
            if not found:
                errors.append('Strona %d bez ofert: ochrona Allegro albo zmiana HTML' % page)
                if page >= 2:break
            for cand in found: offers[cand['url']]=cand
        except Exception as e:
            errors.append(f'Strona {page}: {e}')
            if page>=2:break
        print(f'Konta Allegro: strona {page}; ofert w bazie {len(offers)}',flush=True)
        time.sleep(delay)
    matches=[]
    for path,meta,raw,match in books:
        scores=sorted([(similarity(meta,c),c) for c in offers.values()],key=lambda x:x[0],reverse=True)
        if not scores or scores[0][0]<.94:continue
        best=scores[0]
        if len(scores)>1 and scores[1][0]>=best[0]-.04:continue
        url=best[1]['url']
        # `offerId` is seller-offer-specific. Check selected product page for seller.
        try:
            response=session.get(url,timeout=30)
            response.raise_for_status()
            text=BeautifulSoup(response.text,'html.parser').get_text(' ',strip=True)
            if 'Piotr448' not in text:continue
            meta['allegro_url']=url
            og=BeautifulSoup(response.text,'html.parser').find('meta',attrs={'property':'og:image'})
            if og and not meta.get('cover_url') and og.get('content','').startswith('https://a.allegroimg.com/'):
                meta['cover_url']=og['content'];meta['cover_mode']='photo'
            updated='---\n'+yaml.safe_dump(meta,allow_unicode=True,sort_keys=False,width=240)+'---\n'+raw[match.end():]
            path.write_text(updated,encoding='utf-8')
            matches.append({'book':path.name,'url':url,'offer_title':best[1]['title']})
        except Exception as e:
            errors.append(f'Weryfikacja {path.name}: {e}')
        time.sleep(delay)
    report={'seller':PROFILE,'new_matches':matches,'offers_scanned':len(offers),'unmatched_books':len(books)-len(matches),'warnings':errors}
    (ROOT/'scripts'/'allegro-match-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Oferty sprawdzone:',len(offers),'dopasowane:',len(matches),'pozostałe:',len(books)-len(matches))

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--pages',type=int,default=24)
    parser.add_argument('--delay',type=float,default=.7)
    args=parser.parse_args()
    run(args.pages,args.delay)
