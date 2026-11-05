# AGENTS.md – pyinit

Diese Datei enthält die projektbezogenen Informationen und Regeln. Die
Arbeitsweisen selbst stehen im lupysta-Skill; hier steht nur, was für dieses
Projekt gilt.

Verwende für die Entwicklung immer den lupysta-Skill.

## Projektprofil

- Projektname: `pyinit`
- Paketname: `pyinit`
- Projekttyp: App (CLI)
- Python-Version: `3.12`
- Quellpfad: `src/pyinit/`
- Testpfad: `tests/`

## Testing

- `just test` und `just check` führen die Unit-/Smoke-Tests aus. Die opt-in
  Suiten laufen dort nie.
- `tests/e2e/` ist die Docker-Suite. Nur mit `just test-e2e` ausführen, nie mit
  einem direkten `pytest` und nie auf dem Host. Der CI-Workflow führt sie bei
  Push und Pull Request automatisch aus, sobald Testdateien vorhanden sind.
- `tests/agent/` ist die opt-in Provider-Suite. Nur mit `just test-agent`
  ausführen; sie ist beratend und nie Teil der CI.
- Beide Runner suchen rekursiv nach `test_*.py`, ohne Testmodule zu
  importieren. Suchfehler brechen laut ab; ein fehlendes Suite-Verzeichnis gilt
  als leere Suite. Bei leerer Suite gibt es einen Hinweis und Exit 0. Sobald
  Testdateien existieren, sind Fehler echte Fehler.
- Das Verzeichnis-Gate steht in `tests/conftest.py`; die Suite-Guards brechen
  ab, bevor Testmodule importiert werden, wenn eine Suite ohne Opt-in
  gesammelt wird.
- `just test-generated` ist die opt-in Prüfung der erzeugten Projekte. Sie
  läuft auf dem Host bzw. in CI, braucht Netzwerk und die echte
  `uv`/`just`-Toolchain. Die hermetische Docker-Suite prüft stattdessen
  `--dry-run`, Dateipläne und Atomarität mit einer Fake-Toolchain.

## Generator

- Die CLI heißt `pyinit` und bietet `new`, `list` und `describe`.
- Profile und Artefakte liegen als TOML unter `src/pyinit/data/`. Profile
  referenzieren Artefakt-IDs, keine Template-Pfade.
- Basisartefakte `base-app`/`base-lib` werden aus dem Profilmodus injiziert.
- Gemeinsame Dateien werden genau einmal von der Basis oder `agent-docs`
  gerendert; Artefakte liefern Includes und Justfile-Fragmente.
- `pyinit` legt nur neue Projekte an; ein Ziel muss fehlen, leer sein oder nur
  `.git` enthalten. Update/Merge in bestehende Projekte gibt es nicht. Die
  bewusste Migration bestehender Projekte ist ein separater Stack-Auftrag
  (`Projekt-Migration`).
- Tests für den Generator gehören in `tests/`; erzeugte Projekte werden über
  `just test-generated` geprüft.

## Dokumentation

- `docs/artefakte.md` ist handgepflegt und beschreibt jedes Artefakt und jedes
  Profil. Änderungen an `src/pyinit/data/artifacts/**` oder
  `src/pyinit/data/profiles/**` erfordern eine Anpassung dieser Seite im selben
  Commit. `pyinit describe <id>` zeigt dieselben Daten zur Laufzeit.
- Die Herkunftswerte stehen in `src/pyinit/models.py`: `LUPYSTA_VERSION` und
  `CONTRACT_VERSION`. Templates lesen sie über den Kontext
  (`{{ lupysta_version }}`, `{{ contract_version }}`); Literale in Templates
  sind ein Fehler.
- Ein Bump von `LUPYSTA_VERSION` wird mit dem Feld `version:` in
  `ludesta/Luxus-Python-Stack/lupysta/SKILL.md` abgeglichen. Einen
  automatischen Abgleich über die Repo-Grenze gibt es bewusst nicht: Er würde
  die eigenständigen Repositories über Netzwerk und Fremdzustand koppeln; ein
  fehlgeschlagener Clone würde das Gate blockieren, obwohl die Änderung nichts
  damit zu tun hat. Die Tests sichern nur die Repo-interne Einmaligkeit.

## ADRs

Architekturentscheidungen liegen in `docs/adr/`; die Konvention steht in
`docs/adr/README.md`. Der Agent liest ADRs nur: Er legt keine an, ändert sie
nicht und nummeriert sie nicht um.

## Attention Points

<!--
Format eines Eintrags:

    ### Kurztitel

    - **Situation**: Genau ein Satz; wiederholt die Überschrift nicht.
    - **Handhabung**: Kurzer Satz oder knappe Liste.

Attention Points sind gegenwartsbezogen: keine Nummern, keine Tombstones und
keine Felder für beteiligte ADRs oder Kontext. Obsolete Einträge werden
ersatzlos gelöscht; die Git-Historie ist das Archiv.
-->

### Generierte Projektprüfung gehört in `test-generated`

- **Situation**: Erzeugte Projekte brauchen `uv sync`, Netzwerk und die echte
  `just`-Toolchain, während die Docker-Suite hermetisch mit `--network none`
  läuft.
- **Handhabung**: `just check` im erzeugten Projekt läuft über
  `just test-generated` auf dem Host bzw. in CI. Die Docker-Suite prüft
  stattdessen `--dry-run`, Dateipläne und Atomarität mit Fake-Tools.

### MCP-Projekt nicht `mcp` nennen

- **Situation**: Die Profile `mcp` und `cli-mcp` hängen über `mcp-server` von
  der PyPI-Distribution `mcp` ab; ein Projekt namens `mcp` versucht `uv lock`
  deshalb, als Abhängigkeit seiner selbst aufzulösen, und bricht mit einer
  unsatisfiable-Resolution ab.
- **Handhabung**:
  - `pyinit` lehnt den normalisierten Projektnamen `mcp` im Preflight ab,
    sobald das aufgelöste Artefaktset die MCP-Abhängigkeit enthält; das gilt
    auch für `--dry-run`, externe Profile sowie die Profile `mcp` und
    `cli-mcp`.
  - Für Profil-Checks und Nutzerbeispiele ist ein abweichender Name nötig,
    etwa `mcp-project` oder ein fachlicher Name wie `arithmetic-mcp`. Der
    Profilname bleibt `mcp`, nur der Projektname muss abweichen.
  - `scripts/test-generated.sh` legt das Ziel für `mcp` als `mcp-project` an;
    die übrigen Profile behalten ihren Profilnamen.

### Herkunft erzeugter Projekte ist nicht selbstaktualisierend

- **Situation**: `pyinit` legt nur neue Projekte an und aktualisiert keine
  bestehenden, sodass `AGENTS.md` (Herkunft) und `pyinit.toml` eines Projekts
  die Skill- und Contract-Version zum Zeitpunkt der Erzeugung nennen.
- **Handhabung**: Vor Arbeiten an einem generierten Projekt die Herkunft lesen
  und mit `version:` in `ludesta/Luxus-Python-Stack/lupysta/SKILL.md`
  vergleichen. Bei Abweichung die Differenz melden und die betroffenen Dateien
  bewusst abgleichen; `AGENTS.md` und `pyinit.toml` nicht stillschweigend
  umschreiben, als wäre das Projekt neu erzeugt worden. Einen echten
  Upgrade-Pfad (`pyinit doctor`/`diff`) gibt es noch nicht – nicht ungefragt
  nachbauen, sondern als Aufgabe anlegen.

## Herkunft

- lupysta_version: `0.15.0`
- contract_version: `4`
