# pyinit

Data-driven generator for new Python projects from the Luxus-Python-Stack.

## Usage

```bash
uv run pyinit list                                  # show bundled profiles
uv run pyinit describe app-cli                      # show a profile or artifact
uv run pyinit new app-cli my-project                # generate an application
uv run pyinit new lib my-lib --python 3.13          # library with MkDocs
uv run pyinit new mcp arithmetic-mcp                # app with an MCP server
uv run pyinit new cli-mcp arithmetic-tool           # CLI with an `mcp` subcommand
uv run pyinit new app . --dry-run                   # print the plan, write nothing
```

Available profiles are `app`, `app-cli`, `cli-mcp`, `lib`, and `mcp`.
Generation writes only new projects; it never updates or merges into an
existing project. A target must be missing, empty, or contain only `.git`. Use
`--no-check` to skip the final `just check`, and `--profile-file` to load an
external profile (artifacts stay bundled).

## Getting Started

```bash
uv sync
just check
```

## Development

```bash
just test        # run tests
just lint        # lint + type check
just fix         # auto-fix lint issues
just clean       # remove caches and generated artifacts
just rate-design run             # design metrics → .refactor/
just rate-design save <name>     # save an immutable baseline
just rate-design compare <name>  # compare the current run with a baseline
just refactor                    # prepare a refactoring session
just merge       # fast-forward main to a branch from any checkout (no push)
just check       # full quality gate (unit/smoke tests only)
just test-e2e    # Docker E2E suite locally (hint + exit 0 until tests exist)
just test-agent  # provider suite manually (hint + exit 0 until tests exist)
just test-generated  # generate every profile and run its quality gate
```

`just check` runs unit and smoke tests only. The E2E suite is not part of the
gate: run it locally with `just test-e2e`; CI runs it automatically once test
files exist. Agent tests are manual-only and never run in CI.

`just test-generated` needs network access and the real `uv`/`just` toolchain.
It generates `app`, `app-cli`, `cli-mcp`, `lib`, and `mcp` under
`generated-artifacts.*` and runs `just check` inside each project. The hermetic
Docker suite never runs it: it checks plans and fake-toolchain applies instead.

## Documentation

```bash
just docs         # regenerate docs/reference/cli.md
just docs-check   # verify the generated CLI reference is current
```

The hand-maintained overview of every artifact and profile is
[docs/artefakte.md](docs/artefakte.md). It mirrors the bundled TOML data; run
`pyinit describe <id>` to see the same facts at runtime.

## Release

```bash
just bump patch   # 0.1.0 → 0.1.1
git push origin main --tags
```

See [AGENTS.md](AGENTS.md) for AI agent guidelines.

Möge aus jedem kleinen Anfang etwas Großes wachsen.
