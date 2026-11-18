"""A partial crawl is a recovery checkpoint, never a completed migration."""
import importlib.util,json,sys
from pathlib import Path
from types import SimpleNamespace
spec=importlib.util.spec_from_file_location('swch_partial_migration',Path(__file__).resolve().parents[1]/'scripts/migrate_all.py')
m=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=m
spec.loader.exec_module(m)
def test_incomplete_capture_stays_incomplete(tmp_path,monkeypatch):
    monkeypatch.setattr(m,'ROOT',tmp_path/'site')
    monkeypatch.setattr(m,'SEEDS',['https://swch.pl/'])
    old=tmp_path/'old'/'swch'
    old.mkdir(parents=True)
    html=b'<html><head><title>Test</title></head><body><p>Original archived text</p></body></html>'
    (old/'index.html').write_bytes(html)
    (tmp_path/'site'/'_data').mkdir(parents=True)
    args=SimpleNamespace(delay=0,offline_dir=str(tmp_path/'old'),max_asset_mb=1,max_total_mb=1,max_pages=10,max_assets=10,overwrite=True,allow_incomplete=True)
    m.mirror(args)
    report=json.loads((tmp_path/'site'/'migration-report.json').read_text())
    assert report['status']=='INCOMPLETE'
    assert report['summary']['error_types']['catalog-verification']==1
    assert (tmp_path/'site'/'_source_archive'/'swch'/'index.html').read_bytes()==html
    assert (tmp_path/'site'/'archiwum'/'swch'/'index.html').read_bytes()==html
