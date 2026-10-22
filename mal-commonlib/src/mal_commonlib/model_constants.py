"""Read-only access to the single model-constants YAML from mal-commonlib.

``mal-core/config/model_constants.yaml`` is the ONLY source of shared model
parameters (R1).  Schema and invariant validation live in **mal-core**
(``mal_core.config_validation``, R2), which is the ONLY validator.

This module exists because ``mal-commonlib`` sits BELOW ``mal-core`` in the
dependency graph: loaders need shared values (NoData sentinels and
loader-owned parameter sections) and cannot import the validator without
inverting that dependency.  It never validates and never invents defaults —
it resolves the same path (explicit > ``MAL_MODEL_CONSTANTS`` > repo
default), reads one dotted key and fails loudly when the key is missing.

Use it only for parameters consumed by mal-commonlib loaders (NoData
sentinels and loader-owned sections such as ``wildlife``).  Parameters that
only mal-core consumes belong there, where the validated tree is available.
"""
from __future__ import annotations

import functools
import os
import pathlib
from typing import Any

import yaml

from .config import REPO_ROOT

ENV_VAR = "MAL_MODEL_CONSTANTS"
DEFAULT_PATH = REPO_ROOT / "mal-core" / "config" / "model_constants.yaml"


def resolve_path(path: str | os.PathLike[str] | None = None) -> pathlib.Path:
    """Resolve the constants path (explicit > env var > repo default)."""
    if path is not None:
        return pathlib.Path(path)
    env = os.environ.get(ENV_VAR)
    if env:
        return pathlib.Path(env)
    return DEFAULT_PATH


@functools.lru_cache(maxsize=8)
def _tree(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"model_constants: {path} is not a mapping")
    return data


def model_constant(
    *keys: str, path: str | os.PathLike[str] | None = None
) -> Any:
    """Return one dotted key of the model-constants YAML.

    Raises ``KeyError`` naming the full dotted path when absent: a missing
    key is never silently defaulted.
    """
    resolved = resolve_path(path)
    node: Any = _tree(str(resolved))
    for key in keys:
        if not isinstance(node, dict) or key not in node:
            raise KeyError(
                f"model_constants: {'.'.join(keys)} not found in {resolved}")
        node = node[key]
    return node


__all__ = [
    "DEFAULT_PATH",
    "ENV_VAR",
    "model_constant",
    "resolve_path",
]
