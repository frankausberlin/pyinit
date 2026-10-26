"""Target validation and command planning."""

from __future__ import annotations

from pathlib import Path

from pyinit.errors import TargetError
from pyinit.models import Command, Context, Plan, PlannedFile
from pyinit.resolver import Resolution


def validate_target(target: Path) -> None:
    """Require an absent, empty, or git-only target directory."""
    if not target.exists():
        if not target.parent.is_dir():
            raise TargetError(f"parent directory '{target.parent}' does not exist")
        return
    if not target.is_dir():
        raise TargetError(f"target '{target}' exists but is not a directory")
    unexpected = sorted(entry.name for entry in target.iterdir() if entry.name != ".git")
    if unexpected:
        shown = ", ".join(unexpected[:5])
        more = "" if len(unexpected) <= 5 else ", ..."
        raise TargetError(
            f"target directory '{target}' is not empty ({shown}{more}); "
            "pyinit only initializes empty directories or directories containing only .git"
        )


def build_commands(
    resolution: Resolution,
    target: Path,
    *,
    no_check: bool,
    has_git: bool,
) -> tuple[Command, ...]:
    """Return the ordered command plan for one generation run."""
    commands: list[Command] = [
        Command(args=("uv", "lock"), cwd="staging", description="Lock dependencies before the move"),
    ]
    if not has_git:
        commands.append(Command(args=("git", "init", "-b", "main"), cwd="target", description="Initialize git"))
    commands.append(Command(args=("uv", "sync"), cwd="target", description="Create the project environment"))
    commands.append(Command(args=("uv", "run", "pre-commit", "install"), cwd="target", description="Install git hooks"))
    if resolution.needs_docs:
        commands.append(Command(args=("just", "docs"), cwd="target", description="Generate documentation"))
    if not no_check:
        commands.append(Command(args=("just", "check"), cwd="target", description="Run the quality gate"))
    return tuple(commands)


def build_plan(
    resolution: Resolution,
    context: Context,
    files: tuple[PlannedFile, ...],
    target: Path,
    *,
    no_check: bool,
) -> Plan:
    """Assemble the complete plan for a generation run."""
    has_git = (target / ".git").exists()
    return Plan(
        profile=context.profile,
        mode=context.mode,
        target=target,
        files=files,
        commands=build_commands(resolution, target, no_check=no_check, has_git=has_git),
    )
