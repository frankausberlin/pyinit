"""Regression tests for the generated MCP development start path."""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

from pyinit.apply import generate
from pyinit.context import FixedClock

CLOCK = FixedClock(datetime(2026, 10, 26, 20, 0, tzinfo=UTC))


def _write_plan(profile_id: str, target: Path) -> None:
    plan = generate(profile_id, target, dry_run=True, clock=CLOCK, author_name="Tester")
    for item in plan.files:
        path = target / item.target
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(item.content, encoding="utf-8")


def _mcp_dev_command(target: Path) -> str:
    lines = (target / "Justfile").read_text(encoding="utf-8").splitlines()
    index = lines.index("mcp-dev:")
    return next(line.strip() for line in lines[index + 1 :] if line.strip())


def _write_fake_toolchain(directory: Path) -> None:
    npx = directory / "npx"
    npx.write_text('#!/bin/sh\nshift\nexec "$@"\n', encoding="utf-8")
    uv = directory / "uv"
    uv.write_text(
        f"#!{sys.executable}\n"
        "import sys\n"
        "import tomllib\n"
        "\n"
        'if len(sys.argv) < 3 or sys.argv[1] != "run":\n'
        '    raise SystemExit(f"unexpected uv invocation: {sys.argv[1:]}")\n'
        "sys.argv = sys.argv[2:]\n"
        'with open("pyproject.toml", "rb") as handle:\n'
        "    data = tomllib.load(handle)\n"
        'module_name, attribute = data["project"]["scripts"][sys.argv[0]].split(":")\n'
        "module = __import__(module_name, fromlist=[attribute])\n"
        "getattr(module, attribute)()\n",
        encoding="utf-8",
    )
    for script in (npx, uv):
        script.chmod(0o755)


def _write_stub_sdk(directory: Path) -> None:
    package = directory / "mcp"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "server.py").write_text(
        "class MCPServer:\n"
        "    def __init__(self, name):\n"
        "        self.name = name\n"
        "\n"
        "    def tool(self):\n"
        "        def register(function):\n"
        "            return function\n"
        "\n"
        "        return register\n"
        "\n"
        "    def resource(self, uri):\n"
        "        def register(function):\n"
        "            return function\n"
        "\n"
        "        return register\n"
        "\n"
        "    def run(self):\n"
        "        print('MCP-SERVER-STARTED')\n",
        encoding="utf-8",
    )


@pytest.mark.parametrize(
    ("profile_id", "expected_run"),
    [
        ("mcp", "uv run demo"),
        ("cli-mcp", "uv run demo mcp"),
    ],
)
def test_mcp_dev_starts_entrypoint_with_relative_import(
    profile_id: str,
    expected_run: str,
    tmp_path: Path,
) -> None:
    """The Inspector recipe imports the package so relative imports work."""
    target = tmp_path / "demo"
    _write_plan(profile_id, target)
    (target / "src" / "demo" / "tools.py").write_text(
        'def add(a: int, b: int) -> int:\n    """Add two numbers."""\n    return a + b\n',
        encoding="utf-8",
    )
    (target / "src" / "demo" / "server.py").write_text(
        '"""MCP server for demo."""\n'
        "\n"
        "from mcp.server import MCPServer\n"
        "\n"
        "from .tools import add\n"
        "\n"
        'mcp = MCPServer("demo")\n'
        "mcp.tool()(add)\n"
        "\n"
        "\n"
        '@mcp.resource("greeting://{name}")\n'
        "def greeting(name: str) -> str:\n"
        '    """Greet someone by name."""\n'
        '    return f"Hello, {name}!"\n',
        encoding="utf-8",
    )

    fakebin = tmp_path / "fakebin"
    fakebin.mkdir()
    _write_fake_toolchain(fakebin)
    stub_root = tmp_path / "stubs"
    _write_stub_sdk(stub_root)

    command = _mcp_dev_command(target)
    assert command == f"HOST=127.0.0.1 npx @modelcontextprotocol/inspector@2.12.0 {expected_run}"
    environment = {
        **os.environ,
        "PATH": f"{fakebin}{os.pathsep}{os.environ.get('PATH', '')}",
        "PYTHONPATH": f"{target / 'src'}{os.pathsep}{stub_root}",
    }
    result = subprocess.run(
        ["bash", "-uc", command],
        cwd=target,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "MCP-SERVER-STARTED" in result.stdout
