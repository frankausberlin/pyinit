"""CLI tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from pyinit import main as main_module
from pyinit.cli import app

runner = CliRunner()


def test_help() -> None:
    """Test."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "new" in result.output
    assert "describe" in result.output


def test_list_profiles() -> None:
    """Test."""
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "app-cli" in result.output
    assert "[lib]" in result.output


def test_describe_profile_and_artifact() -> None:
    """Test."""
    profile = runner.invoke(app, ["describe", "app-cli"])
    assert profile.exit_code == 0
    assert "Mode: app" in profile.output
    artifact = runner.invoke(app, ["describe", "cli"])
    assert artifact.exit_code == 0
    assert "Provides: entrypoint.cli, docs.cli" in artifact.output
    assert "Justfile fragments:" in artifact.output


def test_describe_unknown() -> None:
    """Test."""
    result = runner.invoke(app, ["describe", "nope"])
    assert result.exit_code == 1
    assert "unknown artifact" in result.output


def test_new_dry_run(tmp_path: Path) -> None:
    """Test."""
    target = tmp_path / "demo"
    result = runner.invoke(app, ["new", "app", str(target), "--dry-run"])
    assert result.exit_code == 0
    assert "Files:" in result.output
    assert "tests/test_smoke.py" in result.output
    assert not target.exists()


def test_new_unknown_profile(tmp_path: Path) -> None:
    """Test."""
    result = runner.invoke(app, ["new", "nope", str(tmp_path / "demo"), "--dry-run"])
    assert result.exit_code == 1
    assert "unknown profile" in result.output


def test_new_invalid_python(tmp_path: Path) -> None:
    """Test."""
    result = runner.invoke(app, ["new", "app", str(tmp_path / "demo"), "--dry-run", "--python", "3.9"])
    assert result.exit_code == 1
    assert "Python 3.11" in result.output


def test_new_non_empty_target(tmp_path: Path) -> None:
    """Test."""
    target = tmp_path / "demo"
    target.mkdir()
    (target / "keep").write_text("x", encoding="utf-8")
    result = runner.invoke(app, ["new", "app", str(target), "--dry-run"])
    assert result.exit_code == 1
    assert "not empty" in result.output


def test_external_profile(tmp_path: Path) -> None:
    """Test."""
    profile = tmp_path / "custom.toml"
    profile.write_text('id = "custom"\nmode = "app"\nartifacts = ["app-main"]\n', encoding="utf-8")
    result = runner.invoke(
        app,
        ["new", "custom", str(tmp_path / "demo"), "--dry-run", "--profile-file", str(profile)],
    )
    assert result.exit_code == 0
    assert "Profile: custom" in result.output


def test_entry_point_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test."""
    monkeypatch.setattr(sys, "argv", ["pyinit", "--help"])
    with pytest.raises(SystemExit) as excinfo:
        main_module.main()
    assert excinfo.value.code == 0
