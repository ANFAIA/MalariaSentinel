"""Single-validator contract (Task 03).

These tests protect the one thing future YAML edits must not break: the
schema in :mod:`mal_core.config_validation` covers EVERY key of
``model_constants.yaml``, rejects unknown keys/types, enforces the plan v1
invariants, and gates the CLI before any command runs.
"""
from __future__ import annotations

import logging
import pathlib

import pydantic
import pytest
import yaml as _yaml
from mal_core import config_validation as cv
from mal_core.config_validation import (
    DEFAULT_PATH,
    HABITAT_TYPES_V1,
    ModelConfig,
    SchemaError,
    ensure_valid,
    validate_model_config,
)
from typer.testing import CliRunner

_DEFAULT_TEXT = DEFAULT_PATH.read_text(encoding="utf-8")


def _tmp_yaml(tmp_path: pathlib.Path, mutate) -> pathlib.Path:
    data = _yaml.safe_load(_DEFAULT_TEXT)
    mutate(data)
    path = tmp_path / "model_constants.yaml"
    path.write_text(_yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def _message(path: pathlib.Path) -> str:
    with pytest.raises(SchemaError) as exc:
        validate_model_config(path)
    return str(exc.value)


# -- valid file + typed exposure --------------------------------------------

def test_canonical_yaml_validates_and_is_typed():
    cfg = validate_model_config()
    assert isinstance(cfg, ModelConfig)
    assert cfg.version == 2
    assert isinstance(cfg.pluvial.rain_scale_mm, float)
    assert cfg.pluvial.rain_scale_mm == 2.5
    assert cfg.num_persistent == 3
    assert cfg.persistent_names == frozenset(
        {"surface_persistent", "wetland_persistent", "urban_persistent"})
    assert cfg.pluvial_names == frozenset(
        {"wetland_pluvial", "open_pluvial", "crop_pluvial"})
    assert cfg.species.coluzzii.weights["open_pluvial"] == 0.25
    assert cfg.species.default_species == "coluzzii"


def test_logs_resolved_path(tmp_path, caplog):
    path = _tmp_yaml(tmp_path, lambda data: None)
    with caplog.at_level(logging.DEBUG, logger="mal_core.config_validation"):
        validate_model_config(path)
    assert f"model_constants: {path}" in caplog.text


def test_ensure_valid_raises_system_exit(tmp_path, capsys):
    path = _tmp_yaml(
        tmp_path, lambda data: data["pluvial"].pop("rain_scale_mm"))
    with pytest.raises(SystemExit) as exc:
        ensure_valid(path)
    assert "pluvial.rain_scale_mm" in str(exc.value)
    assert str(path) in str(exc.value)


# -- no defaults, extra=forbid, immutability --------------------------------

def _all_models() -> list[type[pydantic.BaseModel]]:
    found = []
    for value in vars(cv).values():
        if (isinstance(value, type) and issubclass(value, pydantic.BaseModel)
                and value is not pydantic.BaseModel):
            found.append(value)
    return found


def test_no_model_has_defaults():
    for model in _all_models():
        for name, field in model.model_fields.items():
            assert field.is_required(), f"{model.__name__}.{name} has a default"


def test_every_model_forbids_extra_and_is_frozen():
    for model in _all_models():
        assert model.model_config.get("extra") == "forbid", model.__name__
        assert model.model_config.get("frozen") is True, model.__name__


# -- one missing key per section (parametrised) -----------------------------

_MISSING_CASES = [
    ("version",),
    ("contracts", "env_nc"),
    ("habitat_types", "types"),
    ("habitat", "activation_min_engine"),
    ("pluvial", "rain_scale_mm"),
    ("aquatic_stress", "desicc_grace_days"),
    ("urban", "beta_urban"),
    ("species", "default_species"),
    ("species", "coluzzii", "weights"),
    ("species", "funestus", "pref"),
    ("species", "neutral", "weights"),
    ("capacity", "persistent_availability"),
    ("geodesy", "earth_radius_m"),
    ("ingest", "nodata_sentinel"),
    ("adults", "daily_mort_basal"),
    ("eip", "base_c"),
    ("transmission", "beta_hv"),
    ("thermal", "efd_topt_c"),
    ("gonotrophic", "egg_batch_n"),
    ("dispersal", "adult_prob_day"),
    ("host_seeking", "starvation_days"),
    ("oviposition", "scale_m"),
    ("aquatic_stages", "egg_daily_mort"),
    ("rng", "aquatic_seed_washout"),
]


@pytest.mark.parametrize("path", _MISSING_CASES)
def test_missing_key_is_named(tmp_path, path):
    def mutate(data):
        node = data
        for key in path[:-1]:
            node = node[key]
        del node[path[-1]]

    broken = _tmp_yaml(tmp_path, mutate)
    message = _message(broken)
    assert ".".join(path) in message
    assert str(broken) in message
    assert "missing keys" in message


def test_all_missing_keys_listed_together(tmp_path):
    def mutate(data):
        del data["pluvial"]["rain_scale_mm"]
        del data["rng"]["aquatic_seed_washout"]
        del data["adults"]["opt_c"]

    message = _message(_tmp_yaml(tmp_path, mutate))
    for dotted in ("pluvial.rain_scale_mm", "rng.aquatic_seed_washout",
                   "adults.opt_c"):
        assert dotted in message


def test_missing_whole_section_is_named(tmp_path):
    message = _message(
        _tmp_yaml(tmp_path, lambda data: data.pop("eip")))
    assert "eip" in message


# -- unknown keys / wrong types ---------------------------------------------

@pytest.mark.parametrize("where", [
    ("root",),
    ("section",),
    ("species_row",),
    ("weights",),
    ("pref",),
])
def test_unknown_key_rejected_everywhere(tmp_path, where):
    def mutate(data):
        kind = where[0]
        if kind == "root":
            data["foo"] = 1
        elif kind == "section":
            data["pluvial"]["foo"] = 1
        elif kind == "species_row":
            data["species"]["coluzzii"]["foo"] = 1
        elif kind == "weights":
            data["species"]["coluzzii"]["weights"]["forest"] = 0.0
        else:
            data["species"]["coluzzii"]["pref"]["dog"] = 0.0

    message = _message(_tmp_yaml(tmp_path, mutate))
    kind = where[0]
    key = {"root": "foo", "section": "foo", "species_row": "foo",
           "weights": "forest", "pref": "dog"}[kind]
    assert key in message
    if kind in ("root", "section", "species_row"):
        assert "unrecognized keys" in message
    else:
        assert "weights keys" in message or "pref keys" in message


def test_string_where_number_expected(tmp_path):
    def mutate(data):
        data["pluvial"]["rain_scale_mm"] = "dos"

    message = _message(_tmp_yaml(tmp_path, mutate))
    assert "pluvial.rain_scale_mm" in message
    assert "wrong types" in message
    assert "str" in message


@pytest.mark.parametrize("bad", ["1", 1.5, True])
def test_version_must_be_int(tmp_path, bad):
    message = _message(
        _tmp_yaml(tmp_path, lambda data: data.__setitem__("version", bad)))
    assert "version" in message


def test_bool_rejected_for_number(tmp_path):
    def mutate(data):
        data["pluvial"]["rain_scale_mm"] = True

    message = _message(_tmp_yaml(tmp_path, mutate))
    assert "pluvial.rain_scale_mm" in message


def test_duplicate_key_rejected(tmp_path):
    path = tmp_path / "dup.yaml"
    path.write_text(
        _DEFAULT_TEXT + "\npluvial:\n  rain_scale_mm: 9.9\n",
        encoding="utf-8")
    message = _message(path)
    assert "duplicate" in message.lower()


# -- invariants --------------------------------------------------------------

def test_weight_sum_must_be_one(tmp_path):
    def mutate(data):
        data["species"]["funestus"]["weights"]["crop_pluvial"] = 0.5

    message = _message(_tmp_yaml(tmp_path, mutate))
    assert "species.funestus.weights" in message
    assert "1.0" in message


def test_weight_keys_must_match_habitat_types(tmp_path):
    def mutate(data):
        del data["species"]["funestus"]["weights"]["crop_pluvial"]

    message = _message(_tmp_yaml(tmp_path, mutate))
    assert "species.funestus.weights" in message
    assert "crop_pluvial" in message


def test_wetland_pluvial_weight_must_be_zero(tmp_path):
    """No C++ ZoneId exists for it: non-zero would be dropped silently."""

    def mutate(data):
        data["species"]["coluzzii"]["weights"]["wetland_pluvial"] = 0.10
        data["species"]["coluzzii"]["weights"]["crop_pluvial"] = -0.05

    message = _message(_tmp_yaml(tmp_path, mutate))
    assert "species.coluzzii.weights.wetland_pluvial" in message


def test_types_row_width_must_match(tmp_path):
    def mutate(data):
        data["habitat_types"]["types"].pop()
        data["habitat_types"]["dynamics"].pop("crop_pluvial")

    message = _message(_tmp_yaml(tmp_path, mutate))
    assert "habitat_types.types" in message
    assert "crop_pluvial" in message


def test_pref_sum_must_be_one(tmp_path):
    def mutate(data):
        data["species"]["coluzzii"]["pref"]["human"] = 0.5

    message = _message(_tmp_yaml(tmp_path, mutate))
    assert "species.coluzzii.pref" in message
    assert "1.0" in message


def test_activity_sum_must_be_one(tmp_path):
    def mutate(data):
        data["species"]["coluzzii"]["activity_weights"][0] = 0.5

    message = _message(_tmp_yaml(tmp_path, mutate))
    assert "species.coluzzii.activity_weights" in message
    assert "1.0" in message


def test_activity_phases_must_be_four(tmp_path):
    def mutate(data):
        data["species"]["coluzzii"]["activity_weights"].pop()

    message = _message(_tmp_yaml(tmp_path, mutate))
    assert "activity_weights" in message


def test_num_persistent_at_least_one(tmp_path):
    def mutate(data):
        data["habitat_types"]["dynamics"] = {
            key: "pluvial" for key in data["habitat_types"]["dynamics"]}

    message = _message(_tmp_yaml(tmp_path, mutate))
    assert "num_persistent" in message


def test_default_species_must_be_a_row(tmp_path):
    def mutate(data):
        data["species"]["default_species"] = "aegypti"

    message = _message(_tmp_yaml(tmp_path, mutate))
    assert "aegypti" in message


def test_geodesy_relation(tmp_path):
    def mutate(data):
        data["geodesy"]["metres_per_deg_lat"] = 111194.9

    message = _message(_tmp_yaml(tmp_path, mutate))
    assert "metres_per_deg_lat" in message


@pytest.mark.parametrize("contract", ["3", "v3.0", "3.0.1", ""])
def test_contract_format(tmp_path, contract):
    def mutate(data):
        data["contracts"]["env_nc"] = contract

    message = _message(_tmp_yaml(tmp_path, mutate))
    assert "contracts.env_nc" in message


@pytest.mark.parametrize("key", ["nodata_sentinel", "nodata_sentinel_int"])
def test_nodata_must_be_negative(tmp_path, key):
    def mutate(data):
        data["ingest"][key] = 0 if key.endswith("_int") else 0.0

    message = _message(_tmp_yaml(tmp_path, mutate))
    assert f"ingest.{key}" in message


def test_k_ref_must_be_positive(tmp_path):
    def mutate(data):
        data["species"]["k_ref"] = 0.0

    message = _message(_tmp_yaml(tmp_path, mutate))
    assert "k_ref" in message


# -- full YAML coverage (key-by-key) ---------------------------------------

def _yaml_section_keys(data):
    return {name: set(value) for name, value in data.items()
            if isinstance(value, dict)}


def test_every_yaml_section_key_is_modelled():
    data = _yaml.safe_load(_DEFAULT_TEXT)
    root_fields = set(ModelConfig.model_fields)
    assert set(data) == root_fields, (
        f"YAML-only: {set(data) - root_fields}; "
        f"model-only: {root_fields - set(data)}")

    for section, yaml_keys in _yaml_section_keys(data).items():
        if section == "habitat_types":
            # dynamics maps habitat names, checked by the invariants.
            assert set(ModelConfig.model_fields[section].annotation.model_fields) \
                == yaml_keys
            continue
        model = ModelConfig.model_fields[section].annotation
        assert yaml_keys == set(model.model_fields), section

    species = data["species"]
    species_model = ModelConfig.model_fields["species"].annotation
    for name, row in species.items():
        if not isinstance(row, dict):
            continue
        model = species_model.model_fields[name].annotation
        assert set(row) == set(model.model_fields), f"species.{name}"


def test_habitat_types_are_the_frozen_contract():
    cfg = validate_model_config()
    assert tuple(cfg.habitat_types.types) == HABITAT_TYPES_V1
    assert set(cfg.habitat_types.dynamics) == set(HABITAT_TYPES_V1)


# -- CLI gate ---------------------------------------------------------------

runner = CliRunner()


def _cli_text(result) -> str:
    parts = [result.output]
    stderr = getattr(result, "stderr", "")
    if stderr:
        parts.append(stderr)
    if result.exception is not None:
        parts.append(str(result.exception))
    return "".join(parts)


def test_cli_rejects_broken_yaml_before_running(tmp_path, monkeypatch):
    from mal_core.cli import app

    broken = _tmp_yaml(
        tmp_path, lambda data: data["pluvial"].pop("rain_scale_mm"))
    monkeypatch.setenv(cv.ENV_VAR, str(broken))
    result = runner.invoke(app, ["datasets", "--missing"])
    assert result.exit_code != 0
    text = _cli_text(result)
    assert "pluvial.rain_scale_mm" in text
    assert str(broken) in text


def test_abm_cli_defers_transmission_defaults_to_yaml(monkeypatch):
    """C1: no transmission model value may be pinned by the Python CLI.

    With no flag, the wrapper receives ``None`` and omits the argv entry,
    so the C++ engine reads model_constants.yaml itself.
    """
    import mal_core.abm as abm_pkg

    captured: dict = {}

    def fake(**kwargs):
        captured.update(kwargs)
        return {"returncode": 0, "stdout": "", "stderr": ""}

    monkeypatch.setattr(abm_pkg, "run_abm_from_manifest", fake)
    from mal_core.cli import app

    result = runner.invoke(app, ["abm", "--aoi", "ghana"])
    assert result.exit_code == 0, _cli_text(result)
    for key in (
        "initial_human_prevalence",
        "initial_vector_infected_frac",
        "beta_hv",
        "beta_vh",
        "human_incubation_days",
        "human_infectious_days",
        "immunity_duration_days",
    ):
        assert captured[key] is None, f"{key} must defer to the YAML"

    result = runner.invoke(app, ["abm", "--aoi", "ghana", "--beta-hv", "0.42"])
    assert result.exit_code == 0, _cli_text(result)
    assert captured["beta_hv"] == pytest.approx(0.42)


def test_cli_help_does_not_validate(tmp_path, monkeypatch):
    from mal_core.cli import app

    broken = _tmp_yaml(
        tmp_path, lambda data: data["pluvial"].pop("rain_scale_mm"))
    monkeypatch.setenv(cv.ENV_VAR, str(broken))
    result = runner.invoke(app, ["score", "--help"])
    assert result.exit_code == 0
    assert "Score a completed ABM run" in result.output


def test_cli_announces_constants_path(tmp_path, monkeypatch, caplog):
    from mal_core.cli import app

    good = _tmp_yaml(tmp_path, lambda data: None)
    monkeypatch.setenv(cv.ENV_VAR, str(good))
    # Even with library logging at INFO, the user sees exactly one line:
    # the CLI echo. The library announcement is DEBUG-only (decision 6).
    with caplog.at_level(logging.INFO):
        result = runner.invoke(app, ["datasets", "--missing"])
    assert result.exit_code == 0
    # result.output is the mixed stream the user sees; _cli_text also
    # appends result.stderr, which would count the same line twice.
    assert f"model_constants: {good}" in result.output
    assert result.output.count(f"model_constants: {good}") == 1


# -- no duplicated validation logic -----------------------------------------

def test_no_duplicate_validation_in_cpp_or_thin_loader():
    repo = pathlib.Path(__file__).resolve().parents[1]
    cc = (repo / "src/mal_core/abm/src/config.cc").read_text(encoding="utf-8")
    assert "config invariant" not in cc
    assert "check_unknown" not in cc
    assert "1e-9" not in cc
    assert "!= 1.0" not in cc

    loader = (repo / "src/mal_core/habitat/config.py").read_text(
        encoding="utf-8")
    assert "def _check_invariants" not in loader
    assert "def _check_tree" not in loader
    assert "validate_model_config" in loader


# -- task-07 sections: probabilities, thresholds and kernels ---------------

@pytest.mark.parametrize("path,value", [
    (("transmission", "beta_hv"), 1.5),
    (("transmission", "beta_vh"), -0.1),
    (("transmission", "initial_human_prevalence"), 2.0),
    (("gonotrophic", "feeding_success_rate"), 1.2),
    (("oviposition", "min_attraction"), 2.0),
    (("ingest", "residential_from_indoor_frac"), 1.5),
])
def test_probability_must_be_a_fraction(tmp_path, path, value):
    def mutate(data):
        node = data
        for key in path[:-1]:
            node = node[key]
        node[path[-1]] = value

    message = _message(_tmp_yaml(tmp_path, mutate))
    assert ".".join(path) in message
    assert "[0, 1]" in message


@pytest.mark.parametrize("path", [
    ("transmission", "human_incubation_days"),
    ("transmission", "human_infectious_days"),
    ("transmission", "human_immunity_days"),
    ("gonotrophic", "cycle_duration_days"),
    ("gonotrophic", "first_cycle_days"),
    ("gonotrophic", "resting_duration_days"),
])
def test_duration_must_be_positive(tmp_path, path):
    def mutate(data):
        data[path[0]][path[1]] = 0

    message = _message(_tmp_yaml(tmp_path, mutate))
    assert ".".join(path) in message
    assert "> 0" in message


def test_thermal_thresholds_must_be_ordered(tmp_path):
    def mutate(data):
        data["thermal"]["efd_topt_c"] = 40.0

    message = _message(_tmp_yaml(tmp_path, mutate))
    assert "thermal.efd_*" in message
    assert "tmin < topt < tmax" in message


@pytest.mark.parametrize("stage", ["egg", "larva", "pupa"])
def test_stage_thresholds_must_be_ordered(tmp_path, stage):
    def mutate(data):
        data["thermal"][f"{stage}_development_tmin_c"] = 50.0

    message = _message(_tmp_yaml(tmp_path, mutate))
    assert f"thermal.{stage}_development_tmin_c" in message


def test_egg_batch_ordering_invariant(tmp_path):
    def mutate(data):
        data["gonotrophic"]["egg_batch_min"] = 200

    message = _message(_tmp_yaml(tmp_path, mutate))
    assert "gonotrophic egg batch" in message
    assert "min <= mean <= max" in message


@pytest.mark.parametrize("hour", [-1, 24])
def test_night_hours_must_be_in_day(tmp_path, hour):
    def mutate(data):
        data["dispersal"]["night_start_hour"] = hour

    message = _message(_tmp_yaml(tmp_path, mutate))
    assert "dispersal.night_start_hour" in message
    assert "[0, 24)" in message


def test_night_window_must_not_be_empty(tmp_path):
    def mutate(data):
        data["dispersal"]["night_end_hour"] = data["dispersal"]["night_start_hour"]

    message = _message(_tmp_yaml(tmp_path, mutate))
    assert "night_start_hour" in message
