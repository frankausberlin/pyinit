"""Tests for rendering and file composition."""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

import pytest
from jinja2 import Environment

import pyinit.render as render_module
from pyinit.context import FixedClock, build_context
from pyinit.discovery import Catalog, load_catalog
from pyinit.errors import DuplicateRecipeError, DuplicateTargetError, PathTraversalError, RenderError
from pyinit.models import CONTRACT_VERSION, LUPYSTA_VERSION, Artifact, Context, FileSpec, Profile
from pyinit.render import (
    artifact_source_exists,
    build_environment,
    package_data_root,
    recipe_names,
    render_files,
    render_target,
)
from pyinit.resolver import resolve

CLOCK = FixedClock(datetime(2026, 10, 26, 20, 0, tzinfo=UTC))


def context_for(profile: Profile, target: Path) -> Context:
    """Build a deterministic context."""
    return build_context(
        profile=profile,
        target=target,
        python_version="3.12",
        author_name="Tester",
        clock=CLOCK,
    )


@pytest.mark.parametrize("profile_id", ["app", "app-cli", "cli-mcp", "lib", "mcp"])
def test_render_all_profiles(profile_id: str, tmp_path: Path) -> None:
    """Test."""
    catalog = load_catalog()
    profile = catalog.profile(profile_id)
    resolution = resolve(profile, catalog)
    context = context_for(profile, tmp_path / "demo")
    files = render_files(resolution, context)
    targets = {item.target for item in files}
    assert "pyproject.toml" in targets
    assert "Justfile" in targets
    assert "pyinit.toml" in targets
    assert "src/demo/__init__.py" in targets
    assert "tests/test_smoke.py" in targets
    assert len(targets) == len(files)
    for item in files:
        if item.target.endswith(".py"):
            assert item.content.endswith("\n")
            assert not item.content.endswith("\n\n")
    justfile = next(item for item in files if item.target == "Justfile")
    assert 'merge branch=""' in justfile.content
    assert 'bash scripts/merge.sh "{{branch}}" "{{target}}"' in justfile.content
    merge_script = next(item for item in files if item.target == "scripts/merge.sh")
    assert merge_script.executable
    assert merge_script.content.startswith("#!/usr/bin/env bash\n")
    pyproject = next(item for item in files if item.target == "pyproject.toml")
    if profile_id == "lib":
        assert "[project.scripts]" not in pyproject.content
        assert "run" not in recipe_names(justfile.content)
    else:
        assert "[project.scripts]" in pyproject.content
        assert "run" in recipe_names(justfile.content)


@pytest.mark.parametrize("profile_id", ["app", "app-cli", "cli-mcp", "mcp"])
def test_entrypoint_key_is_quoted_for_dotted_names(profile_id: str, tmp_path: Path) -> None:
    """A dotted project name stays a single command key in TOML."""
    catalog = load_catalog()
    profile = catalog.profile(profile_id)
    context = context_for(profile, tmp_path / "my.project")
    files = render_files(resolve(profile, catalog), context)
    pyproject = next(item for item in files if item.target == "pyproject.toml")
    scripts = tomllib.loads(pyproject.content)["project"]["scripts"]
    assert scripts == {"my.project": "my_project.main:main"}


@pytest.mark.parametrize("profile_id", ["app", "app-cli", "cli-mcp", "mcp"])
def test_entrypoint_key_is_unchanged_for_plain_names(profile_id: str, tmp_path: Path) -> None:
    """Names without a dot produce the same command key as before."""
    catalog = load_catalog()
    profile = catalog.profile(profile_id)
    context = context_for(profile, tmp_path / "demo")
    files = render_files(resolve(profile, catalog), context)
    pyproject = next(item for item in files if item.target == "pyproject.toml")
    scripts = tomllib.loads(pyproject.content)["project"]["scripts"]
    assert scripts == {"demo": "demo.main:main"}


