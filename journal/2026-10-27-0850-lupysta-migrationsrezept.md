## 2026-10-27 — Lupysta-Migrationsrezept und Skill-Version 0.13.0

* **Stand**: `LUPYSTA_VERSION` ist mit dem lupysta-Skill auf `0.13.0`
  synchronisiert; `CONTRACT_VERSION` bleibt `4`.
* **Änderungen**: Die Versionskonstante in `src/pyinit/models.py` wurde für das
  neue lupysta-Rezept `project-migration.md` angehoben. Das Rezept beschreibt
  Upgrade, Adoption und Teilmigration bestehender Python-Projekte; `pyinit`
  bleibt ein reiner Initialisierer und dient dabei als Zielreferenz.
* **Review**: `just check` grün; 143 Tests bestanden, Coverage 94,58 %,
  Dokumentationsprüfung aktuell.
* **ADRs**: keine
* **Attention Points**: keine
* **Offen**: Commit und Merge stehen noch aus.
