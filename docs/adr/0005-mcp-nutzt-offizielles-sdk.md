# 0005 – MCP nutzt das offizielle SDK über stdio

- Status: accepted
- Datum: 2026-10-26

## Kontext

Das Profil `mcp` erzeugt einen MCP-Server als Teil einer Anwendung. Zur Wahl
standen das offizielle `mcp`-SDK und das eigenständige `fastmcp`-Framework.
Außerdem musste entschieden werden, wie der Server lokal gestartet und geprüft
wird, ohne die hermetische Qualitätsprüfung von Node.js abhängig zu machen.

## Entscheidung

Der Generator verwendet `mcp[cli]` 2.x mit `MCPServer` und `Client`. Der Server
läuft über stdio und nutzt den bestehenden Entrypoint `main:main`; `just run`
startet ihn. Die Runtime-Abhängigkeit ist `mcp`, die Entwicklung braucht
zusätzlich `mcp[cli]`. Der Inspector läuft über `just mcp-dev` mit einer
gepinnten npm-Version von `@modelcontextprotocol/inspector` und bindet nur an
Loopback; Node.js bleibt eine dokumentierte manuelle Voraussetzung und ist nicht
Teil von `just check`. Streamable HTTP, Auth und Deployment sind nicht Teil des
Starters.

## Konsequenzen

- Das Profil bleibt nah am offiziellen Protokoll und erhält SDK-Verbesserungen
  direkt.
- Der In-Memory-`Client` macht Tool, Resource und Entrypoint ohne Subprozess
  testbar.
- Zwei Dependency-Gruppen werden von uv zu einer Auflösung mit `cli`-Extra
  vereinigt.
- Ohne Node.js schlägt nur `just mcp-dev` fehl, nicht das Qualitätsgate.
- Das SDK bleibt auf `<3` begrenzt, um API-Brüche zu vermeiden.

## Alternativen

- **`fastmcp`:** eigenständige Entwicklung, aber zusätzliche Abhängigkeit und
  ein vom offiziellen SDK abweichender Pfad.
- **Streamable HTTP als Standard:** mehr Betriebsaufwand und Auth-Fragen, die
  der Starter nicht beantworten soll.
