## 2026-10-26 — MCP-Startweg und Namensprüfung korrigiert

* **Stand**: `just mcp-dev` startet den installierten Projekt-Entrypoint
  (`uv run <project_name>`) statt `mcp run <datei>`; relative Paketimporte
  funktionieren damit auch im Inspector. Das Entwicklungsextra `mcp[cli]` ist
  entfernt. `pyinit` lehnt Selbstabhängigkeiten nach der Artefaktauflösung im
  Preflight ab; `new mcp mcp`, `MCP` und externe Profile mit MCP-Artefakt
  scheitern vor Staging und `uv lock`, auch mit `--dry-run`.
* **Änderungen**: MCP-Justfile-Fragment und Artefaktabhängigkeiten angepasst;
  `validate_project_dependencies` und `SelfDependencyError` ergänzt; README-
  und AGENTS-Templates, ADR-0004 und den Attention Point „MCP-Projekt nicht
  `mcp` nennen“ aktualisiert. Die Details zum Inspector-Start und zur
  Namensprüfung stehen inzwischen in `docs/artefakte.md`. Regressionstest
  führt das Rezept über Fake-`npx`/`uv`, den echten Paket-Entrypoint und einen
  relativen Import aus. `just check` und `just test-generated` sind grün.
* **ADRs**: ADR-0004 (damals als ADR-0005 angelegt); die früheren ADRs 0006
  und 0007 sind inzwischen in `docs/artefakte.md` überführt.
* **Attention Points**: MCP-Projekt nicht `mcp` nennen (präzisiert)
* **Offen**: Ein interaktiver Inspector-Lauf mit Node.js wurde nicht
  durchgeführt; der Startweg ist im Regressionstest ohne Node.js ausgeführt.
