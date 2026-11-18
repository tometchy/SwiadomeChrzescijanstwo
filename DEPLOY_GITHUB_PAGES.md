# Wdrożenie — GitHub Pages (bez własnej domeny)

Repozytorium: https://github.com/tometchy/SwiadomeChrzescijanstwo
Przewidywany adres: https://tometchy.github.io/SwiadomeChrzescijanstwo/

## Konfiguracja konta

1. W repozytorium w `Settings → General` sprawdź `Visibility`. Repozytorium było `private` 18.11.2026. GitHub Pages na planie GitHub Free wymaga publicznego repozytorium. Jeśli masz GitHub Pro, możesz zachować prywatne; publikowany serwis i tak jest publiczny. Nie zmieniono tej opcji automatycznie.
2. Otwórz `Settings → Pages → Build and deployment → Source → GitHub Actions`. Nie wybieraj publikowania z `/docs` ani `gh-pages`.
3. Pole `Custom domain` musi pozostać **puste**. Nie tworzymy `CNAME`.
4. Jeżeli workflow migracji nie może wysłać plików, sprawdź `Settings → Actions → General → Workflow permissions → Read and write permissions` i ograniczenia gałęzi `master`. Workflow deklaruje `contents: write`.
5. Wejdź do `Actions`. Początkowy proces `Bootstrap Jekyll source bundle` importuje pliki do `master`, a następnie `Jednorazowa migracja treści swch.pl i wswch.pl` pobiera archiwum.
6. Zobacz raport importu `migration-audit` oraz `migration-report.json`. Bez poprawnego raportu **publikacja jest blokowana** zgodnie z wymaganiem niezmienności treści.
7. Po udanym imporcie i audycie `Publish Jekyll to GitHub Pages` skompiluje Jekyll i opublikuje serwis. Sprawdź właściwy URL w `Settings → Pages`.

## Pipeline'y

- `.github/workflows/ci.yml` — Python unit tests, składnia, walidacja 41/39, suchy build Jekylla bez udawania pełnej migracji.
- `.github/workflows/migrate-content.yml` — jednorazowy import źródłowych HTML i plików wraz z rygorystycznym audytem; raport błędów jako artefakt.
- `.github/workflows/pages.yml` — publikacja dopiero po udanym imporcie i kontroli treści.

## Dalsza zmiana domeny

Po zakupie: ustaw `url: https://swiadomechrzescijanstwo.pl`, `baseurl: ''` w `_config.yml`, dodaj domenę w `Settings → Pages`, skonfiguruj DNS i dopiero wtedy przełącz witrynę. Nie trzeba zmieniać źródeł książek ani artykułów.

## Ograniczenia audytu

Aktualne dane książek i broszur zostały porównane z zapisanym snapshotem katalogu, a nie z pełnym, fizycznie pobranym backupem dawnych serwerów. Crawl nie gwarantuje, że znalazł osierocone pliki. Nawet pomyślne zakończenie pipeline'u wymaga ręcznego porównania z backupem przy deklarowaniu 100% kompletności.

## Dawna wersja i uprawnienia

Dawny projekt graficzny w szablonie Kaira zachowano w gałęzi `backup/legacy-kaira-2025`. Wdrożony szablon nie zawiera demonstracyjnych tekstów e-commerce.

Pierwsza próba instalacji zgłosiła brak uprawnienia `workflows` dla tokenu GitHub Actions; poprawiono to przez oddzielne zapisanie trzech workflow z uprawnionego połączenia GitHub, przed automatycznym odtworzeniem pozostałych plików. Ponowny bootstrap zakończył się sukcesem.

`GitHub Pages` nie opublikuje serwisu, dopóki `migration-report.json` nie potwierdzi zaimportowania treści i nie przejdzie `scripts/strict_audit.py --require-import`. To celowe zabezpieczenie przed częściową migracją.
