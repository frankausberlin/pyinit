"""Command-line interface for pyinit."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, NoReturn

import typer

from pyinit.apply import generate
from pyinit.discovery import Catalog, load_catalog
from pyinit.errors import PyinitError

app = typer.Typer(
    name="pyinit",
    help="Generate new Python projects from data-driven profiles.",
    no_args_is_help=True,
)


def _fail(error: PyinitError) -> NoReturn:
    typer.echo(f"Error: {error}", err=True)
    raise typer.Exit(code=1)


def _artifact_lines(catalog: Catalog, artifact_id: str) -> list[str]:
    artifact = catalog.artifact(artifact_id)
    lines = [f"Artifact: {artifact.id}", f"Description: {artifact.description}"]
    if artifact.modes:
        lines.append(f"Modes: {', '.join(artifact.modes)}")
    if artifact.requires:
        lines.append(f"Requires: {', '.join(artifact.requires)}")
    if artifact.conflicts:
        lines.append(f"Conflicts: {', '.join(artifact.conflicts)}")
    if artifact.provides:
        lines.append(f"Provides: {', '.join(artifact.provides)}")
    if artifact.runtime_dependencies:
        lines.append(f"Runtime dependencies: {', '.join(artifact.runtime_dependencies)}")
    if artifact.dev_dependencies:
        lines.append(f"Development dependencies: {', '.join(artifact.dev_dependencies)}")
    if artifact.e2e_dependencies:
        lines.append(f"E2E dependencies: {', '.join(artifact.e2e_dependencies)}")
    if artifact.files:
        lines.append("Files:")
        lines.extend(f"  {item.source} -> {item.target}" for item in artifact.files)
    if artifact.just_fragments:
        lines.append("Justfile fragments:")
        lines.extend(f"  {item}" for item in artifact.just_fragments)
    return lines


@app.command()
def new(
    profile: Annotated[str, typer.Argument(help="Profile id, for example app-cli.")],
    directory: Annotated[str, typer.Argument(help="Target directory (default: current directory).")] = ".",
    python: Annotated[str, typer.Option("--python", help="Python version X.Y (3.11 or newer).")] = "3.12",
    no_check: Annotated[bool, typer.Option("--no-check", help="Skip the final 'just check'.")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Print the plan without writing anything.")] = False,
    profile_file: Annotated[
        Path | None,
        typer.Option("--profile-file", help="Load an external profile TOML file."),
    ] = None,
) -> None:
    """Create a new project from a profile."""
    try:
        plan = generate(
            profile,
            directory,
            python_version=python,
            no_check=no_check,
            dry_run=dry_run,
            profile_file=profile_file,
        )
    except PyinitError as error:
        _fail(error)
    if dry_run:
        typer.echo(plan.render_dry_run())
        return
    typer.echo(f"Created '{plan.profile}' project in {plan.target}")


@app.command(name="list")
def list_profiles() -> None:
    """List available profiles."""
    try:
        catalog = load_catalog()
    except PyinitError as error:
        _fail(error)
    for profile in sorted(catalog.profiles.values(), key=lambda item: item.id):
        typer.echo(f"{profile.id}\t[{profile.mode}]\t{profile.description}")


@app.command()
def describe(identifier: Annotated[str, typer.Argument(help="Profile or artifact id.")]) -> None:
    """Show a profile or artifact."""
    try:
        catalog = load_catalog()
        profile = catalog.profiles.get(identifier)
        artifact = catalog.artifacts.get(identifier)
        if profile is None and artifact is None:
            catalog.artifact(identifier)
        lines: list[str] = []
        if profile is not None:
            lines = [
                f"Profile: {profile.id}",
                f"Description: {profile.description}",
                f"Mode: {profile.mode}",
                f"Artifacts: {', '.join(profile.artifacts)}",
            ]
        if artifact is not None:
            if lines:
                lines.append("")
            lines.extend(_artifact_lines(catalog, identifier))
    except PyinitError as error:
        _fail(error)
    typer.echo("\n".join(lines))


if __name__ == "__main__":
    app()
