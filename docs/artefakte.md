# Artefakte und Profile

`pyinit` erzeugt Projekte aus Daten, nicht aus Verzweigungen im Code. Ein
**Profil** ist ein Modus plus eine Liste von Artefakt-IDs. Jedes **Artefakt**
liefert Dateien, Justfile-Fragmente und Abhängigkeiten. Das Basisartefakt wird
nicht im Profil genannt, sondern aus dem Modus injiziert: `app` → `base-app`,
`lib` → `base-lib`. `base-lib` verlangt seinerseits `base-app`.

## Kompositionsregeln

- **`requires`** zieht weitere Artefakte in die Auflösung; die Reihenfolge ist
  eine stabile topologische Sortierung, Zyklen brechen ab.
- **`conflicts`** lehnt Kombinationen ab, die sich gegenseitig ausschließen.
- **`provides`** vergibt Fähigkeiten. Doppelte Fähigkeiten brechen ab; aus den
  Namensräumen `entrypoint.*` und `docs.*` ist jeweils höchstens eine Fähigkeit
  erlaubt.
- **`modes`** beschränkt ein Artefakt auf `app` oder `lib`; ein Profil mit
  fremdem Modus bricht ab.
- **Dateien** werden genau einmal geschrieben. Zwei Artefakte mit demselben Ziel
  brechen ab (`DuplicateTargetError`), ebenso zwei Justfile-Rezepte mit demselben
  Namen (`DuplicateRecipeError`).
- **Justfile-Fragmente** werden in Auflösungsreihenfolge an das Basis-Justfile
  gehängt. Das Basisartefakt liefert `set shell := ["bash", "-uc"]`.
- **Abhängigkeiten** werden je Gruppe (`runtime`, `dev`, `e2e`) zusammengeführt.
  Abweichende Constraints für denselben Namen brechen ab; ein Projektname, der
  einer eigenen Abhängigkeit entspricht, wird im Preflight abgelehnt.
- **Templates** laufen mit `StrictUndefined`: Eine fehlende Variable bricht laut
  ab, statt still eine Lücke zu lassen. Statische Dateien (`render = false`)
  werden byte-genau kopiert; `executable = true` setzt das Ausführungsbit.
- **Pfade** in Manifesten und Zielen müssen relativ sein und dürfen weder `..`
  noch absolute Pfade enthalten.

### Kontextvariablen

Alle Templates sehen: `project_name`, `package_name`, `python_version`,
`author_name`, `year`, `mode`, `profile`, `artifacts`, `generated_at`,
`pyinit_version`, `contract_version`. Zusätzlich stehen
`runtime_dependencies`, `dev_dependencies`, `e2e_dependencies`, `has_docs`,
`has_entrypoint` und `capabilities` bereit.

### Erzeugungsablauf

`pyinit new` validiert Ziel und Toolchain, rendert den vollständigen Dateiplan im
Speicher, schreibt ihn in ein Staging-Verzeichnis, führt dort `uv lock` aus und
verschiebt das Ergebnis erst dann an das Ziel. Danach folgen `git init -b main`
(nur wenn kein `.git` vorhanden ist), `uv sync`, `uv run pre-commit install`,
bei Bedarf `just docs` und – sofern nicht `--no-check` – `just check`.
`--dry-run` zeigt genau diesen Plan, ohne zu schreiben.

## Artefakte

### `base-app`

Basis für jede Anwendung; wird bei Modus `app` automatisch injiziert.

**Dateien**

| Quelle | Ziel |
| --- | --- |
| `templates/pyproject.toml.j2` | `pyproject.toml` |
| `templates/justfile.j2` | `Justfile` |
| `templates/readme.md.j2` | `README.md` |
| `templates/contributing.md.j2` | `CONTRIBUTING.md` |
| `templates/license.j2` | `LICENSE` |
| `templates/python-version.j2` | `.python-version` |
| `templates/init.py.j2` | `src/<paket>/__init__.py` |
| `templates/pyinit.toml.j2` | `pyinit.toml` |
| `files/.gitignore` | `.gitignore` |
| `files/.editorconfig` | `.editorconfig` |
| `files/.envrc` | `.envrc` |
| `files/.pre-commit-config.yaml` | `.pre-commit-config.yaml` |
| `files/tests-conftest.py` | `tests/conftest.py` |
| `files/ci.yml` | `.github/workflows/ci.yml` |
| `files/settings.json` | `.vscode/settings.json` |
| `files/launch.json` | `.vscode/launch.json` |
| `files/extensions.json` | `.vscode/extensions.json` |

