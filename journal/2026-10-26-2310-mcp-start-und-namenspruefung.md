## 2026-10-26 — MCP-Startweg und Namensprüfung korrigiert

* **Stand**: `just mcp-dev` startet den installierten Projekt-Entrypoint
  (`uv run <project_name>`) statt `mcp run <datei>`; relative Paketimporte
  funktionieren damit auch im Inspector. Das Entwicklungsextra `mcp[cli]` ist
  entfernt. `pyinit` lehnt Selbstabhängigkeiten nach der Artefaktauflösung im
  Preflight ab; `new mcp mcp`, `MCP` und externe Profile mit MCP-Artefakt
  scheitern vor Staging und `uv lock`, auch mit `--dry-run`.
* **Änderungen**: MCP-Justfile-Fragment und Artefaktabhängigkeiten angepasst;
  `validate_project_dependencies` und `SelfDependencyError` ergänzt; README-
  und AGENTS-Templates, ADR-0005/0006/0007 und AP-2 aktualisiert. Regressionstest
  führt das Rezept über Fake-`npx`/`uv`, den echten Paket-Entrypoint und einen
  relativen Import aus. `just check` und `just test-generated` sind grün.
* **ADRs**: ADR-0006 (neu), ADR-0007 (neu); ADR-0005 ersetzt
* **Attention Points**: AP-2 (präzisiert)
* **Offen**: Ein interaktiver Inspector-Lauf mit Node.js wurde nicht
  durchgeführt; der Startweg ist im Regressionstest ohne Node.js ausgeführt.
