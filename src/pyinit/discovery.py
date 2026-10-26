"""Discovery of bundled and external profiles and artifacts."""

from __future__ import annotations

import re
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import cast

from pyinit.errors import ArtifactNotFoundError, InvalidDataError, ProfileNotFoundError
from pyinit.models import Artifact, FileSpec, Profile

_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_MODES = frozenset({"app", "lib"})


@dataclass(frozen=True, slots=True)
class Catalog:
    """All profiles and artifacts available to one run."""

    profiles: dict[str, Profile]
    artifacts: dict[str, Artifact]

    def profile(self, artifact_id: str) -> Profile:
        """Return a profile or raise a clear error."""
        try:
            return self.profiles[artifact_id]
        except KeyError:
            available = ", ".join(sorted(self.profiles)) or "none"
            raise ProfileNotFoundError(f"unknown profile '{artifact_id}' (available: {available})") from None

    def artifact(self, artifact_id: str) -> Artifact:
        """Return an artifact or raise a clear error."""
        try:
            return self.artifacts[artifact_id]
        except KeyError:
            available = ", ".join(sorted(self.artifacts)) or "none"
            raise ArtifactNotFoundError(f"unknown artifact '{artifact_id}' (available: {available})") from None


def _data_root() -> Traversable:
    return resources.files("pyinit").joinpath("data")


def _read_toml(path: Path) -> dict[str, object]:
    try:
        with path.open("rb") as handle:
            data = cast(dict[str, object], tomllib.load(handle))
    except OSError as error:
        raise InvalidDataError(f"cannot read '{path}': {error}") from error
    except tomllib.TOMLDecodeError as error:
        raise InvalidDataError(f"invalid TOML in '{path}': {error}") from error
    return data


def _read_resource(path: Traversable, label: str) -> dict[str, object]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise InvalidDataError(f"cannot read bundled data '{label}': {error}") from error
    try:
        data = cast(dict[str, object], tomllib.loads(text))
    except tomllib.TOMLDecodeError as error:
        raise InvalidDataError(f"invalid TOML in bundled data '{label}': {error}") from error
    return data


def _string(data: Mapping[str, object], key: str, *, label: str, default: str | None = None) -> str:
    value = data.get(key, default)
    if not isinstance(value, str):
        raise InvalidDataError(f"{label}: '{key}' must be a string")
    return value


def _string_list(data: Mapping[str, object], key: str, *, label: str) -> tuple[str, ...]:
    value = data.get(key, [])
    if not isinstance(value, list):
        raise InvalidDataError(f"{label}: '{key}' must be a list of strings")
    items: list[str] = []
    for item in cast(list[object], value):
        if not isinstance(item, str):
            raise InvalidDataError(f"{label}: '{key}' must be a list of strings")
        items.append(item)
    return tuple(items)


def _boolean(item: Mapping[str, object], key: str, *, label: str, default: bool) -> bool:
    value = item.get(key, default)
    if not isinstance(value, bool):
        raise InvalidDataError(f"{label}: '{key}' must be a boolean")
    return value


def _table(item: object, *, label: str) -> Mapping[str, object]:
    if not isinstance(item, dict):
        raise InvalidDataError(f"{label}: expected a table")
    return cast(dict[str, object], item)


def _validate_id(value: str, *, label: str) -> str:
    if _ID_PATTERN.fullmatch(value) is None:
        raise InvalidDataError(f"{label}: id '{value}' must match [a-z0-9][a-z0-9-]*")
    return value


def _parse_profile(data: Mapping[str, object], *, label: str, fallback_id: str | None = None) -> Profile:
    profile_id = _validate_id(_string(data, "id", label=label, default=fallback_id), label=label)
    mode = _string(data, "mode", label=label)
    if mode not in _MODES:
        raise InvalidDataError(f"{label}: mode must be one of app, lib (got '{mode}')")
    return Profile(
        id=profile_id,
        description=_string(data, "description", label=label, default=""),
        mode=mode,
        artifacts=_string_list(data, "artifacts", label=label),
    )


def _parse_file_spec(item: object, *, label: str) -> FileSpec:
    spec = _table(item, label=f"{label}: each file")
    source = _string(spec, "source", label=label)
    target = _string(spec, "target", label=label)
    if not source or not target:
        raise InvalidDataError(f"{label}: file source and target must not be empty")
    return FileSpec(
        source=source,
        target=target,
        render=_boolean(spec, "render", label=label, default=True),
        executable=_boolean(spec, "executable", label=label, default=False),
    )


def _parse_artifact(data: Mapping[str, object], *, label: str, fallback_id: str) -> Artifact:
    artifact_id = _validate_id(_string(data, "id", label=label, default=fallback_id), label=label)
    modes = _string_list(data, "modes", label=label)
    for mode in modes:
        if mode not in _MODES:
            raise InvalidDataError(f"{label}: modes must be a subset of app, lib (got '{mode}')")
    raw_files = data.get("files", [])
    if not isinstance(raw_files, list):
        raise InvalidDataError(f"{label}: 'files' must be a list")
    files = tuple(
        _parse_file_spec(item, label=f"{label}: files[{index}]")
        for index, item in enumerate(cast(list[object], raw_files))
    )
    return Artifact(
        id=artifact_id,
        description=_string(data, "description", label=label, default=""),
        requires=_string_list(data, "requires", label=label),
        conflicts=_string_list(data, "conflicts", label=label),
        modes=modes,
        provides=_string_list(data, "provides", label=label),
        runtime_dependencies=_string_list(data, "runtime_dependencies", label=label),
        dev_dependencies=_string_list(data, "dev_dependencies", label=label),
        e2e_dependencies=_string_list(data, "e2e_dependencies", label=label),
        files=files,
        just_fragments=_string_list(data, "just_fragments", label=label),
    )


def _bundled_names(directory: Traversable) -> list[Traversable]:
    try:
        return sorted(directory.iterdir(), key=lambda item: item.name)
    except OSError as error:
        raise InvalidDataError(f"cannot list bundled data '{directory}': {error}") from error


def load_catalog(profile_file: Path | None = None) -> Catalog:
    """Load bundled data and optionally add an external profile."""
    root = _data_root()
    artifacts: dict[str, Artifact] = {}
    for child in _bundled_names(root.joinpath("artifacts")):
        if not child.is_dir():
            continue
        label = f"artifacts/{child.name}/artifact.toml"
        data = _read_resource(child.joinpath("artifact.toml"), label)
        artifact = _parse_artifact(data, label=label, fallback_id=child.name)
        if artifact.id in artifacts:
            raise InvalidDataError(f"duplicate bundled artifact id '{artifact.id}'")
        artifacts[artifact.id] = artifact

    profiles: dict[str, Profile] = {}
    for child in _bundled_names(root.joinpath("profiles")):
        if not child.name.endswith(".toml"):
            continue
        label = f"profiles/{child.name}"
        data = _read_resource(child, label)
        profile = _parse_profile(data, label=label, fallback_id=child.name.removesuffix(".toml"))
        if profile.id in profiles:
            raise InvalidDataError(f"duplicate bundled profile id '{profile.id}'")
        profiles[profile.id] = profile

    if profile_file is not None:
        path = profile_file.expanduser()
        data = _read_toml(path)
        profile = _parse_profile(data, label=str(path), fallback_id=path.stem)
        profiles[profile.id] = profile

    return Catalog(profiles=profiles, artifacts=artifacts)
