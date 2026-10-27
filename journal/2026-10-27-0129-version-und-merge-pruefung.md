## 2026-10-27 — Herkunftsversion entdoppelt, Merge-Rezept getestet

* **Stand**: `lupysta_version` steht nur noch in `src/pyinit/models.py`
  (`LUPYSTA_VERSION`), wird über den Kontext gerendert und ist in jedem Profil
  testabgedeckt. Erzeugte Projekte nennen wieder die aktuelle Skill-Version
  `0.12.0` statt des Literals `0.11.0` aus dem Template. Das Rezept `merge`
  enthält keine Logik mehr: Die Bash-Logik liegt in `scripts/merge.sh`, das
  jedes Projekt erhält; das Rezept reicht nur `branch` und `target` weiter.
  pyinit nutzt dieselbe Datei selbst (`Cargo`-freies Dogfooding), ein Test
  sichert die Gleichheit beider Kopien.
* **Änderungen**: `models.py` (`LUPYSTA_VERSION`, Kontextfeld),
  `agent-docs/templates/AGENTS.md.j2` (Variable statt Literal, AP-Beispiel
  eingerückt), `base-app/files/merge.sh` (neu, executable),
  `base-app/templates/justfile.j2` (Rezept ruft Skript), `base-app/artifact.toml`,
  `Justfile`, `scripts/merge.sh` (neu), `tests/test_merge_script.py` (neu,
  8 Fälle), `tests/test_render.py`, `docs/artefakte.md`, `AGENTS.md`.
  `just check` ist grün (143 Tests, 94,6 % Coverage).
* **Gefundener Fehler**: Das Rezept hat `just merge` ohne Argument in einem
  Projekt mit Branch-Worktree kaputt gemacht. `git worktree list --porcelain`
  liefert volle Refs; der Kandidat wurde als `refs/heads/<branch>` gemergt,
  danach schlug `git branch -d` fehl (Exit 1, Branch blieb stehen). Das ist
  genau der in der Skill-Doku beschriebene Harness-Ablauf. Behoben, Test
  `test_merges_from_linked_worktree_and_removes_it` deckt den Fall ab.
* **ADRs**: ADR-0008 (neu) – lupysta-Version als Konstante im Generator,
  Abgleich über die Repo-Grenze bewusst manuell.
* **Attention Points**: AP-3 (neu) – Herkunft erzeugter Projekte ist nicht
  selbstaktualisierend; `AGENTS.md`/`pyinit.toml` bei Abweichung nicht
  stillschweigend umschreiben.
* **Offen**: Es gibt weiterhin keinen Upgrade-Pfad (`pyinit doctor`/`diff`).
  Ebenso unbestimmt ist, wann `CONTRACT_VERSION` zu erhöhen ist; mit dem neuen
  `scripts/merge.sh` hat sich der Vertrag erzeugter Projekte faktisch
  geändert, die Version steht aber weiter auf 4. Diese Datei selbst nennt in
  ihrer Herkunft noch `0.11.0` und wurde nicht rückdatiert.
