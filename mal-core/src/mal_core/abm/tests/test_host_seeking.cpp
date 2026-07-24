// SPDX-License-Identifier: MIT
// test_host_seeking.cpp — GoogleTest tests for G5: HostLandscape and
// HostSeekingModel (spatial host-seeking kernel).
//
// Tests cover:
//   1. HostCell defaults
//   2. HostLandscape defaults (no NC file)
//   3. HostLandscape at() bounds
//   4. HostPreference defaults (An. gambiae anthropophily)
//   5. HostSeekingModel select_host weighted roulette
//   6. HostSeekingModel approach_vector direction and magnitude
//   7. HostSeekingModel compute_attraction on default landscape
//   8. Dominant host type selection
//   9. Approach vector zero distance
//  10. Select host with empty attraction list
#include <gtest/gtest.h>

#include <cmath>
#include <cstdint>
#include <utility>
#include <vector>

#include "aoi.hpp"
#include "host_landscape.hpp"
#include "host_seeking.hpp"
#include "prng.hpp"
#include "wire.hpp"

namespace {

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

}  // namespace

// ---------------------------------------------------------------------------
// HostCell defaults
// ---------------------------------------------------------------------------

TEST(HostCell, DefaultValues) {
    mal_abm_fast::HostCell cell;
    EXPECT_FLOAT_EQ(cell.humans_present, 1.0f);
    EXPECT_FLOAT_EQ(cell.cattle_present, 0.0f);
    EXPECT_FLOAT_EQ(cell.goats_present, 0.0f);
    EXPECT_FLOAT_EQ(cell.sheep_present, 0.0f);
    EXPECT_FLOAT_EQ(cell.wildlife_proxy, 0.0f);
    EXPECT_GT(cell.indoor_fraction, 0.0f);
    EXPECT_LE(cell.indoor_fraction, 1.0f);
    EXPECT_GE(cell.urbanicity, 0.0f);
    EXPECT_LE(cell.urbanicity, 1.0f);
}

// ---------------------------------------------------------------------------
// HostLandscape defaults
// ---------------------------------------------------------------------------

TEST(HostLandscape, DefaultsWhenNoFile) {
    mal_abm_fast::HostLandscape landscape;
    const auto aoi = make_test_aoi();
    // Non-existent file should populate defaults without throwing.
    landscape.load_from_nc("/tmp/nonexistent_host_static.nc", aoi);

    EXPECT_FALSE(landscape.has_data());
    EXPECT_GT(landscape.h(), 0);
    EXPECT_GT(landscape.w(), 0);
}

TEST(HostLandscape, AtReturnsDefaultsForOutOfBounds) {
    mal_abm_fast::HostLandscape landscape;
    const auto aoi = make_test_aoi();
    landscape.load_from_nc("/tmp/nonexistent_host_static.nc", aoi);

    // Out of bounds should return default HostCell.
    auto cell = landscape.at(-1, 0);
    EXPECT_FLOAT_EQ(cell.humans_present, 1.0f);

    cell = landscape.at(0, landscape.w() + 10);
    EXPECT_FLOAT_EQ(cell.humans_present, 1.0f);
}

TEST(HostLandscape, AtReturnsPopulatedCellInBounds) {
    mal_abm_fast::HostLandscape landscape;
    const auto aoi = make_test_aoi();
    landscape.load_from_nc("/tmp/nonexistent_host_static.nc", aoi);

    // In-bounds cell should have the default humans_present=1.0.
    auto cell = landscape.at(0, 0);
    EXPECT_FLOAT_EQ(cell.humans_present, 1.0f);
    EXPECT_FLOAT_EQ(cell.cattle_present, 0.0f);
}

// ---------------------------------------------------------------------------
// HostPreference defaults
// ---------------------------------------------------------------------------

TEST(HostPreference, AnthropophilicDefaults) {
    mal_abm_fast::HostPreference pref;
    EXPECT_FLOAT_EQ(pref.human, 0.99f);
    EXPECT_FLOAT_EQ(pref.cattle, 0.005f);
    EXPECT_FLOAT_EQ(pref.goat, 0.003f);
    EXPECT_FLOAT_EQ(pref.sheep, 0.001f);
    EXPECT_FLOAT_EQ(pref.wildlife, 0.001f);

    // Sum should be ~1.0.
    const float total = pref.human + pref.cattle + pref.goat +
                        pref.sheep + pref.wildlife;
    EXPECT_NEAR(total, 1.0f, 0.001f);
}

// ---------------------------------------------------------------------------
// HostSeekingModel::select_host
// ---------------------------------------------------------------------------

TEST(HostSeekingModel, SelectHostFromEmptyReturnsHuman) {
    mal_abm_fast::HostSeekingModel model;
    mal_abm_fast::Prng rng(42);
    std::vector<mal_abm_fast::HostAttraction> empty;
    auto host = model.select_host(empty, rng);
    EXPECT_EQ(host, mal_abm_fast::HostType::HUMAN);
}

TEST(HostSeekingModel, SelectHostDominantWhenSingleEntry) {
    mal_abm_fast::HostSeekingModel model;
    mal_abm_fast::Prng rng(42);
    std::vector<mal_abm_fast::HostAttraction> attrs = {
        {30.0f, 1.0f, mal_abm_fast::HostType::CATTLE}
    };
    // With only one entry, should always select that host type.
    for (int i = 0; i < 100; ++i) {
        auto host = model.select_host(attrs, rng);
        EXPECT_EQ(host, mal_abm_fast::HostType::CATTLE);
    }
}

