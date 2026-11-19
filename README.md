# Świadome Chrześcijaństwo — Jekyll, tryb zgodności treści ze źródłem

**Status: PODGLĄD Z ZACHOWANYCH ŹRÓDEŁ; PEŁNA WERYFIKACJA 1:1 NIEZAKOŃCZONA.** GitHub Actions zapisało do repozytorium 594 oryginalne strony HTML, 487 bezstratnie przekonwertowanych artykułów oraz 112 plików. Oryginalne HTML kolejnych 50 artykułów pozostają dostępne bez konwersji. 109 adresów ze starego serwisu odpowiada HTTP 404. Nie zmieniaj jeszcze DNS.

## Co jest w repozytorium

- 41 kart książek i 39 kart broszur. Tytuły, autorzy, wydania, historyczne ceny i statusy zostały przepisane z publicznego katalogu `https://www.wswch.pl/` z 17.11.2026 bez poprawiania błędów oryginału. Po imporcie katalog został zweryfikowany względem rzeczywiście pobranej tabeli HTML (`source_text_verified: true`).
- 17 zachowanych linków do ofert Allegro (dystrybutor `Piotr448` potwierdzony przez właściciela). Linki są technicznymi odnośnikami i nie zmieniają treści oryginalnych katalogów.
- Usunięte dwa napisane przez asystenta artykuły oraz wszystkie własne opisy książek, marketingowe slogany, fikcyjne streszczenia i dopisane interpretacje.
- Teksty wstawione na stronę główną i podstrony informacyjne pochodzą z oryginalnej zawartości obu witryn; przed produkcją wymagają porównania z bajtami źródłowymi.
- `scripts/migrate_all.py` — importuje wszystkie odkryte przez linki oryginalne strony HTML obu witryn, zasoby, pliki PDF/EPUB, tabele 41+39. Archiwalne HTML publikuje jako **kopie bajt w bajt** w `/archiwum/swch/...` i `/archiwum/wswch/...`; oryginalne bajty pozostają w `_source_archive/`.
- Artykuły są dodatkowo zapisywane jako dokumenty Jekyll `_artykuly/*.md`, z oryginalnym HTML wewnątrz, bez parafrazowania i ucinań. Porównanie Unicode i SHA-256 jest obowiązkowe. Jedynie linki techniczne mogą być aktualizowane.
- `scripts/strict_audit.py` — blokuje publikację bez raportu o kompletnym pobraniu znanych adresów, kompletnym katalogu i zgodności treści.

## Jak uruchomić

1. Repozytorium docelowe: `tometchy/SwiadomeChrzescijanstwo`, gałąź `master`. Poprzednią ręczną inspirację zachowano w `backup/legacy-kaira-2025`.
2. Włącz `Settings → Actions → General → Workflow permissions → Read and write permissions`, jeśli akcja nie może zapisywać importu. W `Settings → Pages` wybierz publikację przez GitHub Actions.
3. GitHub Actions zaimportowało i zapisało dostępne źródła. Zwykłe zmiany w `master` weryfikują zapisane pliki, bez ponownego ściągania kilkuset stron; ręczne uruchomienie `Jednorazowa migracja treści...` w `Actions → Run workflow` wymusza nowe pobranie źródeł.
4. Workflow `.github/workflows/pages.yml` publikuje **tymczasowy podgląd** po pozytywnym sprawdzeniu bajtów, SHA-256, artykułów i katalogu przez `scripts/verify_reachable.py` oraz `scripts/strict_audit.py`. Wykryte źródłowe HTTP 404 pozostają w raporcie. To NIE jest pozytywny pełny audyt 1:1.
5. Pełny audyt `scripts/strict_audit.py --require-import` nadal wymaga statusu `VERIFIED`, a więc bezbłędnej migracji wszystkich znalezionych URL. Nie przełączaj domeny przed ręczną kontrolą braków.

### Lokalnie na Linux Mint / Ubuntu

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-import.txt pytest
.venv/bin/python -m pytest -q tests/
.venv/bin/python scripts/strict_audit.py                # tylko weryfikacja danych dostępnych w ZIP
.venv/bin/python scripts/migrate_all.py --max-pages 6000 --max-assets 5000 --max-total-mb 1400 --delay 0.3 --overwrite --fail-on-errors
.venv/bin/python scripts/strict_audit.py --require-import
bundle install && bundle exec jekyll build
.venv/bin/python scripts/rebuild_large_assets.py --output _site
```

## Dokładny zakres wymagania 1:1

- Nie poprawiać ani jednego słowa, przecinka, literówki, wielkości liter, cytatu ani nazwy własnej.
- Żaden opis produktu nie może pochodzić z generowania AI. Jeżeli oryginalna strona nie podaje opisu, pole opisu pozostaje puste.
- Treści z artykułów zostają w oryginalnym HTML. Konwersja do własnej redakcji Markdown jest celowo wyłączona, aby nie zgubić przypisów, tabel i śródtytułów. Plik `.md` zawiera oryginalny HTML, który Jekyll obsługuje.
- Zewnętrzne zasoby podlinkowane spoza obu domen i niepodlinkowane stare pliki mogą wymagać osobnego backupu. **Automatyczny crawl nie dowodzi kompletności URL-i, które nie występują w żadnym odnośniku, ani treści generowanych dynamicznie przez JavaScript.** Nie można podawać stuprocentowej kompletności bez porównania z pełnym backupem katalogów obu oryginalnych witryn.
- Nawigacja, etykiety przycisków, filtrów i linki do Allegro stanowią nowy interfejs; nie są przedstawiane jako oryginalny materiał redakcyjny.

**Nie podmieniaj obu stron przed zatwierdzeniem raportu różnic i inwentaryzacji źródłowej.**

## GitHub Pages pod adresem tymczasowym

Zobacz `DEPLOY_GITHUB_PAGES.md`. URL projektu to `https://tometchy.github.io/SwiadomeChrzescijanstwo/`; nie konfiguruj `CNAME` ani własnego DNS. Repozytorium zostało już ustawione jako publiczne. W `Settings → Pages` wybierz źródło **GitHub Actions**.

