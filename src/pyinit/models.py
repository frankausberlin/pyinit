"""Typed data model for pyinit profiles, artifacts, context, and plans."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pyinit import __version__

SCHEMA_VERSION = 1
PYINIT_VERSION = __version__
CONTRACT_VERSION = 4
# Version of the lupysta skill that generated projects are documented against.
# This is the single source of truth for the value written to AGENTS.md; it must
# be bumped together with the `version:` frontmatter field in
# ludesta/Luxus-Python-Stack/lupysta/SKILL.md.
LUPYSTA_VERSION = "0.13.0"
MINIMUM_PYTHON = (3, 11)


@dataclass(frozen=True, slots=True)
class FileSpec:
    """One file contributed by an artifact."""

    source: str
    target: str
    render: bool = True
    executable: bool = False


@dataclass(frozen=True, slots=True)
class Artifact:
    """A composable unit of project content."""

    id: str
    description: str
    requires: tuple[str, ...] = ()
    conflicts: tuple[str, ...] = ()
    modes: tuple[str, ...] = ()
    provides: tuple[str, ...] = ()
    runtime_dependencies: tuple[str, ...] = ()
    dev_dependencies: tuple[str, ...] = ()
    e2e_dependencies: tuple[str, ...] = ()
    files: tuple[FileSpec, ...] = ()
    just_fragments: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Profile:
    """A named combination of a mode and artifact ids."""

    id: str
    description: str
    mode: str
    artifacts: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Context:
    """Values available to every template."""

    project_name: str
    package_name: str
    python_version: str
    author_name: str
    year: int
    mode: str
    profile: str
    artifacts: tuple[str, ...]
    generated_at: str
    pyinit_version: str = PYINIT_VERSION
    contract_version: int = CONTRACT_VERSION
    lupysta_version: str = LUPYSTA_VERSION

    def as_mapping(self) -> dict[str, object]:
        """Return the template variables as a plain mapping."""
        return {
            "project_name": self.project_name,
            "package_name": self.package_name,
            "python_version": self.python_version,
            "author_name": self.author_name,
            "year": self.year,
            "mode": self.mode,
            "profile": self.profile,
            "artifacts": self.artifacts,
            "generated_at": self.generated_at,
            "pyinit_version": self.pyinit_version,
            "contract_version": self.contract_version,
            "lupysta_version": self.lupysta_version,
        }


@dataclass(frozen=True, slots=True)
class PlannedFile:
    """A fully rendered file that will be written."""

    target: str
    content: str
    executable: bool = False


@dataclass(frozen=True, slots=True)
class Command:
    """One external command in a plan."""

    args: tuple[str, ...]
    cwd: str
    description: str

    @property
    def display(self) -> str:
        """Return a shell-like rendering of the command."""
        return " ".join(self.args)


@dataclass(frozen=True, slots=True)
class Plan:
    """A deterministic description of everything pyinit will do."""

    profile: str
    mode: str
    target: Path
    files: tuple[PlannedFile, ...]
    commands: tuple[Command, ...]

    def sorted_files(self) -> tuple[PlannedFile, ...]:
        """Return files in stable path order."""
        return tuple(sorted(self.files, key=lambda item: item.target))

    def render_dry_run(self) -> str:
        """Return the stable human-readable dry-run report."""
        lines = [f"Profile: {self.profile}", f"Mode: {self.mode}", f"Target: {self.target}", "", "Files:"]
        lines.extend(f"  {item.target}" for item in self.sorted_files())
        lines.extend(["", "Commands:"])
        lines.extend(f"  [{item.cwd}] {item.display}" for item in self.commands)
        return "\n".join(lines)
