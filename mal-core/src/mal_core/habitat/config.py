"""Thin loader of the single model constants YAML (plan constants-yaml §3).

``mal-core/config/model_constants.yaml`` is the ONLY source of shared
model parameters (py ⇄ C++).  Schema and invariant checking live in ONE
place: :mod:`mal_core.config_validation` (R2).  This module only:

* resolves the path (explicit > ``MAL_MODEL_CONSTANTS`` > default),
* delegates validation to :func:`mal_core.config_validation.validate_model_config`,
* exposes the validated tree as an immutable ``MappingProxyType`` singleton,
* derives the ordered habitat names / dynamics helpers.

There are NO silent fallbacks and NO model-constant defaults here: the
validator fails loudly and lists every problem in the file.
"""
from __future__ import annotations

import os
import types
from typing import Any

from ..config_validation import (
    DEFAULT_PATH,
    ENV_VAR,
    SCHEMA,
    ConfigError,
    SchemaError,
    freeze,
    resolve_path,
    validate_model_config,
)

__all__ = [
    "ConfigError",
    "SchemaError",
    "CONFIG",
    "SCHEMA",
    "ENV_VAR",
    "DEFAULT_PATH",
    "resolve_path",
    "load_config",
    "dump_raw",
    "habitat_names",
    "dynamics_map",
    "persistent_names",
    "pluvial_names",
]


def load_config(path: str | os.PathLike[str] | None = None) -> types.MappingProxyType:
    """Load + validate the model constants YAML (see module docstring)."""
    return freeze(validate_model_config(path).model_dump())


# Derived API (plan §3.) ---------------------------------------------------

def dump_raw(path: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    """Flat "dotted"-key view (plan §6 test 4) for the py⇄C++ parity test.

    Species weight rows are emitted as LISTS in the canonical habitat
    order (the pre-transformed C++ std::array shape). Compare key-by-key
    (numeric tolerance 1e-9) against ``config_dump``'s JSON.
    """
    data = dict(load_config(path)) if path is not None else dict(CONFIG)
    types_list = data["habitat_types"]["types"]
    out: dict[str, Any] = {}
    out["version"] = data["version"]
    for k, v in data["contracts"].items():
        out[f"contracts.{k}"] = v
    for i, name in enumerate(types_list):
        out[f"habitat_types.types.{i}"] = name
    for k, v in data["habitat_types"]["dynamics"].items():
        out[f"habitat_types.dynamics.{k}"] = v
    out["habitat_types.num_persistent"] = sum(
        1 for v in data["habitat_types"]["dynamics"].values()
        if v == "persistent")
    for sec in ("habitat", "pluvial", "aquatic_stress", "urban", "capacity",
                "geodesy"):
        for k, v in data[sec].items():
            out[f"{sec}.{k}"] = v
    out["species.default_species"] = data["species"]["default_species"]
    out["species.k_ref"] = data["species"]["k_ref"]
    for name, row in data["species"].items():
        if name in ("default_species", "k_ref"):
            continue
        if "weights" not in row:
            continue
        out[f"species.{name}.weights"] = [
            float(row["weights"][g]) for g in types_list]
        for k in ("salinity_hi_tol_ppt", "host_seeking_scale_m",
                  "host_seeking_radius_m", "salinity_opt_ppt",
                  "salinity_slope"):
            if k in row:
                out[f"species.{name}.{k}"] = row[k]
        if "activity_weights" in row:
            out[f"species.{name}.activity_weights"] = [
                float(v) for v in row["activity_weights"]]
        if "pref" in row:
            # Parity with the C++ dump: the pref row as a HostType-ordered
            # array (human, cattle, goat, sheep, wildlife).
            out[f"species.{name}.pref"] = [
                float(row["pref"][h]) for h in
                ("human", "cattle", "goat", "sheep", "wildlife")]
    for sec in ("ingest", "adults", "eip", "transmission", "dispersal",
                "host_seeking", "oviposition", "aquatic_stages", "thermal",
                "gonotrophic", "rng"):
        for k, v in data[sec].items():
            out[f"{sec}.{k}"] = v
    return out


def habitat_names() -> tuple[str, ...]:
    """Ordered habitat type names (frozen habitat_types.types)."""
    return tuple(CONFIG["habitat_types"]["types"])


def dynamics_map() -> dict[str, str]:
    """Habitat type -> dynamics label (persistent|pluvial)."""
    return dict(CONFIG["habitat_types"]["dynamics"])


def persistent_names() -> frozenset[str]:
    """Derived habitat subsets (replaces the old PERSISTENT_TYPES const)."""
    return frozenset(
        g for g, k in dynamics_map().items() if k == "persistent")


def pluvial_names() -> frozenset[str]:
    """Derived habitat subsets (replaces the old PLUVIAL_TYPES const)."""
    return frozenset(
        g for g, k in dynamics_map().items() if k == "pluvial")


CONFIG = load_config()
