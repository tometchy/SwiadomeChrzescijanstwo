from pathlib import Path
import importlib.util, sys, types, hashlib
from bs4 import BeautifulSoup
import pytest

SPEC=importlib.util.spec_from_file_location('migrate_all',Path(__file__).resolve().parents[1]/'scripts/migrate_all.py')
m=importlib.util.module_from_spec(SPEC);sys.modules[SPEC.name]=m;SPEC.loader.exec_module(m)

def test_links():
    assert m.normalize_url('http://www.swch.pl/autorzy/tozer/index.html?utm=x#y')==('swch','https://swch.pl/autorzy/tozer/index.html')
    assert m.normalize_url('http://wswch.pl/')==('wswch','https://www.wswch.pl/index.html')
    assert m.normalize_url('javascript:alert(1)','https://swch.pl/') is None

def test_full_text_lossless_across_tables_paragraphs_notes_unicode():
    html='<html><body><table><tr><td>Zażółć</td><td>gęślą łoś 🐝</td></tr></table><p>A  B  <strong>„C”</strong> &amp; D</p><div>Przypis: [a] <i>Tekst</i></div><form><label>Nazwisko:</label></form><script>alert(1)</script></body></html>'
    raw=BeautifulSoup(html,'html.parser')
    body,checksum,count=m.safe_body_html(raw)
    assert 'Zażółć' in body and 'Przypis:' in body and 'Nazwisko:' in body
    assert 'alert(1)' not in body
    original=m.exact_text(raw.body)
    assert m.exact_text(BeautifulSoup(body,'html.parser')) == original
    assert checksum==hashlib.sha256(original.encode('utf-8')).hexdigest()
    assert count==len(original)


def test_full_catalog_parser_41_39():
    html='<html><body><table>'
    for i in range(41,0,-1):html+=f'<tr><td>{i}</td><td>Autor {i}</td><td>Tytuł {i}</td><td>Wydanie</td><td>30 zł</td><td></td></tr>'
    for i in range(39,0,-1):html+=f'<tr><td>{i}</td><td>Autor {i}</td><td>Tytuł {i}</td><td></td></tr>'
    html+='</table></body></html>'
    out=m.parse_publisher_catalog(BeautifulSoup(html,'html.parser'))
    assert len(out['books'])==41 and len(out['brochures'])==39
    assert out['books'][0]['title']=='Tytuł 41'


def test_catalog_incomplete_fails_closed():
    with pytest.raises(ValueError,match='katalogu 41'):
        m.parse_publisher_catalog(BeautifulSoup('<html><body><table><tr><td>1</td><td>X</td><td>Y</td></tr></table></body></html>','html.parser'))


def test_offline_missing_fails(tmp_path,monkeypatch):
    monkeypatch.setattr(m,'ROOT',tmp_path)
    args=types.SimpleNamespace(delay=0,offline_dir=str(tmp_path/'missing'),max_asset_mb=1,max_total_mb=1,max_pages=1,max_assets=0,overwrite=False,fail_on_errors=True)
    with pytest.raises(RuntimeError,match='Nie pobrano żadnej strony'):
        m.mirror(args)


def test_index_never_guess_as_article():
    page=BeautifulSoup('<html><body><p>'+'ABC '*100+'</p><ul>'+''.join('<li><a href="x.html">Ważne pozycje</a></li>' for _ in range(100))+'</ul></body></html>','html.parser')
    assert not m.is_article('https://swch.pl/autorzy/index.html',page)


def test_imported_article_links_work_under_github_pages_project_prefix():
    original_url='https://swch.pl/autorzy/a/tekst.html'
    related_url='https://swch.pl/autorzy/a/drugi.html'
    original=BeautifulSoup('<html><body><p><a href="drugi.html">Wierny tekst</a></p><img src="/grafika/logo.png"></body></html>','html.parser')
    related=BeautifulSoup('<html><body><article>'+('Tekst '*50)+'</article></body></html>','html.parser')
    image_url='https://swch.pl/grafika/logo.png'
    body,digest,chars=m.safe_body_html(original, original_url, {original_url:original,related_url:related}, {image_url:'/assets/legacy/swch/grafika/logo.png'})
    assert 'href="../../czytelnia/' in body
    assert 'src="../../assets/legacy/swch/grafika/logo.png"' in body
    assert m.exact_text(BeautifulSoup(body,'html.parser')) == m.exact_text(original.body)
