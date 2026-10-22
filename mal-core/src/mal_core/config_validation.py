"""Single validator of ``mal-core/config/model_constants.yaml`` (R2).

``model_constants.yaml`` is the ONLY source of shared model parameters
(py ⇄ C++).  This module is the ONLY place where its content is checked:
every consumer (CLI, thin loader, ingest scripts) delegates here.

Contract of the validator:

* **No defaults.**  Every key is required; a missing key is an error.
* **``extra="forbid"`` at every level.**  A typo or an unmodelled key is an
  error, never silently ignored.
* **Strict types.**  ``2`` is accepted where a float is expected, but
  ``"2"``/``true`` are not.
* **All problems at once.**  Missing keys are collected and reported
  together, then unknown keys, wrong types and broken invariants.
* **Frozen-friendly.**  Models are immutable; derived values (e.g.
  ``num_persistent``) are computed, never stored in the YAML.

Invariants implemented (plan constants-yaml v1 §3/§6 plus the existing
loader tests):

* ``Σ species.<row>.weights == 1`` (±1e-9) for the six named rows and
  ``neutral``; weight keys are exactly ``habitat_types.types``.
* ``Σ species.<row>.pref == 1`` (±1e-9); keys are exactly the host types.
* ``Σ species.<row>.activity_weights == 1`` (±1e-9); exactly 4 phases.
* ``habitat_types.types`` equals the frozen habitat order; ``dynamics``
  covers exactly those keys; ``count(dynamics == persistent) >= 1``.
* ``species.default_species`` is one of the named species rows.
* ``geodesy.metres_per_deg_lat == π · earth_radius_m / 180`` (±1e-9).
* ``contracts.*`` match ``mayor.menor``; ``ingest.nodata_*`` are negative;
  ``species.k_ref > 0``; ``version > 0``.
* ``transmission.*`` probabilities/fractions in ``[0, 1]`` and durations
  positive; ``thermal.*`` thresholds ordered (tmin < topt < tmax) with
  positive scales; ``gonotrophic`` egg batch ``0 < min <= mean <= max <= n``;
  movement kernels positive, ``oviposition.min_attraction`` in ``[0, 1]``
  and ``dispersal.night_*_hour`` in ``[0, 24)`` with a non-empty window.

Growing the schema (R2): add the field to the matching ``BaseModel``
below.  Unknown keys fail loudly, so a YAML edit without a matching model
edit can never pass validation.

Path resolution is explicit > ``MAL_MODEL_CONSTANTS`` > repo default, and
the resolved path is ALWAYS logged as ``model_constants: <path>``.
"""
from __future__ import annotations

import logging
import math
import os
import pathlib
import re
import types
from typing import Any, Literal

import pydantic
import yaml
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

logger = logging.getLogger(__name__)

REPO_MAL_CORE_DIR = pathlib.Path(__file__).resolve().parents[2]
DEFAULT_PATH = REPO_MAL_CORE_DIR / "config" / "model_constants.yaml"
ENV_VAR = "MAL_MODEL_CONSTANTS"

# Frozen habitat order (contract: changing it requires a version bump).
HABITAT_TYPES_V1: tuple[str, ...] = (
    "surface_persistent",
    "wetland_persistent",
    "urban_persistent",
    "wetland_pluvial",
    "open_pluvial",
    "crop_pluvial",
)

# Host types in ``species.<row>.pref`` (HostType order, never positional).
HOST_PREF_KEYS: tuple[str, ...] = (
    "human", "cattle", "goat", "sheep", "wildlife")

# Species rows with a full parameter set (v2).
NAMED_SPECIES: tuple[str, ...] = (
    "coluzzii", "gambiae_ss", "funestus", "arabiensis", "melas",
    "stephensi")

ACTIVITY_PHASES = 4
_CONTRACT_RE = re.compile(r"^\d+\.\d+$")
_TOL = 1e-9


class ConfigError(Exception):
    """Base class of model-constants failures."""


class SchemaError(ConfigError):
    """The YAML does not satisfy the declared schema/invariants."""


