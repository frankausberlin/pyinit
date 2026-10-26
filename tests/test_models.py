"""Tests for the model constants."""

from __future__ import annotations

import pyinit
from pyinit.models import PYINIT_VERSION


def test_pyinit_version_matches_package_version() -> None:
    """The model version constant follows the package version."""
    assert pyinit.__version__ == PYINIT_VERSION