def test_mcp_profile_renders_server_entrypoint_and_recipe(tmp_path: Path) -> None:
    """The MCP profile ships a server, stdio entry point, and Inspector recipe."""
    catalog = load_catalog()
    profile = catalog.profile("mcp")
    files = render_files(resolve(profile, catalog), context_for(profile, tmp_path / "demo"))
    by_target = {item.target: item.content for item in files}
    assert 'mcp = MCPServer("demo")' in by_target["src/demo/server.py"]
    assert "mcp.run()" in by_target["src/demo/main.py"]
    assert "from demo.server import mcp" in by_target["src/demo/main.py"]
    assert "Client(mcp, raise_exceptions=True)" in by_target["tests/test_mcp.py"]
    assert "def test_entry_point_starts_server" not in by_target["tests/test_mcp.py"]
    assert "main_module.main()" in by_target["tests/test_smoke.py"]
    assert "mcp-dev" in recipe_names(by_target["Justfile"])
    assert "HOST=127.0.0.1 npx @modelcontextprotocol/inspector@2.12.0 uv run demo" in by_target["Justfile"]
    assert "mcp run src/demo/server.py" not in by_target["Justfile"]
    assert "## MCP Server" in by_target["README.md"]
    assert "just mcp-dev" in by_target["README.md"]
    assert "App (MCP-Server)" in by_target["AGENTS.md"]
    data = tomllib.loads(by_target["pyproject.toml"])
    assert data["project"]["dependencies"] == ["mcp>=2.3.0,<3"]
    assert data["dependency-groups"]["dev"] == [
        "basedpyright>=1.40.2",
        "bump-my-version>=1.6.7",
        "pip-audit>=2.10.1",
        "pre-commit>=4.7.0",
        "pytest>=9.1.1",
        "pytest-cov>=7.1.0",
        "ruff>=0.17.2",
        "radon>=6.0.1",
        "vulture>=2.16",
    ]
    assert data["project"]["scripts"] == {"demo": "demo.main:main"}


def test_app_cli_smoke_keeps_typer_single_command_form(tmp_path: Path) -> None:
    """The CLI-only profile keeps Typer's implicit single-command arguments."""
    catalog = load_catalog()
    profile = catalog.profile("app-cli")
    files = render_files(resolve(profile, catalog), context_for(profile, tmp_path / "demo"))
    smoke = next(item.content for item in files if item.target == "tests/test_smoke.py")
    assert 'runner.invoke(app, ["--name", "tester"])' in smoke
    assert 'runner.invoke(app, ["hello", "--name", "tester"])' not in smoke


def test_cli_mcp_profile_shares_one_entrypoint_and_render_targets(tmp_path: Path) -> None:
    """The combined profile renders one entry point, one CLI, and one server."""
    catalog = load_catalog()
    profile = catalog.profile("cli-mcp")
    files = render_files(resolve(profile, catalog), context_for(profile, tmp_path / "lion"))
    targets = [item.target for item in files]
    by_target = {item.target: item.content for item in files}
    assert targets.count("src/lion/main.py") == 1
    assert targets.count("tests/test_smoke.py") == 1
    assert targets.count("tests/test_mcp.py") == 1
    assert "from lion import server" in by_target["src/lion/cli.py"]
    assert '@app.command(name="mcp")' in by_target["src/lion/cli.py"]
    assert "server.mcp.run()" in by_target["src/lion/cli.py"]
    assert "    from lion import server" in by_target["src/lion/cli.py"]
    assert 'runner.invoke(app, ["mcp"])' in by_target["tests/test_mcp.py"]
    assert 'runner.invoke(app, ["hello", "--name", "tester"])' in by_target["tests/test_smoke.py"]
    assert "calls == []" in by_target["tests/test_smoke.py"]
    assert "App (CLI mit MCP-Server)" in by_target["AGENTS.md"]
    assert "just run         # run the hello command" in by_target["README.md"]
    assert "uv run lion mcp" in by_target["Justfile"]
    assert "uv run lion hello" in by_target["Justfile"]
    data = tomllib.loads(by_target["pyproject.toml"])
    assert data["project"]["dependencies"] == ["typer>=0.27.3", "mcp>=2.3.0,<3"]
    assert data["project"]["scripts"] == {"lion": "lion.main:main"}


