"""Error hierarchy for pyinit."""


class PyinitError(Exception):
    """Base class for all user-facing pyinit errors."""


class DataError(PyinitError):
    """Bundled or external generator data is invalid."""


class ProfileNotFoundError(DataError):
    """The requested profile does not exist."""


class ArtifactNotFoundError(DataError):
    """An artifact referenced by a profile does not exist."""


class InvalidDataError(DataError):
    """A profile or artifact declaration is malformed."""


class ResolutionError(PyinitError):
    """The requested artifacts cannot be combined."""


class ConflictError(ResolutionError):
    """Two selected artifacts declare a conflict."""


class CycleError(ResolutionError):
    """Artifact requirements form a cycle."""


class ProvideConflictError(ResolutionError):
    """Two selected artifacts provide the same capability."""


class ModeConflictError(ResolutionError):
    """An artifact is not valid for the profile mode."""


class DependencyConflictError(ResolutionError):
    """Two artifacts declare different constraints for the same dependency."""


class DuplicateRecipeError(ResolutionError):
    """Two Justfile fragments define the same recipe."""


class ContextError(PyinitError):
    """The project context cannot be derived or is invalid."""


class InvalidNameError(ContextError):
    """The project or package name is not usable."""


class InvalidPythonVersionError(ContextError):
    """The requested Python version is unsupported or malformed."""


class TargetError(PyinitError):
    """The target directory cannot be initialized."""


class RenderError(PyinitError):
    """A file cannot be rendered."""


class PathTraversalError(RenderError):
    """A target path escapes the project directory."""


class DuplicateTargetError(RenderError):
    """Two files map to the same target path."""


class ApplyError(PyinitError):
    """The generated project cannot be written."""


class MissingToolError(ApplyError):
    """A required external tool is missing."""


class CommandFailedError(ApplyError):
    """An external command failed."""
