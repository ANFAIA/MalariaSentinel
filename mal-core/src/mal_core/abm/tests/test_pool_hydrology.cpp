// SPDX-License-Identifier: MIT
// test_pool_hydrology.cpp — GoogleTest tests for the M14 pool hydrology
// (water balance, desiccation rate, washout fraction).
//
// Tests cover:
//   1. advance_pool — filling, drying, accumulation, capping
//   2. desiccation_rate — grace period, temperature ramp
//   3. washout_fraction — threshold, linear, cap
//   4. Integration with AquaticCohortBank (desiccation + washout)
#include <gtest/gtest.h>

#include <cmath>
#include <cstdint>
#include <vector>

#include "wire.hpp"
#include "pool_hydrology.hpp"
#include "aquatic_cohort_bank.hpp"

namespace {

// Helper: create PatchState with pool hydrology fields.
mal_abm_fast::PatchState make_patch(int64_t pid, float rain, float temp,
                                     bool active, float water_mm, int days_dry) {
    mal_abm_fast::PatchState ps;
    ps.patch_id = pid;
    ps.row = static_cast<int32_t>(pid / 10);
    ps.col = static_cast<int32_t>(pid % 10);
    ps.activated = active;
    ps.rain_d = rain;
    ps.temp_d = temp;
    ps.water_frac = 0.5f;
    ps.pool_water_mm = water_mm;
    ps.pool_days_dry = days_dry;
    return ps;
}

}  // namespace

// ---------------------------------------------------------------------------
// advance_pool tests
// ---------------------------------------------------------------------------

TEST(PoolHydrology, FillPool) {
    // Rain > evaporation → water accumulates.
    mal_abm_fast::PoolState pool;
    mal_abm_fast::DailyForcing f{30.0f, 25.0f};  // 30mm rain, 25°C
    pool = mal_abm_fast::advance_pool(pool, f);
    EXPECT_GT(pool.water_mm, 0.0f);
    EXPECT_EQ(pool.days_dry, 0);
}

TEST(PoolHydrology, DryPool) {
    // No rain + hot → water depletes.
    mal_abm_fast::PoolState pool;
    pool.water_mm = 10.0f;  // start with some water
    mal_abm_fast::DailyForcing f{0.0f, 35.0f};  // no rain, 35°C
    pool = mal_abm_fast::advance_pool(pool, f);
    EXPECT_LT(pool.water_mm, 10.0f);
}

TEST(PoolHydrology, Accumulation) {
    // Two consecutive rain days → water accumulates.
    mal_abm_fast::PoolState pool;
    mal_abm_fast::DailyForcing f{20.0f, 25.0f};
    pool = mal_abm_fast::advance_pool(pool, f);
    const float after_day1 = pool.water_mm;
    pool = mal_abm_fast::advance_pool(pool, f);
    EXPECT_GT(pool.water_mm, after_day1);
}

TEST(PoolHydrology, Capping) {
    // Water cannot exceed POOL_WATER_MAX_MM.
    mal_abm_fast::PoolState pool;
    pool.water_mm = mal_abm_fast::POOL_WATER_MAX_MM - 1.0f;
    mal_abm_fast::DailyForcing f{100.0f, 20.0f};  // huge rain
    pool = mal_abm_fast::advance_pool(pool, f);
    EXPECT_LE(pool.water_mm, mal_abm_fast::POOL_WATER_MAX_MM);
}

TEST(PoolHydrology, DryDayCounter) {
    // Days below DRY threshold are counted.
    mal_abm_fast::PoolState pool;
    pool.water_mm = 0.5f;  // below DRY (1.0)
    mal_abm_fast::DailyForcing f{0.0f, 30.0f};
    pool = mal_abm_fast::advance_pool(pool, f);
    EXPECT_GE(pool.days_dry, 1);
}

TEST(PoolHydrology, DryDayCounterResets) {
    // Days dry resets when water recovers.
    mal_abm_fast::PoolState pool;
    pool.water_mm = 0.5f;
    pool.days_dry = 5;
    mal_abm_fast::DailyForcing f{30.0f, 25.0f};  // big rain
    pool = mal_abm_fast::advance_pool(pool, f);
    EXPECT_EQ(pool.days_dry, 0);
}

TEST(PoolHydrology, TemperatureAffectsEvaporation) {
    // Higher temperature → faster evaporation → less water retained.
    mal_abm_fast::PoolState pool_cold, pool_hot;
    mal_abm_fast::DailyForcing fc{10.0f, 20.0f};  // 20°C
    mal_abm_fast::DailyForcing fh{10.0f, 35.0f};  // 35°C
    pool_cold = mal_abm_fast::advance_pool(pool_cold, fc);
    pool_hot = mal_abm_fast::advance_pool(pool_hot, fh);
    EXPECT_GT(pool_cold.water_mm, pool_hot.water_mm);
}

// ---------------------------------------------------------------------------
// desiccation_rate tests
// ---------------------------------------------------------------------------

TEST(PoolHydrology, DesiccationRateWet) {
    // Wet pool → no desiccation.
    mal_abm_fast::PoolState pool;
    pool.water_mm = 5.0f;
    EXPECT_EQ(mal_abm_fast::desiccation_rate(pool), 0.0f);
}

TEST(PoolHydrology, DesiccationRateGracePeriod) {
    // Dry but within grace period → no desiccation.
    mal_abm_fast::PoolState pool;
    pool.water_mm = 0.5f;
    pool.days_dry = 3;  // < GRACE_DAYS (5)
    EXPECT_EQ(mal_abm_fast::desiccation_rate(pool), 0.0f);
}