**Rezepte:** `test`, `lint`, `typecheck`, `fix`, `clean`, `audit`, `bump`,
`check`, `run` (nur mit Entrypoint), `merge`.
`check` ruft zusätzlich `docs-check` auf, sobald eine Dokumentationsfähigkeit
(`docs.*`) vorhanden ist.

**Entwicklungsabhängigkeiten:** `basedpyright>=1.40.2`,
`bump-my-version>=1.6.7`, `pip-audit>=2.10.1`, `pre-commit>=4.7.0`,
`pytest>=9.1.1`, `pytest-cov>=7.1.0`, `ruff>=0.17.2`.

**Besonderheiten**

- `pyproject.toml` setzt Ruff (Zeilenhöhe 120, Google-Docstrings, breiter
  Regelkatalog), basedpyright im Strict-Modus, pytest mit `--strict-markers` und
  den Markern `e2e`/`agent`, Coverage mit `fail_under = 90` sowie
  `bump-my-version` (Version `0.1.0`, Tag `v{new_version}`, Hooks `uv lock` und
  `git add uv.lock`). `[project.scripts]` entsteht nur mit einem Entrypoint.
- `pyinit.toml` dokumentiert die Herkunft: Schema, pyinit-Version, Profil, Modus,
  Artefaktliste, Zeitstempel und `contract_version`.
- `.gitignore` deckt Caches, `.venv`, `site/`, `.refactor/`, `.kilo/`,
  `e2e-artifacts.*`, `agent-artifacts.*` und `ignore/` ab; `.vscode/` bleibt
  versionierbar.
- `.envrc` deaktiviert fremde Conda-Umgebungen, lädt `uv.lock` als Watch-Datei,
  löscht `UV_PROJECT_ENVIRONMENT`/`VIRTUAL_ENV` und nutzt `layout uv`. Ein
  `direnv allow` erfolgt nie automatisch.
- `tests/conftest.py` ist das Gate der opt-in-Suiten: `tests/e2e` und
  `tests/agent` werden ohne `LUPYSTA_E2E=1` bzw. `LUPYSTA_AGENT=1` gar nicht
  gesammelt.
- `.github/workflows/ci.yml` prüft bei Push/PR und manuell mit
  `uv sync --locked --dev`, `just check` und `just audit`.
- `.pre-commit-config.yaml` nutzt Standard-Hooks plus lokale Ruff-Hooks;
  basedpyright läuft bewusst im Gate und in der CI.
- VS Code deaktiviert Pylance zugunsten von basedpyright, formatiert mit Ruff und
  aktiviert pytest.
- `bump` verlangt einen sauberen Arbeitsbaum; `merge` ist ein
  Fast-Forward-Helfer ohne Push.
- Die Lizenz ist MIT mit Autor aus `git config user.name` (Fallback
  `Project Author`) und dem aktuellen Jahr.

### `base-lib`

Basis für Bibliotheken; verlangt `base-app` und wird bei Modus `lib`
automatisch injiziert.

**Dateien**

| Quelle | Ziel |
| --- | --- |
| `templates/lib-test_smoke.py.j2` | `tests/test_smoke.py` |
| `files/release.yml` | `.github/workflows/release.yml` |

**Besonderheiten**

- Der Smoke-Test vergleicht `__version__` mit der installierten
  Paket-Metadatenversion.
- `release.yml` läuft bei Tags `v*`, prüft im `check`-Job das Gate und
  veröffentlicht im `publish`-Job über PyPI Trusted Publishing (OIDC,
  Environment `pypi`). Der Tag muss exakt `v<project.version>` entsprechen.
- Es gibt kein `main.py`; der `run`-Eintrag im Justfile entfällt ohne
  Entrypoint.

### `app-main`

Einfacher Anwendungseinstieg für Modus `app`; bietet `entrypoint.app`.

**Dateien**

| Quelle | Ziel |
| --- | --- |
| `templates/main.py.j2` | `src/<paket>/main.py` |
| `templates/test_smoke.py.j2` | `tests/test_smoke.py` |

**Besonderheiten**

- `main()` gibt `Hello from <projekt>!` aus; der Smoke-Test ruft `main()` auf.
- Der Entrypoint im `pyproject.toml` zeigt auf `<paket>.main:main`, das
  Justfile erhält `run`.
- Kollidiert mit `cli` und `mcp`: alle drei liefern `src/<paket>/main.py`,
  `tests/test_smoke.py` und einen Entrypoint. `mcp` erklärt den Konflikt
  explizit. Zwischen `app-main` und `cli` ist er nicht deklariert, sondern folgt
  aus `provides`: `entrypoint.app` und `entrypoint.cli` belegen denselben
  Namensraum, den nur ein Artefakt liefern darf.

