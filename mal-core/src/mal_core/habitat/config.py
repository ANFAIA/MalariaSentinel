"""Loader of the single model constants YAML (plan constants-yaml §3).

``mal-core/config/model_constants.yaml`` is the ONLY source of shared
model parameters (py ⇄ C++). There are NO silent fallbacks anywhere:

* a missing key ⇒ ``SchemaError`` listing ALL missing keys at once;
* an unknown key ⇒ ``SchemaError`` listing the offenders (typo guard);
* a wrong-typed value ⇒ ``SchemaError`` with expected/actual type;
* duplicate keys inside the file ⇒ parse error.

The module exposes an immutable singleton ``CONFIG`` built at import time
(the repo already assumes import-time constants in habitat/scoring) and
``load_config(path=None)`` for re-loading (tests / calibration):

* ``path=None`` resolves ``MAL_MODEL_CONSTANTS`` from the environment or
  the default ``<mal-core>/config/model_constants.yaml``;
* the resolved path is ALWAYS logged (``model_constants: <path>``);
* the returned mapping is a ``types.MappingProxyType`` tree — writes fail
  with ``TypeError``.

Nothing in this module embeds a model-constant default: the YAML is the
source. (The rest of this file is schema/loader machinery only.)
"""
from __future__ import annotations

import logging
import math
import os
import pathlib
import types
from typing import Any

import yaml

logger = logging.getLogger(__name__)

REPO_MAL_CORE_DIR = pathlib.Path(__file__).resolve().parents[3]
DEFAULT_PATH = REPO_MAL_CORE_DIR / "config" / "model_constants.yaml"
ENV_VAR = "MAL_MODEL_CONSTANTS"

# Species rows the v1 schema knows (v2 adds melas/stephensi).
_NAMED_SPECIES = ("coluzzii", "gambiae_ss", "funestus", "arabiensis",
                  "melas", "stephensi")
_SPECIES_SCALARS = (
    "salinity_hi_tol_ppt",
    "host_seeking_scale_m",
    "host_seeking_radius_m",
    "salinity_opt_ppt",
    "salinity_slope",
)
_HOST_PREF_KEYS = ("human", " cattle", "goat", "sheep", "wildlife")
_HOST_PREF_KEYS = ("human",  "cattle", "goat", "sheep", "wildlife")
_HABITAT_TYPES_V1 = (
    "surface_persistent",
    "wetland_persistent",
    "urban_persistent",
    "wetland_pluvial",
    "open_pluvial",
    "crop_pluvial",
)

_NUM = (int, float)  # YAML numerics; bool is rejected separately


class ConfigError(Exception):
    """Base class of loader failures."""


class SchemaError(ConfigError):
    """The YAML does not satisfy the declared schema."""


# ---------------------------------------------------------------------------
# Schema (declarative tree). Leaf values are the accepted python types.
# ---------------------------------------------------------------------------

SCHEMA: dict = {
    "version": int,
    "contracts": {"env_nc": str, "cogs_state": str},
    "habitat_types": {
        "types": list,
        "dynamics": dict,
    },
    "habitat": {
        "activation_min_engine": _NUM,
        "candidate_min_engine": _NUM,
    },
    "pluvial": {
        "rain_scale_mm": _NUM,
        "dry_memory_days": _NUM,
        "delta_days": _NUM,
        "cold_start_z": _NUM,
    },
    "aquatic_stress": {
        "desicc_grace_days": _NUM,
        "desicc_base_daily": _NUM,
        "desicc_ramp_decay": _NUM,
        "wash_threshold_mm": _NUM,
        "wash_fraction_max": _NUM,
        "vulnerable_instar_max": int,
    },
    "urban": {
        "beta_urban": _NUM,
        "rain_pools_built_damage": _NUM,
    },
    "species": {
        "default_species": str,
        "k_ref": _NUM,
        **{
            name: {
                "weights": dict,
                "activity_weights": list,
                "pref": dict,
                **{k: _NUM for k in _SPECIES_SCALARS},
            }
            for name in _NAMED_SPECIES
        },
        "neutral": {"weights": dict},
    },
    "capacity": {"persistent_availability": _NUM},
    "geodesy": {
        "earth_radius_m": _NUM,
        "metres_per_deg_lat": _NUM,
    },
    "ingest": {
        "nodata_sentinel": _NUM,
        "nodata_sentinel_int": int,
        "coastline_buffer_m": _NUM,
        "cell_size_hint_m": _NUM,
        "candidate_min_ingest": _NUM,
        "min_dilation_radius_cells": int,
        "fill_frac_valid_max": _NUM,
        "ocean_mask_threshold": _NUM,
        "land_mask_threshold": _NUM,
        "valid_count_epsilon": _NUM,
        "grid_degrees_step_max": int,
        "nc_compression_level": int,
    },
    "adults": {
        "daily_mort_basal": _NUM,
        "opt_c": _NUM,
        "sigma_c": _NUM,
        "mort_cap": _NUM,
        "mort_floor": _NUM,
    },
    "eip": {"base_c": _NUM, "threshold_gd": _NUM},
    "dispersal": {
        "adult_prob_day": _NUM,
        "adult_sigma_m": _NUM,
        "adult_max_m": _NUM,
        "wind_migration_prob": _NUM,
        "wind_flight_hours": _NUM,
        "wind_survival": _NUM,
        "wind_self_speed_ms": _NUM,
        "flight_hour": int,
    },
    "host_seeking": {
        "starvation_days": int,
        "indoor_attraction_add": _NUM,
        "urbanicity_add": _NUM,
        "indoor_fraction_urban": _NUM,
        "indoor_fraction_rural": _NUM,
    },
    "oviposition": {
        "scale_m": _NUM,
        "radius_m": _NUM,
        "timeout_days": int,
    },
    "aquatic_stages": {
        "egg_daily_mort": _NUM,
        "pupa_daily_mort": _NUM,
        "larva_bh_s0": _NUM,
        "larva_bh_alpha": _NUM,
        "last_larval_instar": int,
        "salinity_missing_psu": _NUM,
    },
    "rng": {
        "aquatic_seed_washout": int,
        "aquatic_seed_stage_mortality": int,
        "aquatic_seed_larva_mortality": int,
    },
}

