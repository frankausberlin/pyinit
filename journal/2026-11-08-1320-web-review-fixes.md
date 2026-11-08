## 2026-11-08 — Review-Fixes am `web`-Profil

* **Stand**: `create_app()` löst seine Settings über `Settings.from_env()` auf,
  damit `WEB_APP_NAME` auch im von uvicorn importierten Modul greift. Der
  Action-Test prüft den `303`-Status und den `Location`-Header, statt dem
  Redirect zu folgen; der Smoke-Test deckt die Env-Auflösung der App-Fabrik ab.
* **Änderungen**: `web/templates/app.py.j2`, `test_actions.py.j2` und
  `test_smoke.py.j2`.
* **Review**: `just check` im pyinit-Repository ist grün (178 Tests). Das neu
  erzeugte `web`-Projekt besteht `just check` mit 10 Tests und 100 % Coverage.
* **Offen**: Keine neuen Follow-ups; die übrigen Review-Hinweise waren
  Duplikate oder bewusst gewählte Defaults.
