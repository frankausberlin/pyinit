# 0009 – CLI und MCP teilen einen Entrypoint

- Status: accepted
- Datum: 2026-10-27

## Kontext

Das Profil `app-cli` liefert eine Typer-CLI, das Profil `mcp` einen
eigenständigen MCP-Server über stdio. Beide brauchen `src/<paket>/main.py`,
einen Eintrag in `[project.scripts]` und `tests/test_smoke.py`. Ein Profil
`cli-mcp`, das beides kombiniert, kann diese Ziele nicht einfach addieren: Der
Resolver lehnt doppelte Zieldateien und den zweiten `entrypoint.*`-Slot ab.
Gleichzeitig soll der MCP-Server auch weiterhin ohne CLI nutzbar bleiben.

## Entscheidung

`cli-mcp` hat genau einen installierten Projektbefehl. Er startet die
Typer-CLI; das Subkommando `mcp` startet den MCP-Server über stdio.

Dafür wird das MCP-Artefakt in zwei Bausteine geteilt:

- `mcp-server` liefert `server.py`, `tests/test_mcp.py`, die
  Laufzeitabhängigkeit `mcp>=2.3.0,<3`, das `mcp-dev`-Rezept und die Fähigkeit
  `mcp.server`. Es liefert weder `main.py` noch einen Entrypoint.
- `mcp` bleibt der eigenständige Einstieg: `main.py`, ein reiner
  Entrypoint-Smoke-Test, `entrypoint.mcp` und `requires = ["mcp-server"]`.

Das CLI-Template registriert den Befehl `mcp` nur, wenn `mcp.server` in
`capabilities` liegt. `app-cli` bleibt dadurch unverändert. `just mcp-dev`
kommt aus `mcp-server` und wählt den Startweg anhand des Entrypoints: mit
`entrypoint.mcp` `uv run <projekt>`, mit `entrypoint.cli`
`uv run <projekt> mcp`; ohne passenden Entrypoint entsteht kein Rezept.

Die generierten Tests bleiben nach Besitzer getrennt: `cli` schreibt
`tests/test_smoke.py`, `mcp-server` schreibt `tests/test_mcp.py`, `mcp` schreibt
den Entrypoint-Test in `tests/test_smoke.py` – dieser Fall tritt nur im Profil
`mcp` auf, wo `cli` nicht beteiligt ist. Damit entsteht in keinem Profil eine
Zieldatei doppelt.

## Konsequenzen

- `pyinit new cli-mcp <projekt>` erzeugt eine CLI mit `hello` und `mcp`, genau
  eine `main.py`, einen `[project.scripts]`-Eintrag und beide
  Abhängigkeitssätze.
- Im kombinierten Profil führt `just run` den Befehl `hello` aus, weil Typer
  mit zwei Befehlen keinen impliziten Einzelbefehl mehr kennt. Der
  MCP-Startweg bleibt `just mcp-dev` beziehungsweise `<projekt> mcp`.
- `mcp-server` prüft Tool, Resource und gegebenenfalls die CLI-Weiterleitung;
  den Entrypoint-Test trägt `mcp` in `tests/test_smoke.py`, damit er nicht in
  zwei Dateien gepflegt werden muss.
- Das Profil `mcp` behält sein Verhalten, verteilt seine Tests aber auf
  `tests/test_smoke.py` (Entrypoint) und `tests/test_mcp.py` (Server).
- `mcp-server` ist allein kein sinnvoller Einstieg, sondern ein Baustein für
  `cli` oder `mcp`.
- Die Selbstabhängigkeitsprüfung aus ADR-0007 gilt automatisch auch für
  `cli-mcp`, weil sie das aufgelöste Abhängigkeitsset prüft.
- Templates dürfen Fähigkeiten auswerten; der Resolver braucht dafür keine neue
  Regel, weil `mcp.server` außerhalb der Einmal-Namensräume `entrypoint.*` und
  `docs.*` liegt.
- Ein externes Profil mit `mcp-server`, aber ohne `cli` oder `mcp`, erhält kein
  `mcp-dev`-Rezept.

## Alternativen

- **`server.py` und Tests in `cli-mcp` duplizieren:** erzeugt zwei Quellen für
  denselben Server und lässt sie auseinanderlaufen.
- **Zieldateien bedingt über ein `when`-Feld im Dateimanifest ausblenden:** Der
  Resolver müsste Manifeste auswerten und Konflikte vor dem Rendern erkennen;
  die Fähigkeitsprüfung im Template reicht für diesen Fall und hält die
  Dateiziele eindeutig.
- **Zwei Entrypoints zulassen (`entrypoint.cli` und `entrypoint.mcp`):** Das
  installiert zwei Projektbefehle und widerspricht dem Ziel genau eines
  Befehls.
- **`mcp-server` direkt als Profil anbieten:** ergäbe ein Projekt ohne
  ausführbaren Einstieg.
