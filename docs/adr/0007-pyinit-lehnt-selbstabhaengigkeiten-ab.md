# 0007 – pyinit lehnt Selbstabhängigkeiten im Preflight ab

- Status: accepted
- Datum: 2026-10-26

## Kontext

Das MCP-Artefakt hängt von der PyPI-Distribution `mcp` ab. Ein erzeugtes
Projekt namens `mcp` plant damit eine Abhängigkeit auf seine eigene
Distribution. Der Konflikt fiel bisher erst bei `uv lock` auf; `--dry-run`
akzeptierte die unmögliche Konfiguration. Die Namensprüfung kannte nur das
Profil `mcp`, externe Profile mit demselben Artefakt konnten die Prüfung
umgehen. Distributionsnamen vergleicht uv ohne Beachtung der
Groß-/Kleinschreibung und normalisiert `-`, `_` und `.` zu `-`.

## Entscheidung

Nach der Artefaktauflösung vergleicht pyinit den normalisierten
Distributionsnamen des Projekts mit den normalisierten Namen aller aufgelösten
Laufzeit-, Entwicklungs- und E2E-Abhängigkeiten. Bei einer Kollision bricht die
Generierung vor dem Rendern, Staging und `uv lock` mit einer verständlichen
Fehlermeldung ab. Die Prüfung wertet das aufgelöste Artefaktset aus, nicht die
Profil-ID, und gilt damit auch für `--dry-run` und externe Profile. Namen, die
`mcp` nur enthalten, etwa `arithmetic-mcp` oder `mcp-project`, bleiben erlaubt.
Für den MCP-Fall nennt die Meldung einen Ausweichnamen.

## Konsequenzen

- Nutzer erhalten den Fehler vor dem ersten externen Befehl und vor jeder
  Änderung am Ziel.
- Die Regel deckt auch andere echte Selbstabhängigkeiten ab, ohne Projekte
  ohne Kollision pauschal einzuschränken.
- AP-2 dokumentiert die Handhabung; `scripts/test-generated.sh` bleibt bei
  `mcp-project`, weil dieser Name kollisionsfrei ist.
- Der Resolver bleibt unverändert; eine allgemeine Abhängigkeitsgraph-Prüfung
  ist für diesen Fall nicht nötig.

## Alternativen

- **Nur `profile.id == "mcp"` prüfen:** externe Profile könnten die Prüfung
  umgehen.
- **Nur den Namen `mcp` ablehnen:** übersieht andere Selbstabhängigkeiten, die
  erst später an `uv lock` scheitern.
- **Resolver um eine vollständige Abhängigkeitsgraph-Prüfung erweitern:** mehr
  Komplexität als für die konkrete Kollision erforderlich.
