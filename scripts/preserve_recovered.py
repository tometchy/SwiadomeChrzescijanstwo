#!/usr/bin/env python3
"""Persist inspected Wayback candidates as a non-published historical collection.

This is not a substitute for source files from the original 2026 server.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
from recover_missing import valid_bytes, source_path

def preserve(repo:Path, directories:list[Path]):
    approved={}
    for directory in directories:
        if not (directory/"recovery-report.json").is_file():
            raise ValueError("Missing recovery-report.json in "+str(directory))
        report=json.loads((directory/"recovery-report.json").read_text(encoding="utf-8"))
        if report.get("old_status")!="INCOMPLETE" or report.get("source_missing")!=109:
            raise ValueError("Unexpected source manifest version")
        if report.get("fallback_byte_exact")!=50:
            raise ValueError("Fallback integrity not verified")
        for entry in report["results"]:
            if entry["status"]!="candidate":
                continue
            original=entry["url"]
            if entry.get("method")!="wayback" or not entry.get("timestamp"):
                raise ValueError("Only provenance-stamped Wayback bytes may be preserved")
            if not entry.get("retrieved_url","").startswith("https://web.archive.org/web/"):
                raise ValueError("Unexpected archive host")
            rel=source_path(original)
            path=(directory/entry["file"]).resolve()
            if not path.is_relative_to(directory.resolve()) or not path.is_file():
                raise ValueError("Invalid candidate path")
            raw=path.read_bytes()
            digest=hashlib.sha256(raw).hexdigest()
            if digest!=entry["sha256"] or len(raw)!=entry["bytes"]:
                raise ValueError("Candidate bytes do not match SHA-256 or size")
            if not valid_bytes(raw,original,entry["type"],entry.get("content_type","")):
                continue  # Quarantine blocker pages are not source documents.
            if original not in approved:
                approved[original]=(entry,raw,rel)
    base=repo/"_historical_sources"
    base.mkdir(parents=True,exist_ok=True)
    ledger=[]
    for original,(entry,raw,rel) in sorted(approved.items()):
        target=base/"candidates"/rel
        target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists() and target.read_bytes()!=raw:
            raise ValueError("Historical source changed; refusing to overwrite "+original)
        target.write_bytes(raw)
        ledger.append({
            "source_url":original,
            "historical_archive_url":entry["retrieved_url"],
            "wayback_timestamp":entry["timestamp"],
            "sha256":entry["sha256"],
            "bytes":entry["bytes"],
            "path":str(target.relative_to(repo)).replace("\\","/"),
        })
    summary={
      "original_missing":109,
      "historical_candidates":len(ledger),
      "remaining_without_candidate":109-len(ledger),
      "byte_exact_fallback_articles":50,
      "full_migration_verified":False,
      "warning":"Wayback snapshots are not validated as originals from 18 Nov 2026",
      "items":ledger,
    }
    (base/"manifest.json").write_text(
        json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in summary.items() if k!="items"},ensure_ascii=False,indent=2))
    return summary

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument("folders",nargs="+",type=Path)
    args=p.parse_args()
    preserve(args.root,args.folders)
