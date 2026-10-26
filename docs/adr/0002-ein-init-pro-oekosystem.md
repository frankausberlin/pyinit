# 0002 – Ein Init pro Ökosystem

- Status: accepted
- Datum: 2026-10-26

## Kontext

Ein sprachagnostischer Generator mit Plugins verspricht Wiederverwendung, kostet
aber eine Abstraktion, die die Eigenheiten von Python-Tooling (uv, ruff,
basedpyright, pytest, Justfile) verwischt. Der Luxus-Python-Stack ist bewusst
Python-spezifisch.

## Entscheidung

`pyinit` bleibt ein Python-Initialisierer. Es gibt keinen sprachagnostischen
Kern und keine Plugin-Runtime. Weitere Ökosysteme bekommen bei Bedarf eigene
Generatoren.

## Konsequenzen

- Profile, Artefakte und Kontext bleiben auf Python zugeschnitten.
- Die Engine bleibt klein und kann direkt auf Python-Tooling reagieren.
- Gemeinsame Logik mit anderen Sprachen wird nicht angestrebt.
