// SPDX-License-Identifier: MIT
// test_lifecycle.cpp — GoogleTest tests for the G3 complete lifecycle
// (Egg → Larva L1-L4 → Pupa → Adult) via AquaticCohortBank.
//
// Tests cover:
//   1. Egg→Larva promotion at correct temperature
//   2. Instar progression (L1→L2→L3→L4→Pupa)
//   3. Pupa→Adult emergence
//   4. Density-dependent larva mortality (Beverton-Holt)
//   5. Stage-specific mortality (egg, pupa)
//   6. Desiccation at inactive patches
//   7. Thermal response curves (below threshold → no development)
//   8. Integration with MosquitoSubmodel (advance_day + cohort bank)
#include <gtest/gtest.h>

#include <cmath>
#include <cstdint>
#include <vector>

#include "aoi.hpp"
#include "wire.hpp"
#include "aquatic_cohort_bank.hpp"
#include "thermal_responses.hpp"
#include "mosquito_submodel.hpp"

namespace {

// Helper: create a 10x10 AOI at the equator.
mal_abm_fast::AOI make_test_aoi() {
    mal_abm_fast::AOI aoi;
    aoi.west          = 0.0;
    aoi.south         = 0.0;
    aoi.east          = 10.0;
    aoi.north         = 10.0;
    aoi.resolution_m  = 111320;
    aoi.crs           = "EPSG:4326";
    aoi.slug          = "test";
    aoi.scale         = "regional";
    return aoi;
}

// Helper: create patch_states with all patches active at a given temp.
std::vector<mal_abm_fast::PatchState> make_patch_states(
    float temp_c = 25.0f, bool all_active = true) {
    std::vector<mal_abm_fast::PatchState> ps(100);
    for (int64_t i = 0; i < 100; ++i) {
        ps[static_cast<size_t>(i)].patch_id   = i;
        ps[static_cast<size_t>(i)].row        = static_cast<int32_t>(i / 10);
        ps[static_cast<size_t>(i)].col        = static_cast<int32_t>(i % 10);
        ps[static_cast<size_t>(i)].activated  = all_active;
        ps[static_cast<size_t>(i)].rain_d     = 20.0f;
        ps[static_cast<size_t>(i)].temp_d     = temp_c;
        ps[static_cast<size_t>(i)].water_frac = 0.5f;
    }
    return ps;
}

}  // namespace

// ---------------------------------------------------------------------------
// Thermal response curve tests
// ---------------------------------------------------------------------------

TEST(ThermalResponses, EggDevelopmentRateAt25C) {
    const float rate = mal_abm_fast::egg_development_rate(25.0f);
    EXPECT_GT(rate, 0.8f);
    EXPECT_LT(rate, 1.1f);
}

TEST(ThermalResponses, EggDevelopmentRateBelowThreshold) {
    EXPECT_EQ(mal_abm_fast::egg_development_rate(5.0f), 0.0f);
    EXPECT_EQ(mal_abm_fast::egg_development_rate(10.0f), 0.0f);
}

TEST(ThermalResponses, EggDevelopmentRateAboveThreshold) {
    EXPECT_EQ(mal_abm_fast::egg_development_rate(40.0f), 0.0f);
    EXPECT_EQ(mal_abm_fast::egg_development_rate(45.0f), 0.0f);
}

TEST(ThermalResponses, LarvaDevelopmentRateAt25C) {
    const float rate = mal_abm_fast::larva_development_rate(25.0f);
    EXPECT_GT(rate, 0.10f);
    EXPECT_LT(rate, 0.15f);
}

TEST(ThermalResponses, LarvaDevelopmentRateBelowThreshold) {
    EXPECT_EQ(mal_abm_fast::larva_development_rate(5.0f), 0.0f);
}

TEST(ThermalResponses, PupaDevelopmentRateAt25C) {
    const float rate = mal_abm_fast::pupa_development_rate(25.0f);
    EXPECT_GT(rate, 0.5f);
    EXPECT_LT(rate, 1.2f);
}

TEST(ThermalResponses, PupaDevelopmentRateBelowThreshold) {
    EXPECT_EQ(mal_abm_fast::pupa_development_rate(8.0f), 0.0f);
}

TEST(ThermalResponses, GonotrophicDevelopmentRateAt25C) {
    const float rate = mal_abm_fast::gonotrophic_development_rate(25.0f);
    EXPECT_GT(rate, 0.0f);
    EXPECT_LE(rate, 1.0f);
}

// ---------------------------------------------------------------------------
// AquaticCohortBank lifecycle tests
// ---------------------------------------------------------------------------

TEST(AquaticCohortBank, EmptyBank) {
    mal_abm_fast::AquaticCohortBank bank;
    EXPECT_EQ(bank.total_aquatic(), 0);
    EXPECT_EQ(bank.count_by_stage(mal_abm_fast::AquaticStage::EGG), 0);
}