@pytest.mark.parametrize(
    "artifacts",
    [
        ["agent-docs", "mcp-server"],
        ["agent-docs", "app-main", "mcp-server"],
    ],
)
def test_external_mcp_server_without_entrypoint_has_no_mcp_start_path(
    artifacts: list[str],
    tmp_path: Path,
) -> None:
    """A module-only MCP artifact renders clean tests and honest documentation."""
    profile_file = tmp_path / "external.toml"
    rendered_artifacts = ", ".join(f'"{item}"' for item in artifacts)
    profile_file.write_text(
        f'id = "external"\nmode = "app"\nartifacts = [{rendered_artifacts}]\n',
        encoding="utf-8",
    )
    catalog = load_catalog(profile_file)
    profile = catalog.profile("external")
    files = render_files(resolve(profile, catalog), context_for(profile, tmp_path / "demo"))
    by_target = {item.target: item.content for item in files}
    for item in files:
        if item.target.endswith(".py"):
            assert item.content.endswith("\n")
            assert not item.content.endswith("\n\n")
    assert "TextResourceContents\n\nfrom demo.server import mcp" in by_target["tests/test_mcp.py"]
    assert "mcp-dev" not in recipe_names(by_target["Justfile"])
    assert "just mcp-dev" not in by_target["README.md"]
    assert "provides no `mcp-dev` recipe" in by_target["README.md"]
    assert "tests/test_smoke.py prüft den stdio-Entrypoint" not in by_target["AGENTS.md"]
    assert "MCP-Entrypoint" in by_target["AGENTS.md"]


@pytest.mark.parametrize("profile_id", ["app", "app-cli", "cli-mcp", "lib", "mcp"])
def test_provenance_records_the_bundled_skill_version(profile_id: str, tmp_path: Path) -> None:
    """The herkunft section renders the single-source version, not a literal."""
    catalog = load_catalog()
    profile = catalog.profile(profile_id)
    files = render_files(resolve(profile, catalog), context_for(profile, tmp_path / "demo"))
    agents = next(item.content for item in files if item.target == "AGENTS.md")
    assert f"- lupysta_version: `{LUPYSTA_VERSION}`" in agents
    assert f"- contract_version: `{CONTRACT_VERSION}`" in agents


def test_profile_without_entrypoint_omits_scripts_and_run(tmp_path: Path) -> None:
    """An app profile without an entrypoint artifact gets no command or run recipe."""
    data = _catalog_with()
    profile = data.profile("test")
    files = render_files(resolve(profile, data), context_for(profile, tmp_path / "demo"))
    by_target = {item.target: item for item in files}
    assert "[project.scripts]" not in by_target["pyproject.toml"].content
    assert "run" not in recipe_names(by_target["Justfile"].content)


def test_author_name_is_escaped_in_pyproject(tmp_path: Path) -> None:
    """Quotes and backslashes in the author name produce valid TOML."""
    catalog = load_catalog()
    profile = catalog.profile("app")
    author = 'Zoe "Zed" \\ Backslash'
    context = build_context(
        profile=profile,
        target=tmp_path / "demo",
        python_version="3.12",
        author_name=author,
        clock=CLOCK,
    )
    files = render_files(resolve(profile, catalog), context)
    pyproject = next(item for item in files if item.target == "pyproject.toml")
    data = tomllib.loads(pyproject.content)
    assert data["project"]["authors"] == [{"name": author}]


