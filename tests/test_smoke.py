"""Smoke test for the pyinit application."""

import sys

import pytest
from typer.testing import CliRunner

from pyinit import main as main_module
from pyinit.cli import app

runner = CliRunner()


def test_cli_hello() -> None:
    """Run the CLI with an explicit name."""
    result = runner.invoke(app, ["--name", "tester"])
    assert result.exit_code == 0
    assert "Hello, tester!" in result.output


def test_entry_point_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    """Run the console entry point with a patched command line."""
    monkeypatch.setattr(sys, "argv", ["pyinit", "--name", "tester"])
    with pytest.raises(SystemExit) as excinfo:
        main_module.main()
    assert excinfo.value.code == 0