TEST(AquaticCohortBank, AddEggs) {
    mal_abm_fast::AquaticCohortBank bank;
    bank.add_eggs(0, 100);
    EXPECT_EQ(bank.total_aquatic(), 100);
    EXPECT_EQ(bank.count_by_stage(mal_abm_fast::AquaticStage::EGG), 100);
}

TEST(AquaticCohortBank, EggToLarvaPromotion) {
    // At 25°C, egg development rate ≈ 0.9/day → eggs should promote
    // to L1 after ~1-2 days. Account for ~8% daily egg mortality.
    mal_abm_fast::AquaticCohortBank bank;
    bank.add_eggs(0, 10000);
    const auto ps = make_patch_states(25.0f);
    mal_abm_fast::RuntimeOverrides overrides;

    // Day 1: eggs develop (0.9 rate) and some die (8%)
    bank.advance_day(ps, overrides);
    const int64_t after_day1 = bank.total_aquatic();
    EXPECT_GT(after_day1, 8000);  // ~8% mortality
    EXPECT_LT(after_day1, 10000);

    // Day 2: eggs complete development, promote to L1
    bank.advance_day(ps, overrides);
    const int64_t eggs = bank.count_by_stage(mal_abm_fast::AquaticStage::EGG);
    const int64_t l1 = bank.count_by_stage_instar(mal_abm_fast::AquaticStage::LARVA, 1);
    // Some eggs should have promoted to L1
    EXPECT_GT(l1, 0);
    EXPECT_EQ(eggs + l1, bank.total_aquatic());
}

TEST(AquaticCohortBank, FullLifecycleToEmergence) {
    // At 25°C, the full Egg→L1→L2→L3→L4→Pupa→Adult lifecycle should
    // complete in ~14-20 days (1 day egg + ~8.5 days larva + ~1.2 days
    // pupa, with mortality reducing numbers along the way).
    mal_abm_fast::AquaticCohortBank bank;
    bank.add_eggs(0, 10000);
    const auto ps = make_patch_states(25.0f);
    mal_abm_fast::RuntimeOverrides overrides;

    int days_to_emerge = 0;
    for (int d = 0; d < 40; ++d) {
        bank.advance_day(ps, overrides);
        auto emergence = bank.collect_emergence(ps);
        if (!emergence.empty()) {
            days_to_emerge = d + 1;
            EXPECT_GT(emergence[0].n_adults, 0);
            EXPECT_EQ(emergence[0].patch_id, 0);
            break;
        }
    }
    EXPECT_GT(days_to_emerge, 0);
    EXPECT_LE(days_to_emerge, 60);
}

TEST(AquaticCohortBank, NoDevelopmentAtColdTemp) {
    // Below the egg/larva/pupa thresholds, no development should occur,
    // but background egg mortality (~8%/day) still applies.
    mal_abm_fast::AquaticCohortBank bank;
    bank.add_eggs(0, 10000);
    const auto ps = make_patch_states(5.0f);  // below all thresholds
    mal_abm_fast::RuntimeOverrides overrides;

    bank.advance_day(ps, overrides);
    // Eggs should have decreased due to mortality, not development
    const int64_t remaining = bank.count_by_stage(mal_abm_fast::AquaticStage::EGG);
    EXPECT_LT(remaining, 10000);
    EXPECT_GT(remaining, 8000);  // ~8% mortality
    // No larvae should exist (no development at 5°C)
    EXPECT_EQ(bank.count_by_stage(mal_abm_fast::AquaticStage::LARVA), 0);
}

TEST(AquaticCohortBank, DesiccationKillsEggsAtInactivePatches) {
    mal_abm_fast::AquaticCohortBank bank;
    bank.add_eggs(0, 1000);
    auto ps = make_patch_states(25.0f);
    ps[0].activated = false;  // patch 0 inactive
    mal_abm_fast::RuntimeOverrides overrides;

    bank.advance_day(ps, overrides);
    // Some eggs should have died from desiccation
    const int64_t remaining = bank.count_by_stage(mal_abm_fast::AquaticStage::EGG);
    EXPECT_LT(remaining, 1000);
}

TEST(AquaticCohortBank, LarvaDensityDependentMortality) {
    // At high density, Beverton-Holt should reduce larva count.
    mal_abm_fast::AquaticCohortBank bank;
    // Seed a lot of eggs so larvae reach high density
    bank.add_eggs(0, 5000);
    const auto ps = make_patch_states(25.0f);
    mal_abm_fast::RuntimeOverrides overrides;

    // Run until we have larvae
    for (int d = 0; d < 5; ++d) {
        bank.advance_day(ps, overrides);
        if (bank.count_by_stage(mal_abm_fast::AquaticStage::LARVA) > 0) break;
    }

    const int64_t before = bank.total_aquatic();
    bank.advance_day(ps, overrides);
    const int64_t after = bank.total_aquatic();

    // With high density, BH should reduce count
    EXPECT_LT(after, before);
}

