"""Tests for M14 pool hydrology + canon pool scorers D19/D20.

Hydrology model tests promoted from the calibration harness (2026-10);
loaded via the plain ``mal_core.abm.pool_hydrology`` import now.
"""
from __future__ import annotations

from mal_core.abm.pool_hydrology import (
    DailyForcing,
    POOL_DESICCATION_GRACE_DAYS,
    POOL_DESICC_BASE_DAILY,
    POOL_RAIN_WASH_MM,
    POOL_WASH_FRACTION_MAX,
    POOL_WATER_BREED_MM,
    POOL_WATER_DRY_MM,
    POOL_WATER_MAX_MM,
    PoolState,
    advance_pool,
    desiccation_rate,
    washout_fraction,
)

from mal_core.scoring.scorers.d19_pool_persistence import PoolPersistenceScorer
from mal_core.scoring.scorers.d20_washout_response import WashoutResponseScorer


# ---------------------------------------------------------------------------
# advance_pool tests
# ---------------------------------------------------------------------------


class TestAdvancePool:
    def test_fill_pool(self):
        """Rain > evaporation → water accumulates."""
        pool = PoolState()
        f = DailyForcing(rain_mm=30.0, temp_c=25.0)
        pool = advance_pool(pool, f)
        assert pool.water_mm > 0.0

    def test_dry_pool(self):
        """No rain + hot → water depletes."""
        pool = PoolState(water_mm=10.0)
        f = DailyForcing(rain_mm=0.0, temp_c=35.0)
        pool = advance_pool(pool, f)
        assert pool.water_mm < 10.0

    def test_accumulation(self):
        """Two consecutive rain days → water accumulates."""
        pool = PoolState()
        f = DailyForcing(rain_mm=20.0, temp_c=25.0)
        pool = advance_pool(pool, f)
        after_day1 = pool.water_mm
        pool = advance_pool(pool, f)
        assert pool.water_mm > after_day1

    def test_capping(self):
        """Water cannot exceed POOL_WATER_MAX_MM."""
        pool = PoolState(water_mm=POOL_WATER_MAX_MM - 1.0)
        f = DailyForcing(rain_mm=100.0, temp_c=20.0)
        pool = advance_pool(pool, f)
        assert pool.water_mm <= POOL_WATER_MAX_MM

    def test_dry_day_counter(self):
        """Days below DRY threshold are counted."""
        pool = PoolState(water_mm=0.5)  # below DRY (1.0)
        f = DailyForcing(rain_mm=0.0, temp_c=30.0)
        pool = advance_pool(pool, f)
        assert pool.days_dry >= 1

    def test_dry_day_counter_resets(self):
        """Days dry resets when water recovers."""
        pool = PoolState(water_mm=0.5, days_dry=5)
        f = DailyForcing(rain_mm=30.0, temp_c=25.0)
        pool = advance_pool(pool, f)
        assert pool.days_dry == 0

    def test_temperature_affects_evaporation(self):
        """Higher temperature → faster evaporation → less water retained."""
        pool_cold = PoolState()
        pool_hot = PoolState()
        fc = DailyForcing(rain_mm=10.0, temp_c=20.0)
        fh = DailyForcing(rain_mm=10.0, temp_c=35.0)
        pool_cold = advance_pool(pool_cold, fc)
        pool_hot = advance_pool(pool_hot, fh)
        assert pool_cold.water_mm > pool_hot.water_mm


# ---------------------------------------------------------------------------
# desiccation_rate tests
# ---------------------------------------------------------------------------


class TestDesiccationRate:
    def test_wet_pool(self):
        """Wet pool → no desiccation."""
        pool = PoolState(water_mm=5.0)
        assert desiccation_rate(pool) == 0.0

    def test_grace_period(self):
        """Dry but within grace period → no desiccation."""
        pool = PoolState(water_mm=0.5, days_dry=POOL_DESICCATION_GRACE_DAYS - 1)
        assert desiccation_rate(pool) == 0.0

    def test_after_grace(self):
        """Past grace period → desiccation ramps up."""
        pool = PoolState(water_mm=0.5, days_dry=POOL_DESICCATION_GRACE_DAYS + 2)
        rate = desiccation_rate(pool)
        assert 0.0 < rate <= POOL_DESICC_BASE_DAILY

    def test_saturates(self):
        """Many days dry → rate approaches BASE_DAILY."""
        pool = PoolState(water_mm=0.0, days_dry=30)
        rate = desiccation_rate(pool)
        assert rate > POOL_DESICC_BASE_DAILY * 0.9


# ---------------------------------------------------------------------------
# washout_fraction tests
# ---------------------------------------------------------------------------


class TestWashoutFraction:
    def test_below_threshold(self):
        assert washout_fraction(30.0) == 0.0
        assert washout_fraction(39.0) == 0.0

    def test_at_threshold(self):
        """Exactly at threshold → fraction should be ~0."""
        frac = washout_fraction(POOL_RAIN_WASH_MM)
        assert frac <= 0.01

    def test_at_50mm(self):
        """50mm = threshold + 10mm → fraction = (10/40) * 0.6 = 0.15."""
        frac = washout_fraction(50.0)
        assert 0.0 < frac < POOL_WASH_FRACTION_MAX

    def test_at_80mm(self):
        """80mm = 2*threshold → fraction = 0.6 (cap)."""
        frac = washout_fraction(80.0)
        assert abs(frac - POOL_WASH_FRACTION_MAX) < 0.001

    def test_above_80mm(self):
        """Above 2*threshold → capped at WASH_FRACTION_MAX."""
        frac = washout_fraction(100.0)
        assert abs(frac - POOL_WASH_FRACTION_MAX) < 0.001


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
