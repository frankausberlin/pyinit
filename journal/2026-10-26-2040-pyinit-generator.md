## 2026-10-26 — Datengetriebener pyinit-Generator

* **Stand**: Die Shell-Funktion ist durch eine Python-CLI mit Profilen,
  Artefakten, Jinja-Templates und atomarem Apply ersetzt; die drei Profile
  `app`, `app-cli` und `lib` erzeugen grüne Projekte.
* **Änderungen**: Engine (`context`, `discovery`, `resolver`, `render`, `plan`,
  `apply`, `runner`), CLI `new`/`list`/`describe`, Datendateien unter
  `src/pyinit/data/`, Unit- und Docker-E2E-Tests, `scripts/test-generated.sh`
  mit `just test-generated`, CI-Job `generated`, neue CLI-Referenz und
  Projektdokumentation.
* **ADRs**: 0001, 0002, 0003, 0004
* **Attention Points**: AP-1
* **Offen**: `mcp`-Artefakt und Profil als Folgeschritt; Ablösung der alten
  Shell-Funktion im Luxus-Python-Stack als separate Änderung.