def test_static_files_and_executables(tmp_path: Path) -> None:
    """Test."""
    catalog = load_catalog()
    profile = catalog.profile("app")
    context = context_for(profile, tmp_path / "demo")
    files = render_files(resolve(profile, catalog), context)
    scripts = {item.target: item for item in files}
    assert scripts["scripts/test-e2e.sh"].executable is True
    assert scripts["scripts/test-agent.sh"].executable is True
    assert "LUPYSTA_E2E" in scripts["scripts/test-e2e.sh"].content
    assert scripts[".vscode/settings.json"].content.lstrip().startswith("{")
    assert "{{" not in scripts["pyproject.toml"].content


def _catalog_with(*artifacts: Artifact) -> Catalog:
    base = load_catalog().artifacts["base-app"]
    items = {base.id: base, **{item.id: item for item in artifacts}}
    profile = Profile(id="test", description="", mode="app", artifacts=tuple(item.id for item in artifacts))
    return Catalog(profiles={"test": profile}, artifacts=items)


def test_duplicate_target(tmp_path: Path) -> None:
    """Test."""
    duplicate = Artifact(
        id="duplicate",
        description="",
        files=(FileSpec(source="files/ci.yml", target="README.md", render=False),),
    )
    data = _catalog_with(duplicate)
    resolution = resolve(data.profile("test"), data)
    with pytest.raises(DuplicateTargetError, match=r"README\.md"):
        render_files(resolution, context_for(data.profile("test"), tmp_path / "demo"))


def test_path_traversal_and_undefined_target(tmp_path: Path) -> None:
    """Test."""
    environment = build_environment()
    context = context_for(Profile("x", "", "app", ()), tmp_path / "demo")
    variables = context.as_mapping()
    for target in ("../escape", "/absolute", "a/../b", "a/./b", "C:/x", "a\\b", ""):
        with pytest.raises(PathTraversalError):
            render_target(target, variables, environment)
    with pytest.raises(RenderError, match="cannot render target"):
        render_target("{{ missing }}", variables, environment)


def test_missing_template(tmp_path: Path) -> None:
    """Test."""
    broken = Artifact(id="broken", description="", files=(FileSpec(source="templates/missing.j2", target="x"),))
    data = _catalog_with(broken)
    with pytest.raises(RenderError, match="cannot load template"):
        render_files(resolve(data.profile("test"), data), context_for(data.profile("test"), tmp_path / "demo"))


def test_missing_static_file(tmp_path: Path) -> None:
    """Test."""
    broken = Artifact(
        id="broken",
        description="",
        files=(FileSpec(source="files/missing", target="x", render=False),),
    )
    data = _catalog_with(broken)
    with pytest.raises(RenderError, match="cannot read static file"):
        render_files(resolve(data.profile("test"), data), context_for(data.profile("test"), tmp_path / "demo"))


def test_recipe_names() -> None:
    """Test."""
    text = """
set shell := ["bash", "-uc"]
# comment
test:
    echo hi
lint x="1":
    echo hi
not-a-recipe := 1
"""
    assert recipe_names(text) == {"test", "lint"}


def test_duplicate_recipe(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test."""
    duplicate = Artifact(id="dup", description="", just_fragments=("templates/dup.j2",))
    data = _catalog_with(duplicate)
    resolution = resolve(data.profile("test"), data)

    def fake_render(
        artifact_id: str,
        source: str,
        variables: Mapping[str, object],
        environment: Environment,
    ) -> str:
        del artifact_id, source, variables, environment
        return "test:\n    true\n"

    monkeypatch.setattr(render_module, "_render_file", fake_render)
    with pytest.raises(DuplicateRecipeError, match="test"):
        render_files(resolution, context_for(data.profile("test"), tmp_path / "demo"))


def test_packaging_helpers() -> None:
    """Test."""
    assert artifact_source_exists("base-app", "files/ci.yml")
    assert not artifact_source_exists("base-app", "../nope")
    assert not artifact_source_exists("base-app", "files/missing")
    assert package_data_root().joinpath("profiles", "app.toml").is_file()
