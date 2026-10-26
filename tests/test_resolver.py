"""Tests for artifact graph resolution."""

from __future__ import annotations

import pytest

from pyinit.discovery import Catalog, load_catalog
from pyinit.errors import (
    ArtifactNotFoundError,
    ConflictError,
    CycleError,
    DependencyConflictError,
    ModeConflictError,
    ProvideConflictError,
    SelfDependencyError,
)
from pyinit.models import Artifact, Profile
from pyinit.resolver import resolve, validate_project_dependencies


def artifact(identifier: str, **values: object) -> Artifact:
    """Build an artifact with test defaults."""
    return Artifact(id=identifier, description=identifier, **values)  # type: ignore[arg-type]


def catalog(*artifacts: Artifact, mode: str = "app") -> Catalog:
    """Build a catalog with both base artifacts and the given artifacts."""
    base = artifact("base-app")
    library = artifact("base-lib")
    items = {item.id: item for item in (base, library, *artifacts)}
    profile = Profile(id="test", description="", mode=mode, artifacts=tuple(item.id for item in artifacts))
    return Catalog(profiles={"test": profile}, artifacts=items)


def test_injects_base_and_orders_requirements() -> None:
    """Test."""
    first = artifact("first")
    second = artifact("second", requires=("first",))
    result = resolve(catalog(first, second).profiles["test"], catalog(first, second))
    assert [item.id for item in result.artifacts] == ["base-app", "first", "second"]


def test_library_base_and_mode_check() -> None:
    """Test."""
    library = artifact("library", modes=("lib",))
    data = catalog(library, mode="lib")
    result = resolve(data.profiles["test"], data)
    assert [item.id for item in result.artifacts] == ["base-lib", "library"]

    app = artifact("app-only", modes=("app",))
    data = catalog(app, mode="lib")
    with pytest.raises(ModeConflictError):
        resolve(data.profiles["test"], data)


def test_conflict_symmetric() -> None:
    """Test."""
    first = artifact("first", conflicts=("second",))
    second = artifact("second")
    data = catalog(first, second)
    with pytest.raises(ConflictError, match=r"first.*second"):
        resolve(data.profiles["test"], data)


def test_provide_conflict_and_namespace() -> None:
    """Test."""
    first = artifact("first", provides=("entrypoint.one",))
    second = artifact("second", provides=("entrypoint.two",))
    data = catalog(first, second)
    with pytest.raises(ProvideConflictError, match="entrypoint"):
        resolve(data.profiles["test"], data)

    third = artifact("third", provides=("agents.one",))
    fourth = artifact("fourth", provides=("agents.one",))
    data = catalog(third, fourth)
    with pytest.raises(ProvideConflictError, match="provided by both"):
        resolve(data.profiles["test"], data)


def test_cycle_and_unknown_requirement() -> None:
    """Test."""
    first = artifact("first", requires=("second",))
    second = artifact("second", requires=("first",))
    data = catalog(first, second)
    with pytest.raises(CycleError, match=r"first -> second -> first"):
        resolve(data.profiles["test"], data)

    broken = artifact("broken", requires=("missing",))
    data = catalog(broken)
    with pytest.raises(ArtifactNotFoundError, match="required by broken"):
        resolve(data.profiles["test"], data)


def test_dependency_union() -> None:
    """Test."""
    first = artifact("first", runtime_dependencies=("One>=1", "shared>=1"))
    second = artifact("second", runtime_dependencies=("two", "shared>=1"), dev_dependencies=("ruff",))
    data = catalog(first, second)
    result = resolve(data.profiles["test"], data)
    assert result.runtime_dependencies == ("One>=1", "shared>=1", "two")
    assert result.dev_dependencies == ("ruff",)
    assert result.capabilities == frozenset()
    assert result.needs_docs is False


def test_dependency_conflict() -> None:
    """Test."""
    first = artifact("first", runtime_dependencies=("shared>=1",))
    second = artifact("second", runtime_dependencies=("Shared>=2",))
    data = catalog(first, second)
    with pytest.raises(DependencyConflictError, match="conflicting constraints"):
        resolve(data.profiles["test"], data)


def test_dependencies_deduplicate_same_normalized_name() -> None:
    """Test."""
    first = artifact("first", runtime_dependencies=("zope.interface>=1",))
    second = artifact("second", runtime_dependencies=("zope-interface>=1",))
    data = catalog(first, second)
    result = resolve(data.profiles["test"], data)
    assert result.runtime_dependencies == ("zope.interface>=1",)


