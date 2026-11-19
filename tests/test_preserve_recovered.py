from pathlib import Path
import importlib.util
import json
import hashlib
import sys
import pytest

SCRIPTS=Path(__file__).resolve().parents[1]/"scripts"
sys.path.insert(0,str(SCRIPTS))
spec=importlib.util.spec_from_file_location("preserve_recovered",SCRIPTS/"preserve_recovered.py")
p=importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)

def test_persist_only_actual_html_and_reject_quarantined_archive(tmp_path):
    inbox=tmp_path/"input"
    paths=[
      ("https://swch.pl/biografie/example.html",b"<html>Verified historic text</html>"),
      ("https://swch.pl/biblia/index.html",b"<html><title>Administrative Quarantine</title>Blocked because of admin action</html>")
    ]
    report={"old_status":"INCOMPLETE","source_missing":109,"fallback_byte_exact":50,"results":[]}
    for url,data in paths:
        filename="candidates/swch/"+("biografie/example.html" if "biografie" in url else "biblia/index.html")
        file=inbox/filename
        file.parent.mkdir(parents=True,exist_ok=True)
        file.write_bytes(data)
        report["results"].append({"url":url,"status":"candidate","method":"wayback",
             "retrieved_url":"https://web.archive.org/web/20080101000000id_/https://swch.pl/example",
             "timestamp":"20080101000000","file":filename,"type":"page",
             "content_type":"text/html","sha256":hashlib.sha256(data).hexdigest(),"bytes":len(data)})
    (inbox/"recovery-report.json").write_text(json.dumps(report))
    root=tmp_path/"repo"
    result=p.preserve(root,[inbox])
    assert result["historical_candidates"]==1
    assert (root/"_historical_sources/candidates/swch/biografie/example.html").read_bytes()==paths[0][1]
    assert not (root/"_historical_sources/candidates/swch/biblia/index.html").exists()
    assert result["remaining_without_candidate"]==108
