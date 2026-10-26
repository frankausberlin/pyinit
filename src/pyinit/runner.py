"""Injectable command runner and environment hygiene."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

_CLEARED_VARIABLES = (
    "VIRTUAL_ENV",
    "UV_PROJECT_ENVIRONMENT",
    "UV_PROJECT",
    "UV_WORKING_DIR",
    "PYTHONHOME",
    "PYTHONPATH",
)


@dataclass(frozen=True, slots=True)
class CommandResult:
    """The captured result of one external command."""

    returncode: int
    stdout: str
    stderr: str


class Runner(Protocol):
    """Interface used by pyinit to run external commands."""

    def run(self, args: Sequence[str], *, cwd: Path, env: Mapping[str, str]) -> CommandResult:
        """Run one command and capture its output."""
        ...


class SubprocessRunner:
    """Production runner backed by :func:`subprocess.run`."""

    def run(self, args: Sequence[str], *, cwd: Path, env: Mapping[str, str]) -> CommandResult:
        """Run one command without raising on a non-zero exit."""
        completed = subprocess.run(
            list(args),
            cwd=cwd,
            env=dict(env),
            check=False,
            capture_output=True,
            text=True,
        )
        return CommandResult(
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )


def clean_environment(*, project_environment: Path | None = None) -> dict[str, str]:
    """Return a subprocess environment without inherited Python state."""
    env = dict(os.environ)
    for name in _CLEARED_VARIABLES:
        env.pop(name, None)
    env["UV_PYTHON_PREFERENCE"] = "only-managed"
    if project_environment is not None:
        env["UV_PROJECT_ENVIRONMENT"] = str(project_environment)
    return env