TEST(HostSeekingModel, SelectHostWeightedBias) {
    mal_abm_fast::HostSeekingModel model;
    mal_abm_fast::Prng rng(42);

    // Two entries: human with high attraction, cattle with low.
    std::vector<mal_abm_fast::HostAttraction> attrs = {
        {30.0f, 100.0f, mal_abm_fast::HostType::HUMAN},
        {50.0f, 1.0f,   mal_abm_fast::HostType::CATTLE}
    };

    int human_count = 0;
    const int n_trials = 1000;
    for (int i = 0; i < n_trials; ++i) {
        if (model.select_host(attrs, rng) == mal_abm_fast::HostType::HUMAN) {
            human_count++;
        }
    }
    // Human should be selected >99% of the time given 100:1 ratio.
    EXPECT_GT(human_count, 990);
}

// ---------------------------------------------------------------------------
// HostSeekingModel::approach_vector
// ---------------------------------------------------------------------------

TEST(HostSeekingModel, ApproachVectorTowardTarget) {
    mal_abm_fast::HostSeekingModel model;
    const auto aoi = make_test_aoi();

    // Mosquito at (0,0), target at (1,0) — one cell south.
    auto [dr, dc] = model.approach_vector(0, 0, 1, 0, aoi, 50.0f);

    // Should move toward the target (positive d_row).
    EXPECT_GT(dr, 0.0f);
    EXPECT_NEAR(dc, 0.0f, 1e-5f);
}

TEST(HostSeekingModel, ApproachVectorClampedToStepSize) {
    mal_abm_fast::HostSeekingModel model;
    const auto aoi = make_test_aoi();

    // Mosquito at (0,0), target at (5,5) — far away.
    // step_size = 50m, cell_size = 111320m → step is < 1 cell.
    auto [dr, dc] = model.approach_vector(0, 0, 5, 5, aoi, 50.0f);

    // Step magnitude should be ≤ step_size_m / cell_size_m.
    const float cell_size = static_cast<float>(aoi.resolution_m);
    const float max_step_cells = 50.0f / cell_size;
    const float mag = std::sqrt(dr * dr + dc * dc);
    EXPECT_LE(mag, max_step_cells + 1e-5f);
}

TEST(HostSeekingModel, ApproachVectorZeroDistance) {
    mal_abm_fast::HostSeekingModel model;
    const auto aoi = make_test_aoi();

    // Same position — should return (0, 0).
    auto [dr, dc] = model.approach_vector(3, 3, 3, 3, aoi, 50.0f);
    EXPECT_NEAR(dr, 0.0f, 1e-6f);
    EXPECT_NEAR(dc, 0.0f, 1e-6f);
}

// ---------------------------------------------------------------------------
// HostSeekingModel::compute_attraction on default landscape
// ---------------------------------------------------------------------------

TEST(HostSeekingModel, ComputeAttractionDefaultLandscape) {
    mal_abm_fast::HostSeekingModel model;
    mal_abm_fast::HostLandscape landscape;
    const auto aoi = make_test_aoi();
    landscape.load_from_nc("/tmp/nonexistent_host_static.nc", aoi);

    // Mosquito at centre of grid.
    const int32_t mid_r = landscape.h() / 2;
    const int32_t mid_c = landscape.w() / 2;

    auto attrs = model.compute_attraction(mid_r, mid_c, landscape, aoi);

    // Default landscape has humans=1.0 everywhere, so there should be
    // attraction from nearby cells.
    EXPECT_FALSE(attrs.empty());

    // All attractions should be positive.
    for (const auto& a : attrs) {
        EXPECT_GT(a.attraction, 0.0f);
        EXPECT_GE(a.distance_m, 0.0f);
    }

    // Attractions should be sorted descending.
    for (size_t i = 1; i < attrs.size(); ++i) {
        EXPECT_GE(attrs[i - 1].attraction, attrs[i].attraction);
    }
}

TEST(HostSeekingModel, ComputeAttractionExcludesFarCells) {
    mal_abm_fast::HostSeekingModel model;
    mal_abm_fast::HostLandscape landscape;
    const auto aoi = make_test_aoi();
    landscape.load_from_nc("/tmp/nonexistent_host_static.nc", aoi);

    // Search radius 70m should not reach cells beyond 70m.
    const int32_t mid_r = landscape.h() / 2;
    const int32_t mid_c = landscape.w() / 2;

    auto attrs = model.compute_attraction(mid_r, mid_c, landscape, aoi, 70.0f);
    for (const auto& a : attrs) {
        EXPECT_LE(a.distance_m, 70.0f + 1e-3f);
    }
}

// ---------------------------------------------------------------------------
// Dominant host type
// ---------------------------------------------------------------------------

TEST(HostSeekingModel, DominantHostIsHumanInDefault) {
    mal_abm_fast::HostSeekingModel model;
    mal_abm_fast::HostLandscape landscape;
    const auto aoi = make_test_aoi();
    landscape.load_from_nc("/tmp/nonexistent_host_static.nc", aoi);

    const int32_t mid_r = landscape.h() / 2;
    const int32_t mid_c = landscape.w() / 2;

    auto attrs = model.compute_attraction(mid_r, mid_c, landscape, aoi);
    ASSERT_FALSE(attrs.empty());

    // Default landscape has only humans → primary_host should be HUMAN.
    for (const auto& a : attrs) {
        EXPECT_EQ(a.primary_host, mal_abm_fast::HostType::HUMAN);
    }
}
