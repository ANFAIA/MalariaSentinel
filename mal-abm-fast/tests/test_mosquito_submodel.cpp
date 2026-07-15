// SPDX-License-Identifier: MIT
// test_mosquito_submodel.cpp — GoogleTest pin for the F1.b
// `MosquitoSubmodel` (SoA + 5 per-day ops + density queries).
//
// The three properties pinned here match the wire-spec's
// `tests/test_smoke.cpp` style and the brief in the f1e-submodel
// delegation:
//
//   1. Construction: round(100 * 1000 * 0.3) = 30000 agents.
//   2. 30-day rollout on a 10x10 AOI with 4 active patches: total
//      > 0, both queries non-empty.
//   3. Determinism: two submodels with the same seed and the same
//      patch-state sequence produce byte-equal density results.
#include <gtest/gtest.h>

#include <cstdint>
#include <tuple>
#include <utility>
#include <vector>

#include "aoi.hpp"
#include "mosquito_submodel.hpp"
#include "wire.hpp"

namespace {

// 10x10 AOI at the equator with resolution_m = 111320 so that
// `cells_per_side()` = 10 and `cells_per_side_h()` = 10.
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

// 100 patches at the 10x10 cells (row = i/10, col = i%10); the first
// 4 are active (the top-left 2x2 block), the rest are inactive. Env
// values are pinned to rain=20 mm, temp=25 C, water_frac=0.5.
std::vector<mal_abm_fast::PatchState> make_test_patch_states() {
    std::vector<mal_abm_fast::PatchState> ps(100);
    for (int64_t i = 0; i < 100; ++i) {
        const size_t si = static_cast<size_t>(i);
        ps[si].patch_id   = i;
        ps[si].row        = static_cast<int32_t>(i / 10);
        ps[si].col        = static_cast<int32_t>(i % 10);
        ps[si].activated  = (i < 4);
        ps[si].rain_d     = 20.0f;
        ps[si].temp_d     = 25.0f;
        ps[si].water_frac = 0.5f;
    }
    return ps;
}

}  // namespace

TEST(MalAbmFastMosquitoSubmodel, ConstructionSeedsRoundRobin) {
    mal_abm_fast::MosquitoSubmodel sub(100, 1000, 0.3f, 42);
    // round(100 * 1000 * 0.3) = 30000.
    EXPECT_EQ(sub.total_agents(), 30000);
    // All 100 patches are represented (round-robin: 300 per patch).
    const auto density = sub.density_by_patch();
    ASSERT_EQ(density.size(), 100u);
    for (const auto& [pid, count] : density) {
        EXPECT_EQ(count, 300);
    }
}

TEST(MalAbmFastMosquitoSubmodel, ThirtyDayRollout) {
    mal_abm_fast::MosquitoSubmodel sub(100, 1000, 0.3f, 42);
    const auto aoi = make_test_aoi();
    const auto ps  = make_test_patch_states();
    for (int day = 0; day < 30; ++day) {
        sub.advance_day(aoi, ps);
    }
    EXPECT_GT(sub.total_agents(), 0);
    const auto density = sub.density_by_patch();
    EXPECT_FALSE(density.empty());
    const auto adults = sub.adult_density_by_cell(aoi);
    EXPECT_FALSE(adults.empty());
}

TEST(MalAbmFastMosquitoSubmodel, Determinism) {
    mal_abm_fast::MosquitoSubmodel a(100, 1000, 0.3f, 42);
    mal_abm_fast::MosquitoSubmodel b(100, 1000, 0.3f, 42);
    const auto aoi = make_test_aoi();
    const auto ps  = make_test_patch_states();
    for (int day = 0; day < 30; ++day) {
        a.advance_day(aoi, ps);
        b.advance_day(aoi, ps);
    }
    EXPECT_EQ(a.total_agents(), b.total_agents());
    const auto da = a.density_by_patch();
    const auto db = b.density_by_patch();
    EXPECT_EQ(da, db);
    const auto aa = a.adult_density_by_cell(aoi);
    const auto ab = b.adult_density_by_cell(aoi);
    EXPECT_EQ(aa, ab);
}
