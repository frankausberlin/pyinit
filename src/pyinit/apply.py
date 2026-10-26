"""Preflight, staging, atomic move, and post-generation commands."""

from __future__ import annotations

import shutil
import tempfile
import tomllib
from collections.abc import Callable
from pathlib import Path
from typing import cast

from pyinit.context import Clock, SystemClock, build_context, resolve_author
from pyinit.discovery import load_catalog
from pyinit.errors import ApplyError, CommandFailedError, MissingToolError
from pyinit.models import Plan
from pyinit.plan import build_plan, validate_target
from pyinit.render import render_files
from pyinit.resolver import Resolution, resolve, validate_project_dependencies
from pyinit.runner import CommandResult, Runner, SubprocessRunner, clean_environment

Which = Callable[[str], str | None]


def _require_tools(which: Which) -> None:
    for tool in ("uv", "git", "just"):
        if which(tool) is None:
            raise MissingToolError(f"required tool '{tool}' is not installed or not on PATH")


def _write_staging(stage: Path, plan: Plan) -> None:
    for item in plan.sorted_files():
        destination = stage / item.target
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(item.content, encoding="utf-8")
            if item.executable:
                destination.chmod(0o755)
        except OSError as error:
            raise ApplyError(f"cannot write '{item.target}': {error}") from error


def validate_pyproject(content: str) -> None:
    """Validate the rendered pyproject.toml content."""
    try:
        data = cast(dict[str, object], tomllib.loads(content))
    except tomllib.TOMLDecodeError as error:
        raise ApplyError(f"generated pyproject.toml is invalid: {error}") from error
    project = data.get("project")
    if not isinstance(project, dict):
        raise ApplyError("generated pyproject.toml has no [project] name")
    table = cast(dict[str, object], project)
    if not isinstance(table.get("name"), str):
        raise ApplyError("generated pyproject.toml has no [project] name")


def _validate_staged_pyproject(stage: Path) -> None:
    path = stage / "pyproject.toml"
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as error:
        raise ApplyError(f"generated pyproject.toml is invalid: {error}") from error
    validate_pyproject(content)


def _run_command(
    runner: Runner,
    args: tuple[str, ...],
    *,
    cwd: Path,
    env: dict[str, str],
    description: str,
    after_move: bool,
) -> CommandResult:
    result = runner.run(args, cwd=cwd, env=env)
    if result.returncode != 0:
        command = " ".join(args)
        details = (result.stderr or result.stdout).strip()
        message = f"{description} failed: '{command}' exited with {result.returncode}"
        if details:
            message = f"{message}\n{details}"
        if after_move:
            message = f"{message}\nThe generated tree in '{cwd}' is complete; fix the failed step and rerun it there."
        raise CommandFailedError(message)
    return result


def _move_staging(stage: Path, target: Path) -> None:
    validate_target(target)
    if not target.exists():
        stage.rename(target)
        return
    moved: list[str] = []
    try:
        for entry in sorted(stage.iterdir(), key=lambda item: item.name):
            if entry.name == ".git":
                continue
            shutil.move(str(entry), str(target / entry.name))
            moved.append(entry.name)
    except BaseException:
        for name in reversed(moved):
            source = target / name
            if source.exists() or source.is_symlink():
                shutil.move(str(source), str(stage / name))
        raise
    shutil.rmtree(stage)


def apply_plan(plan: Plan, runner: Runner, *, which: Which = shutil.which) -> None:
    """Apply a plan atomically up to the move and report post-move failures."""
    _require_tools(which)
    target = plan.target
    validate_target(target)
    stage = Path(tempfile.mkdtemp(prefix=f".{target.name}.pyinit-", dir=target.parent))
    moved = False
    try:
        _write_staging(stage, plan)
        _validate_staged_pyproject(stage)
        staging_env = clean_environment(project_environment=stage / ".venv")
        staging_commands = [command for command in plan.commands if command.cwd == "staging"]
        for command in staging_commands:
            _run_command(
                runner,
                command.args,
                cwd=stage,
                env=staging_env,
                description=command.description,
                after_move=False,
            )
        _move_staging(stage, target)
        moved = True
    except BaseException as error:
        if not moved:
            shutil.rmtree(stage, ignore_errors=True)
        if isinstance(error, OSError):
            raise ApplyError(f"cannot move the staged project into '{target}': {error}") from error
        raise

    target_env = clean_environment(project_environment=target / ".venv")
    for command in plan.commands:
        if command.cwd != "target":
            continue
        _run_command(
            runner,
            command.args,
            cwd=target,
            env=target_env,
            description=command.description,
            after_move=True,
        )


def generate(
    profile_id: str,
    directory: str | Path = ".",
    *,
    python_version: str = "3.12",
    no_check: bool = False,
    dry_run: bool = False,
    profile_file: Path | None = None,
    clock: Clock | None = None,
    runner: Runner | None = None,
    author_name: str | None = None,
    which: Which = shutil.which,
) -> Plan:
    """Resolve, render, and optionally apply a profile."""
    catalog = load_catalog(profile_file)
    profile = catalog.profile(profile_id)
    target = Path(directory).expanduser()
    if not target.is_absolute():
        target = Path.cwd() / target
    target = target.resolve()
    validate_target(target)

    command_runner: Runner = runner if runner is not None else SubprocessRunner()
    if not dry_run:
        _require_tools(which)
    if author_name is None:
        author_name = "Project Author" if dry_run else resolve_author(command_runner)
    context = build_context(
        profile=profile,
        target=target,
        python_version=python_version,
        author_name=author_name,
        clock=clock if clock is not None else SystemClock(),
    )
    resolution: Resolution = resolve(profile, catalog)
    validate_project_dependencies(context.project_name, resolution)
    files = render_files(resolution, context)
    pyproject = next((item for item in files if item.target == "pyproject.toml"), None)
    if pyproject is None:
        raise ApplyError("generated pyproject.toml is missing")
    validate_pyproject(pyproject.content)
    plan = build_plan(resolution, context, files, target, no_check=no_check)
    if not dry_run:
        apply_plan(plan, command_runner, which=which)
    return plan
