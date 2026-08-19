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
#include <stdexcept>
#include <utility>
#include <vector>

#include "aoi.hpp"
#include "host_landscape.hpp"
#include "host_seeking.hpp"
#include "mobility_schedule.hpp"
#include "prng.hpp"
#include "species.hpp"
#include "species_params.hpp"
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

// 1 km cells (like the Ghana ABM): ~7x7 grid for a 0.06 deg AOI.
mal_abm_fast::AOI make_fine_aoi() {
    mal_abm_fast::AOI aoi;
    aoi.west          = 0.0;
    aoi.south         = 0.0;
    aoi.east          = 0.06;
    aoi.north         = 0.06;
    aoi.resolution_m  = 1000;
    aoi.crs           = "EPSG:4326";
    aoi.slug          = "test_fine";
    aoi.scale         = "regional";
    return aoi;
}

// Row-major zero-filled H_eff grid for a loaded landscape.
std::vector<float> zero_grid(const mal_abm_fast::HostLandscape& l) {
    return std::vector<float>(static_cast<size_t>(l.h()) * static_cast<size_t>(l.w()),
                              0.0f);
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

// ---------------------------------------------------------------------------
// M7.8 Fase 3: effective (phase-specific) HostLandscape views
// ---------------------------------------------------------------------------

TEST(HostLandscape, MakeEffectiveReplacesHumansLeavesResidentialUntouched) {
    const auto aoi = make_fine_aoi();
    mal_abm_fast::HostLandscape residential;
    residential.load_from_nc("/tmp/nonexistent_host_static.nc", aoi);  // humans=1.0

    const int32_t h = residential.h();
    const int32_t w = residential.w();
    auto h_eff = zero_grid(residential);
    h_eff[static_cast<size_t>(3) * w + 3] = 500.0f;  // strong host at (3,3)

    auto eff = mal_abm_fast::HostLandscape::make_effective(residential, h_eff, h, w);

    // The effective view shows the replaced humans.
    EXPECT_TRUE(eff.is_effective());
    EXPECT_EQ(eff.h(), h);
    EXPECT_EQ(eff.w(), w);
    EXPECT_FLOAT_EQ(eff.at(3, 3).humans_present, 500.0f);
    EXPECT_FLOAT_EQ(eff.at(0, 0).humans_present, 0.0f);

    // The residential grid is untouched.
    EXPECT_FALSE(residential.is_effective());
    EXPECT_FLOAT_EQ(residential.at(3, 3).humans_present, 1.0f);
    EXPECT_FLOAT_EQ(residential.at(0, 0).humans_present, 1.0f);

    // Non-human fields are inherited from the residential grid.
    EXPECT_FLOAT_EQ(eff.at(3, 3).indoor_fraction, residential.at(3, 3).indoor_fraction);
    EXPECT_FLOAT_EQ(eff.at(3, 3).urbanicity, residential.at(3, 3).urbanicity);
    EXPECT_FLOAT_EQ(eff.at(3, 3).cattle_present, residential.at(3, 3).cattle_present);
}

TEST(HostLandscape, MakeEffectiveRejectsWrongSize) {
    const auto aoi = make_fine_aoi();
    mal_abm_fast::HostLandscape residential;
    residential.load_from_nc("/tmp/nonexistent_host_static.nc", aoi);

    const int32_t h = residential.h();
    const int32_t w = residential.w();
    std::vector<float> bad(static_cast<size_t>(h) * w + 1, 0.0f);
    EXPECT_THROW(
        mal_abm_fast::HostLandscape::make_effective(residential, bad, h, w),
        std::runtime_error);
}

// ---------------------------------------------------------------------------
// M7.8 Fase 3: species params integration
// ---------------------------------------------------------------------------

TEST(HostSeekingModel, SpeciesRadiusIsDefaultWhenNotOverridden) {
    const auto aoi = make_fine_aoi();
    mal_abm_fast::HostLandscape landscape;
    landscape.load_from_nc("/tmp/nonexistent_host_static.nc", aoi);  // humans=1.0

    auto sp = mal_abm_fast::species_params_for(
        mal_abm_fast::MosquitoSpeciesId::ANOPHELES_COLUZZII);
    sp.host_seeking_radius_m = 1500.0f;  // non-default → proves species value is used

    mal_abm_fast::HostSeekingModel model;
    EXPECT_FALSE(model.has_species_params());
    model.set_species_params(sp);
    EXPECT_TRUE(model.has_species_params());

    const int32_t mid_r = landscape.h() / 2;
    const int32_t mid_c = landscape.w() / 2;

    // Default (sentinel) radius resolves to the species radius.
    const auto by_default   = model.compute_attraction(mid_r, mid_c, landscape, aoi);
    const auto by_explicit  = model.compute_attraction(mid_r, mid_c, landscape, aoi, 1500.0f);
    ASSERT_EQ(by_default.size(), by_explicit.size());
    for (size_t i = 0; i < by_default.size(); ++i) {
        EXPECT_NEAR(by_default[i].attraction, by_explicit[i].attraction, 1e-6f);
        EXPECT_FLOAT_EQ(by_default[i].distance_m, by_explicit[i].distance_m);
    }
    // Species radius is wider than the 300m default → more cells.
    const auto by_300 = model.compute_attraction(mid_r, mid_c, landscape, aoi, 300.0f);
    EXPECT_GT(by_default.size(), by_300.size());

    // A positive explicit radius still overrides the species default.
    EXPECT_EQ(by_300.size(),
              model.compute_attraction(mid_r, mid_c, landscape, aoi, 300.0f).size());
}

TEST(HostSeekingModel, SpeciesPreferenceDrivesDominantHost) {
    const auto aoi = make_fine_aoi();
    mal_abm_fast::HostLandscape residential;
    residential.load_from_nc("/tmp/nonexistent_host_static.nc", aoi);

    const int32_t h = residential.h();
    const int32_t w = residential.w();
    auto h_eff = zero_grid(residential);
    auto c_eff = zero_grid(residential);
    h_eff[static_cast<size_t>(3) * w + 3] = 10.0f;    // 10 humans
    c_eff[static_cast<size_t>(3) * w + 3] = 1000.0f;  // 1000 cattle

    auto eff = mal_abm_fast::HostLandscape::make_effective(
        residential, h_eff, c_eff, h, w);

    // coluzzii: strongly anthropophilic → HUMAN dominates despite 100x cattle.
    mal_abm_fast::HostSeekingModel coluzzii;
    coluzzii.set_species_params(mal_abm_fast::species_params_for(
        mal_abm_fast::MosquitoSpeciesId::ANOPHELES_COLUZZII));
    auto attrs = coluzzii.compute_attraction(3, 3, eff, aoi);
    ASSERT_FALSE(attrs.empty());
    EXPECT_EQ(attrs.front().primary_host, mal_abm_fast::HostType::HUMAN);

    // arabiensis: more zoophilic → cattle dominates.
    mal_abm_fast::HostSeekingModel arabiensis;
    arabiensis.set_species_params(mal_abm_fast::species_params_for(
        mal_abm_fast::MosquitoSpeciesId::ANOPHELES_ARABIENSIS));
    auto attrs2 = arabiensis.compute_attraction(3, 3, eff, aoi);
    ASSERT_FALSE(attrs2.empty());
    EXPECT_EQ(attrs2.front().primary_host, mal_abm_fast::HostType::CATTLE);
}

// ---------------------------------------------------------------------------
// M7.8 Fase 3: directed movement (step_toward_host)
// ---------------------------------------------------------------------------

TEST(HostSeekingModel, StepTowardHostMovesCloser) {
    const auto aoi = make_fine_aoi();
    mal_abm_fast::HostLandscape residential;
    residential.load_from_nc("/tmp/nonexistent_host_static.nc", aoi);

    const int32_t h = residential.h();
    const int32_t w = residential.w();
    auto h_eff = zero_grid(residential);
    h_eff[static_cast<size_t>(3) * w + 3] = 5000.0f;  // strong host at (3,3)

    auto eff = mal_abm_fast::HostLandscape::make_effective(residential, h_eff, h, w);

    mal_abm_fast::HostSeekingModel model;
    auto sp = mal_abm_fast::species_params_for(
        mal_abm_fast::MosquitoSpeciesId::ANOPHELES_COLUZZII);
    sp.host_seeking_scale_m = 1000.0f;  // long plume → detection reaches ~2 km
    model.set_species_params(sp);

    // Mosquito 2 cells west of the host, step one full cell.
    auto step = model.step_toward_host(3, 1, eff, aoi, /*step_size_m=*/1000.0f);
    ASSERT_TRUE(step.has_value());
    const auto [nr, nc] = *step;
    EXPECT_EQ(nr, 3);
    EXPECT_EQ(nc, 2);

    // The new cell is strictly closer to the host cell (3,3).
    const auto dist_to_host = [](int32_t r, int32_t c) {
        const float dr = static_cast<float>(r - 3);
        const float dc = static_cast<float>(c - 3);
        return std::sqrt(dr * dr + dc * dc) * 1000.0f;
    };
    EXPECT_LT(dist_to_host(nr, nc), dist_to_host(3, 1));
}

TEST(HostSeekingModel, StepTowardHostNulloptWhenNoHost) {
    const auto aoi = make_fine_aoi();
    mal_abm_fast::HostLandscape residential;
    residential.load_from_nc("/tmp/nonexistent_host_static.nc", aoi);

    const int32_t h = residential.h();
    const int32_t w = residential.w();
    auto h_eff = zero_grid(residential);  // no hosts anywhere
    auto eff = mal_abm_fast::HostLandscape::make_effective(residential, h_eff, h, w);

    mal_abm_fast::HostSeekingModel model;
    model.set_species_params(mal_abm_fast::species_params_for(
        mal_abm_fast::MosquitoSpeciesId::ANOPHELES_COLUZZII));

    EXPECT_FALSE(model.step_toward_host(3, 3, eff, aoi, 1000.0f).has_value());
}

// ---------------------------------------------------------------------------
// M7.8 Fase 4: phase activity gate
// ---------------------------------------------------------------------------

TEST(TimePhase, PhaseActiveGatesByWeight) {
    auto coluzzii = mal_abm_fast::species_params_for(
        mal_abm_fast::MosquitoSpeciesId::ANOPHELES_COLUZZII);
    // coluzzii weights {0.02, 0.10, 0.80, 0.08} all > epsilon → active in
    // all four phases (including a small DAY fraction).
    EXPECT_TRUE(mal_abm_fast::phase_active(coluzzii, mal_abm_fast::TimePhase::DAY));
    EXPECT_TRUE(mal_abm_fast::phase_active(coluzzii, mal_abm_fast::TimePhase::EVENING));
    EXPECT_TRUE(mal_abm_fast::phase_active(coluzzii, mal_abm_fast::TimePhase::NIGHT));
    EXPECT_TRUE(mal_abm_fast::phase_active(coluzzii, mal_abm_fast::TimePhase::DAWN));

    // A species with zero DAY weight is inactive during the day but still
    // active at night.
    mal_abm_fast::SpeciesParams nocturnal = coluzzii;
    nocturnal.activity_weights[static_cast<size_t>(mal_abm_fast::TimePhase::DAY)] = 0.0f;
    EXPECT_FALSE(mal_abm_fast::phase_active(nocturnal, mal_abm_fast::TimePhase::DAY));
    EXPECT_TRUE(mal_abm_fast::phase_active(nocturnal, mal_abm_fast::TimePhase::NIGHT));
}
