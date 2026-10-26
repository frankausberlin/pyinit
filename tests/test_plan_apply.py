"""Tests for target validation, planning, and applying."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path

import pytest

from pyinit.apply import apply_plan, generate
from pyinit.context import FixedClock, build_context
from pyinit.discovery import load_catalog
from pyinit.errors import CommandFailedError, MissingToolError, TargetError
from pyinit.models import Context, Profile
from pyinit.plan import build_plan, validate_target
from pyinit.resolver import resolve
from pyinit.runner import CommandResult

CLOCK = FixedClock(datetime(2026, 10, 26, 20, 0, tzinfo=UTC))


def context_for(profile: Profile, target: Path) -> Context:
    """Build a deterministic template context."""
    return build_context(
        profile=profile,
        target=target,
        python_version="3.12",
        author_name="Tester",
        clock=CLOCK,
    )


class FakeRunner:
    """Configurable command runner."""

    def __init__(self, fail_on: tuple[str, ...] = ()) -> None:
        """Implement __init__."""
        self.calls: list[tuple[tuple[str, ...], Path]] = []
        self.fail_on = fail_on

    def run(self, args: Sequence[str], *, cwd: Path, env: Mapping[str, str]) -> CommandResult:
        """Implement run."""
        del env
        command = tuple(args)
        self.calls.append((command, cwd))
        if self.fail_on and command[: len(self.fail_on)] == self.fail_on:
            return CommandResult(1, "", "boom")
        return CommandResult(0, "", "")


def tools(name: str) -> str:
    """Pretend every tool exists."""
    return f"/usr/bin/{name}"


@pytest.mark.parametrize("profile_id", ["app", "app-cli", "lib"])
def test_dry_run_writes_nothing(profile_id: str, tmp_path: Path) -> None:
    """Test."""
    target = tmp_path / "demo"
    plan = generate(profile_id, target, dry_run=True, clock=CLOCK, author_name="Tester")
    assert not target.exists()
    assert any(item.target == "pyproject.toml" for item in plan.files)
    assert plan.commands[0].args == ("uv", "lock")
    assert "Files:" in plan.render_dry_run()


def test_dry_run_and_apply_have_same_paths(tmp_path: Path) -> None:
    """Test."""
    target = tmp_path / "demo"
    dry = generate("app-cli", target, dry_run=True, no_check=True, clock=CLOCK, author_name="Tester")
    runner = FakeRunner()
    applied = generate(
        "app-cli",
        target,
        no_check=True,
        clock=CLOCK,
        author_name="Tester",
        runner=runner,
        which=tools,
    )
    assert [item.target for item in dry.files] == [item.target for item in applied.files]
    assert dry.commands == applied.commands
    assert (target / "pyproject.toml").is_file()
    assert (target / "src" / "demo" / "cli.py").is_file()
    assert (target / "scripts" / "test-e2e.sh").stat().st_mode & 0o111
    assert runner.calls[0][0] == ("uv", "lock")
    assert ("just", "docs") in [call[0] for call in runner.calls]
    assert ("just", "check") not in [call[0] for call in runner.calls]


def test_no_check_command(tmp_path: Path) -> None:
    """Test."""
    plan = generate("app", tmp_path / "demo", dry_run=True, clock=CLOCK, author_name="Tester")
    assert ("just", "check") in [command.args for command in plan.commands]


def test_existing_empty_target(tmp_path: Path) -> None:
    """Test."""
    target = tmp_path / "demo"
    target.mkdir()
    generate("app", target, no_check=True, clock=CLOCK, author_name="Tester", runner=FakeRunner(), which=tools)
    assert (target / "pyproject.toml").is_file()


def test_git_only_target_skips_git_init(tmp_path: Path) -> None:
    """Test."""
    target = tmp_path / "demo"
    (target / ".git").mkdir(parents=True)
    runner = FakeRunner()
    generate("app", target, no_check=True, clock=CLOCK, author_name="Tester", runner=runner, which=tools)
    assert ("git", "init", "-b", "main") not in [call[0] for call in runner.calls]
    assert (target / ".git").is_dir()
    assert (target / "pyproject.toml").is_file()


def test_non_empty_target_is_rejected(tmp_path: Path) -> None:
    """Test."""
    target = tmp_path / "demo"
    target.mkdir()
    (target / "keep.txt").write_text("keep", encoding="utf-8")
    with pytest.raises(TargetError, match="not empty"):
        generate("app", target, no_check=True, clock=CLOCK, author_name="Tester", runner=FakeRunner(), which=tools)
    assert (target / "keep.txt").read_text(encoding="utf-8") == "keep"
    assert not list(tmp_path.glob(".demo.pyinit-*"))


def test_target_is_file_and_parent_missing(tmp_path: Path) -> None:
    """Test."""
    file_target = tmp_path / "file"
    file_target.write_text("x", encoding="utf-8")
    with pytest.raises(TargetError, match="not a directory"):
        validate_target(file_target)
    with pytest.raises(TargetError, match="parent directory"):
        validate_target(tmp_path / "missing" / "demo")


def test_missing_tool(tmp_path: Path) -> None:
    """Test."""
    with pytest.raises(MissingToolError, match="uv"):
        generate(
            "app",
            tmp_path / "demo",
            no_check=True,
            clock=CLOCK,
            author_name="Tester",
            runner=FakeRunner(),
            which=lambda name: None if name == "uv" else "/bin/true",
        )
    assert not (tmp_path / "demo").exists()


def test_lock_failure_is_atomic(tmp_path: Path) -> None:
    """Test."""
    target = tmp_path / "demo"
    with pytest.raises(CommandFailedError, match="lock"):
        generate(
            "app",
            target,
            no_check=True,
            clock=CLOCK,
            author_name="Tester",
            runner=FakeRunner(fail_on=("uv", "lock")),
            which=tools,
        )
    assert not target.exists()
    assert not list(tmp_path.glob(".demo.pyinit-*"))


def test_post_move_failure_leaves_complete_tree(tmp_path: Path) -> None:
    """Test."""
    target = tmp_path / "demo"
    runner = FakeRunner(fail_on=("uv", "sync"))
    with pytest.raises(CommandFailedError, match="uv sync"):
        generate("app", target, no_check=True, clock=CLOCK, author_name="Tester", runner=runner, which=tools)
    assert (target / "pyproject.toml").is_file()
    assert (target / "AGENTS.md").is_file()


def test_commands_include_check_and_docs(tmp_path: Path) -> None:
    """Test."""
    catalog = load_catalog()
    profile = catalog.profile("lib")
    resolution = resolve(profile, catalog)
    context = context_for(profile, tmp_path / "demo")
    files = ()
    plan = build_plan(resolution, context, files, tmp_path / "demo", no_check=False)
    assert [command.args for command in plan.commands] == [
        ("uv", "lock"),
        ("git", "init", "-b", "main"),
        ("uv", "sync"),
        ("uv", "run", "pre-commit", "install"),
        ("just", "docs"),
        ("just", "check"),
    ]
    app = catalog.profile("app")
    app_plan = build_plan(
        resolve(app, catalog),
        context_for(app, tmp_path / "app"),
        (),
        tmp_path / "app",
        no_check=True,
    )
    assert ("just", "docs") not in [command.args for command in app_plan.commands]


def test_apply_plan_runs_staging_first(tmp_path: Path) -> None:
    """Test."""
    catalog = load_catalog()
    profile = catalog.profile("app")
    resolution = resolve(profile, catalog)
    context = context_for(profile, tmp_path / "demo")
    files = generate("app", tmp_path / "dry", dry_run=True, clock=CLOCK, author_name="Tester").files
    plan = build_plan(resolution, context, files, tmp_path / "demo", no_check=True)
    runner = FakeRunner()
    apply_plan(plan, runner, which=tools)
    assert runner.calls[0][0] == ("uv", "lock")
    assert runner.calls[-1][0] == ("uv", "run", "pre-commit", "install")
