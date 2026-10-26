"""Template rendering and file composition."""

from __future__ import annotations

import re
from collections.abc import Mapping
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import PurePosixPath

from jinja2 import Environment, PackageLoader, StrictUndefined, TemplateError

from pyinit.errors import DuplicateRecipeError, DuplicateTargetError, PathTraversalError, RenderError
from pyinit.models import Context, PlannedFile
from pyinit.resolver import Resolution

_DRIVE_PATTERN = re.compile(r"^[A-Za-z]:")
_RECIPE_PATTERN = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*)(?:\s+[^:]*)?:(?!=)")


def build_environment() -> Environment:
    """Return the configured Jinja environment for bundled templates."""
    return Environment(
        loader=PackageLoader("pyinit", package_path="data"),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
        autoescape=False,
    )


def _validate_relative_path(path: str, *, label: str) -> None:
    if not path:
        raise PathTraversalError(f"{label}: empty path")
    if "\\" in path or _DRIVE_PATTERN.match(path) or PurePosixPath(path).is_absolute():
        raise PathTraversalError(f"{label}: '{path}' must be a relative path")
    if any(part in {"", ".", ".."} for part in path.split("/")):
        raise PathTraversalError(f"{label}: '{path}' must not contain '.' or '..' segments")


def _variables(context: Context, resolution: Resolution) -> dict[str, object]:
    variables = context.as_mapping()
    variables.update(
        {
            "runtime_dependencies": list(resolution.runtime_dependencies),
            "dev_dependencies": list(resolution.dev_dependencies),
            "e2e_dependencies": list(resolution.e2e_dependencies),
            "has_docs": resolution.needs_docs,
            "capabilities": sorted(resolution.capabilities),
        }
    )
    return variables


def render_target(target: str, variables: Mapping[str, object], environment: Environment) -> str:
    """Render and validate one target path."""
    try:
        rendered = environment.from_string(target).render(variables)
    except TemplateError as error:
        raise RenderError(f"cannot render target path '{target}': {error}") from error
    _validate_relative_path(rendered, label="target path")
    return rendered


def recipe_names(text: str) -> set[str]:
    """Extract top-level Justfile recipe names from a fragment."""
    names: set[str] = set()
    for line in text.splitlines():
        if not line or line[0].isspace() or line.startswith("#"):
            continue
        match = _RECIPE_PATTERN.match(line)
        if match is not None:
            names.add(match.group(1))
    return names


def _static_content(artifact_id: str, source: str) -> str:
    _validate_relative_path(source, label=f"artifact '{artifact_id}' source")
    path = resources.files("pyinit").joinpath("data", "artifacts", artifact_id, source)
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise RenderError(f"cannot read static file '{artifact_id}/{source}': {error}") from error
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise RenderError(f"static file '{artifact_id}/{source}' is not UTF-8 text") from error


def _render_file(
    artifact_id: str,
    source: str,
    variables: Mapping[str, object],
    environment: Environment,
) -> str:
    _validate_relative_path(source, label=f"artifact '{artifact_id}' source")
    try:
        template = environment.get_template(f"artifacts/{artifact_id}/{source}")
    except TemplateError as error:
        raise RenderError(f"cannot load template '{artifact_id}/{source}': {error}") from error
    try:
        return template.render(variables)
    except TemplateError as error:
        raise RenderError(f"cannot render template '{artifact_id}/{source}': {error}") from error


def _compose_justfile(
    content: str,
    resolution: Resolution,
    variables: Mapping[str, object],
    environment: Environment,
) -> str:
    names = recipe_names(content)
    fragments: list[str] = []
    for artifact_id, source in resolution.just_fragments:
        fragment = _render_file(artifact_id, source, variables, environment)
        fragment_names = recipe_names(fragment)
        duplicates = sorted(names & fragment_names)
        if duplicates:
            raise DuplicateRecipeError(
                f"duplicate Justfile recipe(s) {', '.join(duplicates)} in '{artifact_id}/{source}'"
            )
        names |= fragment_names
        fragments.append(fragment.rstrip("\n"))
    if not fragments:
        return content if content.endswith("\n") else f"{content}\n"
    merged = content.rstrip("\n") + "\n\n" + "\n\n".join(fragments) + "\n"
    return merged


def render_files(resolution: Resolution, context: Context) -> tuple[PlannedFile, ...]:
    """Render every file in the artifact closure."""
    environment = build_environment()
    variables = _variables(context, resolution)
    rendered: dict[str, tuple[str, PlannedFile]] = {}
    justfile: PlannedFile | None = None

    for artifact in resolution.artifacts:
        for spec in artifact.files:
            target = render_target(spec.target, variables, environment)
            if target in rendered:
                other_artifact, _ = rendered[target]
                raise DuplicateTargetError(
                    f"target '{target}' is written by both '{other_artifact}' and '{artifact.id}'"
                )
            content = (
                _render_file(artifact.id, spec.source, variables, environment)
                if spec.render
                else _static_content(artifact.id, spec.source)
            )
            planned = PlannedFile(target=target, content=content, executable=spec.executable)
            rendered[target] = (artifact.id, planned)
            if target == "Justfile":
                justfile = planned

    if justfile is None:
        raise RenderError("the resolved artifact set does not contribute a Justfile")
    composed = _compose_justfile(justfile.content, resolution, variables, environment)
    rendered["Justfile"] = ("base", PlannedFile(target="Justfile", content=composed, executable=justfile.executable))

    return tuple(sorted((item for _, item in rendered.values()), key=lambda item: item.target))


def artifact_source_exists(artifact_id: str, source: str) -> bool:
    """Return whether a bundled artifact source exists (used by tests)."""
    try:
        _validate_relative_path(source, label="source")
    except PathTraversalError:
        return False
    return resources.files("pyinit").joinpath("data", "artifacts", artifact_id, source).is_file()


def package_data_root() -> Traversable:
    """Return the bundled data root for packaging tests."""
    return resources.files("pyinit").joinpath("data")
