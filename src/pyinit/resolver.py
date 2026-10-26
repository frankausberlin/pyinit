"""Artifact graph resolution."""

from __future__ import annotations

import re
from dataclasses import dataclass

from pyinit.discovery import Catalog
from pyinit.errors import (
    ArtifactNotFoundError,
    ConflictError,
    CycleError,
    DependencyConflictError,
    ModeConflictError,
    ProvideConflictError,
)
from pyinit.models import Artifact, Profile

_DEPENDENCY_PATTERN = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)")
_UNIQUE_NAMESPACES = ("entrypoint.", "docs.")


@dataclass(frozen=True, slots=True)
class Resolution:
    """The ordered artifact closure of one profile."""

    profile: Profile
    artifacts: tuple[Artifact, ...]
    runtime_dependencies: tuple[str, ...]
    dev_dependencies: tuple[str, ...]
    e2e_dependencies: tuple[str, ...]
    just_fragments: tuple[tuple[str, str], ...]

    @property
    def capabilities(self) -> frozenset[str]:
        """Return every capability provided by the closure."""
        return frozenset(capability for artifact in self.artifacts for capability in artifact.provides)

    @property
    def needs_docs(self) -> bool:
        """Return whether any artifact contributes documentation recipes."""
        return any(capability.startswith("docs.") for capability in self.capabilities)


def _dependency_name(requirement: str) -> str:
    match = _DEPENDENCY_PATTERN.match(requirement)
    if match is None:
        raise DependencyConflictError(f"invalid dependency declaration '{requirement}'")
    return re.sub(r"[-_.]+", "-", match.group(1)).lower()


def _merge_dependencies(groups: list[tuple[str, ...]]) -> tuple[str, ...]:
    seen: dict[str, str] = {}
    ordered: list[str] = []
    for group in groups:
        for requirement in group:
            name = _dependency_name(requirement)
            if name in seen:
                if seen[name] != requirement:
                    raise DependencyConflictError(
                        f"conflicting constraints for '{name}': '{seen[name]}' and '{requirement}'"
                    )
                continue
            seen[name] = requirement
            ordered.append(requirement)
    return tuple(ordered)


def _validate_modes(profile: Profile, artifacts: tuple[Artifact, ...]) -> None:
    for artifact in artifacts:
        if artifact.modes and profile.mode not in artifact.modes:
            modes = ", ".join(artifact.modes)
            raise ModeConflictError(
                f"artifact '{artifact.id}' supports mode {modes} but profile '{profile.id}' uses '{profile.mode}'"
            )


def _validate_conflicts(artifacts: tuple[Artifact, ...]) -> None:
    selected = {artifact.id for artifact in artifacts}
    for artifact in artifacts:
        for conflict in artifact.conflicts:
            if conflict in selected and conflict != artifact.id:
                raise ConflictError(f"artifacts '{artifact.id}' and '{conflict}' conflict")


def _validate_provides(artifacts: tuple[Artifact, ...]) -> None:
    capabilities: dict[str, str] = {}
    namespaces: dict[str, tuple[str, str]] = {}
    for artifact in artifacts:
        for capability in artifact.provides:
            if capability in capabilities:
                raise ProvideConflictError(
                    f"capability '{capability}' is provided by both '{capabilities[capability]}' and '{artifact.id}'"
                )
            capabilities[capability] = artifact.id
            for prefix in _UNIQUE_NAMESPACES:
                if capability.startswith(prefix):
                    if prefix in namespaces:
                        other_artifact, other_capability = namespaces[prefix]
                        raise ProvideConflictError(
                            f"only one '{prefix}*' capability is allowed, but '{other_artifact}' provides "
                            f"'{other_capability}' and '{artifact.id}' provides '{capability}'"
                        )
                    namespaces[prefix] = (artifact.id, capability)


def _order(catalog: Catalog, start: list[str]) -> tuple[Artifact, ...]:
    state: dict[str, int] = {}
    stack: list[str] = []
    ordered: list[Artifact] = []

    def visit(artifact_id: str) -> None:
        current = state.get(artifact_id, 0)
        if current == 2:
            return
        if current == 1:
            cycle_start = stack.index(artifact_id)
            cycle = " -> ".join([*stack[cycle_start:], artifact_id])
            raise CycleError(f"artifact requirement cycle: {cycle}")
        state[artifact_id] = 1
        stack.append(artifact_id)
        try:
            artifact = catalog.artifact(artifact_id)
        except ArtifactNotFoundError as error:
            raise ArtifactNotFoundError(f"{error} (required by {stack[-2] if len(stack) > 1 else 'profile'})") from None
        for requirement in artifact.requires:
            visit(requirement)
        stack.pop()
        state[artifact_id] = 2
        ordered.append(artifact)

    for artifact_id in start:
        visit(artifact_id)
    return tuple(ordered)


def resolve(profile: Profile, catalog: Catalog) -> Resolution:
    """Resolve a profile into a deterministic artifact closure."""
    base_id = f"base-{profile.mode}"
    requested = [base_id, *profile.artifacts]
    ordered = _order(catalog, requested)
    _validate_modes(profile, ordered)
    _validate_conflicts(ordered)
    _validate_provides(ordered)
    return Resolution(
        profile=profile,
        artifacts=ordered,
        runtime_dependencies=_merge_dependencies([artifact.runtime_dependencies for artifact in ordered]),
        dev_dependencies=_merge_dependencies([artifact.dev_dependencies for artifact in ordered]),
        e2e_dependencies=_merge_dependencies([artifact.e2e_dependencies for artifact in ordered]),
        just_fragments=tuple((artifact.id, fragment) for artifact in ordered for fragment in artifact.just_fragments),
    )
