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

mal_core_root = Path(__file__).resolve().parent.parent


from mal_core.habitat import (
    HABITAT_TYPES,
    HABITAT_DYNAMICS,
    availability,
    aquatic_stress,
    capacity,
    constants,
    potential,
)


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
    expected = constants.BETA_URBAN * 0.40
    assert math.isclose(float(h["urban_persistent"]), expected)
    assert h["urban_persistent"] > 0.0


def test_beta_urban_matches_the_cpp_engine_mirror():
    """Single beta surface: the Python constant and the C++ header must
    quote the same value (the one contract the plans demanded)."""
    hpp = (mal_core_root / "src" / "mal_core" / "abm" / "include" /
           "mal_abm_fast" / "habitat_availability.hpp").read_text()
    expected = 0.75
    assert constants.BETA_URBAN == expected
    import re
    m = re.search(r"URBAN_PERSISTENT_BETA\s*=\s*([0-9.]+)f", hpp)
    assert m, "URBAN_PERSISTENT_BETA not found in habitat_availability.hpp"
    assert float(m.group(1)) == expected


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
    assert float(h["open_pluvial"]) == 0.5


# ---------------------------------------------------------------------------
# availability.py — pluvial response (plan 02 §5.2)
# ---------------------------------------------------------------------------

def test_no_rain_decay_matches_exponential_memory():
    z0 = np.array([1.0, 0.4])
    z1 = availability.update_pluvial_state(z0, 0.0)
    assert np.allclose(z1, z0 * math.exp(-1.0 / constants.DRY_MEMORY_DAYS))


def test_heavy_rain_repractives_toward_full():
    z = availability.update_pluvial_state(0.0, 100.0)
    expected = 1.0 - math.exp(-100.0 / constants.RAIN_SCALE_MM)
    assert math.isclose(float(z), expected)


def test_reference_example_20mm_from_cold_start():
    # 20 mm rain given RAIN_SCALE_MM=20: recharge = 1 - e^-1 ≈ 0.632.
    z = availability.update_pluvial_state(0.0, 20.0)
    assert math.isclose(float(z), 1.0 - math.exp(-1.0), rel_tol=1e-9)


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


def test_species_accuracy_sum1_weights():
    h = _h_all_at(1.0)
    z = np.array([0.5])
    s = capacity.species_accuracy(h, z)
    # persistent half: 0.40+0.20+0.15 = 0.75 fully credited; pluvial half
    # 0.25 credited at z=0.5 -> total 0.875
    assert math.isclose(s[0], 0.75 + 0.25 * 0.5)


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
                        constants.K_REF_DAILY_PER_KM2["coluzzii"] * area_row)


def test_k_ref_value_documents_literature_anchor():
    k_ref = constants.K_REF_DAILY_PER_KM2["coluzzii"]
    assert math.isclose(k_ref, 0.143 * 9.3 * 1.0e6)


# ---------------------------------------------------------------------------
# aquatic_stress.py — preserved biological bits (plan 02 §7.2)
# ---------------------------------------------------------------------------

def test_desiccation_grace_then_ramp_to_baseline():
    assert aquatic_stress.desiccation_rate(constants.DESICCATION_GRACE_DAYS) == 0.0
    rate = aquatic_stress.desiccation_rate(constants.DESICCATION_GRACE_DAYS + 20)
    assert 0.0 < rate <= constants.DESICC_BASE_DAILY
    assert math.isclose(rate, constants.DESICC_BASE_DAILY, rel_tol=0.05)


def test_washout_linear_cap():
    assert aquatic_stress.washout_fraction(10.0) == 0.0
    assert 0.0 < aquatic_stress.washout_fraction(60.0) < constants.RAIN_WASH_FRACTION_MAX
    assert math.isclose(aquatic_stress.washout_fraction(80.0),
                        constants.RAIN_WASH_FRACTION_MAX)


# ---------------------------------------------------------------------------
# constants.py — contract guards
# ---------------------------------------------------------------------------

def test_weights_sum_to_one():
    for weights in constants.SPECIES_HABITAT_WEIGHTS.values():
        assert math.isclose(sum(weights.values()), 1.0)


def test_dynamics_partition_is_exhaustive():
    assert constants.PERSISTENT_TYPES | constants.PLUVIAL_TYPES == set(HABITAT_TYPES)
    assert not (constants.PERSISTENT_TYPES & constants.PLUVIAL_TYPES)


def test_activation_scales_documented():
    assert 0.0 < constants.ACTIVATION_MIN < 1.0
    assert constants.RAIN_SCALE_MM > 0.0
    assert constants.DRY_MEMORY_DAYS > 0.0
