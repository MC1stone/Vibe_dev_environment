"""Compatibility shims for the installed crewai release.

crewai >= 0.80 monkey-patches ``warnings.warn`` at import time with a
fixed-signature wrapper (message, category, stacklevel, source). Callers
that pass any other keyword argument (Django uses ``skip_file_prefixes``
when loading settings, pydantic uses it too) crash with a TypeError,
which takes down the whole Django process at startup.

``ensure_crewai_compat()`` detects the patched wrapper and replaces it
with a signature-safe version that keeps crewai's pydantic-deprecation
filtering while forwarding arbitrary keyword arguments to the original
``warnings.warn``.
"""

import inspect
import warnings


def _is_crewai_patched_warn(func) -> bool:
    try:
        signature = inspect.signature(func)
    except (TypeError, ValueError):
        return False
    parameters = signature.parameters.values()
    has_var_keyword = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in parameters)
    accepts_skip_file_prefixes = "skip_file_prefixes" in signature.parameters
    if has_var_keyword or accepts_skip_file_prefixes:
        return False
    closure = getattr(func, "__closure__", None)
    if not closure:
        return False
    names = getattr(func.__code__, "co_freevars", ())
    return "original_warn" in names and func.__module__ == "crewai"


def ensure_crewai_compat() -> None:
    """Make the installed crewai release safe to use inside Django.

    Idempotent: importing crewai is enough to trigger its patch, so this
    must be called after ``import crewai`` (or it imports crewai itself
    when the package has not been loaded yet).
    """
    try:
        import crewai  # noqa: F401
    except ImportError:
        return

    current_warn = warnings.warn
    if not _is_crewai_patched_warn(current_warn):
        return

    try:
        original_warn = inspect.getclosurevars(current_warn).nonlocals["original_warn"]
    except (TypeError, ValueError, KeyError):
        return

    supported = set()
    try:
        supported = set(inspect.signature(original_warn).parameters)
    except (TypeError, ValueError):
        pass

    def safe_warn(message, category=None, stacklevel=1, source=None, **kwargs):
        if category is not None and getattr(category, "__module__", None) == "pydantic.warnings":
            return None
        forwarded = {k: v for k, v in kwargs.items() if k in supported}
        return original_warn(message, category=category, stacklevel=stacklevel + 1, source=source, **forwarded)

    warnings.warn = safe_warn
