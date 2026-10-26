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
- Tests für den Generator gehören in `tests/`; erzeugte Projekte werden über
  `just test-generated` geprüft.

## Dokumentation

- `docs/artefakte.md` ist handgepflegt und beschreibt jedes Artefakt und jedes
  Profil. Änderungen an `src/pyinit/data/artifacts/**` oder
  `src/pyinit/data/profiles/**` erfordern eine Anpassung dieser Seite im selben
  Commit. `pyinit describe <id>` zeigt dieselben Daten zur Laufzeit.
- Ein Bump der Skill-Version erfordert manuell `lupysta_version` in
  `src/pyinit/data/artifacts/agent-docs/templates/AGENTS.md.j2` und
  `CONTRACT_VERSION` in `src/pyinit/models.py` nachzuziehen. Es gibt bewusst
  keinen Automatismus und keinen CI-Check dafür.

## ADRs

Architekturentscheidungen liegen als Dateien in `docs/adr/`. Verschaffe dir mit
`ls -1 docs/adr` einen Überblick, falls das Verzeichnis existiert.

* Dateiname: `NNNN-entscheidung.md`, zum Beispiel `0001-wir-verwenden-zsh.md`.
  Der Name nennt die Entscheidung, nicht nur das Thema.
* Ein `ADR`-Präfix im Dateinamen ist nicht nötig; das Verzeichnis benennt die
  Dokumentart.
* Der Name reicht für den Überblick; lies eine aktive ADR, wenn ihre
  Entscheidung die Aufgabe berührt.
* Revidierte Entscheidungen tragen ein `_`-Präfix, zum Beispiel
  `_0001-wir-verwenden-zsh.md`. Ihre Nummer bleibt vergeben.
* Der Status steht im Dokument: `accepted`, `superseded by ADR-NNNN` oder
  `deprecated`.

## Attention Points

<!--
Format eines Eintrags:

### AP-1: Kurztitel

- **Situation**: ...
- **Handhabung**: ...
- **Involvierte ADRs**: ...
- **Kontext**: ...

Entfernte APs bleiben als `### AP-N: entfernt (YYYY-MM-DD)` stehen; ihre
Nummer wird nicht neu vergeben.
-->

### AP-1: Generierte Projektprüfung gehört in `test-generated`

- **Situation**: Erzeugte Projekte brauchen `uv sync`, Netzwerk und die echte
  `just`-Toolchain. Die Docker-Suite läuft hermetisch mit `--network none`.
- **Handhabung**: `just check` im erzeugten Projekt läuft über
  `just test-generated` auf dem Host bzw. in CI. Die Docker-Suite prüft
  stattdessen `--dry-run`, Dateipläne und Atomarität mit Fake-Tools.
- **Involvierte ADRs**: ADR-0001, ADR-0003.
- **Kontext**: Ein grüner Generator-Test soll nicht durch fehlendes Netzwerk
  oder einen anderen Interpreter im Container verfälscht werden.

### AP-2: MCP-Projekt nicht `mcp` nennen

- **Situation**: Das Profil `mcp` hängt von der PyPI-Distribution `mcp` ab.
  Heißt das erzeugte Projekt selbst `mcp`, versucht `uv lock`, das Projekt als
  Abhängigkeit seiner selbst aufzulösen, und bricht mit einer
  unsatisfiable-Resolution ab.
- **Handhabung**: `pyinit` lehnt den normalisierten Projektnamen `mcp` im
  Preflight ab, sobald das aufgelöste Artefaktset die MCP-Abhängigkeit enthält;
  das gilt auch für `--dry-run` und externe Profile. Für Profil-Checks und
  Nutzerbeispiele ist ein abweichender Name nötig, etwa `mcp-project` oder ein
  fachlicher Name wie `arithmetic-mcp`. Der Profilname bleibt `mcp`, nur der
  Projektname muss abweichen.
- **Involvierte ADRs**: ADR-0007.
- **Kontext**: `scripts/test-generated.sh` legt das Ziel für `mcp` als
  `mcp-project` an; die übrigen Profile behalten ihren Profilnamen.

## Herkunft

- lupysta_version: `0.11.0`
- contract_version: `4`