Podgląd można opublikować z niekompletnym raportem WYŁĄCZNIE wtedy, gdy **wszystkie pobrane bajty i artykuły są sprawdzone**, a pozostałe błędy ograniczają się do oryginalnych HTTP 404 i udokumentowanych kopii HTML artykułów. Nie oznacza to, że pełna migracja 1:1 została zakończona.

### Obrazy książek, galeria i favicon

- Oryginalne zdjęcia są niezmienione w `assets/img/books/*.webp`. `scripts/generate_book_fronts.py` zapisuje przycięte do frontów pliki w `assets/img/books/fronts/` (bez sztucznego tworzenia okładek).
- Katalog i strona główna wyświetlają front. Szczegóły książki pokazują galerię: front, niezmienioną fotografię źródłową i wszystkie opcjonalne dodatkowe `gallery_images` z front matter. Strzałki, miniatury i klawisze pozwalają przełączać fotografie.
- Własne następne zdjęcia można dodać do `gallery_images` w `_ksiazki/*.md`. Każdy wskazany plik powinien rzeczywiście istnieć, najlepiej lokalnie w repozytorium. Nie należy zastępować realnych fotografii grafikami generowanymi.
- Generator działa podczas CI i publikacji Pages. `.github/workflows/generate-book-fronts.yml` może dodatkowo zapisać utworzone pliki na gałęzi. Dla zdjęć rozłożonych można zmienić współrzędne w `FRONT_CROPS`.
- Przywrócono oryginalną faviconę z `assets/legacy/swch/favicon.ico`. Linki do pobierania Przekładu Toruńskiego uwzględniają `baseurl` GitHub Pages.

### Tytuły, galeria, okładki i dane wydań

- Nie zmieniamy historycznych `title` w `_ksiazki/*.md`. `_includes/book_title.html` usuwa tylko otaczające cudzysłowy przy renderowaniu. Dodatkowe pola `display_title`, `subtitle`, `card_subtitle` pozwalają oddzielić tytuł główny od wariantu wydania.
- Zidentyfikowane wydania mają potwierdzone dane `isbn`, `publication_year`, `pages`, `binding`, `format`, `publisher` i krótkie opisy. `bibliographic_source` wskazuje źródło metadanych. Niepotwierdzone wartości nie są dopisywane.
- Oryginalne zdjęcia pozostają bez zmian. Generator przycina fronty i usuwa cienkie, jednolite pasy skanu; szablony pokazują fronty przy ich naturalnych proporcjach.
- Kliknięcie zdjęcia otwiera powiększenie. Miniatury i strzałki przełączają zdjęcia; Escape zamyka okno, strzałki na klawiaturze zmieniają zdjęcie.
- `scripts/make_favicon.py` przekształca **oryginalny** `assets/legacy/swch/favicon.ico` w szarą przezroczystą PNG (`assets/img/favicon-gray-transparent.png`), a nie pobiera białego tła z wswch.pl.

### Wyszukiwanie i metadane publikacji

- Każda z 41 książek ma co najmniej dwa tematyczne `tags` i właściwą kategorię. Przekłady Biblii mają aliasy: *Biblia*, *Pismo Święte*, *TNP*, *Przekład Toruński*, *Nowy Testament* itd.
- Katalog przeszukuje tytuł, podtytuł, opis, autora i warianty nazwiska, słowa kluczowe, tagi, ISBN, kategorię, rok, wydawcę, oprawę, format, wydanie i tekst książki. Kolejność wyrazów i polskie znaki nie wpływają na wynik.
- Tagi na karcie szczegółów prowadzą do `/ksiazki/?q=tag`. Nie ma potrzeby dublowania tytułów ani zmieniania historycznych danych archiwalnych.
- Rzeczywiste okładki bezpiecznie odnawiane są z listy konkretnych, zweryfikowanych stron produktów (`scripts/verified_cover_sources.yml`). `scripts/fetch_verified_cover_photos.py` sprawdza tytuł i wydawcę strony, pobiera wyłącznie jej zdjęcia produktu, zapisuje lokalne WebP i uzupełnia metadane tylko po udanym pobraniu. Niepowodzenie nie powoduje użycia zdjęcia nieodpowiedniego wydania. Nie rusza istniejących zdjęć.
- Obsługa wielu zdjęć jest w `gallery_images`; generator frontów działa następnie na nowych, pobranych plikach.
