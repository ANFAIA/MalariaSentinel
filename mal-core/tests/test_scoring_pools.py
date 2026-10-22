"""Tests for the proxy-habitat aquatic stress + canon pool scorers D19/D20
(contract v3.0, promoted 2026-10-17 from the deleted calibration harness).

The pool water balance is gone; what remains biologically is the
aquatic-stress layer (desiccation ramp, heavy-rain washout) driven by the
habitat-dry streak, and the D19/D20 scorers re-anchored on the proxy
model.
"""
from __future__ import annotations

import math

from mal_core.habitat.aquatic_stress import (
    desiccation_rate,
    washout_fraction,
)
from mal_core.habitat.constants import (
    DESICC_BASE_DAILY,
    DESICCATION_GRACE_DAYS,
    RAIN_WASH_FRACTION_MAX,
    RAIN_WASH_MM,
)
from mal_core.habitat import HABITAT_TYPES
from mal_core.habitat.availability import update_pluvial_state

from mal_core.scoring.scorers.d19_pool_persistence import PoolPersistenceScorer
from mal_core.scoring.scorers.d20_washout_response import WashoutResponseScorer


# ---------------------------------------------------------------------------
# pluvial recursion tests (availability)
# ---------------------------------------------------------------------------


class TestPluvialAvailability:
    def test_single_pulse_activates(self) -> None:
        """A 30 mm pulse lifts z well above the activation floor."""
        import numpy as np

        z = update_pluvial_state(
            np.zeros(1), np.array([30.0]), delta_days=1.0
        )
        assert float(z[0]) > 0.7

    def test_decay_is_monotone(self) -> None:
        import numpy as np

        z = float(update_pluvial_state(
            np.zeros(1), np.array([20.0]), delta_days=1.0
        )[0])
        prev = z
        for _ in range(5):
            nxt = float(update_pluvial_state(
                np.array([prev]), np.zeros(1), delta_days=1.0
            )[0])
            assert nxt <= prev
            prev = nxt

    def test_recharge_never_exceeds_one(self) -> None:
        import numpy as np

        z = update_pluvial_state(
            np.zeros(1), np.array([100.0])
        )
        assert float(z[0]) <= 1.0

    def test_memory_time_scale(self) -> None:
        """The z decay after DRY_MEMORY_DAYS lands near e^{-1}."""
        import math

        import numpy as np

        z = update_pluvial_state(
            np.array([1.0]), np.zeros(1), delta_days=5.0
        )
        assert abs(float(z[0]) - math.exp(-1.0)) < 0.02

    def test_temperature_is_never_a_pluvial_forcing(self) -> None:
        """update_pluvial_state takes no temperature — temperature acts
        through the existing aquatic development/survival, never a second
        supply term."""
        import inspect

        params = list(
            inspect.signature(update_pluvial_state).parameters
        )
        assert "temp" not in {p.lower() for p in params}


# ---------------------------------------------------------------------------
# aquatic stress constants (preserved)
# ---------------------------------------------------------------------------


class TestDesiccationRate:
    def test_inside_grace(self) -> None:
        assert desiccation_rate(DESICCATION_GRACE_DAYS - 1) == 0.0

    def test_after_grace_ramps(self) -> None:
        rate = desiccation_rate(DESICCATION_GRACE_DAYS + 2)
        assert 0.0 < rate <= DESICC_BASE_DAILY

    def test_saturates(self) -> None:
        rate = desiccation_rate(30)
        assert rate > DESICC_BASE_DAILY * 0.9


class TestWashoutFraction:
    def test_below_threshold(self) -> None:
        assert washout_fraction(30.0) == 0.0
        assert washout_fraction(39.0) == 0.0

    def test_at_threshold(self) -> None:
        frac = washout_fraction(RAIN_WASH_MM)
        assert frac <= 0.01

    def test_at_50mm(self) -> None:
        frac = washout_fraction(50.0)
        assert 0.0 < frac < RAIN_WASH_FRACTION_MAX

    def test_at_80mm(self) -> None:
        frac = washout_fraction(80.0)
        assert abs(frac - RAIN_WASH_FRACTION_MAX) < 0.001

    def test_above_80mm(self) -> None:
        frac = washout_fraction(100.0)
        assert abs(frac - RAIN_WASH_FRACTION_MAX) < 0.001


# ---------------------------------------------------------------------------
# static conditions on the new habitat surface
# ---------------------------------------------------------------------------


def test_built_fraction_is_a_persistent_habitat() -> None:
    """The urban persistent premise is wired through the habitat-type list:
    a built column keeps a persistent (non-pluvial) supply entry."""
    from mal_core.habitat.constants import PERSISTENT_TYPES

    assert "urban_persistent" in PERSISTENT_TYPES


# ---------------------------------------------------------------------------
# Canon scorers D19 / D20
# ---------------------------------------------------------------------------


class TestPoolPersistenceScorer:
    def test_reference_scenario_passes(self, tmp_path) -> None:
        scorer = PoolPersistenceScorer()
        result = scorer.score(tmp_path, {})
        assert result.passed is True
        assert result.score >= 0.70
        assert result.value >= 4.0  # active days
        assert result.diagnostics["active_days"] >= 4
        # persistent floor strictly inside (0, 1]
        from mal_core.habitat import HABITAT_TYPES
        from mal_core.habitat.capacity import species_accuracy
        h_map = {
            g: float(v)
            for g, v in zip(
                HABITAT_TYPES, (0.20, 0.075, 0.30, 0.40, 0.10, 0.0)
            )
        }
        w_map = {
            g: float(v)
            for g, v in zip(
                HABITAT_TYPES, (0.25, 0.15, 0.15, 0.40, 0.05, 0.0)
            )
        }
        floor = float(species_accuracy(h_map, 0.0, w_map))
        assert 0.0 < floor <= 1.0

    def test_name_and_kind(self, tmp_path) -> None:
        scorer = PoolPersistenceScorer()
        assert scorer.name == "D19_pool_persistence"
        assert scorer.kind == "composite"


class TestWashoutResponseScorer:
    def test_reference_thresholds_pass(self, tmp_path) -> None:
        scorer = WashoutResponseScorer()
        result = scorer.score(tmp_path, {})
        assert result.passed is True
        assert result.score >= 0.70
        assert result.diagnostics["frac_30mm"] == 0.0

    def test_name_and_kind(self, tmp_path) -> None:
        scorer = WashoutResponseScorer()
        assert scorer.name == "D20_washout_response"
        assert scorer.kind == "composite"