def test_dependencies_deduplicate_normalized_extras() -> None:
    """Test."""
    first = artifact("first", runtime_dependencies=("pkg[security,socks]>=1",))
    second = artifact("second", runtime_dependencies=("Pkg[ Socks , security ] >= 1",))
    data = catalog(first, second)
    result = resolve(data.profiles["test"], data)
    assert result.runtime_dependencies == ("pkg[security,socks]>=1",)


def test_dependencies_deduplicate_normalized_specifier() -> None:
    """Test."""
    first = artifact("first", runtime_dependencies=("pkg >= 1, < 2",))
    second = artifact("second", runtime_dependencies=("pkg<2,>=1",))
    data = catalog(first, second)
    result = resolve(data.profiles["test"], data)
    assert result.runtime_dependencies == ("pkg >= 1, < 2",)


def test_dependencies_conflict_on_different_canonical_requirement() -> None:
    """Test."""
    first = artifact("first", runtime_dependencies=("pkg[a]>=1",))
    second = artifact("second", runtime_dependencies=("pkg[b]>=1",))
    data = catalog(first, second)
    with pytest.raises(DependencyConflictError, match="conflicting constraints for 'pkg'"):
        resolve(data.profiles["test"], data)


def test_just_fragments_follow_resolution_order() -> None:
    """Test."""
    first = artifact("first", just_fragments=("templates/a.j2",))
    second = artifact("second", requires=("first",), just_fragments=("templates/b.j2",))
    data = catalog(second, first)
    result = resolve(data.profiles["test"], data)
    assert result.just_fragments == (("first", "templates/a.j2"), ("second", "templates/b.j2"))


def test_docs_capability() -> None:
    """Test."""
    docs = artifact("docs", provides=("docs.cli",))
    data = catalog(docs)
    result = resolve(data.profiles["test"], data)
    assert result.needs_docs is True
    assert result.capabilities == frozenset({"docs.cli"})


@pytest.mark.parametrize("conflicting", ["cli", "app-main"])
def test_mcp_conflicts_with_other_entrypoints(conflicting: str) -> None:
    """The MCP artifact cannot be combined with another entry point artifact."""
    data = load_catalog()
    profile = Profile(id="test", description="", mode="app", artifacts=("mcp", conflicting))
    with pytest.raises(ConflictError, match=conflicting):
        resolve(profile, data)


def test_mcp_profile_resolves_entrypoint_capability() -> None:
    """The bundled MCP profile provides exactly one MCP entry point."""
    data = load_catalog()
    resolution = resolve(data.profile("mcp"), data)
    assert [item.id for item in resolution.artifacts] == [
        "base-app",
        "agent-docs",
        "adr",
        "ap",
        "mcp",
        "e2e",
        "agent",
        "refactor",
    ]
    assert {capability for capability in resolution.capabilities if capability.startswith("entrypoint.")} == {
        "entrypoint.mcp"
    }
    assert resolution.runtime_dependencies == ("mcp>=2.3.0,<3",)
    assert "mcp[cli]>=2.3.0,<3" not in resolution.dev_dependencies


@pytest.mark.parametrize("name", ["mcp", "MCP", "Mcp"])
def test_mcp_project_name_collides_with_sdk_dependency(name: str) -> None:
    """The MCP profile rejects a project that would depend on itself."""
    data = load_catalog()
    resolution = resolve(data.profile("mcp"), data)
    with pytest.raises(SelfDependencyError, match="MCP SDK"):
        validate_project_dependencies(name, resolution)


@pytest.mark.parametrize("name", ["arithmetic-mcp", "mcp-project", "my-mcp"])
def test_mcp_project_names_without_collision_pass(name: str) -> None:
    """Names that only contain 'mcp' remain allowed."""
    data = load_catalog()
    resolution = resolve(data.profile("mcp"), data)
    validate_project_dependencies(name, resolution)


def test_project_name_collision_depends_on_resolved_dependencies() -> None:
    """A project named 'mcp' is fine when its closure has no MCP dependency."""
    data = load_catalog()
    resolution = resolve(data.profile("app"), data)
    validate_project_dependencies("mcp", resolution)
