# Issue #1 — weryfikacja i odzyskiwanie źródeł

Oryginalny raport `migration-report.json` pozostaje punktem odniesienia.
Zapisano 594 strony HTML oraz 112 plików. Import przekonwertował 487 artykułów,
a kolejne 50 zachował jako oryginalny HTML. Dla każdego z tych 50 raportów
`recover_missing.py` porównuje bajty w `_source_archive` i `archiwum`;
`verify_reachable.py` sprawdza dodatkowo sumy SHA-256 wszystkich pobranych
plików.

47 stron HTML i 62 pliki dodatkowe zwracały 404 w pierwszym imporcie.

## Próba odzyskania

Uruchom `python scripts/recover_missing.py --output recovery-output`,
albo pobierz artefakt `issue-1-source-recovery` z workflow GitHub Actions.

Dla każdego 404 program próbuje adresu z alternatywnym wariantem hosta `www`.
Jeśli to nie wystarcza, pyta Wayback Availability API o datowany snapshot,
pobiera rzeczywiste bajty i sprawdza typ pliku. Pliki trafiają **wyłącznie
do kwarantanny** (`candidates/`), a raport zawiera pochodzenie, datę, rozmiar,
oryginalny URL i SHA-256. Nie zmienia produkcyjnej witryny ani manifestu
migracji. Powrót HTTP 200 z ekranu Cloudflare nie jest uznawany za sukces.

## Warunki zamknięcia issue

- 109 pozycji trzeba odzyskać, albo udokumentować, że linki były martwe
  na oryginalnym serwerze. Wymagana decyzja właściciela o dopuszczeniu
  historycznie martwych odsyłaczy.
- 50 artykułów w fallback musi pozostać bajt w bajt identyczne.
- Dla odzyskanych źródeł trzeba przeprowadzić drugi PR wprowadzający
  oryginalne binaria/HTML i aktualizujący manifest oraz kontrolę linków.
- `scripts/strict_audit.py --require-import` musi przejść, zanim strona
  otrzyma etykietę pełnej migracji 1:1; sam stary raport 404 nie wystarczy.
- Stron niepodlinkowanych na serwerze nie da się odkryć samym crawlerem.
  Pełną kompletność można potwierdzić po porównaniu z serwerowym ZIP
  katalogów HTML/PDF/obrazów/EPUB lub wiarygodnym spisem plików.

**Nie wpisywać pustych zastępczych stron, generowanych PDF-ów ani 
wymyślonych treści, aby uzyskać zielony wynik audytu.**
