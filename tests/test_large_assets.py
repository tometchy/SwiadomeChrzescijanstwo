"""Test preservation of original bytes for GitHub-compatible large downloads."""
import hashlib
import importlib.util
import sys
from pathlib import Path
import types
import yaml
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('legacy_migration_for_large_assets',ROOT/'scripts/migrate_all.py')
m=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=m
spec.loader.exec_module(m)
spec2=importlib.util.spec_from_file_location('rebuild_large_assets',ROOT/'scripts/rebuild_large_assets.py')
r=importlib.util.module_from_spec(spec2)
sys.modules[spec2.name]=r
spec2.loader.exec_module(r)

def test_binary_chunks_roundtrip(tmp_path, monkeypatch):
    # Simulate an oversized TNP PDF without requiring a 126 MB fixture.
    monkeypatch.setattr(m,'ROOT',tmp_path/'site')
    monkeypatch.setattr(m,'LARGE_LIMIT',10)
    monkeypatch.setattr(m,'CHUNK_SIZE',8)
    monkeypatch.setattr(m,'SEEDS',['https://swch.pl/'])
    source=tmp_path/'old'/'swch'
    source.mkdir(parents=True)
    (source/'index.html').write_text('<html><a href="biblia.pdf">PDF</a></html>')
    data=b'%PDF-1.7\n' + bytes(range(100)) + b'%%EOF'
    (source/'biblia.pdf').write_bytes(data)
    site=tmp_path/'site'
    (site/'_data').mkdir(parents=True)
    args=types.SimpleNamespace(delay=0,offline_dir=str(tmp_path/'old'),max_asset_mb=2,max_total_mb=2,max_pages=5,max_assets=5,overwrite=False,fail_on_errors=False)
    # Archive is generated, but strict publication must fail without full original 41+39 catalog.
    with pytest.raises(RuntimeError, match='Odmowa oznaczenia migracji 1:1'):
        m.mirror(args)
    manifest=yaml.safe_load((site/'_data/large_assets.yml').read_text())
    assert len(manifest)==1
    assert len(manifest[0]['parts'])>1
    assert all((site/p).stat().st_size<=8 for p in manifest[0]['parts'])
    assert not (site/'assets/legacy/swch/biblia.pdf').exists()
    output=site/'_site'
    assert r.rebuild(site,output)==1
    assert (output/'assets/legacy/swch/biblia.pdf').read_bytes()==data
    assert manifest[0]['sha256']==hashlib.sha256(data).hexdigest()