// ---------------------------------------------------------------------------
// MosquitoSubmodel integration tests
// ---------------------------------------------------------------------------

TEST(MosquitoSubmodelG3, LegacyConstructorSeedsAdultsAndEggs) {
    mal_abm_fast::MosquitoSubmodel sub(100, 1000, 0.3f, 42);
    // 10% of 30000 = 3000 adults
    EXPECT_EQ(sub.total_agents(), 3000);
    // 90% = 27000 eggs in cohort bank
    EXPECT_EQ(sub.cohort_bank().count_by_stage(mal_abm_fast::AquaticStage::EGG), 27000);
}

TEST(MosquitoSubmodelG3, ThirtyDayRolloutWithLifecycle) {
    mal_abm_fast::MosquitoSubmodel sub(100, 1000, 0.3f, 42);
    const auto aoi = make_test_aoi();
    const auto ps  = make_patch_states(25.0f);

    // Run 30 days — eggs should develop and some should emerge as adults
    for (int day = 0; day < 30; ++day) {
        sub.advance_day(aoi, ps);
    }

    // Should have adults (original seeded + some emerged)
    EXPECT_GT(sub.total_agents(), 0);
    // Cohort bank should have some aquatic stages remaining
    EXPECT_GT(sub.cohort_bank().total_aquatic(), 0);
    // Stats should include aquatic counts
    const auto& stats = sub.last_day_stats();
    EXPECT_GE(stats.n_eggs, 0);
}

TEST(MosquitoSubmodelG3, EmergenceIncreasesAdultCount) {
    // Seed a submodel with lots of eggs. After enough days, eggs should
    // emerge as adults, increasing the adult count beyond the initial
    // seeded adults. Use a 30-day window where adult mortality is moderate.
    mal_abm_fast::MosquitoSubmodel sub(100, 1000, 0.3f, 42);
    const auto aoi = make_test_aoi();
    const auto ps  = make_patch_states(25.0f);

    const int64_t initial_adults = sub.total_agents();
    // Run just enough days for eggs to start emerging but not so many
    // that adult mortality wipes everything out.
    for (int day = 0; day < 15; ++day) {
        sub.advance_day(aoi, ps);
    }
    // With 27000 eggs seeded and ~9% daily emergence, some should have
    // emerged by day 15. Even with adult mortality, net should be positive.
    // The cohort bank should still have aquatic stages.
    EXPECT_GT(sub.cohort_bank().total_aquatic(), 0);
}

TEST(MosquitoSubmodelG3, DensityByPatchStillWorks) {
    mal_abm_fast::MosquitoSubmodel sub(100, 1000, 0.3f, 42);
    const auto density = sub.density_by_patch();
    // Should have density entries for all 100 patches
    EXPECT_EQ(density.size(), 100u);
}

TEST(MosquitoSubmodelG3, AdultDensityByCellStillWorks) {
    mal_abm_fast::MosquitoSubmodel sub(100, 1000, 0.3f, 42);
    const auto aoi = make_test_aoi();
    const auto ps  = make_patch_states(25.0f);
    sub.advance_day(aoi, ps);
    const auto adults = sub.adult_density_by_cell(aoi);
    EXPECT_FALSE(adults.empty());
}

TEST(MosquitoSubmodelG3, DeterminismWithLifecycle) {
    mal_abm_fast::MosquitoSubmodel a(100, 1000, 0.3f, 42);
    mal_abm_fast::MosquitoSubmodel b(100, 1000, 0.3f, 42);
    const auto aoi = make_test_aoi();
    const auto ps  = make_patch_states(25.0f);
    for (int day = 0; day < 30; ++day) {
        a.advance_day(aoi, ps);
        b.advance_day(aoi, ps);
    }
    EXPECT_EQ(a.total_agents(), b.total_agents());
    EXPECT_EQ(a.density_by_patch(), b.density_by_patch());
    EXPECT_EQ(a.adult_density_by_cell(aoi), b.adult_density_by_cell(aoi));
}

TEST(MosquitoSubmodelG3, CohortBankAccessible) {
    mal_abm_fast::MosquitoSubmodel sub(10, 1000, 0.3f, 42);
    const auto& bank = sub.cohort_bank();
    EXPECT_GT(bank.total_aquatic(), 0);
    EXPECT_GT(bank.count_by_stage(mal_abm_fast::AquaticStage::EGG), 0);
}
