# 0001 – pyinit wird ein Python-Generator

- Status: accepted
- Datum: 2026-10-26

## Kontext

Die Projektinitialisierung lag als Bash-Funktion im Luxus-Python-Stack. Die
Funktion enthielt Heredocs, `sed`-Patches und fest verdrahtete Abläufe. Pflege,
Tests und Fehlermeldungen waren an eine Shell gebunden, und die erzeugten
Dateien ließen sich nur indirekt prüfen.

## Entscheidung

Die Bash-Funktion wird durch die Python-CLI `pyinit` in diesem Repository
ersetzt. Die alte Funktion bleibt bis zur erreichten Parität als Referenz
unangetastet; ihre Ablösung im Luxus-Python-Stack ist eine separate Änderung.

## Konsequenzen

- Der Generator ist mit Python-Tests, Typprüfung und Fehlerhierarchie testbar.
- Die erzeugten Projekte werden über `just test-generated` mit der echten
  Toolchain geprüft.
- Bis zur Ablösung existieren zwei Implementierungen; Template-Drift wird
  durch wörtliche Extraktion und den grünen Generator-Test begrenzt.
