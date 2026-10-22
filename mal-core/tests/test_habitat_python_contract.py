"""Unit tests for the proxy_habitat_v1 in-repo Python contract.

Parity: every numeric assertion here is mirrored by a C++ assertion in
``mal-core/src/mal_core/abm/tests/test_habitat_availability.cpp`` — these
Python tests are the canonical reference of the two plans.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest
from mal_core.habitat.config import CONFIG

mal_core_root = Path(__file__).resolve().parent.parent


from mal_core.habitat import (
    HABITAT_TYPES,
    aquatic_stress,
    availability,
    capacity,
    potential,
)

# ---------------------------------------------------------------------------
# package exports (task-01 B2): __all__ must resolve for every name
# ---------------------------------------------------------------------------

def test_star_import_exports_resolve():
    import mal_core.habitat as hab

    namespace: dict[str, object] = {}
    exec("from mal_core.habitat import *", namespace)  # noqa: S102
    for name in hab.__all__:
        assert name in namespace, f"{name} declared in __all__ but not exported"
        assert getattr(hab, name) is namespace[name]


# ---------------------------------------------------------------------------
# potential.py — explicit static mapping (plan 02 §6.2-§6.4)
# ---------------------------------------------------------------------------

def test_static_potential_jrc_only_cell():
    h = potential.static_potential({"jrc_persistent": 0.30, "lc_wetland": 0.0,
                                   "lc_built": 0.0, "lc_open_plus_water": 0.0,
                                   "lc_crop": 0.0})
    assert math.isclose(float(h["surface_persistent"]), 0.30)
    assert float(h["urban_persistent"]) == 0.0
    assert float(h["wetland_pluvial"]) == 0.0


def test_urban_persistent_contribution_not_zero():
    # Premise preserved (memory #167): built cover keeps persistent offer,
    # never silently zeroed.
    h = potential.static_potential({"jrc_persistent": 0.0, "lc_wetland": 0.0,
                                   "lc_built": 0.40, "lc_open_plus_water": 0.0,
                                   "lc_crop": 0.0})
    expected = float(CONFIG["urban"]["beta_urban"]) * 0.40
    assert math.isclose(float(h["urban_persistent"]), expected)
    assert h["urban_persistent"] > 0.0


def test_beta_urban_matches_the_cpp_engine_mirror():
    """Single beta surface: the loader normalization scope"""
    # Single surface of truth: the YAML value and the C++ load accessor
    # are the constant (test_upper_v1_min in habitat config.py).
    expected = 0.75
    assert float(CONFIG["urban"]["beta_urban"]) == expected
    # The C++ header no longer compiles any constant (plan pasos 6-7):
    # check the shadow is gone from the header.
    hpp = (mal_core_root / "src" / "mal_core" / "abm" / "include" /
           "mal_abm_fast" / "habitat_availability.hpp").read_text()
    assert "URBAN_PERSISTENT_BETA =" not in hpp
    assert "load_config().urban.beta_urban" in hpp


def test_wetland_feature_caps_both_persistent_and_pluvial():
    h = potential.static_potential({"jrc_persistent": 0.0, "lc_wetland": 0.5,
                                   "lc_built": 0.0, "lc_open_plus_water": 0.0,
                                   "lc_crop": 0.0})
    assert math.isclose(float(h["wetland_persistent"]), 0.5)
    assert math.isclose(float(h["wetland_pluvial"]), 0.5)


def test_open_pluvial_uses_open_plus_water():
    h = potential.static_potential({"jrc_persistent": 0.0, "lc_wetland": 0.0,
                                   "lc_built": 0.0, "lc_open_plus_water": 1.0,
                                   "lc_crop": 0.0})
    assert math.isclose(float(h["open_pluvial"]), 1.0)


def test_missing_required_feature_is_a_contract_error():
    with pytest.raises(KeyError):
        potential.static_potential({"jrc_persistent": 1.0})


def test_nan_features_are_zero_not_wet():
    h = potential.static_potential({"jrc_persistent": float("nan"),
                                   "lc_wetland": float("nan"),
                                   "lc_built": 0.0, "lc_open_plus_water": 0.0,
                                   "lc_crop": 0.0})
    assert float(h["surface_persistent"]) == 0.0
    assert float(h["wetland_persistent"]) == 0.0


def test_all_six_types_present_and_clipped():
    h = potential.static_potential({"jrc_persistent": 2.0, "lc_wetland": -1.0,
                                   "lc_built": 3.0, "lc_open_plus_water": 0.5,
                                   "lc_crop": 0.2})
    assert set(h) == set(HABITAT_TYPES)
    assert float(h["surface_persistent"]) == 1.0
    # open_pluvial = lc_open (0.5) + rain_pools_built_damage (0.3) * lc_built
    # (3.0 clipped to 1.0 by the feature contract) = 0.8.
    assert float(h["open_pluvial"]) == 0.8


def test_open_pluvial_receives_built_damage_term():
    """Aligned with the engine (plan constants-yaml paso 2)."""
    h = potential.static_potential({"jrc_persistent": 0.0, "lc_wetland": 0.0,
                                   "lc_built": 0.40, "lc_open_plus_water": 0.5,
                                   "lc_crop": 0.0})
    built_damage = float(CONFIG["urban"]["rain_pools_built_damage"])
    assert math.isclose(float(h["open_pluvial"]), 0.5 + built_damage * 0.40)


# ---------------------------------------------------------------------------
# availability.py — pluvial response (plan 02 §5.2)
# ---------------------------------------------------------------------------

def test_no_rain_decay_matches_exponential_memory():
    z0 = np.array([1.0, 0.4])
    z1 = availability.update_pluvial_state(z0, 0.0)
    assert np.allclose(z1, z0 * math.exp(
        -1.0 / float(CONFIG["pluvial"]["dry_memory_days"])))


def test_heavy_rain_repractives_toward_full():
    z = availability.update_pluvial_state(0.0, 100.0)
    expected = 1.0 - math.exp(
        -100.0 / float(CONFIG["pluvial"]["rain_scale_mm"]))
    assert math.isclose(float(z), expected)


def test_reference_example_20mm_from_cold_start():
    # Canonical rain_scale_mm=2.5 (engine value): recharge = 1 - e^-8.
    z = availability.update_pluvial_state(0.0, 20.0)
    assert math.isclose(float(z), 1.0 - math.exp(-20.0 / 2.5), rel_tol=1e-9)


def test_cold_start_is_zero():
    z = availability.warm_up_pluvial(np.array([0.0, 0.0, 0.0]))
    assert math.isclose(float(z), 0.0)


def test_warmup_causal_heavy_pre_rain_raises_day0():
    # A heavy shower on the last warm-up day must raise day-0 z.
    z = availability.warm_up_pluvial(np.array([0.0, 0.0, 50.0]))
    assert float(z) > 0.0


# ---------------------------------------------------------------------------
# capacity.py — species accuracy + K (plan 02 §5.4 + §6.5)
# ---------------------------------------------------------------------------

def _h_all_at(v):
    return {g: v for g in HABITAT_TYPES}


def test_persistent_availability_comes_from_config(monkeypatch):
    """C8 Python twin: persistent A is read from capacity.persistent_availability."""
    monkeypatch.setattr(capacity, "CONFIG",
                        {"capacity": {"persistent_availability": 0.5}})
    h = {"surface_persistent": np.ones(1), "open_pluvial": np.zeros(1)}
    s = capacity.species_accuracy(
        h, np.zeros(1), weights={"surface_persistent": 1.0})
    assert math.isclose(float(s[0]), 0.5)


def test_species_accuracy_sum1_weights():
    h = _h_all_at(1.0)
    z = np.array([0.5])
    s = capacity.species_accuracy(h, z)
    # canonical coluzzii row (C++ remapped): persistent half 0.40+0.10+0.20
    # = 0.70 fully credited; pluvial half 0.00+0.25+0.05 = 0.30 at z=0.5.
    assert math.isclose(s[0], 0.70 + 0.30 * 0.5)


def test_urban_cell_keeps_persistent_capacity_in_drought():
    h = potential.static_potential({"jrc_persistent": 0.0, "lc_wetland": 0.0,
                                   "lc_built": 0.4, "lc_open_plus_water": 0.0,
                                   "lc_crop": 0.0})
    s = capacity.species_accuracy(h, np.array([0.0]))
    assert s > 0.0, "urban persistent offer survives dry state"


def test_k_habitat_scales_with_area_and_S():
    s = np.full((3, 1), 1.0)
    lat = np.array([7.0, 7.0, 7.0])
    k = capacity.k_habitat(s, lat, 1000.0)
    area_row = capacity.cell_area_km2(7.0, 1000.0)
    assert math.isclose(float(k[0][0]),
                        capacity.K_REF_DIAG_PER_KM2 * area_row)


def test_k_ref_value_documents_literature_anchor():
    k_ref = capacity.K_REF_DIAG_PER_KM2
    assert math.isclose(k_ref, 0.143 * 9.3 * 1.0e6)


# ---------------------------------------------------------------------------
# aquatic_stress.py — preserved biological bits (plan 02 §7.2)
# ---------------------------------------------------------------------------

def test_desiccation_grace_then_ramp_to_baseline():
    _aq = CONFIG["aquatic_stress"]
    grace = int(_aq["desicc_grace_days"])
    assert aquatic_stress.desiccation_rate(grace) == 0.0
    rate = aquatic_stress.desiccation_rate(grace + 20)
    base = float(_aq["desicc_base_daily"])
    assert 0.0 < rate <= base
    assert math.isclose(rate, base, rel_tol=0.05)


def test_washout_linear_cap():
    _aq = CONFIG["aquatic_stress"]
    assert aquatic_stress.washout_fraction(10.0) == 0.0
    waxf = float(_aq["wash_fraction_max"])
    assert 0.0 < aquatic_stress.washout_fraction(60.0) < waxf
    assert math.isclose(aquatic_stress.washout_fraction(80.0),
                        waxf)


# ---------------------------------------------------------------------------
# constants.py — contract guards
# ---------------------------------------------------------------------------





def test_activation_scales_documented():
    from mal_core.habitat.config import CONFIG
    assert 0.0 < CONFIG["habitat"]["activation_min_engine"] < 1.0
    assert CONFIG["pluvial"]["rain_scale_mm"] > 0.0
    assert CONFIG["pluvial"]["dry_memory_days"] > 0.0
