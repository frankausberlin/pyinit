"""Tests for bundled data and wheel packaging."""

from __future__ import annotations

import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

from pyinit.render import package_data_root

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_data_root_contains_profiles_and_templates() -> None:
    """Test."""
    root = package_data_root()
    assert root.joinpath("profiles", "app.toml").is_file()
    assert root.joinpath("profiles", "app-cli.toml").is_file()
    assert root.joinpath("profiles", "cli-mcp.toml").is_file()
    assert root.joinpath("profiles", "lib.toml").is_file()
    template = root.joinpath("artifacts", "base-app", "templates", "pyproject.toml.j2")
    assert template.is_file()
    assert root.joinpath("artifacts", "mcp-server", "templates", "server.py.j2").is_file()


def test_built_wheel_contains_generator_data(tmp_path: Path) -> None:
    """Test."""
    if shutil.which("uv") is None:
        pytest.skip("uv is required to build the wheel")
    result = subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(tmp_path)],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    wheels = list(tmp_path.glob("*.whl"))
    assert len(wheels) == 1
    with zipfile.ZipFile(wheels[0]) as archive:
        names = set(archive.namelist())
    assert "pyinit/data/profiles/app.toml" in names
    assert any(name.startswith("pyinit/data/artifacts/") and name.endswith(".j2") for name in names)