### `agent-docs`

Dokumente für die agentische Arbeit; bietet `agents.docs`.

**Dateien**

| Quelle | Ziel |
| --- | --- |
| `templates/AGENTS.md.j2` | `AGENTS.md` |
| `files/journal-README.md` | `journal/README.md` |

**Besonderheiten**

- `AGENTS.md` ist die Projektquelle: Projektprofil, Testing-Abschnitt,
  optional MCP-Hinweise, optional ADR-Konventionen (bei `adr`), optional
  Attention-Point-Gerüst (bei `ap`) und Herkunft mit `lupysta_version: 0.11.0`
  sowie `contract_version`.
- `journal/README.md` legt die Chronik-Konvention fest: ein unveränderlicher
  Eintrag pro Sitzung, Dateiname `YYYY-MM-DD-HHMM-<slug>.md` in UTC, kein
  Frontmatter.

### `adr`

ADR-Konvention; verlangt `agent-docs`, bietet `agents.adr`.

**Dateien**

| Quelle | Ziel |
| --- | --- |
| `files/README.md` | `docs/adr/README.md` |

**Besonderheiten**

- Es wird nur das Verzeichnis mit Konvention angelegt, keine ADR selbst.
- Dateinamen `NNNN-entscheidung.md`, Status im Dokument, Revisionen mit
  `_`-Präfix und unveränderter Nummer.

### `ap`

Attention-Point-Abschnitt; verlangt `agent-docs`, bietet `agents.ap`.

**Dateien:** keine eigene Datei.

**Besonderheiten**

- Das Artefakt schaltet im `AGENTS.md`-Template den Abschnitt
  `## Attention Points` samt Kommentar-Gerüst frei. Entfernte APs bleiben mit
  Nummer stehen; Nummern werden nicht neu vergeben.

### `refactor`

Design-Metriken und Refactoring-Sitzung; bietet `refactor`.

**Dateien**

| Quelle | Ziel |
| --- | --- |
| `files/design_report.py` | `scripts/design_report.py` |

**Rezepte:** `rate-design *args`, `refactor name=""`.

**Entwicklungsabhängigkeiten:** `radon>=6.0.1`, `vulture>=2.16`.

**Besonderheiten**

- `scripts/design_report.py` misst `src`/`tests` mit radon (Komplexität,
  Maintainability, Rohmetriken) und vulture (advisory) und schreibt
  `.refactor/report.json` und `.refactor/report.md`. Schema:
  `lupysta-design-report-v1`, eigener Contract-Version `1`.
- `rate-design save <name>` legt eine unveränderliche Baseline unter
  `.refactor/baselines/<name>/` an; `compare <name>` schreibt
  `.refactor/compare-<name>.md`. Regressionsmeldungen sind Befunde, keine
  Betriebsfehler; unvollständige Messungen führen zu Exitcode 1.
- `refactor` verlangt einen sauberen Baum, ruft `just check` auf, speichert eine
  Baseline und legt den Branch `refactor/<slug>` an. Es ändert keinen Code.
- `just clean` entfernt die Arbeitsdateien, behält aber `.refactor/baselines/`.

### `e2e`

Docker-E2E-Suite; bietet `suite.e2e`.

**Dateien**

| Quelle | Ziel |
| --- | --- |
| `files/README.md` | `tests/e2e/README.md` |
| `files/conftest.py` | `tests/e2e/conftest.py` |
| `files/Dockerfile` | `tests/e2e/Dockerfile` |
| `files/dockerignore` | `.dockerignore` |
| `files/test-e2e.sh` | `scripts/test-e2e.sh` (ausführbar) |
| `files/e2e.yml` | `.github/workflows/e2e.yml` |

**Rezept:** `test-e2e`.

**E2E-Abhängigkeiten:** `pytest>=9.1.1` in der Gruppe `e2e`.

**Besonderheiten**

- Das Gerüst enthält keine `test_*.py`-Datei. Die Suite sucht rekursiv; eine
  leere Suite gibt einen Hinweis aus und endet mit Exitcode 0, ohne Docker
  aufzurufen.
- `conftest.py` bricht ab, bevor Testmodule importiert werden, wenn
  `LUPYSTA_E2E=1`, `LUPYSTA_E2E_CONTAINER=1` oder `/.dockerenv` fehlen. Im
  Container werden Skips – auch Collection-Skips – zu Fehlern.
