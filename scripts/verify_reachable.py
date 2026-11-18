#!/usr/bin/env python3
"""Audit the *captured* live source without falsely claiming complete migration.

A failed original URL (HTTP 404) was not downloaded and stays unresolved.
An article that could not be reserialized exactly must have its raw-byte HTML
mirror. Any fetched source bytes, catalog, or actual Jekyll article mismatch
makes this command fail. Only intended for the temporary GitHub Pages preview;
strict_audit.py --require-import remains the full 1:1 release gate.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> tuple[str, int]:
    h, size = hashlib.sha256(), 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            size += len(chunk)
            h.update(chunk)
    return h.hexdigest(), size


def inside(root: Path, path: str) -> Path:
    clean = PurePosixPath(path.lstrip("/"))
    if clean.is_absolute() or ".." in clean.parts or not clean.parts:
        raise ValueError(f"Unsafe target path: {path}")
    return root.joinpath(*clean.parts)


def source_path(root: Path, url: str) -> Path:
    parsed = urlsplit(url)
    if parsed.hostname not in ("swch.pl", "www.swch.pl", "wswch.pl", "www.wswch.pl"):
        raise ValueError(f"Unexpected source domain: {url}")
    alias = "wswch" if "wswch.pl" in parsed.hostname else "swch"
    rel = unquote(parsed.path).lstrip("/") or "index.html"
    if rel.endswith("/"):
        rel += "index.html"
    return inside(root / alias, rel)


def audit(root: Path) -> tuple[list[str], dict]:
    errors = []
    report_path = root / "migration-report.json"
    if not report_path.is_file():
        return ["Brak raportu migracji (nie wolno publikować niezaimportowanej strony)"], {}
    report = json.loads(report_path.read_text(encoding="utf-8"))
    summary = report.get("summary", {})
    state = report.get("status")
    if state not in ("VERIFIED", "INCOMPLETE"):
        errors.append(f"Nieznany stan importu: {state!r}")
    if summary.get("books_verified") != 41 or summary.get("brochures_verified") != 39:
        errors.append("Katalog książek/broszur niezweryfikowany z wydawcą")
    if summary.get("source_html_pages", 0) < 594:
        errors.append("Zniknęły pobrane strony źródłowe z pierwszego pełnego przebiegu")
    if summary.get("assets_downloaded", 0) < 112:
        errors.append("Zniknęły pobrane zasoby ze źródłowego archiwum")

    raw_pages = report.get("archived_html_pages", [])
    if len(raw_pages) != summary.get("source_html_pages"):
        errors.append("Manifest HTML nie odpowiada liczbie pobranych stron")
    if len({x.get("url") for x in raw_pages}) != len(raw_pages):
        errors.append("Powtórzone adresy w manifeście HTML")
    for row in raw_pages:
        url = row["url"]
        try:
            source = source_path(root / "_source_archive", url)
            mirror = inside(root, row["path"])
            for p in (source, mirror):
                if not p.is_file():
                    raise ValueError(f"Brak pliku: {p.relative_to(root)}")
                if digest(p)[0] != row["sha256"]:
                    raise ValueError(f"SHA256 inny niż pobrany oryginał: {p.relative_to(root)}")
        except (KeyError, ValueError, OSError) as exc:
            errors.append(f"Archiwum {url}: {exc}")

    large_entries = yaml.safe_load((root / "_data" / "large_assets.yml").read_text(encoding="utf-8")) or []
    large_by_target = {x["target"]: x for x in large_entries}
    assets = report.get("assets", {})
    if len(assets) != summary.get("assets_downloaded"):
        errors.append("Manifest zasobów nie odpowiada liczbie pobranych plików")
    for url, target in assets.items():
        try:
            path = inside(root, target)
            original_mirror = source_path(root / "archiwum", url)
            if path.is_file():
                if not original_mirror.is_file() or digest(path)[0] != digest(original_mirror)[0]:
                    raise ValueError("Kopia pobranego pliku różni się od archiwalnej kopii oryginału")
            else:
                entry = large_by_target.get(target)
                if entry is None:
                    raise ValueError("Brak zasobu i manifestu fragmentów dużego pliku")
                h, size = hashlib.sha256(), 0
                for fragment in entry["parts"]:
                    fragment_path = inside(root, fragment)
                    if not fragment_path.is_file():
                        raise ValueError(f"Brak fragmentu {fragment}")
                    with fragment_path.open("rb") as stream:
                        for part in iter(lambda: stream.read(1024 * 1024), b""):
                            h.update(part)
                            size += len(part)
                if size != entry["size"] or h.hexdigest() != entry["sha256"]:
                    raise ValueError("Złożony zasób nie zgadza się z SHA256 i rozmiarem")
        except (KeyError, ValueError, OSError) as exc:
            errors.append(f"Zasób {url}: {exc}")

    articles = report.get("articles", [])
    fallback = report.get("fallback_articles", [])
    if len(articles) != summary.get("articles_written"):
        errors.append("Liczba artykułów nie zgadza się z raportem")
    if len(articles) + len(fallback) != summary.get("articles_discovered"):
        errors.append("Niekompletna lista artykułów i kopii zapasowych")
    if len(list((root / "_artykuly").glob("*.md"))) != len(articles):
        errors.append("Niezgodna liczba faktycznych plików Markdown")
    for row in articles:
        try:
            path = inside(root, row["path"])
            data = yaml.safe_load(path.read_text(encoding="utf-8").split("---", 2)[1])
            if not data.get("source_verified") or data.get("source_text_sha256") != row["sha256"]:
                raise ValueError("Artykuł niezweryfikowany lub jego suma tekstowa uległa zmianie")
            if not source_path(root / "_source_archive", row["source_url"]).is_file():
                raise ValueError("Brak źródłowego HTML artykułu")
        except (KeyError, ValueError, OSError, IndexError) as exc:
            errors.append(f"Artykuł {row.get('source_url')}: {exc}")

    fallback_urls = {x.get("source_url") for x in fallback}
    if len(fallback_urls) != len(fallback):
        errors.append("Powtórzone artykuły używające wiernego oryginału HTML")
    for row in fallback:
        try:
            raw = source_path(root / "_source_archive", row["source_url"])
            mirror = inside(root, row["url"])
            if not raw.is_file() or not mirror.is_file() or digest(raw)[0] != digest(mirror)[0]:
                raise ValueError("Brak wiernej kopii HTML w miejsce nieudanej konwersji")
        except (KeyError, ValueError, OSError) as exc:
            errors.append(f"Artykuł fallback {row.get('source_url')}: {exc}")

    recorded_errors = report.get("errors", [])
    if len(recorded_errors) != summary.get("errors"):
        errors.append("Raport błędów źródłowych ma niespójną liczbę pozycji")
    kinds = Counter(row.get("type") for row in recorded_errors)
    if dict(kinds) != summary.get("error_types"):
        errors.append("Liczby błędów poszczególnych typów nie zgadzają się")
    fallback_failed = set()
    for row in recorded_errors:
        kind = row.get("type")
        if kind in ("page", "asset"):
            if not str(row.get("error", "")).startswith("404 Client Error: Not Found"):
                errors.append(f"Błąd źródłowy inny niż 404: {row.get('url')}")
        elif kind == "article-text":
            fallback_failed.add(row.get("url"))
        else:
            errors.append(f"Nieobsłużony błąd źródłowy: {kind} — {row.get('url')}")
    if fallback_failed != fallback_urls:
        errors.append("Nie wszystkie nieudane transformacje artykułów mają oryginalny HTML")
    if state == "VERIFIED" and recorded_errors:
        errors.append("Status VERIFIED nie może zawierać brakujących źródeł")
    return errors, {
        "status": "CAPTURED_PREVIEW" if not errors else "INVALID",
        "full_1_to_1_verified": state == "VERIFIED" and not recorded_errors and not errors,
        "html_exact_copies": len(raw_pages),
        "articles": len(articles),
        "archived_only_articles": len(fallback),
        "downloaded_assets": len(assets),
        "upstream_404": kinds["page"] + kinds["asset"],
        "transform_fallbacks": kinds["article-text"],
        "note": "To podgląd zachowanych źródeł, NIE deklaracja kompletności serwisów.",
    }


if __name__ == "__main__":
    issues, stats = audit(ROOT)
    print(json.dumps({"passed": not issues, "errors": issues[:100], "summary": stats}, ensure_ascii=False, indent=2))
    if not issues:
        print("UWAGA: niewidoczne i niedostępne źródłowe linki nie zostały magicznie odzyskane.")
    sys.exit(1 if issues else 0)