# Species-only sections with looser key sets (v1):
_SPECIES_ROW_KEYS = frozenset(
    ("weights", "activity_weights", "pref") + _SPECIES_SCALARS)


# ---------------------------------------------------------------------------
# YAML parsing with duplicate-key detection (invariant §6-5f).
# ---------------------------------------------------------------------------

class _StrictLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        seen = set()
        for key_node, _value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in seen:
                raise yaml.YAMLError(
                    f"duplicate key '{key}' in model_constants YAML")
            seen.add(key)
        return super().construct_mapping(node, deep=deep)


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

def _raise_schema_errors(errors: list[str], prefix: str, path: Any) -> None:
    if errors:
        n = len(errors)
        detail = "\n  ".join(errors)
        raise SchemaError(
            f"{prefix}: {n} problem{'s' if n > 1 else ''} in "
            f"{path}:\n  {detail}")


def _check_tree(node: Any, schema: dict, missing: list[str],
                unknown: list[str], bad_type: list[str],
                prefix: str = "") -> None:
    if not isinstance(node, dict):
        missing.append(prefix or "(root)")
        return
    for key in schema:
        dotted = f"{prefix}{key}" if prefix else key
        if key not in node:
            missing.append(dotted)
    for key, value in node.items():
        dotted = f"{prefix}{key}" if prefix else key
        if key not in schema:
            unknown.append(dotted)
            continue
        expected = schema[key]
        if isinstance(expected, dict):
            _check_tree(value, expected, missing, unknown, bad_type,
                        prefix=dotted + ".")
        elif isinstance(value, bool):
            # bool is an int subclass; model keys never accept bools.
            bad_type.append(f"{dotted} (expected numeric/typed key, got bool)")
        elif not isinstance(value, expected):
            got = type(value).__name__
            want = getattr(expected, "__name__", "number")
            bad_type.append(f"{dotted} (expected {want}, got {got})")


