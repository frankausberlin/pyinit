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
from pyinit.models import Artifact, Context, FileSpec, Profile
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


@pytest.mark.parametrize("profile_id", ["app", "app-cli", "lib", "mcp"])
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
    justfile = next(item for item in files if item.target == "Justfile")
    assert 'merge branch=""' in justfile.content
    assert "{{branch}}" in justfile.content
    pyproject = next(item for item in files if item.target == "pyproject.toml")
    if profile_id == "lib":
        assert "[project.scripts]" not in pyproject.content
        assert "run" not in recipe_names(justfile.content)
    else:
        assert "[project.scripts]" in pyproject.content
        assert "run" in recipe_names(justfile.content)


@pytest.mark.parametrize("profile_id", ["app", "app-cli", "mcp"])
def test_entrypoint_key_is_quoted_for_dotted_names(profile_id: str, tmp_path: Path) -> None:
    """A dotted project name stays a single command key in TOML."""
    catalog = load_catalog()
    profile = catalog.profile(profile_id)
    context = context_for(profile, tmp_path / "my.project")
    files = render_files(resolve(profile, catalog), context)
    pyproject = next(item for item in files if item.target == "pyproject.toml")
    scripts = tomllib.loads(pyproject.content)["project"]["scripts"]
    assert scripts == {"my.project": "my_project.main:main"}


@pytest.mark.parametrize("profile_id", ["app", "app-cli", "mcp"])
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
    assert "Client(mcp, raise_exceptions=True)" in by_target["tests/test_smoke.py"]
    assert "mcp-dev" in recipe_names(by_target["Justfile"])
    assert "HOST=127.0.0.1 npx @modelcontextprotocol/inspector@2.12.0" in by_target["Justfile"]
    assert "mcp run src/demo/server.py" in by_target["Justfile"]
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
        "mcp[cli]>=2.3.0,<3",
        "radon>=6.0.1",
        "vulture>=2.16",
    ]
    assert data["project"]["scripts"] == {"demo": "demo.main:main"}


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
