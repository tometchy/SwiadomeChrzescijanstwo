# Audyt zgodności 1:1 — 17 listopada 2026

## Stwierdzone niezgodności wcześniejszego ZIP-a

1. 41 opublikowanych kart książek miało dodane przez asystenta streszczenia i opisy; nie były one tekstami z `wswch.pl`. **Usunięto.**
2. Dwa wpisy w `_artykuly/` były napisane od zera, a nie przeniesione z `swch.pl`. **Usunięto.**
3. Występowały przepisywane, poprawiane tytuły i pełne imiona autorów, zamiast oryginalnej treści tabeli. **Przywrócono pierwotną pisownię dla 41 + 39 rekordów na podstawie publicznego widoku katalogu.**
4. Strona główna i strony informacyjne zawierały autorskie hasła i dopiski. **Usunięto większość i zamieniono opisowe akapity na cytowane fragmenty oryginalnych stron.** Pozostała nawigacja jako element projektu.
5. Wcześniejszy konwerter mógł pomijać części wielokolumnowych tabel i treści. **Zastąpiono pełnym źródłowym HTML w dokumentach Jekyll i byte-identical archiwum każdego pobranego HTML**.

## Granice weryfikacji

Na etapie tworzenia ZIP nie udało się pobrać pełnych HTML i zasobów ze starych witryn do tego kontenera. Weryfikacja bajtowa całej zawartości **NIE ZOSTAŁA WYKONANA**, dlatego stan finalny = **NIEPOTWIERDZONY**.

Właściwy wynik audytu technicznego w `STRICT_AUDIT.json` dotyczy wyłącznie danych w paczce. `migration-report.json` i `STRICT_AUDIT.json` po imporcie w GitHub Actions muszą potwierdzić wszystkie odkryte strony, teksty i pliki. Niepodlinkowane strony wymagają backupu właściciela serwera.

## Reguła publikacji

Jeśli importer wykryje choć jeden niepobrany plik, brak pozycji w katalogu lub zmianę znaków tekstu, kończy się błędem. Wdrożenie GitHub Pages wymaga statusu `VERIFIED`. Liczba 41+39 potwierdza kompletność katalogu na głównej stronie wydawnictwa, **nie** kompletność całej czytelni.
