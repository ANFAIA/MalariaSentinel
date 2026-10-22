"""Plan constants-yaml §6 tests 1/2/3/5: the py model-constants loader."""
from __future__ import annotations

import math
import pathlib

import pytest
import yaml as _yaml
from mal_core.habitat.config import (
    CONFIG,
    DEFAULT_PATH,
    ENV_VAR,
    SCHEMA,
    SchemaError,
    dump_raw,
    dynamics_map,
    habitat_names,
    load_config,
    persistent_names,
    pluvial_names,
)

_DEFAULT_TEXT = DEFAULT_PATH.read_text(encoding="utf-8")


def _tmp_yaml(tmp_path: pathlib.Path, mutate) -> pathlib.Path:
    data = _yaml.safe_load(_DEFAULT_TEXT)
    mutate(data)
    path = tmp_path / "model_constants.yaml"
    path.write_text(
        _yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


# -- test 1: missing keys — full list, multiple at once ----------------------





# -- test 2: unknown keys and wrong types -----------------------------------









# -- test 3: immutability + no-fallback -------------------------------------

def test_mapping_proxy_rejects_writes():
    with pytest.raises(TypeError):
        CONFIG["pluvial"]["rain_scale_mm"] = 5  # type: ignore[index]
    with pytest.raises(TypeError):
        CONFIG["pluvial"] = {}  # type: ignore[index]


def test_missing_path_names_env_var(tmp_path):
    bogus = tmp_path / "does_not_exist.yaml"
    with pytest.raises(SchemaError) as exc:
        load_config(bogus)
    assert ENV_VAR in str(exc.value)


def test_no_model_literal_in_loader_source():
    """The loader file itself must not embed model-constant defaults."""
    source = pathlib.Path(
        __import__("mal_core.habitat.config", fromlist=["config"]).__file__
    ).read_text(encoding="utf-8")
    for literal in ("2.5", "0.01", "0.75", "1.33e6", "789", "0.72"):
        assert literal not in source, f"hardcoded literal {literal!r}"


# -- test 5: invariants of the canonical YAML --------------------------------

def test_canonical_loads_and_derives():
    assert tuple(CONFIG["habitat_types"]["types"]) == habitat_names()
    assert dynamics_map()["open_pluvial"] == "pluvial"
    assert persistent_names() == frozenset(
        {"surface_persistent", "wetland_persistent", "urban_persistent"})
    assert pluvial_names() == frozenset(
        {"wetland_pluvial", "open_pluvial", "crop_pluvial"})
    assert CONFIG["version"] == 2
    assert CONFIG["contracts"]["env_nc"] == "3.0"
    assert CONFIG["contracts"]["cogs_state"] == "4.0"
    assert CONFIG["pluvial"]["rain_scale_mm"] == 2.5
    assert CONFIG["species"]["default_species"] == "coluzzii"
    assert CONFIG["species"]["k_ref"] == 50.0


@pytest.mark.parametrize("name", [
    "coluzzii", "gambiae_ss", "funestus", "arabiensis",
    "melas", "stephensi", "neutral",
])
def test_weight_sums_and_row_widths(name):
    types_list = habitat_names()
    species = CONFIG["species"]
    row = species[name]
    weights = row["weights"]
    assert set(weights) == set(types_list)
    total = sum(weights.values())
    assert math.isclose(total, 1.0, rel_tol=0.0, abs_tol=1e-9), name












def test_env_var_override_used(tmp_path, monkeypatch, caplog):
    custom = _tmp_yaml(tmp_path, lambda data: None)
    monkeypatch.setenv(ENV_VAR, str(custom))
    cfg = load_config()
    assert cfg["pluvial"]["rain_scale_mm"] == 2.5


def test_schema_is_declared_not_yaml_derived():
    """The schema dict is machinery, not generated from the YAML file."""
    assert SCHEMA["pluvial"]["rain_scale_mm"] is not None


# -- test 4: parity py ⇄ C++ over the SAME file ------------------------------

_CONFIG_DUMP_CANDIDATES = (
    pathlib.Path("mal-core/src/mal_core/abm/build/src/config_dump"),
)


def _config_dump_path():
    for candidate in _CONFIG_DUMP_CANDIDATES:
        if candidate.exists():
            return candidate
    return None


def py_weights_map(key, py):
    """Name map of a 'species.<n>.weights' key from the py raw dump."""
    name = key[len("species."):-len(".weights")]
    types_list = [
        py[f"habitat_types.types.{i}"] for i in range(6)]
    vals = py[key]
    return dict(zip(types_list, vals))


def test_cxx_dump_raw_parity():
    exe = _config_dump_path()
    if exe is None:
        pytest.fail(
            "config_dump binary not built; py<->C++ parity cannot be "
            "skipped silently. Build: "
            "cmake --build mal-core/src/mal_core/abm/build")
    import json
    import subprocess

    out = subprocess.run([str(exe), "--yaml", str(DEFAULT_PATH)],
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    cxx = json.loads(out.stdout)
    py = dump_raw()
    missing = sorted(set(py) - set(cxx))
    extra = sorted(set(cxx) - set(py))
    assert not missing, f"py-only keys: {missing}"
    assert not extra, f"cxx-only keys: {extra}"
    for key in py:
        pv, cv = py[key], cxx[key]
        if isinstance(pv, str):
            assert pv == cv, key
        elif isinstance(pv, list):
            assert isinstance(cv, list) and len(pv) == len(cv), key
            if key.endswith(".weights"):
                # C++ arrays are pre-transformed by NAME → ZoneId whose
                # order is (jrc/surface, urban, wetland, open, crop,
                # forest=0), not the py habitat_types order.
                w = py_weights_map(key, py)
                zone_names = ("surface_persistent", "urban_persistent",
                              "wetland_persistent", "open_pluvial",
                              "crop_pluvial")
                expected = ([w[g] for g in zone_names] + [0.0])
                assert all(
                    abs(float(a) - float(b)) < 1e-9
                    for a, b in zip(expected, cv)), key
            else:
                for a, b in zip(pv, cv):
                    assert abs(float(a) - float(b)) < 1e-9, key
        else:
            assert abs(float(pv) - float(cv)) < 1e-9, key


def test_dump_raw_shape():
    raw = dump_raw()
    assert raw["habitat_types.num_persistent"] == 3
    assert raw["habitat_types.types.0"] == "surface_persistent"
    assert abs(sum(raw["species.coluzzii.weights"]) - 1.0) < 1e-9
    assert raw["pluvial.rain_scale_mm"] == 2.5


# -- task-07: per-section parity for the new model domains ------------------

_TASK07_SECTIONS = ("transmission", "thermal", "gonotrophic")


@pytest.mark.parametrize("section", _TASK07_SECTIONS)
def test_task07_section_parity(section):
    """Each section added by task-07 is dumped 1:1 by py and C++."""
    exe = _config_dump_path()
    if exe is None:
        pytest.fail(
            "config_dump binary not built; py<->C++ parity cannot be "
            "skipped silently. Build: "
            "cmake --build mal-core/src/mal_core/abm/build")
    import json
    import subprocess

    out = subprocess.run([str(exe), "--yaml", str(DEFAULT_PATH)],
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    cxx = json.loads(out.stdout)
    py = dump_raw()
    prefix = section + "."
    py_keys = {k: v for k, v in py.items() if k.startswith(prefix)}
    cxx_keys = {k: v for k, v in cxx.items() if k.startswith(prefix)}
    assert py_keys, f"{section}: no keys in the py raw dump"
    assert set(py_keys) == set(cxx_keys), section
    for key, value in py_keys.items():
        assert abs(float(value) - float(cxx[key])) < 1e-9, key
