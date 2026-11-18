# Świadome Chrześcijaństwo — Jekyll, tryb zgodności treści ze źródłem

**Status: NIEZAKOŃCZONA WERYFIKACJA 1:1.** Nie zmieniaj jeszcze DNS. W środowisku przygotowującym ZIP nie udało się pobrać kompletnych oryginalnych stron internetowych.

## Co jest w ZIP

- 41 kart książek i 39 kart broszur. Tytuły, autorzy, wydania, historyczne ceny i statusy zostały przepisane z publicznego katalogu `https://www.wswch.pl/` z 17.11.2026 bez poprawiania błędów oryginału. W `source_text_verified` jest **false** aż do pobrania i zweryfikowania oryginalnego HTML.
- 17 zachowanych linków do ofert Allegro (dystrybutor `Piotr448` potwierdzony przez właściciela). Linki są technicznymi odnośnikami i nie zmieniają treści oryginalnych katalogów.
- Usunięte dwa napisane przez asystenta artykuły oraz wszystkie własne opisy książek, marketingowe slogany, fikcyjne streszczenia i dopisane interpretacje.
- Teksty wstawione na stronę główną i podstrony informacyjne pochodzą z oryginalnej zawartości obu witryn; przed produkcją wymagają porównania z bajtami źródłowymi.
- `scripts/migrate_all.py` — importuje wszystkie odkryte przez linki oryginalne strony HTML obu witryn, zasoby, pliki PDF/EPUB, tabele 41+39. Archiwalne HTML publikuje jako **kopie bajt w bajt** w `/archiwum/swch/...` i `/archiwum/wswch/...`; oryginalne bajty pozostają w `_source_archive/`.
- Artykuły są dodatkowo zapisywane jako dokumenty Jekyll `_artykuly/*.md`, z oryginalnym HTML wewnątrz, bez parafrazowania i ucinań. Porównanie Unicode i SHA-256 jest obowiązkowe. Jedynie linki techniczne mogą być aktualizowane.
- `scripts/strict_audit.py` — blokuje publikację bez raportu o kompletnym pobraniu znanych adresów, kompletnym katalogu i zgodności treści.

## Jak uruchomić

1. Repozytorium docelowe: `tometchy/SwiadomeChrzescijanstwo`, gałąź `master`. Poprzednią ręczną inspirację zachowano w `backup/legacy-kaira-2025`.
2. Włącz `Settings → Actions → General → Workflow permissions → Read and write permissions`, jeśli akcja nie może zapisywać importu. W `Settings → Pages` wybierz publikację przez GitHub Actions.
3. Push uruchomi `.github/workflows/migrate-content.yml`. Import **kończy się błędem**, jeśli pobranie choćby jednego odkrytego zasobu albo porównanie tekstu się nie powiedzie. Raport błędów będzie dostępny jako artefakt działania.
4. Workflow wdrożeniowy `.github/workflows/pages.yml` nie opublikuje strony bez pozytywnej weryfikacji `scripts/strict_audit.py --require-import`.
5. Po imporcie zweryfikuj spis adresów i przytoczone treści w `migration-report.json` i `STRICT_AUDIT.json`, a następnie rzeczywiste wyświetlanie na podglądowej domenie.

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

Zobacz `DEPLOY_GITHUB_PAGES.md`. URL projektu to `https://tometchy.github.io/SwiadomeChrzescijanstwo/`; nie konfiguruj `CNAME` ani własnego DNS. Repozytorium jest obecnie prywatne: na darmowym planie GitHub Pages wymaga repozytorium publicznego; na GitHub Pro/Team/Enterprise może być prywatne.

Import 1:1 nadal wymaga kontroli: nawet pomyślny crawl nie dowodzi obecności osieroconych zasobów niepowiązanych odnośnikami. Strona pozostaje zablokowana dla publikacji, jeśli raport importu jest niekompletny.
