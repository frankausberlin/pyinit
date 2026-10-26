"""Tests for context derivation and validation."""

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path

import pytest

from pyinit.context import (
    FixedClock,
    build_context,
    derive_package_name,
    derive_project_name,
    resolve_author,
    validate_python_version,
)
from pyinit.errors import InvalidNameError, InvalidPythonVersionError
from pyinit.models import Profile
from pyinit.runner import CommandResult

FIXED = FixedClock(datetime(2024, 3, 4, 5, 6, 7, tzinfo=UTC))


class FakeRunner:
    """Runner returning a configured result."""

    def __init__(self, result: CommandResult) -> None:
        """Implement __init__."""
        self.result = result

    def run(self, args: Sequence[str], *, cwd: Path, env: Mapping[str, str]) -> CommandResult:
        """Implement run."""
        del args, cwd, env
        return self.result


def test_validate_python_version_accepts_supported() -> None:
    """Test."""
    assert validate_python_version("3.11") == "3.11"
    assert validate_python_version("3.13") == "3.13"


@pytest.mark.parametrize("value", ["3.10", "2.12", "3", "3.12.1", "python3"])
def test_validate_python_version_rejects(value: str) -> None:
    """Test."""
    with pytest.raises(InvalidPythonVersionError):
        validate_python_version(value)


def test_name_derivation(tmp_path: Path) -> None:
    """Test."""
    target = tmp_path / "My-Cool.Project"
    assert derive_project_name(target) == "My-Cool.Project"
    assert derive_package_name("My-Cool.Project") == "my_cool_project"


@pytest.mark.parametrize("name", ["1bad-start", "-leading", "with space", "tab\tname"])
def test_invalid_project_names(name: str) -> None:
    """Test."""
    with pytest.raises(InvalidNameError):
        derive_project_name(Path("/tmp") / name)


def test_keyword_package_name() -> None:
    """Test."""
    with pytest.raises(InvalidNameError):
        derive_package_name("class")


def test_resolve_author_uses_git(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test."""
    del monkeypatch
    runner = FakeRunner(CommandResult(0, "Ada Lovelace\n", ""))
    assert resolve_author(runner) == "Ada Lovelace"


def test_resolve_author_falls_back() -> None:
    """Test."""
    runner = FakeRunner(CommandResult(1, "", "no user"))
    assert resolve_author(runner) == "Project Author"
    assert resolve_author(FakeRunner(CommandResult(0, "  ", ""))) == "Project Author"


def test_build_context(tmp_path: Path) -> None:
    """Test."""
    profile = Profile(id="app", description="", mode="app", artifacts=("cli",))
    context = build_context(
        profile=profile,
        target=tmp_path / "demo",
        python_version="3.12",
        author_name="Tester",
        clock=FIXED,
    )
    assert context.project_name == "demo"
    assert context.package_name == "demo"
    assert context.year == 2024
    assert context.generated_at == "2024-03-04T05:06:07Z"
    assert context.artifacts == ("cli",)
    assert context.as_mapping()["profile"] == "app"
