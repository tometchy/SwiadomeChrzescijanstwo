import pathlib, re, yaml, json
ROOT=pathlib.Path(__file__).resolve().parents[1]

def collection(folder):
    return [(p,yaml.safe_load(p.read_text(encoding='utf-8').split('---',2)[1])) for p in (ROOT/folder).glob('*.md')]

def test_original_catalog_snapshot_complete():
    src=json.loads((ROOT/'_data/catalog_web_snapshot.json').read_text())
    books=collection('_ksiazki');brochures=collection('_broszury')
    assert len(books)==41 and len(brochures)==39
    assert {v['catalog_number'] for _,v in books}==set(range(1,42))
    assert {v['catalog_number'] for _,v in brochures}==set(range(1,40))
    for files,key in ((books,'books'),(brochures,'brochures')):
        reference={x['number']:x for x in src[key]}
        for p,data in files:
            original=reference[data['catalog_number']]
            assert data['title']==original['title'],p
            assert data['author']==original['author'],p
            assert data['catalog_status']==original['status'],p
            assert data.get('historical_price','')==original.get('price',''),p
            assert data.get('edition_note','')==original.get('edition',''),p
            assert data.get('description') is None,p
            assert p.read_text(encoding='utf-8').split('---',2)[2].strip()==''

def test_no_generated_articles_or_unsourced_prose():
    assert not list((ROOT/'_artykuly').glob('*.md'))
    assert yaml.safe_load((ROOT/'_data/legacy_articles.yml').read_text())==[]
    assert not any('subtitle' in x for x in yaml.safe_load((ROOT/'_data/archive.yml').read_text()))

def test_seller_confirmed():
    data=yaml.safe_load((ROOT/'_data/site.yml').read_text())
    assert data['distributor_verified_identity'] is True
    assert data['distributor_profile']=='https://allegro.pl/uzytkownik/Piotr448'

def test_offer_urls_and_covers():
    books=collection('_ksiazki')
    offers=[d['allegro_url'] for _,d in books if d.get('allegro_url')]
    assert len(offers)==17
    assert len(set(offers))==17
    assert all(x.startswith('https://allegro.pl/') for x in offers)
