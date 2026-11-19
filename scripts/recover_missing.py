#!/usr/bin/env python3
"""Issue #1: research legacy 404 sources without declaring a false 1:1 success.

Candidate files and SHA-256 receipts are kept in quarantine, never overwritten
into the published website or the original migration manifest.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from urllib.parse import unquote, urlsplit, urlunsplit
import requests

ROOT=Path(__file__).resolve().parents[1]
HOSTS={"swch.pl","www.swch.pl","wswch.pl","www.wswch.pl"}
BAD=(b"please wait while your request is being verified", b"cf-chl-", b"just a moment...",
     b"checking your browser",b"attention required! | cloudflare")


def source_path(url):
    parts=urlsplit(url)
    if parts.hostname not in HOSTS or parts.scheme not in ("https","http"):
        raise ValueError("Untrusted source URL")
    path=unquote(parts.path).lstrip("/") or "index.html"
    if path.endswith("/"):path+="index.html"
    bits=PurePosixPath(path).parts
    if not bits or ".." in bits or "\\" in path:
        raise ValueError("Unsafe source path")
    return Path("wswch" if parts.hostname.endswith("wswch.pl") else "swch", *bits)


def alternate(url):
    p=urlsplit(url)
    if p.hostname not in HOSTS:raise ValueError("Untrusted hostname")
    host=p.hostname[4:] if p.hostname.startswith("www.") else "www."+p.hostname
    return urlunsplit(("https",host,p.path,p.query,""))


def valid_bytes(data,url,kind,mime):
    if not data or any(b in data[:16000].lower() for b in BAD):return False
    extension=Path(unquote(urlsplit(url).path)).suffix.lower()
    if kind=="page":
        if extension not in ("",".html",".htm"):return False
        first=data[:8192].lower()
        return b"<html" in first or b"<!doctype html" in first
    if extension==".pdf":return data.lstrip().startswith(b"%PDF-")
    if extension in (".jpg",".jpeg"):return data[:3]==b"\xff\xd8\xff"
    if extension==".png":return data[:8]==b"\x89PNG\r\n\x1a\n"
    if extension==".gif":return data[:6] in (b"GIF87a",b"GIF89a")
    if extension==".css":return b"{" in data and b"}" in data and b"<html" not in data[:8192].lower()
    if "html" in mime.lower():return False
    return True


def get_file(session,url,allowed,max_size=40_000_000):
    if urlsplit(url).hostname not in allowed or not url.startswith("https://"):
        raise ValueError("Untrusted file URL")
    with session.get(url,timeout=(6,13),stream=True,allow_redirects=True) as response:
        if urlsplit(response.url).hostname not in allowed:raise ValueError("Redirect outside allowed domains")
        response.raise_for_status()
        if int(response.headers.get("Content-Length") or 0)>max_size:
            raise ValueError("File exceeds size limit")
        chunks=[];length=0
        for chunk in response.iter_content(131072):
            length+=len(chunk)
            if length>max_size:raise ValueError("File exceeds size limit")
            chunks.append(chunk)
        return b"".join(chunks),response.url,response.headers.get("Content-Type","")


def historical_url(session,source):
    reply=session.get("https://archive.org/wayback/available",
        params={"url":source,"timestamp":"20261118"},timeout=(6,13))
    reply.raise_for_status()
    snapshot=(reply.json().get("archived_snapshots") or {}).get("closest") or {}
    timestamp=str(snapshot.get("timestamp",""))
    if not snapshot.get("available") or str(snapshot.get("status"))!="200":
        return None
    if not re.fullmatch(r"\d{14}",timestamp):raise ValueError("Invalid archive timestamp")
    address=snapshot["url"].replace("http://","https://",1)
    if urlsplit(address).hostname!="web.archive.org":raise ValueError("Untrusted archive host")
    address=re.sub(r"/web/(\d{14})/",r"/web/\1id_/",address,count=1)
    return address,timestamp


def verify_fallbacks(root,manifest):
    result=[]
    for row in manifest["fallback_articles"]:
        name=source_path(row["source_url"])
        a=root/"_source_archive"/name
        b=root/"archiwum"/name
        wanted="/archiwum/"+name.as_posix()
        good=(row["url"]==wanted and a.is_file() and b.is_file()
              and a.read_bytes()==b.read_bytes())
        result.append({"source_url":row["source_url"],"byte_exact":good,
                       "sha256":hashlib.sha256(a.read_bytes()).hexdigest() if good else None})
    return result


def attempt(row,output,wayback):
    url=row["url"];kind=row["type"]
    outcome={"url":url,"type":kind,"status":"unresolved","attempts":[]}
    with requests.Session() as session:
        session.headers["User-Agent"]="SwiadomeChrzescijanstwo-archival-audit/1.0"
        trials=[("alternate-www",alternate(url),None)]
        if wayback:
            try:
                old=historical_url(session,url)
                if old:trials.append(("wayback",old[0],old[1]))
                else:outcome["attempts"].append(["wayback-lookup","no snapshot"])
            except (requests.RequestException, ValueError, KeyError) as e:
                outcome["attempts"].append(["wayback-lookup",str(e)[:200]])
        for method,fetch_url,stamp in trials:
            try:
                raw,final,mime=get_file(session,fetch_url,HOSTS if method=="alternate-www" else {"web.archive.org"})
                if not valid_bytes(raw,url,kind,mime):
                    raise ValueError("Invalid file, anti-bot challenge or wrong file type")
                target=output/"candidates"/source_path(url)
                target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(raw)
                outcome.update(status="candidate",method=method,retrieved_url=final,
                               timestamp=stamp,sha256=hashlib.sha256(raw).hexdigest(),
                               bytes=len(raw),file=target.relative_to(output).as_posix(),
                               note="Historical snapshot; not proof of 2026 original" if stamp
                                    else "Alternate hostname; requires source equivalence check")
                break
            except (requests.RequestException, ValueError, KeyError, OSError) as e:
                outcome["attempts"].append([method,str(e)[:200]])
    return outcome


def inspect(root,output,max_items=109,wayback=True,workers=3):
    manifest=json.loads((root/"migration-report.json").read_text(encoding="utf-8"))
    verified=verify_fallbacks(root,manifest)
    if len(verified)!=manifest["summary"].get("articles_archived_only") or any(not x["byte_exact"] for x in verified):
        raise ValueError("One of the 50 archive fallback files is not an exact original")
    missing=[e for e in manifest["errors"] if e.get("type") in ("page","asset")]
    if len(missing)!=len({e["url"] for e in missing}):raise ValueError("Repeated missing URL")
    for item in missing:source_path(item["url"])
    output.mkdir(parents=True,exist_ok=True)
    results=[]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        tasks=[pool.submit(attempt,e,output,wayback) for e in missing[:max_items]]
        for job in as_completed(tasks):
            results.append(job.result())
    results.sort(key=lambda row:row["url"])
    counts=Counter(e["status"] for e in results)
    report={
        "created_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "old_status":manifest["status"],
        "source_missing":len(missing),
        "processed":len(results),
        "candidates":counts["candidate"],
        "still_unresolved":len(missing)-counts["candidate"],
        "fallback_byte_exact":len(verified),
        "fallback_proofs":verified,
        "full_1_to_1_verified":False,
        "reason":"Candidates are not automatically verified as exact files of the original site in 2026",
        "results":results,
    }
    (output/"recovery-report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k not in ("results","fallback_proofs")},ensure_ascii=False,indent=2))
    return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,default=ROOT)
    p.add_argument("--output",type=Path,default=Path("recovery-output"))
    p.add_argument("--max-items",type=int,default=109)
    p.add_argument("--workers",type=int,default=3)
    p.add_argument("--no-wayback",action="store_true")
    args=p.parse_args()
    if not 0<=args.max_items<=10000 or not 1<=args.workers<=5:p.error("Invalid limits")
    inspect(args.root,args.output,args.max_items,not args.no_wayback,args.workers)


if __name__=="__main__":main()