class _StrictModel(BaseModel):
    """Base: no extra keys, immutable, strict scalar types."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


# ---------------------------------------------------------------------------
# One model per YAML section.  Adding a YAML key means adding a field here.
# ---------------------------------------------------------------------------

class Contracts(_StrictModel):
    env_nc: str
    cogs_state: str


class HabitatTypes(_StrictModel):
    types: list[str]
    dynamics: dict[str, Literal["persistent", "pluvial"]]


class Habitat(_StrictModel):
    activation_min_engine: float
    candidate_min_engine: float


class Pluvial(_StrictModel):
    rain_scale_mm: float
    dry_memory_days: float
    delta_days: float
    cold_start_z: float


class AquaticStress(_StrictModel):
    desicc_grace_days: float
    desicc_base_daily: float
    desicc_ramp_decay: float
    wash_threshold_mm: float
    wash_fraction_max: float
    vulnerable_instar_max: int


class Urban(_StrictModel):
    beta_urban: float
    rain_pools_built_damage: float


class SpeciesRow(_StrictModel):
    """Full parameter row for one of the six named species."""

    weights: dict[str, float]
    activity_weights: list[float] = Field(
        min_length=ACTIVITY_PHASES, max_length=ACTIVITY_PHASES)
    pref: dict[str, float]
    salinity_opt_ppt: float
    salinity_hi_tol_ppt: float
    salinity_slope: float
    host_seeking_scale_m: float
    host_seeking_radius_m: float


class NeutralRow(_StrictModel):
    """Species-neutral row: the engine only consumes its habitat weights."""

    weights: dict[str, float]


class Species(_StrictModel):
    default_species: str
    k_ref: float
    coluzzii: SpeciesRow
    gambiae_ss: SpeciesRow
    funestus: SpeciesRow
    arabiensis: SpeciesRow
    melas: SpeciesRow
    stephensi: SpeciesRow
    neutral: NeutralRow

    def named_rows(self) -> dict[str, SpeciesRow]:
        return {name: getattr(self, name) for name in NAMED_SPECIES}


class Capacity(_StrictModel):
    persistent_availability: float


class Geodesy(_StrictModel):
    earth_radius_m: float
    metres_per_deg_lat: float


class Ingest(_StrictModel):
    nodata_sentinel: float
    nodata_sentinel_int: int
    residential_from_indoor_frac: float
    coastline_buffer_m: float
    cell_size_hint_m: float
    candidate_min_ingest: float
    min_dilation_radius_cells: int
    fill_frac_valid_max: float
    ocean_mask_threshold: float
    land_mask_threshold: float
    valid_count_epsilon: float
    grid_degrees_step_max: int
    nc_compression_level: int


class Adults(_StrictModel):
    daily_mort_basal: float
    opt_c: float
    sigma_c: float
    mort_cap: float
    mort_floor: float


class Eip(_StrictModel):
    base_c: float
    threshold_gd: float


class Transmission(_StrictModel):
    beta_hv: float
    beta_vh: float
    human_incubation_days: int
    human_infectious_days: int
    human_immunity_days: int
    initial_human_prevalence: float
    initial_vector_infected_frac: float


class Thermal(_StrictModel):
    efd_max_eggs_per_day: float
    efd_tmin_c: float
    efd_tmax_c: float
    efd_topt_c: float
    egg_development_tmin_c: float
    egg_development_tmax_c: float
    egg_development_scale: float
    larva_development_tmin_c: float
    larva_development_tmax_c: float
    larva_development_scale: float
    pupa_development_tmin_c: float
    pupa_development_tmax_c: float
    pupa_development_scale: float


class Gonotrophic(_StrictModel):
    cycle_duration_days: float
    first_cycle_days: float
    feeding_success_rate: float
    egg_batch_mean: int
    egg_batch_n: int
    egg_batch_min: int
    egg_batch_max: int
    resting_duration_days: float


class Dispersal(_StrictModel):
    adult_prob_day: float
    adult_sigma_m: float
    adult_max_m: float
    wind_migration_prob: float
    wind_flight_hours: float
    wind_survival: float
    wind_self_speed_ms: float
    flight_hour: int
    host_flight_step_m: float
    snap_radius_m: float
    night_start_hour: int
    night_end_hour: int


class HostSeeking(_StrictModel):
    starvation_days: int
    indoor_attraction_add: float
    urbanicity_add: float
    indoor_fraction_urban: float
    indoor_fraction_rural: float
    detect_range_m: float
    approach_step_m: float


class Oviposition(_StrictModel):
    scale_m: float
    detect_range_m: float
    step_m: float
    min_attraction: float
    timeout_days: int


class AquaticStages(_StrictModel):
    egg_daily_mort: float
    pupa_daily_mort: float
    larva_bh_s0: float
    larva_bh_alpha: float
    last_larval_instar: int
    salinity_missing_psu: float


class Rng(_StrictModel):
    aquatic_seed_washout: int
    aquatic_seed_stage_mortality: int
    aquatic_seed_larva_mortality: int


class ModelConfig(_StrictModel):
    """Whole-file schema + cross-section invariants."""

    version: int
    contracts: Contracts
    habitat_types: HabitatTypes
    habitat: Habitat
    pluvial: Pluvial
    aquatic_stress: AquaticStress
    urban: Urban
    species: Species
    capacity: Capacity
    geodesy: Geodesy
    ingest: Ingest
    adults: Adults
    eip: Eip
    transmission: Transmission
    dispersal: Dispersal
    host_seeking: HostSeeking
    oviposition: Oviposition
    aquatic_stages: AquaticStages
    thermal: Thermal
    gonotrophic: Gonotrophic
    rng: Rng

    _source_path: pathlib.Path | None = PrivateAttr(default=None)

    @property
    def source_path(self) -> pathlib.Path | None:
        """Path the config was loaded from (set by ``validate_model_config``)."""
        return self._source_path

    @pydantic.model_validator(mode="after")
    def _check_invariants(self) -> "ModelConfig":
        errors: list[str] = []
        types_list = self.habitat_types.types
        dynamics = self.habitat_types.dynamics

        if self.version <= 0:
            errors.append("version must be positive")

        for name, value in (
                ("contracts.env_nc", self.contracts.env_nc),
                ("contracts.cogs_state", self.contracts.cogs_state)):
            if not _CONTRACT_RE.match(value):
                errors.append(
                    f"{name}: expected 'mayor.menor' string, got {value!r}")

        if tuple(types_list) != HABITAT_TYPES_V1:
            errors.append(
                "habitat_types.types (frozen contract): expected "
                f"{list(HABITAT_TYPES_V1)}, got {types_list}")
        if set(dynamics) != set(types_list):
            errors.append(
                "habitat_types.dynamics keys must be exactly "
                "habitat_types.types")
        n_persistent = sum(1 for kind in dynamics.values()
                           if kind == "persistent")
        if not (1 <= n_persistent <= len(types_list)):
            errors.append(
                f"habitat_types.num_persistent (derived) = {n_persistent}, "
                f"out of range [1, {len(types_list)}]")

        if self.species.default_species not in NAMED_SPECIES:
            errors.append(
                "species.default_species "
                f"{self.species.default_species!r} is not a named species row")

        rows: list[tuple[str, dict[str, float]]] = [
            (name, row.weights) for name, row in self.species.named_rows().items()]
        rows.append(("neutral", self.species.neutral.weights))
        expected_weights = set(types_list)
        for name, weights in rows:
            got = set(weights)
            if got != expected_weights:
                missing = sorted(expected_weights - got)
                extra = sorted(got - expected_weights)
                detail = []
                if missing:
                    detail.append(f"missing {missing}")
                if extra:
                    detail.append(f"unknown {extra}")
                errors.append(
                    f"species.{name}.weights keys != habitat_types.types "
                    f"({'; '.join(detail)})")
                continue
            total = sum(weights.values())
            if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=_TOL):
                errors.append(
                    f"species.{name}.weights sum {total!r} != 1.0 (±1e-9)")
            # The engine has no ZoneId for wetland_pluvial: a non-zero
            # weight would be silently dropped on the C++ side (plan §2).
            if weights.get("wetland_pluvial", 0.0) != 0.0:
                errors.append(
                    f"species.{name}.weights.wetland_pluvial must be 0.00 "
                    "(no C++ ZoneId), got "
                    f"{weights['wetland_pluvial']!r}")

        for name, row in self.species.named_rows().items():
            pref_keys = set(row.pref)
            if pref_keys != set(HOST_PREF_KEYS):
                errors.append(
                    f"species.{name}.pref keys {sorted(pref_keys)} != "
                    f"host keys {list(HOST_PREF_KEYS)}")
            else:
                pref_total = sum(row.pref.values())
                if not math.isclose(pref_total, 1.0, rel_tol=0.0,
                                    abs_tol=_TOL):
                    errors.append(
                        f"species.{name}.pref sum {pref_total!r} != 1.0 "
                        "(±1e-9)")
            if len(row.activity_weights) != ACTIVITY_PHASES:
                # Enforced by the field constraints; kept for one message.
                errors.append(
                    f"species.{name}.activity_weights: expected "
                    f"{ACTIVITY_PHASES} phases, got "
                    f"{len(row.activity_weights)}")
            else:
                act_total = sum(row.activity_weights)
                if not math.isclose(act_total, 1.0, rel_tol=0.0,
                                    abs_tol=_TOL):
                    errors.append(
                        f"species.{name}.activity_weights sum {act_total!r} "
                        "!= 1.0 (±1e-9)")

        if self.species.k_ref <= 0:
            errors.append(
                f"species.k_ref must be > 0, got {self.species.k_ref!r}")

        expected_mpd = math.pi * self.geodesy.earth_radius_m / 180.0
        if not math.isclose(
                self.geodesy.metres_per_deg_lat, expected_mpd,
                rel_tol=0.0, abs_tol=_TOL):
            errors.append(
                "geodesy.metres_per_deg_lat must equal "
                f"π·earth_radius_m/180 = {expected_mpd!r} (±1e-9), got "
                f"{self.geodesy.metres_per_deg_lat!r}")

        if self.ingest.nodata_sentinel >= 0:
            errors.append(
                "ingest.nodata_sentinel must be negative, got "
                f"{self.ingest.nodata_sentinel!r}")
        if self.ingest.nodata_sentinel_int >= 0:
            errors.append(
                "ingest.nodata_sentinel_int must be negative, got "
                f"{self.ingest.nodata_sentinel_int!r}")

        # [0, 1] fractions/probabilities (task-07 sections).
        for name, value in (
                ("transmission.beta_hv", self.transmission.beta_hv),
                ("transmission.beta_vh", self.transmission.beta_vh),
                ("transmission.initial_human_prevalence",
                 self.transmission.initial_human_prevalence),
                ("transmission.initial_vector_infected_frac",
                 self.transmission.initial_vector_infected_frac),
                ("gonotrophic.feeding_success_rate",
                 self.gonotrophic.feeding_success_rate),
                ("oviposition.min_attraction",
                 self.oviposition.min_attraction),
                ("ingest.residential_from_indoor_frac",
                 self.ingest.residential_from_indoor_frac)):
            if not (0.0 <= value <= 1.0):
                errors.append(f"{name} must be in [0, 1], got {value!r}")

        for name, value in (
                ("transmission.human_incubation_days",
                 self.transmission.human_incubation_days),
                ("transmission.human_infectious_days",
                 self.transmission.human_infectious_days),
                ("transmission.human_immunity_days",
                 self.transmission.human_immunity_days),
                ("gonotrophic.cycle_duration_days",
                 self.gonotrophic.cycle_duration_days),
                ("gonotrophic.first_cycle_days",
                 self.gonotrophic.first_cycle_days),
                ("gonotrophic.resting_duration_days",
                 self.gonotrophic.resting_duration_days)):
            if value <= 0:
                errors.append(f"{name} must be > 0, got {value!r}")

        thermal = self.thermal
        if not (thermal.efd_tmin_c < thermal.efd_topt_c < thermal.efd_tmax_c):
            errors.append(
                "thermal.efd_* must satisfy tmin < topt < tmax, got "
                f"{thermal.efd_tmin_c!r}/{thermal.efd_topt_c!r}/"
                f"{thermal.efd_tmax_c!r}")
        if thermal.efd_max_eggs_per_day <= 0:
            errors.append(
                "thermal.efd_max_eggs_per_day must be > 0, got "
                f"{thermal.efd_max_eggs_per_day!r}")
        for stage in ("egg", "larva", "pupa"):
            tmin = getattr(thermal, f"{stage}_development_tmin_c")
            tmax = getattr(thermal, f"{stage}_development_tmax_c")
            scale = getattr(thermal, f"{stage}_development_scale")
            if not tmin < tmax:
                errors.append(
                    f"thermal.{stage}_development_tmin_c must be < "
                    f"{stage}_development_tmax_c, got {tmin!r}/{tmax!r}")
            if scale <= 0:
                errors.append(
                    f"thermal.{stage}_development_scale must be > 0, got "
                    f"{scale!r}")

        gono = self.gonotrophic
        if gono.egg_batch_n <= 0:
            errors.append(
                f"gonotrophic.egg_batch_n must be > 0, got {gono.egg_batch_n!r}")
        if not (0 < gono.egg_batch_min <= gono.egg_batch_mean
                <= gono.egg_batch_max <= gono.egg_batch_n):
            errors.append(
                "gonotrophic egg batch must satisfy 0 < min <= mean <= max "
                f"<= n, got {gono.egg_batch_min!r}/{gono.egg_batch_mean!r}/"
                f"{gono.egg_batch_max!r}/{gono.egg_batch_n!r}")

        if self.host_seeking.detect_range_m <= 0:
            errors.append(
                "host_seeking.detect_range_m must be > 0, got "
                f"{self.host_seeking.detect_range_m!r}")
        if self.host_seeking.approach_step_m <= 0:
            errors.append(
                "host_seeking.approach_step_m must be > 0, got "
                f"{self.host_seeking.approach_step_m!r}")
        if self.oviposition.detect_range_m <= 0:
            errors.append(
                "oviposition.detect_range_m must be > 0, got "
                f"{self.oviposition.detect_range_m!r}")
        if self.oviposition.step_m <= 0:
            errors.append(
                f"oviposition.step_m must be > 0, got "
                f"{self.oviposition.step_m!r}")

        for name, hour in (("dispersal.night_start_hour",
                            self.dispersal.night_start_hour),
                           ("dispersal.night_end_hour",
                            self.dispersal.night_end_hour)):
            if not (0 <= hour < 24):
                errors.append(f"{name} must be in [0, 24), got {hour!r}")
        if self.dispersal.night_start_hour == self.dispersal.night_end_hour:
            errors.append(
                "dispersal.night_start_hour must differ from night_end_hour")

        if errors:
            raise ValueError(
                "invariants:\n      " + "\n      ".join(errors))
        return self

    # Derived API (never stored in the YAML; plan v1 §9.5).
    @property
    def num_persistent(self) -> int:
        return sum(1 for kind in self.habitat_types.dynamics.values()
                   if kind == "persistent")

    @property
    def persistent_names(self) -> frozenset[str]:
        return frozenset(
            name for name, kind in self.habitat_types.dynamics.items()
            if kind == "persistent")

    @property
    def pluvial_names(self) -> frozenset[str]:
        return frozenset(
            name for name, kind in self.habitat_types.dynamics.items()
            if kind == "pluvial")


# ---------------------------------------------------------------------------
# YAML parsing with duplicate-key detection
# ---------------------------------------------------------------------------

class _StrictLoader(yaml.SafeLoader):
    """SafeLoader that rejects a key re-declared in the same mapping."""

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
# Public API
# ---------------------------------------------------------------------------

def resolve_path(path: str | os.PathLike[str] | None = None) -> pathlib.Path:
    """Resolve the constants path (explicit > env var > repo default)."""
    if path is not None:
        return pathlib.Path(path)
    env = os.environ.get(ENV_VAR)
    if env:
        return pathlib.Path(env)
    return DEFAULT_PATH


def _expected_text(error: dict[str, Any]) -> str:
    """Human wording for a pydantic type error."""
    kind = error["type"]
    labels = {
        "float_type": "float",
        "int_type": "int",
        "string_type": "str",
        "bool_type": "bool",
        "list_type": "list",
        "dict_type": "map",
        "model_type": "map",
    }
    if kind in labels:
        return labels[kind]
    if kind == "too_short":
        return f"at least {error['ctx']['min_length']} items"
    if kind == "too_long":
        return f"at most {error['ctx']['max_length']} items"
    if kind == "string_pattern_mismatch":
        return f"pattern {error['ctx']['pattern']!r}"
    return error["msg"].lower()


def _format_errors(exc: pydantic.ValidationError, path: pathlib.Path) -> str:
    missing: list[str] = []
    unknown: list[str] = []
    wrong_type: list[str] = []
    invariants: list[str] = []

    for error in exc.errors():
        loc = ".".join(str(part) for part in error["loc"])
        if not loc:
            loc = "(root)"
        kind = error["type"]
        if kind == "missing":
            missing.append(loc)
        elif kind == "extra_forbidden":
            unknown.append(loc)
        elif kind == "value_error":
            message = error["msg"]
            prefix = "Value error, "
            if message.startswith(prefix):
                message = message[len(prefix):]
            invariants.append(message)
        else:
            got = error.get("input")
            wrong_type.append(
                f"{loc} (expected {_expected_text(error)}, got "
                f"{type(got).__name__} {got!r})")

    blocks: list[str] = []
    if missing:
        blocks.append("missing keys:\n      " + "\n      ".join(missing))
    if unknown:
        blocks.append("unrecognized keys:\n      " + "\n      ".join(unknown))
    if wrong_type:
        blocks.append("wrong types:\n      " + "\n      ".join(wrong_type))
    if invariants:
        blocks.append("invariants:\n      " + "\n      ".join(invariants))

    n = len(missing) + len(unknown) + len(wrong_type) + len(invariants)
    detail = "\n  ".join(blocks) if blocks else "unknown validation error"
    return (f"model_constants: {n} problem{'s' if n != 1 else ''} in {path}:\n"
            f"  {detail}")


def validate_model_config(
        path: str | os.PathLike[str] | None = None) -> ModelConfig:
    """Load, validate and return the typed model constants.

    Raises ``SchemaError`` listing ALL problems found (missing keys,
    unknown keys, wrong types, broken invariants) and naming the file.
    """
    resolved = resolve_path(path)
    try:
        raw_text = resolved.read_text(encoding="utf-8")
    except OSError as exc:
        raise SchemaError(
            "model constants file not readable "
            f"({ENV_VAR} or default): {resolved} ({exc})") from exc

    try:
        data = yaml.load(raw_text, Loader=_StrictLoader)
    except yaml.YAMLError as exc:
        raise SchemaError(
            f"model_constants YAML parse error in {resolved}: {exc}") from exc

    try:
        cfg = ModelConfig.model_validate(data)
    except pydantic.ValidationError as exc:
        raise SchemaError(_format_errors(exc, resolved)) from exc

    object.__setattr__(cfg, "_source_path", resolved)
    # DEBUG, not INFO: the CLI already echoes the resolved path once for the
    # user (task-06 decision 6). INFO here duplicated that line whenever the
    # embedding app configured logging at INFO.
    logger.debug("model_constants: %s", resolved)
    return cfg


def ensure_valid(
        path: str | os.PathLike[str] | None = None) -> ModelConfig:
    """CLI-facing wrapper: validate or exit with the full message."""
    try:
        return validate_model_config(path)
    except SchemaError as exc:
        raise SystemExit(str(exc)) from None


def freeze(obj: Any) -> Any:
    """Expose a loaded tree as immutable mapping proxies."""
    if isinstance(obj, dict):
        return types.MappingProxyType(
            {key: freeze(value) for key, value in obj.items()})
    return obj


def _schema_tree(model: type[BaseModel]) -> dict[str, Any]:
    """Declarative view of the schema, derived from the pydantic models."""
    tree: dict[str, Any] = {}
    for name, field in model.model_fields.items():
        annotation = field.annotation
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            tree[name] = _schema_tree(annotation)
        else:
            tree[name] = annotation
    return tree


#: Declarative schema tree (derived from the models, never from the YAML).
SCHEMA: dict[str, Any] = _schema_tree(ModelConfig)

__all__ = [
    "ACTIVITY_PHASES",
    "ConfigError",
    "DEFAULT_PATH",
    "ENV_VAR",
    "HABITAT_TYPES_V1",
    "HOST_PREF_KEYS",
    "ModelConfig",
    "NAMED_SPECIES",
    "SCHEMA",
    "SchemaError",
    "ensure_valid",
    "freeze",
    "resolve_path",
    "validate_model_config",
]