- Das `Dockerfile` installiert zuerst Abhängigkeiten
  (`uv sync --locked --no-dev --group e2e --no-install-project`) und danach das
  Projekt mit `--no-editable`. Damit prüft die Suite die Paketierung, nicht den
  kopierten Quellbaum. Sie läuft als unprivilegierter Nutzer `e2e`
  (uid 10001), schreibt JUnit-Bericht und Logs nach `/artifacts` und startet
  pytest ohne Cache-Provider.
- `scripts/test-e2e.sh` prüft Docker und Daemon erst nach der Testsucher,
  baut mit BuildKit-Cache, startet den Container mit `--network none`, kopiert
  die Artefakte nach `e2e-artifacts.*` und meldet fehlgeschlagenes Kopieren als
  Fehler statt als stillen Erfolg. Der Pfad wird am Ende ausgegeben.
- `.github/workflows/e2e.yml` läuft bei Push auf `main`, bei Pull Requests und
  manuell; der Workflow lädt Logs und JUnit-Bericht mit `if: always()` hoch und
  schließt Pytest-Tempdaten unter `work/` aus.
- `.dockerignore` hält `.git`, `.venv`, Caches, `docs`, `site`, `.refactor`,
  `ignore` und die opt-in-Artefaktordner aus dem Build-Kontext.

### `agent`

Opt-in-Provider-Suite; bietet `suite.agent`.

**Dateien**

| Quelle | Ziel |
| --- | --- |
| `files/README.md` | `tests/agent/README.md` |
| `files/conftest.py` | `tests/agent/conftest.py` |
| `files/test-agent.sh` | `scripts/test-agent.sh` (ausführbar) |

**Rezept:** `test-agent`.

**Besonderheiten**

- Das Gerüst ist ein Skelett ohne `test_*.py`, ohne Provider-Adapter und ohne
  Harness. Es enthält bewusst weder `agent.toml` noch ein Report-Schema.
- `conftest.py` verlangt `LUPYSTA_AGENT=1` und bricht sonst vor dem Import der
  Testmodule ab; im opt-in-Lauf werden Skips zu Fehlern.
- `scripts/test-agent.sh` sucht rekursiv, meldet eine leere Suite mit Exitcode 0
  und ruft sonst `LUPYSTA_AGENT=1 uv run pytest tests/agent -v -s` auf.
- Agent-Tests laufen nie in der CI und sind kein Release-Gate.

### `cli`

Typer-CLI mit generierter Referenz; Modus `app`, Konflikt mit `mcp`, bietet
`entrypoint.cli` und `docs.cli`.

**Dateien**

| Quelle | Ziel |
| --- | --- |
| `templates/cli.py.j2` | `src/<paket>/cli.py` |
| `templates/main.py.j2` | `src/<paket>/main.py` |
| `templates/test_smoke.py.j2` | `tests/test_smoke.py` |
| `templates/gen_cli_docs.py.j2` | `scripts/gen_cli_docs.py` |

**Rezepte:** `docs`, `docs-check`.

**Laufzeitabhängigkeit:** `typer>=0.27.3`.

**Besonderheiten**

- Die Typer-App heißt wie das Projekt, zeigt ohne Argumente die Hilfe und
  besitzt den Befehl `hello` mit `--name`.
- `main()` delegiert an die Typer-App; der Entrypoint zeigt auf
  `<paket>.main:main`.
- `scripts/gen_cli_docs.py` erzeugt `docs/reference/cli.md` aus der Typer-App und
  setzt einen „Do not edit“-Kopf. `just docs-check` prüft nur und ist über
  `has_docs` Teil von `just check`.
- Der Konflikt mit `mcp` folgt aus dem einen `entrypoint.*`-Slot und den
  gemeinsamen Zieldateien `main.py` und `tests/test_smoke.py`.

### `diataxis`

MkDocs-Dokumentation für Bibliotheken; Modus `lib`, bietet `docs.mkdocs`.

**Dateien**

| Quelle | Ziel |
| --- | --- |
| `templates/mkdocs.yml.j2` | `mkdocs.yml` |
| `templates/index.md.j2` | `docs/index.md` |
| `templates/api.md.j2` | `docs/api.md` |
| `files/tutorials-index.md` | `docs/tutorials/index.md` |
| `files/how-to-index.md` | `docs/how-to/index.md` |
| `files/reference-index.md` | `docs/reference/index.md` |
| `files/explanation-index.md` | `docs/explanation/index.md` |

