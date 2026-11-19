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


# Per-species keys added by the movement / blood / dry-season / male layers
# (plan individualization-and-movement, Paso 4).
NEW_SPECIES_KEYS: tuple[str, ...] = (
    "co2_activation_radius_m",
    "olfactory_radius_m",
    "visual_radius_m",
    "terminal_radius_m",
    "flight_speed_ms",
    "exploration_range_m",
    "exploration_step_m",
    "exploration_step_correlation",
    "casting_probability",
    "casting_angle_deg",
    "plume_memory_s",
    "anemotaxis_rule",
    "anemotaxis_deviation_deg",
    "wind_reference",
    "wind_block_threshold_ms",
    "daily_move_capacity_m",
    "directed_flight_budget_h",
    "blood_meal_target_ul",
    "first_cycle_target_ul",
    "blood_meal_size_ul",
    "meal_size_min_ul",
    "blood_meal_refractory_days",
    "probing_success_rate",
    "eggs_per_ul",
    "arrested_daily_survival",
    "gonotrophic_arrest_prob_dry",
    "aestivation_supported",
    "male_ratio",
    "male_daily_survival",
)


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
        for k in ("salinity_hi_tol_ppt", "salinity_opt_ppt",
                  "salinity_slope") + NEW_SPECIES_KEYS:
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
    # Engine-consumed sections. ``wildlife`` is deliberately absent: it is a
    # py-only input-loader section with no C++ consumer or config_dump entry
    # (task-08), so emitting it would break the py⇄C++ key parity contract.
    for sec in ("ingest", "adults", "eip", "transmission", "dispersal",
                "host_seeking", "integration", "mating", "oviposition",
                "aquatic_stages", "thermal", "gonotrophic", "rng"):
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