def _check_invariants(data: dict, errors: list[str]) -> None:
    types_list = data["habitat_types"]["types"]
    dynamics = data["habitat_types"]["dynamics"]
    if tuple(types_list) != _HABITAT_TYPES_V1:
        errors.append(
            "habitat_types.types (frozen contract): expected "
            f"{list(_HABITAT_TYPES_V1)}, got {types_list}")
    if set(dynamics) != set(_HABITAT_TYPES_V1):
        errors.append(
            "habitat_types.dynamics keys must be exactly the habitat types")
    for g, kind in dynamics.items():
        if kind not in ("persistent", "pluvial"):
            errors.append(
                f"habitat_types.dynamics.{g}: got {kind!r} "
                "(persistent|pluvial)")
    n_persistent = sum(1 for k in dynamics.values() if k == "persistent")
    if not (1 <= n_persistent <= len(types_list)):
        errors.append(
            f"num_persistent derived = {n_persistent}, out of range "
            f"[1, {len(types_list)}]")

    species = data["species"]
    if species["default_species"] not in _NAMED_SPECIES:
        errors.append(
            "species.default_species "
            f"{species['default_species']!r} is not a named species row")

    for name in _NAMED_SPECIES + ("neutral",):
        row = species[name]
        weights = row["weights"]
        if set(weights) != set(types_list):
            errors.append(
                f"species.{name}.weights keys {sorted(weights)} != "
                f"habitat_types.types")
            continue
        total = sum(weights.values())
        if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=1e-9):
            errors.append(
                f"species.{name}.weights sum {total!r} != 1.0 (±1e-9)")
        if name == "neutral":
            continue
        if not (set(row["pref"]) == set(_HOST_PREF_KEYS)):
            errors.append(
                "species.%s.pref keys %s != host keys" % (
                    name, sorted(row["pref"])))
        else:
            pref_total = sum(row["pref"].values())
            if not math.isclose(pref_total, 1.0, rel_tol=0.0, abs_tol=1e-9):
                errors.append(
                    "species.%s.pref sum %r != 1.0 (±1e-9)" % (
                        name, pref_total))
        act = row["activity_weights"]
        if len(act) != 4:
            errors.append(
                "species.%s.activity_weights: expected 4 phases, got %d" % (
                    name, len(act)))
        else:
            act_total = sum(act)
            if not math.isclose(act_total, 1.0, rel_tol=0.0, abs_tol=1e-9):
                errors.append(
                    "species.%s.activity_weights sum %r != 1.0 (±1e-9)" % (
                        name, act_total))
        for g, w in weights.items():
            if not isinstance(w, (int, float)) or isinstance(w, bool):
                errors.append(
                    f"species.{name}.weights.{g}: expected number, "
                    f"got {type(w).__name__}")

    geo = data["geodesy"]
    expected_mpd = math.pi * geo["earth_radius_m"] / 180.0
    if not math.isclose(float(geo["metres_per_deg_lat"]), expected_mpd,
                        rel_tol=0.0, abs_tol=1e-9):
        errors.append(
            "geodesy.metres_per_deg_lat must equal "
            f"pi·earth_radius_m/180 = {expected_mpd!r} (±1e-9), "
            f"got {geo['metres_per_deg_lat']!r}")

    for key, value in data["contracts"].items():
        if not (isinstance(value, str) and value and "." in value and
                value.replace(".", "").isdigit()):
            errors.append(
                f"contracts.{key}: expected 'mayor.menor' string, got "
                f"{value!r}")
    nodata = data["ingest"]["nodata_sentinel"]
    nodata_int = data["ingest"]["nodata_sentinel_int"]
    if not float(nodata) < 0:
        errors.append("ingest.nodata_sentinel must be negative")
    if nodata_int >= 0:
        errors.append("ingest.nodata_sentinel_int must be negative")


def freeze(obj: Any) -> Any:
    """Expose a loaded tree as immutable mapping proxies."""
    if isinstance(obj, dict):
        return types.MappingProxyType(
            {k: freeze(v) for k, v in obj.items()})
    return obj


def resolve_path(path: str | os.PathLike | None = None) -> pathlib.Path:
    """Resolve the constants path (explicit > MAL_MODEL_CONSTANTS > default)."""
    if path is not None:
        return pathlib.Path(path)
    env = os.environ.get(ENV_VAR)
    if env:
        return pathlib.Path(env)
    return DEFAULT_PATH


def load_config(path: str | os.PathLike | None = None) -> types.MappingProxyType:
    """Load + validate the model constants YAML (see module docstring)."""
    resolved = resolve_path(path)
    try:
        with open(resolved, "r", encoding="utf-8") as fh:
            raw_text = fh.read()
    except OSError as exc:
        raise SchemaError(
            f"model constants file not readable ({ENV_VAR} or default): "
            f"{resolved} ({exc})") from exc
    try:
        data = yaml.load(raw_text, Loader=_StrictLoader)
    except yaml.YAMLError as exc:
        raise SchemaError(f"model_constants YAML parse error in "
                          f"{resolved}: {exc}") from exc

    missing: list[str] = []
    unknown: list[str] = []
    bad_type: list[str] = []
    _check_tree(data, SCHEMA, missing, unknown, bad_type)
    errors: list[str] = []
    if missing:
        errors.append("missing keys:\n      " + "\n      ".join(missing))
    if unknown:
        errors.append("unrecognized keys:\n      " + "\n      ".join(unknown))
    if bad_type:
        errors.append("wrong types:\n      " + "\n      ".join(bad_type))
    _raise_schema_errors(errors, "schema", resolved)

    errors = []
    _check_invariants(data, errors)
    _raise_schema_errors(errors, "invariants", resolved)

    logger.info("model_constants: %s", resolved)
    return freeze(data)


# Derived API (plan §3.) ---------------------------------------------------

def dump_raw(path: str | os.PathLike | None = None) -> dict[str, Any]:
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
                float(row["pref"][h]) for h in _HOST_PREF_KEYS]
    for sec in ("ingest", "adults", "eip", "dispersal", "host_seeking",
                "oviposition", "aquatic_stages", "rng"):
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
