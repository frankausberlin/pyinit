# 0003 – Artefakte sind Daten

- Status: accepted
- Datum: 2026-10-26

## Kontext

Die alte Implementierung mischte Komposition und Dateierzeugung in Shell-Code.
Dadurch war unklar, welche Datei zu welchem Projektbestandteil gehört, und
Profilvarianten mussten im Code abgebildet werden.

## Entscheidung

Artefakte bestehen in v1 aus einem TOML-Manifest, Jinja-Templates und statischen
Dateien. Profile referenzieren Artefakt-IDs. Die Engine löst den Graphen auf,
rendert alle Dateien im Speicher und bildet daraus einen Plan. Python-Hooks in
Artefakten sind nicht vorgesehen.

## Konsequenzen

- Neue Varianten entstehen durch Daten, nicht durch neue Verzweigungen in der
  CLI.
- Fehlende Kontextvariablen brechen dank `StrictUndefined` laut ab.
- Logik, die echte Python-Funktionen bräuchte, muss warten oder als eigenes
  Artefakt mit statischem Inhalt modelliert werden.
