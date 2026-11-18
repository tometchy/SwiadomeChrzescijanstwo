# Wdrożenie — GitHub Pages (bez własnej domeny)

Repozytorium: https://github.com/tometchy/SwiadomeChrzescijanstwo
Przewidywany adres: https://tometchy.github.io/SwiadomeChrzescijanstwo/

## Konfiguracja konta

1. W repozytorium w `Settings → General` sprawdź `Visibility`. Repozytorium było `private` 18.11.2026. GitHub Pages na planie GitHub Free wymaga publicznego repozytorium. Jeśli masz GitHub Pro, możesz zachować prywatne; publikowany serwis i tak jest publiczny. Nie zmieniono tej opcji automatycznie.
2. Otwórz `Settings → Pages → Build and deployment → Source → GitHub Actions`. Nie wybieraj publikowania z `/docs` ani `gh-pages`.
3. Pole `Custom domain` musi pozostać **puste**. Nie tworzymy `CNAME`.
4. Jeżeli workflow migracji nie może wysłać plików, sprawdź `Settings → Actions → General → Workflow permissions → Read and write permissions` i ograniczenia gałęzi `master`. Workflow deklaruje `contents: write`.
5. Wejdź do `Actions`. Początkowy proces `Bootstrap Jekyll source bundle` importuje pliki do `master`, a następnie `Jednorazowa migracja treści swch.pl i wswch.pl` pobiera archiwum.
6. Archiwum dostępnych stron jest już zapisane w `master`. Raport `migration-report.json` zawiera listę HTTP 404 i 50 artykułów zachowanych wyłącznie jako oryginalne kopie HTML. Przy kolejnych pushach nie pobieramy archiwum od nowa.
7. `Publish Jekyll to GitHub Pages` opublikuje **tylko podgląd** po pozytywnym sprawdzeniu SHA-256 i kompletności wszystkich naprawdę pobranych plików. Sprawdź adres w `Settings → Pages`. Nigdy nie oznaczaj tego podglądu jako pełnego audytu 1:1.

## Pipeline'y

- `.github/workflows/ci.yml` — Python unit tests, składnia, walidacja 41/39, suchy build Jekylla bez udawania pełnej migracji.
- `.github/workflows/migrate-content.yml` — jednorazowy import źródłowych HTML i plików wraz z rygorystycznym audytem; raport błędów jako artefakt.
- `.github/workflows/pages.yml` — automatyczna publikacja PODGLĄDU po kontroli kopii pobranych plików (`scripts/verify_reachable.py`). Pełny audyt 1:1 jest osobnym, surowszym wymogiem przed zmianą domeny.

## Dalsza zmiana domeny

Po zakupie: ustaw `url: https://swiadomechrzescijanstwo.pl`, `baseurl: ''` w `_config.yml`, dodaj domenę w `Settings → Pages`, skonfiguruj DNS i dopiero wtedy przełącz witrynę. Nie trzeba zmieniać źródeł książek ani artykułów.

## Ograniczenia audytu

Aktualne dane książek i broszur zostały porównane z zapisanym snapshotem katalogu, a nie z pełnym, fizycznie pobranym backupem dawnych serwerów. Crawl nie gwarantuje, że znalazł osierocone pliki. Nawet pomyślne zakończenie pipeline'u wymaga ręcznego porównania z backupem przy deklarowaniu 100% kompletności.

## Dawna wersja i uprawnienia

Dawny projekt graficzny w szablonie Kaira zachowano w gałęzi `backup/legacy-kaira-2025`. Wdrożony szablon nie zawiera demonstracyjnych tekstów e-commerce.

Pierwsza próba instalacji zgłosiła brak uprawnienia `workflows` dla tokenu GitHub Actions; poprawiono to przez oddzielne zapisanie trzech workflow z uprawnionego połączenia GitHub, przed automatycznym odtworzeniem pozostałych plików. Ponowny bootstrap zakończył się sukcesem.

Podgląd GitHub Pages używa weryfikacji rzeczywiście pobranych źródeł i nie uznaje ich za pełny wynik 1:1. Pełna kontrola `scripts/strict_audit.py --require-import` pozostaje wymagana przed migracją domeny i zamknięciem audytu.

## Checkpoint przy niepełnym imporcie

Crawl GitHub Actions z 18.11.2026 pobrał 594 oryginalne strony HTML, zmapował 487 artykułów do Jekylla oraz pobrał 112 plików. Wykazał 159 błędów (109 odpowiedzi 404 i 50 różnic wyłącznie w białych znakach podczas przenoszenia artykułów). Pełna zgodność całej witryny nie została potwierdzona.

Workflow zapisuje **niekompletny** import, ale kończy się sukcesem podglądowym wyłącznie po walidacji pobranych plików. Artykuły nieprzekształcone bezstratnie są dostępne jako linki do oryginalnych HTML. Błędy HTTP 404 pozostają jawne w raporcie i w zgłoszeniu GitHub Issue #1.

CI zapisuje plik `jekyll-preview` dostępny w zakładce Actions do pobrania i obejrzenia lokalnie. Nie jest to wdrożenie GitHub Pages.

Aby uruchomić domyślny adres `https://tometchy.github.io/SwiadomeChrzescijanstwo/` na GitHub Free, ustaw repozytorium na **Public** (Settings → General → Danger Zone → Change repository visibility), a następnie Settings → Pages → Source → GitHub Actions. Na GitHub Pro można pozostawić prywatne repozytorium. Nie twórz pliku CNAME ani nie ustawiaj własnej domeny.
