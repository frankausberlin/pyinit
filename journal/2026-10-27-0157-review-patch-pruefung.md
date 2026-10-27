## 2026-10-27 — Review-Patch geprüft und E2E-Korrektur übernommen

* **Stand**: Der parametrische Docker-E2E-Dry-Run nutzt für das Profil `mcp`
  den Projektnamen `mcp-project`. Der Name `mcp` kollidiert mit der
  gleichnamigen Abhängigkeit und wird laut ADR-0007 schon im Preflight
  abgelehnt, auch bei `--dry-run`; der reguläre Erfolgsfall scheiterte damit.
  Die Profilabdeckung bleibt erhalten.
* **Änderungen**: In `tests/e2e/test_generator.py` wählt der Test für `mcp`
  den Projektnamen `mcp-project`. Der Patch-Hunk zu einer ADR-0008 wurde
  zunächst verworfen, weil diese ADR im damaligen lokalen Stand nicht
  existierte; der spätere Pull brachte sie mit `538aa8e`. Der Hunk bleibt
  gegenstandslos, weil die ADR dort bereits korrekt benannt ist.
* **ADRs**: keine neuen; ADR-0007 beschreibt die Namensregel bereits,
  ADR-0008 kam mit `538aa8e` hinzu.
* **Attention Points**: keine; AP-2 gilt unverändert.
* **Offen**: `just` ist nicht installiert und `uv` liegt unter
  `~/.local/bin` außerhalb des PATH der Agent-Shell; das vollständige
  `just check` lief daher nicht. Ruff und die Host-Unit-Tests wurden über die
  vorhandene `.venv` ausgeführt, die Hooks mit ergänztem PATH. `just test-e2e`
  wurde nicht auf dem Host ausgeführt.
