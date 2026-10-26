# 0004 – pyinit legt nur neue Projekte an

- Status: accepted
- Datum: 2026-10-26

## Kontext

Ein Update- oder Merge-Modus für bestehende Projekte würde Konflikte mit
lokalen Änderungen, bereits installierten Abhängigkeiten und abweichenden
Konfigurationen lösen müssen. Die alte Funktion war ebenfalls ein reiner
Initialisierer.

## Entscheidung

v1 unterstützt nur `new`. Es gibt kein `add`, kein Update und kein Merge in
bestehende Projekte. Ein Ziel muss fehlen, leer sein oder nur `.git` enthalten.
Die erzeugte Datei `pyinit.toml` dokumentiert Profil, Modus, Artefakte und
Kontext für spätere Werkzeuge.

## Konsequenzen

- Der Zielzustand ist vor dem ersten Schreibzugriff eindeutig prüfbar.
- Atomarität und Fehlerpfade bleiben beherrschbar.
- Bestehende Projekte werden nicht automatisch migriert; das bleibt eine
  bewusste, separate Aufgabe.
