from pathlib import Path
import importlib.util
import json
import pytest

SPEC=importlib.util.spec_from_file_location("recover_missing",Path(__file__).resolve().parents[1]/"scripts/recover_missing.py")
m=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(m)

def test_url_path_security():
    assert m.source_path("https://swch.pl/a/index.html")==Path("swch/a/index.html")
    assert m.source_path("https://www.wswch.pl/")==Path("wswch/index.html")
    with pytest.raises(ValueError):m.source_path("https://evil.example/file.html")
    with pytest.raises(ValueError):m.source_path("https://swch.pl/a/%2e%2e/file.html")

def test_alternate_hostname():
    assert m.alternate("https://swch.pl/A%20B.pdf")=="https://www.swch.pl/A%20B.pdf"
    assert m.alternate("https://www.swch.pl/a.html")=="https://swch.pl/a.html"

def test_not_accepting_captcha_or_fake_pdf():
    assert not m.valid_bytes(b"Please wait while your request is being verified","https://swch.pl/a.html","page","text/html")
    assert not m.valid_bytes(b"<html>Cloudflare</html>","https://swch.pl/x.pdf","asset","text/html")
    assert m.valid_bytes(b"%PDF-1.4\n","https://swch.pl/x.pdf","asset","application/pdf")
    assert m.valid_bytes(b"<html><body>ABC</body></html>","https://swch.pl/a.html","page","text/html")

def test_fallback_must_be_exact(tmp_path):
    raw=tmp_path/"_source_archive/swch/abc.html";published=tmp_path/"archiwum/swch/abc.html"
    for p in (raw,published):
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_bytes(b"<html>original</html>")
    report={
      "status":"INCOMPLETE",
      "summary":{"articles_archived_only":1},
      "fallback_articles":[{"source_url":"https://swch.pl/abc.html","url":"/archiwum/swch/abc.html"}],
      "errors":[{"type":"page","url":"https://swch.pl/missing.html"},{"type":"article-text","url":"https://swch.pl/abc.html"}],
    }
    (tmp_path/"migration-report.json").write_text(json.dumps(report))
    result=m.inspect(tmp_path,tmp_path/"out",max_items=0,wayback=False)
    assert result["fallback_byte_exact"]==1
    assert result["still_unresolved"]==1
    assert not result["full_1_to_1_verified"]
    published.write_bytes(b"corrupted")
    with pytest.raises(ValueError,match="exact original"):
        m.inspect(tmp_path,tmp_path/"out2",max_items=0,wayback=False)
