"""Derivation and validation of the project context."""

from __future__ import annotations

import keyword
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from pyinit.errors import InvalidNameError, InvalidPythonVersionError
from pyinit.models import MINIMUM_PYTHON, Context, Profile
from pyinit.runner import Runner, clean_environment

_PROJECT_NAME_PATTERN = re.compile(r"^[A-Za-z](?:[A-Za-z0-9._-]*[A-Za-z0-9])?$")
_PACKAGE_NAME_PATTERN = re.compile(r"^[a-z_][a-z0-9_]*$")
_PYTHON_PATTERN = re.compile(r"^(\d+)\.(\d+)$")


class Clock(Protocol):
    """Injectable source of the current time."""

    def now(self) -> datetime:
        """Return the current time."""
        ...


class SystemClock:
    """Production clock in UTC."""

    def now(self) -> datetime:
        """Return the current UTC time."""
        return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class FixedClock:
    """Deterministic clock for tests."""

    instant: datetime

    def now(self) -> datetime:
        """Return the configured instant."""
        return self.instant


def validate_python_version(value: str) -> str:
    """Return a normalized X.Y version or raise."""
    match = _PYTHON_PATTERN.fullmatch(value)
    if match is None:
        raise InvalidPythonVersionError(f"invalid Python version '{value}' (expected X.Y, e.g. 3.12)")
    major, minor = int(match.group(1)), int(match.group(2))
    if (major, minor) < MINIMUM_PYTHON:
        raise InvalidPythonVersionError(f"Python 3.11 or newer is required (got '{value}')")
    return f"{major}.{minor}"


def derive_project_name(target: Path) -> str:
    """Derive the project name from the target directory."""
    resolved = target.expanduser().resolve()
    name = resolved.name
    if not name:
        raise InvalidNameError("cannot derive a project name from the target directory")
    if _PROJECT_NAME_PATTERN.fullmatch(name) is None:
        raise InvalidNameError(
            f"project name '{name}' is invalid; use letters, digits, '.', '_' and '-', "
            "starting with a letter and ending with a letter or digit"
        )
    return name


def derive_package_name(project_name: str) -> str:
    """Derive and validate a Python package name."""
    package = re.sub(r"[-_.]+", "_", project_name).lower()
    if _PACKAGE_NAME_PATTERN.fullmatch(package) is None:
        raise InvalidNameError(
            f"package name '{package}' (derived from '{project_name}') is not a valid Python identifier"
        )
    if keyword.iskeyword(package):
        raise InvalidNameError(f"'{package}' is a Python keyword and cannot be a package name")
    return package


def resolve_author(runner: Runner) -> str:
    """Read the author from git, falling back to a neutral name."""
    try:
        result = runner.run(("git", "config", "user.name"), cwd=Path.cwd(), env=clean_environment())
    except OSError:
        return "Project Author"
    author = result.stdout.strip()
    if result.returncode == 0 and author:
        return author
    return "Project Author"


def build_context(
    *,
    profile: Profile,
    target: Path,
    python_version: str,
    author_name: str,
    clock: Clock,
) -> Context:
    """Build the validated template context for one generation run."""
    project_name = derive_project_name(target)
    package_name = derive_package_name(project_name)
    version = validate_python_version(python_version)
    instant = clock.now().astimezone(UTC)
    return Context(
        project_name=project_name,
        package_name=package_name,
        python_version=version,
        author_name=author_name,
        year=instant.year,
        mode=profile.mode,
        profile=profile.id,
        artifacts=profile.artifacts,
        generated_at=instant.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
