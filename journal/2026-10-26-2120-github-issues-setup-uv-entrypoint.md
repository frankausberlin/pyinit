## 2026-10-26 — GitHub-Issues zu setup-uv und Entrypoint behoben

* **Stand**: `astral-sh/setup-uv@v10` existiert upstream nicht; der letzte
  stabile Major-Alias ist v7, die aktuelle Version ist v10.3.2. Beide Befunde
  der Issues #1 und #2 waren reproduzierbar und sind behoben.
* **Änderungen**: Repo-Workflows und Artefakt-Workflows pinnen
  `astral-sh/setup-uv@v10.3.2`. Der Entrypoint-Schlüssel in
  `[project.scripts]` wird als TOML-String gequotet, damit Namen mit Punkt
  nicht als verschachtelte Tabelle geparst werden. Rendering-Regressionstests
  decken `app` und `app-cli` mit `my.project` sowie unveränderte einfache
  Namen ab. Zusätzlich mit echter Toolchain generiert und der Kommando-
  Entrypoint `my.project` erfolgreich ausgeführt.
* **ADRs**: keine
* **Attention Points**: keine
* **Offen**: Issues #1 und #2 sind lokal behoben, aber noch nicht gepusht oder
  geschlossen.
