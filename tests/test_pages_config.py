from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[1]

def test_temporary_pages_url():
    cfg=yaml.safe_load((ROOT/'_config.yml').read_text())
    assert cfg['url']=='https://tometchy.github.io'
    assert cfg['baseurl']=='/SwiadomeChrzescijanstwo'
    assert not (ROOT/'CNAME').exists()

def test_deploy_keeps_integrity_gate():
    pages=(ROOT/'.github/workflows/pages.yml').read_text()
    assert 'strict_audit.py --require-import' in pages
    assert 'actions/deploy-pages@v4' in pages
