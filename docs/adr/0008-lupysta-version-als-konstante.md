# ADR-0001: Die lupysta-Version ist eine Konstante im Generator

- Status: accepted
- Datum: 2026-10-27

## Kontext

Erzeugte Projekte dokumentieren ihre Herkunft in `AGENTS.md`
(`lupysta_version`, `contract_version`) und in `pyinit.toml`. Der Wert für
`lupysta_version` stand bis hierher als Literal `0.11.0` im Template
`agent-docs/templates/AGENTS.md.j2`, während die Skill-Datei in ludesta bereits
`0.12.0` war. Der Fehler war damit in jedem neu erzeugten Projekt eingebaut,
ohne dass ein Test oder eine Prüfung ihn bemerkt hätte.

Der Skill und seine Version liegen in einem anderen Repository
(`ludesta`), der Generator in `pyinit`. Es gibt keine gemeinsame
Abhängigkeit, keinen Submodule-Link und keine gemeinsame CI.

## Entscheidung

`src/pyinit/models.py` hält `LUPYSTA_VERSION` als einzige Quelle. Der Kontext
reicht den Wert als `lupysta_version` an alle Templates weiter; das
`AGENTS.md`-Template rendert `{{ lupysta_version }}`. Literale
Versionsnummern in Templates sind unzulässig und werden durch einen Test
abgedeckt.

Der Abgleich mit dem Feld `version:` in
`ludesta/Luxus-Python-Stack/lupysta/SKILL.md` bleibt ein manueller Schritt und
ist in `AGENTS.md` dokumentiert. Ein automatischer Abgleich über die
Repo-Grenze findet nicht statt.

## Konsequenzen

- Innerhalb von `pyinit` kann die Version nicht mehr auseinanderlaufen: eine
  Stelle, ein Test, ein Renderpfad für alle Profile.
- Die Repo-Grenze bleibt eine mögliche Drift-Quelle. Sie ist bewusst
  akzeptiert und wird durch die Dokumentation und den Attention Point
  „Herkunft ist nicht selbstaktualisierend“ abgefedert.
- Der Fehler, der diese ADR ausgelöst hat (Literal im Template), ist durch
  `tests/test_render.py` dauerhaft ausgeschlossen.

## Alternativen

- **CI-Vergleich über die Repo-Grenze** (ludesta-CI klont pyinit oder
  umgekehrt): findet Drift automatisch, koppelt aber zwei Repositories über
  Netzwerk und Fremdzustand. Ein fehlgeschlagener Clone würde das Gate
  blockieren, obwohl die Änderung nichts damit zu tun hat.
- **Gemeinsames Paket** (`lupysta` als installierbare Abhängigkeit von
  `pyinit`): technisch sauber, aber der Skill ist für Harnesses gedacht
  (Markdown + Symlink), nicht als Bibliothek. Das würde die Installation des
  Stacks umbauen.
- **Submodule**: koppelt die Historie und macht `pyinit` ohne ludesta nicht
  mehr installierbar – der Generator ist bewusst eigenständig.
- **Wert zur Laufzeit aus einer installierten Skill-Kopie lesen**: funktioniert
  nur, wenn der Skill lokal vorhanden ist. `pyinit` muss aber auf einem
  frischen Rechner ohne ludesta lauffähig bleiben.
