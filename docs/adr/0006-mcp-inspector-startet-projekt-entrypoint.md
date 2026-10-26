# 0006 – MCP-Inspector startet den Projekt-Entrypoint

- Status: accepted
- Datum: 2026-10-26

## Kontext

[Die ursprüngliche MCP-Entscheidung](_0005-mcp-nutzt-offizielles-sdk.md) startete
den Server im Inspector über `mcp run src/<package>/server.py` und hielt dafür
das Entwicklungsextra `mcp[cli]` bereit. Die SDK-CLI lädt die angegebene Datei
jedoch ohne Paketkontext. Sobald der Server übliche relative Importe aus
benachbarten Modulen nutzt, funktioniert der reguläre Paketimport weiterhin,
aber der Inspector-Start bricht mit `ImportError` ab. `just run` und
`just mcp-dev` verwendeten damit unterschiedliche Importwege.

## Entscheidung

`just mcp-dev` startet denselben installierten Projekt-Entrypoint wie
`just run`:

```text
HOST=127.0.0.1 npx @modelcontextprotocol/inspector@2.12.0 uv run <project_name>
```

Das erzeugte Projekt braucht nur die Runtime-Abhängigkeit `mcp`; das
Entwicklungsextra `mcp[cli]` entfällt. Der Inspector bleibt auf eine feste
npm-Version gepinnt, bindet nur an Loopback und bleibt außerhalb von
`just check`. Node.js bleibt eine dokumentierte manuelle Voraussetzung.

## Konsequenzen

- Relative Paketimporte funktionieren im Inspector genauso wie über `just run`.
- Der Server wird als Teil seines Python-Pakets importiert, nicht als einzelne
  Datei.
- Die Entwicklungsumgebung wird kleiner, weil uv keine zusätzliche
  CLI-Abhängigkeit auflösen muss.
- In-Memory-Smoke-Tests und der stdio-Betrieb bleiben unverändert.
- Ohne Node.js schlägt nur `just mcp-dev` fehl.

## Alternativen

- **`mcp run` mit Dateipfad beibehalten:** scheitert an relativen Importen und
  erzwingt einen anderen Importweg als der Entrypoint.
- **`python -m <package>.main` starten:** funktioniert, ist aber ein dritter
  Startweg neben Entrypoint und Inspector.
- **`mcp[cli]` als Entwicklungsextra behalten:** nach dem Wechsel auf den
  Entrypoint nicht mehr nötig und zusätzliche Auflösungslast.