TEST(PoolHydrology, DesiccationRateAfterGrace) {
    // Past grace period → desiccation ramps up.
    mal_abm_fast::PoolState pool;
    pool.water_mm = 0.5f;
    pool.days_dry = 8;  // 3 days past grace
    const float rate = mal_abm_fast::desiccation_rate(pool);
    EXPECT_GT(rate, 0.0f);
    EXPECT_LE(rate, mal_abm_fast::POOL_DESICC_BASE_DAILY);
}

TEST(PoolHydrology, DesiccationRateSaturates) {
    // Many days dry → rate approaches BASE_DAILY.
    mal_abm_fast::PoolState pool;
    pool.water_mm = 0.0f;
    pool.days_dry = 30;
    const float rate = mal_abm_fast::desiccation_rate(pool);
    EXPECT_GT(rate, mal_abm_fast::POOL_DESICC_BASE_DAILY * 0.9f);
}

// ---------------------------------------------------------------------------
// washout_fraction tests
// ---------------------------------------------------------------------------

TEST(PoolHydrology, WashoutBelowThreshold) {
    EXPECT_EQ(mal_abm_fast::washout_fraction(30.0f), 0.0f);
    EXPECT_EQ(mal_abm_fast::washout_fraction(39.0f), 0.0f);
}

TEST(PoolHydrology, WashoutAtThreshold) {
    // Exactly at threshold → fraction should be 0 (linear starts above).
    const float frac = mal_abm_fast::washout_fraction(
        mal_abm_fast::POOL_RAIN_WASH_MM);
    EXPECT_LE(frac, 0.01f);
}

TEST(PoolHydrology, WashoutAt50mm) {
    // 50mm = threshold + 10mm excess → fraction = (10/40) * 0.6 = 0.15
    const float frac = mal_abm_fast::washout_fraction(50.0f);
    EXPECT_GT(frac, 0.0f);
    EXPECT_LT(frac, mal_abm_fast::POOL_WASH_FRACTION_MAX);
}

TEST(PoolHydrology, WashoutAt80mm) {
    // 80mm = 2*threshold → fraction = 0.6 (cap).
    const float frac = mal_abm_fast::washout_fraction(80.0f);
    EXPECT_FLOAT_EQ(frac, mal_abm_fast::POOL_WASH_FRACTION_MAX);
}

TEST(PoolHydrology, WashoutAbove80mm) {
    // Above 2*threshold → capped at WASH_FRACTION_MAX.
    const float frac = mal_abm_fast::washout_fraction(100.0f);
    EXPECT_FLOAT_EQ(frac, mal_abm_fast::POOL_WASH_FRACTION_MAX);
}

// ---------------------------------------------------------------------------
// Integration: AquaticCohortBank with pool hydrology
// ---------------------------------------------------------------------------

TEST(PoolHydrologyIntegration, DesiccationKillsEggsAtDryPatch) {
    // Eggs at a dry patch (past grace) should lose population.
    mal_abm_fast::AquaticCohortBank bank;
    bank.add_eggs(0, 1000);

    // Patch is dry, 10 days past grace.
    std::vector<mal_abm_fast::PatchState> ps = {
        make_patch(0, 0.0f, 30.0f, false, 0.0f, 10)
    };

    const int64_t before = bank.count_by_stage(mal_abm_fast::AquaticStage::EGG);
    bank.advance_day(ps, mal_abm_fast::RuntimeOverrides{});
    const int64_t after = bank.count_by_stage(mal_abm_fast::AquaticStage::EGG);
    EXPECT_LT(after, before);
}

TEST(PoolHydrologyIntegration, DesiccationSparesLarvaeAtWetPatch) {
    // Larvae at a wet patch should NOT be killed by desiccation.
    mal_abm_fast::AquaticCohortBank bank;
    bank.add_eggs(0, 100);
    // Promote to larvae first.
    std::vector<mal_abm_fast::PatchState> ps_wet = {
        make_patch(0, 20.0f, 25.0f, true, 20.0f, 0)
    };
    // Run several days to promote eggs → larvae.
    for (int d = 0; d < 3; ++d) {
        bank.advance_day(ps_wet, mal_abm_fast::RuntimeOverrides{});
    }
    const int64_t larvae_before = bank.count_by_stage(mal_abm_fast::AquaticStage::LARVA);
    if (larvae_before > 0) {
        // Now run one more day with wet patch — desiccation should not apply.
        bank.advance_day(ps_wet, mal_abm_fast::RuntimeOverrides{});
        const int64_t larvae_after = bank.count_by_stage(mal_abm_fast::AquaticStage::LARVA);
        // Larvae may die from other causes, but not from desiccation.
        // The loss should be small (< 50%).
        EXPECT_GT(larvae_after, larvae_before / 2);
    }
}

TEST(PoolHydrologyIntegration, WashoutReducesPopulation) {
    // Heavy rain should flush some aquatic cohorts.
    mal_abm_fast::AquaticCohortBank bank;
    bank.add_eggs(0, 10000);

    // Patch with heavy rain (50mm → washout).
    std::vector<mal_abm_fast::PatchState> ps = {
        make_patch(0, 50.0f, 25.0f, true, 50.0f, 0)
    };

    const int64_t before = bank.total_aquatic();
    bank.advance_day(ps, mal_abm_fast::RuntimeOverrides{});
    const int64_t after = bank.total_aquatic();
    // Should lose some to washout + stage mortality.
    EXPECT_LT(after, before);
}