**Rezepte:** `docs`, `docs-check`, `docs-serve`.

**Entwicklungsabhängigkeiten:** `mkdocs-material`, `mkdocstrings[python]`.

**Besonderheiten**

- `mkdocs.yml` nutzt das Material-Theme mit Navigation, `mkdocstrings` für
  Google-Docstrings und eine Diátaxis-Navigation (Tutorials, How-to, Reference,
  Explanation).
- `docs/api.md` bindet das Paket über `::: <paket>` ein.
- `docs-check` baut mit `--strict` und ist über `has_docs` Teil von
  `just check`.
- Bibliotheken erhalten keine CLI-Referenz; Apps mit `cli` erhalten kein
  MkDocs-Gerüst.

### `mcp`

MCP-Server; Modus `app`, Konflikte mit `cli` und `app-main`, bietet
`entrypoint.mcp`.

**Dateien**

| Quelle | Ziel |
| --- | --- |
| `templates/server.py.j2` | `src/<paket>/server.py` |
| `templates/main.py.j2` | `src/<paket>/main.py` |
| `templates/test_smoke.py.j2` | `tests/test_smoke.py` |

**Rezept:** `mcp-dev`.

**Laufzeitabhängigkeit:** `mcp>=2.3.0,<3`.

**Besonderheiten**

- `server.py` erzeugt einen `MCPServer` mit dem Tool `add` und der Resource
  `greeting://{name}`. `main()` startet den Server über stdio.
- `just run` startet denselben installierten Entrypoint; `just mcp-dev` öffnet
  den gepinnten Inspector `@modelcontextprotocol/inspector@2.12.0` auf
  `127.0.0.1` über `npx` und braucht Node.js. Beides ist nicht Teil von
  `just check`.
- Der Smoke-Test prüft Tool, Resource und Entrypoint über den In-Memory-`Client`
  des SDK (anyio/asyncio).
- **Selbstabhängigkeit:** Heißt das Projekt normalisiert `mcp`, versucht
  `uv lock`, das Projekt als Abhängigkeit seiner selbst aufzulösen. Der
  Preflight lehnt das ab – auch mit `--dry-run` und bei externen Profilen mit
  MCP-Artefakt. Ein abweichender Name wie `arithmetic-mcp` ist nötig; der
  Profilname bleibt `mcp` (Attention Point AP-2, ADR-0007).

## Profile

| Profil | Modus | Injizierte Basis | Artefakte | Ergebnis |
| --- | --- | --- | --- | --- |
| `app` | `app` | `base-app` | `agent-docs`, `adr`, `ap`, `app-main`, `e2e`, `agent`, `refactor` | Anwendung mit einfachem Einstieg, Smoke-Test, opt-in-Suiten, Design-Report, Agentendokumenten |
| `app-cli` | `app` | `base-app` | `agent-docs`, `adr`, `ap`, `cli`, `e2e`, `agent`, `refactor` | Wie `app`, aber mit Typer-CLI und generierter CLI-Referenz statt `app-main` |
| `lib` | `lib` | `base-lib` → `base-app` | `agent-docs`, `adr`, `ap`, `e2e`, `agent`, `refactor`, `diataxis` | Bibliothek mit MkDocs-/Diátaxis-Gerüst, Release-Workflow und Versions-Smoke-Test |
| `mcp` | `app` | `base-app` | `agent-docs`, `adr`, `ap`, `mcp`, `e2e`, `agent`, `refactor` | Anwendung mit MCP-Server, Inspector-Rezept und SDK-Smoke-Tests |

Alle Profile bringen `agent-docs`, `adr`, `ap`, `e2e`, `agent` und `refactor`
mit; sie unterscheiden sich im Einstieg (`app-main`, `cli`, `mcp`) und bei `lib`
zusätzlich durch die Dokumentationsartefakte. Externe Profile
(`--profile-file`) dürfen nur gebündelte Artefakt-IDs referenzieren.

## Laufzeitprüfung

`pyinit describe <id>` zeigt dieselben Daten zur Laufzeit: für ein Profil Modus
und Artefaktliste, für ein Artefakt Beschreibung, Modi, `requires`, `conflicts`,
`provides`, Abhängigkeiten, Dateien und Justfile-Fragmente. `pyinit list` zeigt
alle Profile, `pyinit new <profil> <dir> --dry-run` den vollständigen Dateiplan
und die geplanten Befehle.

Diese Seite wird von Hand gepflegt. Änderungen an Artefakten, Profilen oder
Fragmenten erfordern eine Anpassung hier (siehe `AGENTS.md`).
