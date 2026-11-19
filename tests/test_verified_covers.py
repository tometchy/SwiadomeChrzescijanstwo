from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]

def test_sources_are_specific_to_real_books():
    sources = yaml.safe_load((ROOT / "scripts/verified_cover_sources.yml").read_text())
    assert len(sources) >= 8
    names = [s["book"] for s in sources]
    assert len(names) == len(set(names))
    for source in sources:
        path = ROOT / "_ksiazki" / (source["book"] + ".md")
        assert path.is_file()
        assert source["page"].startswith("https://")
        assert source["title"]

def test_downloader_requires_verified_title_and_publisher():
    source = (ROOT / "scripts/fetch_verified_cover_photos.py").read_text()
    assert 'Product title does not match expected edition' in source
    assert 'Publisher cannot be verified' in source
    assert 'if target.exists():' in source
    assert '"cover_source_url"' in source
