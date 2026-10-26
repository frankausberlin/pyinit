"""Hermetic Docker tests for the pyinit generator."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from pyinit.apply import generate
from pyinit.errors import TargetError

FAKEBIN = Path(__file__).resolve().parent / "fakebin"


@pytest.mark.parametrize("profile", ["app", "app-cli", "lib", "mcp"])
def test_dry_run_writes_nothing(profile: str, tmp_path: Path) -> None:
    """Every bundled profile produces a plan without touching the filesystem."""
    target = tmp_path / profile
    plan = generate(profile, target, dry_run=True, author_name="E2E Author")
    assert plan.profile == profile
    assert not target.exists()
    targets = {item.target for item in plan.files}
    assert "pyproject.toml" in targets
    assert "pyinit.toml" in targets
    assert "Justfile" in targets
    assert any(command.args == ("uv", "lock") for command in plan.commands)


def test_apply_with_fake_toolchain(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Apply a profile using fake uv/git/just binaries."""
    monkeypatch.setenv("PATH", f"{FAKEBIN}{os.pathsep}{os.environ.get('PATH', '')}")
    target = tmp_path / "demo"
    plan = generate("app-cli", target, no_check=True, author_name="E2E Author")
    assert plan.target == target
    assert (target / "pyproject.toml").is_file()
    assert (target / "src" / "demo" / "cli.py").is_file()
    assert (target / "tests" / "test_smoke.py").is_file()
    assert (target / "uv.lock").is_file()
    assert (target / "scripts" / "test-e2e.sh").stat().st_mode & 0o111
    assert not list(tmp_path.glob(".demo.pyinit-*"))


def test_apply_mcp_with_fake_toolchain(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Apply the MCP profile and verify its server, entry point, and smoke test."""
    monkeypatch.setenv("PATH", f"{FAKEBIN}{os.pathsep}{os.environ.get('PATH', '')}")
    target = tmp_path / "demo"
    plan = generate("mcp", target, no_check=True, author_name="E2E Author")
    assert plan.target == target
    assert (target / "src" / "demo" / "server.py").is_file()
    assert (target / "src" / "demo" / "main.py").is_file()
    assert (target / "tests" / "test_smoke.py").is_file()
    server = (target / "src" / "demo" / "server.py").read_text(encoding="utf-8")
    assert "@mcp.tool()" in server
    assert '@mcp.resource("greeting://{name}")' in server
    justfile = (target / "Justfile").read_text(encoding="utf-8")
    assert "mcp-dev" in justfile
    assert "HOST=127.0.0.1 npx @modelcontextprotocol/inspector@2.12.0" in justfile
    assert "mcp run src/demo/server.py" in justfile
    assert not list(tmp_path.glob(".demo.pyinit-*"))


def test_non_empty_target_is_unchanged(tmp_path: Path) -> None:
    """A non-empty target fails before staging and keeps its contents."""
    target = tmp_path / "demo"
    target.mkdir()
    keep = target / "keep.txt"
    keep.write_text("keep", encoding="utf-8")
    with pytest.raises(TargetError, match="not empty"):
        generate("app", target, no_check=True, author_name="E2E Author")
    assert keep.read_text(encoding="utf-8") == "keep"
    assert not list(tmp_path.glob(".demo.pyinit-*"))
