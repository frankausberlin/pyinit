"""Tests for bundled and external discovery."""

from pathlib import Path

import pytest

from pyinit.discovery import load_catalog
from pyinit.errors import ArtifactNotFoundError, InvalidDataError, ProfileNotFoundError


def test_bundled_catalog_contains_expected_data() -> None:
    """Test."""
    catalog = load_catalog()
    assert {"app", "app-cli", "cli-mcp", "lib", "mcp"} <= set(catalog.profiles)
    assert {"base-app", "base-lib", "cli", "diataxis", "e2e", "agent", "mcp", "mcp-server"} <= set(catalog.artifacts)
    assert catalog.profiles["app"].mode == "app"
    assert catalog.profiles["lib"].mode == "lib"
    assert catalog.profiles["mcp"].mode == "app"
    assert catalog.profiles["cli-mcp"].mode == "app"


def test_unknown_profile_and_artifact() -> None:
    """Test."""
    catalog = load_catalog()
    with pytest.raises(ProfileNotFoundError, match="unknown profile"):
        catalog.profile("nope")
    with pytest.raises(ArtifactNotFoundError, match="unknown artifact"):
        catalog.artifact("nope")


def test_external_profile_is_loaded(tmp_path: Path) -> None:
    """Test."""
    profile = tmp_path / "custom.toml"
    profile.write_text(
        'id = "custom"\ndescription = "External"\nmode = "app"\nartifacts = ["cli"]\n',
        encoding="utf-8",
    )
    catalog = load_catalog(profile)
    assert catalog.profiles["custom"].artifacts == ("cli",)


def test_external_profile_uses_stem_as_id(tmp_path: Path) -> None:
    """Test."""
    profile = tmp_path / "stem-name.toml"
    profile.write_text('mode = "lib"\nartifacts = []\n', encoding="utf-8")
    catalog = load_catalog(profile)
    assert catalog.profiles["stem-name"].mode == "lib"


@pytest.mark.parametrize(
    "content",
    [
        "mode = 12\n",
        'mode = "app"\nartifacts = "cli"\n',
        'id = "Bad ID"\nmode = "app"\n',
        'id = "bad"\nmode = "web"\n',
        "not = [valid",
    ],
)
def test_invalid_external_profiles(tmp_path: Path, content: str) -> None:
    """Test."""
    profile = tmp_path / "bad.toml"
    profile.write_text(content, encoding="utf-8")
    with pytest.raises(InvalidDataError):
        load_catalog(profile)


def test_unreadable_external_profile(tmp_path: Path) -> None:
    """Test."""
    with pytest.raises(InvalidDataError, match="cannot read"):
        load_catalog(tmp_path / "missing.toml")
