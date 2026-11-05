## 2026-11-05 — ludesta 0.15.0, ADR-Bereinigung und AP-Titel

* **Stand**: pyinit folgt ludesta 0.15.0: ADRs gehören dem Projektnutzer, der
  Agent liest sie nur; Attention Points tragen keine Nummern und keine
  Tombstones. Die ADR-Nummern in `docs/adr/` sind lückenlos `0001`–`0005`;
  `LUPYSTA_VERSION` ist `0.15.0`, `CONTRACT_VERSION` bleibt `4`.
* **Änderungen**: Generator-Templates (`models.py`, `AGENTS.md.j2`,
  `adr/files/README.md`, `ap/artifact.toml`, `journal-README.md`,
  `contributing.md.j2`, `explanation-index.md`), pyinit-Doku (`AGENTS.md`,
  `README.md`, `CONTRIBUTING.md`, `docs/artefakte.md`, neues
  `docs/adr/README.md`), ADR-Bestand, Journal-Verweise und Tests
  (`test_render.py`, neues `test_project_docs.py`).
* **ADRs**: Mapping alt→neu: 0005→0004 (offizielles MCP-SDK über stdio, jetzt
  `accepted`), 0009→0005 (CLI und MCP teilen einen Entrypoint). Die früheren
  0004 (nur neue Projekte), 0006 (Inspector-Start), 0007
  (Selbstabhängigkeits-Preflight) und 0008 (lupysta-Version als Konstante)
  sind ersatzlos entfallen; ihre Inhalte stehen in `README.md`, `AGENTS.md`
  und `docs/artefakte.md`. Ab jetzt gilt die Unveränderlichkeitsregel wieder.
* **Attention Points**: Generierte Projektprüfung gehört in
  `test-generated`; MCP-Projekt nicht `mcp` nennen; Herkunft erzeugter
  Projekte ist nicht selbstaktualisierend.
* **Review**: `just check` und `just test-generated` sind grün; alle fünf
  Profile bestehen ihr Gate. Die ADR-Nummern sind lückenlos `0001`–`0005`, und
  die aktive Dokumentation enthält keine Verweise auf die entfernten ADRs.
* **Offen**: Die Entscheidung zu FastMCP und eine generierte MCP-ADR sind
  nicht Teil dieses Changes; beides braucht einen separaten Change mit eigener
  ADR-Entscheidung.
