# Śpiewnik zborowy — Toruń (449 pieśni)

**Jedyne źródło tekstów** znajduje się w 449 plikach `_piesni/001.md`–`_piesni/449.md`.
Każdy plik ma numer i tytuł w front matter YAML, a niżej zwrotki w Markdownzie. Zachowano numerację i treść dostarczonego EPUB-a; po imporcie nie jest on wymagany w repozytorium.

### Aktualizowanie pieśni

1. Edytuj treść albo tytuł w odpowiednim `_piesni/NNN.md`.
2. Zatwierdź PR i scal go do `master`.
3. Workflow publikacji buduje Jekylla (strony `/spiewnik/piesni/NNN/`), a następnie uruchamia `scripts/build_hymnal_epub.py`. Generator czyta **HTML wyrenderowany przez Jekylla** i zapisuje `_site/spiewnik/Spiewnik-Torun.epub` w tej samej paczce GitHub Pages.

Nie edytuj EPUB-a osobno, bo jest artefaktem builda. Nie trzeba zapisywać wygenerowanego pliku w Git. Zarówno strona WWW, jak i czytnik EPUB wykorzystują tę samą treść. Budowanie EPUB-a lokalnie: `bundle exec jekyll build && python3 scripts/build_hymnal_epub.py --site _site` (wymaga `beautifulsoup4`).
