// test_pool_water.cpp — M7.4.1 catchment-runoff pool physics.
//
// Regression tests for the water balance that lets temporary pools
// actually produce adults:
//   1. Direct-rainfall pool (catchment_factor 1): a 15 mm storm keeps
//      water >= BREED for only a few days — NOT enough for larvae.
//      Documents the old behaviour; the assertion pins it.
//   2. Urban catchment pool (factor 6.6 = 1 + 8*0.7, evap 0.6): the
//      same storm stays breeding-capable >= 20 days — larvae (8-10 d)
//      complete. The fondo fix.
//   3. POOL_WATER_CAPACITY_SAT_MM constant sanity + the urban
//      baseline (6 mm) maps to a ~0.12 capacity factor.
#include "mal_abm_fast/pool_hydrology.hpp"

#include <gtest/gtest.h>

namespace mal_abm_fast {
namespace {

int active_days_after_storm(float rain_mm, float factor, float evap_scale,
                            int horizon) {
    PoolState p;
    p = advance_pool(p, DailyForcing{rain_mm, 27.0f, factor, evap_scale});
    int active = (p.water_mm >= POOL_WATER_BREED_MM) ? 1 : 0;
    const DailyForcing dry{0.0f, 27.0f, 1.0f, 1.0f};
    for (int d = 0; d < horizon; ++d) {
        p = advance_pool(p, dry);
        if (p.water_mm >= POOL_WATER_BREED_MM) ++active;
    }
    return active;
}

TEST(PoolWater, DirectRainStormDriesBeforeLarvaeComplete) {
    // 15 mm direct: evaporates (5 mm/d at ~27 C) in a few days.
    const int days = active_days_after_storm(15.0f, 1.0f, 1.0f, 30);
    EXPECT_LE(days, 6);
    EXPECT_GE(days, 1);
}

TEST(PoolWater, UrbanCatchmentPoolOutlastsLarvalPeriod) {
    // factor 6.6 = 1 + CR(8) * C_eff(0.7); shaded evap 0.6.
    const int days = active_days_after_storm(15.0f, 6.6f, 0.6f, 60);
    EXPECT_GE(days, 20);  // larval development 8-10 d completes
}

TEST(PoolWater, CapacitySatConstantAndUrbanBaselineFactor) {
    EXPECT_FLOAT_EQ(POOL_WATER_CAPACITY_SAT_MM, 50.0f);
    EXPECT_FLOAT_EQ(POOL_URBAN_BASELINE_MM, 6.0f);
    const double baseline_factor =
        static_cast<double>(POOL_URBAN_BASELINE_MM) /
        static_cast<double>(POOL_WATER_CAPACITY_SAT_MM);
    EXPECT_NEAR(baseline_factor, 0.12, 1e-9);
}

}  // namespace
}  // namespace mal_abm_fast
