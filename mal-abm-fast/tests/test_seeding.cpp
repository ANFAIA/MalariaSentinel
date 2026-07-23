// SPDX-License-Identifier: MIT
// test_seeding.cpp — GoogleTest pin for the detection-based
// initial seeding subsystem.
//
// Properties pinned here:
//
//   1. UNIFORM mode: build_seed_instructions returns empty
//      (the submodel uses init_frac for every patch — legacy path).
//   2. RANDOM_VIABLE mode: picks N random patch_ids from the
//      viable list (without replacement, deterministic given seed).
//   3. EXPLICIT mode: a point within radius snaps to the nearest
//      patch; a point outside radius is dropped.
//   4. SeedInstruction counts (n_adults + n_larvae) are honoured by
//      the MosquitoSubmodel detection-based constructor.
//   5. Legacy UNIFORM constructor still works (backward compat).
#include <gtest/gtest.h>

#include <array>
#include <cstdint>
#include <set>
#include <tuple>
#include <vector>

#include "aoi.hpp"
#include "mosquito_submodel.hpp"
#include "prng.hpp"
#include "seeding.hpp"
#include "wire.hpp"

namespace {

// Build a 100-patch synthetic habitat (10x10 grid) with lon/lat
// spread evenly across (0, 0) - (10, 10). All patches pass the
// viability filter (water_frac=1.0, twi=10 > 8).
struct FakeHabitat {
    std::vector<int32_t> ids;
    std::vector<std::array<double, 2>> lonlat;
    std::vector<std::array<int32_t, 2>> rowcol;
};

FakeHabitat make_fake_habitat() {
    FakeHabitat h;
    h.ids.reserve(100);
    h.lonlat.reserve(100);
    h.rowcol.reserve(100);
    for (int32_t i = 0; i < 100; ++i) {
        h.ids.push_back(i);
        // Place each patch at the centre of a 1-deg cell.
        h.lonlat.push_back({static_cast<double>(i % 10) + 0.5,
                            static_cast<double>(i / 10) + 0.5});
        h.rowcol.push_back({i / 10, i % 10});
    }
    return h;
}

}  // namespace

// ---------------------------------------------------------------------------
// build_seed_instructions — UNIFORM mode
// ---------------------------------------------------------------------------

TEST(MalAbmFastSeeding, UniformModeReturnsEmptyInstructions) {
    auto h = make_fake_habitat();
    mal_abm_fast::SeedingConfig cfg;
    cfg.mode = mal_abm_fast::SeedingMode::UNIFORM;
    mal_abm_fast::Prng rng(42);
    const auto out = mal_abm_fast::build_seed_instructions_for_patches(
        cfg, h.ids, h.lonlat, h.rowcol, rng);
    EXPECT_TRUE(out.empty());
}

TEST(MalAbmFastSeeding, UniformModeDoesNotConsumeRng) {
    // UNIFORM is a no-op; the Prng state should be unchanged.
    auto h = make_fake_habitat();
    mal_abm_fast::SeedingConfig cfg;
    cfg.mode = mal_abm_fast::SeedingMode::UNIFORM;
    mal_abm_fast::Prng rng(42);
    const auto state_before = rng.peek_state();
    const auto out = mal_abm_fast::build_seed_instructions_for_patches(
        cfg, h.ids, h.lonlat, h.rowcol, rng);
    EXPECT_TRUE(out.empty());
    EXPECT_EQ(rng.peek_state(), state_before);
}

// ---------------------------------------------------------------------------
// build_seed_instructions — RANDOM_VIABLE mode
// ---------------------------------------------------------------------------

TEST(MalAbmFastSeeding, RandomViablePicksNPatches) {
    auto h = make_fake_habitat();
    mal_abm_fast::SeedingConfig cfg;
    cfg.mode = mal_abm_fast::SeedingMode::RANDOM_VIABLE;
    cfg.n_detections = 5;
    cfg.n_adults_per_detection = 20;
    cfg.n_larvae_per_detection = 10;
    mal_abm_fast::Prng rng(42);
    const auto out = mal_abm_fast::build_seed_instructions_for_patches(
        cfg, h.ids, h.lonlat, h.rowcol, rng);
    ASSERT_EQ(out.size(), 5u);

    // All patch_ids must be unique and within the viable set.
    std::set<int32_t> seen;
    for (const auto& inst : out) {
        EXPECT_GE(inst.patch_id, 0);
        EXPECT_LT(inst.patch_id, 100);
        EXPECT_TRUE(seen.insert(inst.patch_id).second)
            << "duplicate patch_id " << inst.patch_id;
        EXPECT_EQ(inst.n_adults, 20);
        EXPECT_EQ(inst.n_larvae, 10);
    }
}

TEST(MalAbmFastSeeding, RandomViableClampedToViableSetSize) {
    // n_detections > viable size -> capped at viable size.
    auto h = make_fake_habitat();
    mal_abm_fast::SeedingConfig cfg;
    cfg.mode = mal_abm_fast::SeedingMode::RANDOM_VIABLE;
    cfg.n_detections = 10000;  // way more than 100 patches
    mal_abm_fast::Prng rng(42);
    const auto out = mal_abm_fast::build_seed_instructions_for_patches(
        cfg, h.ids, h.lonlat, h.rowcol, rng);
    EXPECT_EQ(out.size(), 100u);
}

TEST(MalAbmFastSeeding, RandomViableIsDeterministic) {
    // Two calls with the same seed produce the same selection.
    auto h = make_fake_habitat();
    mal_abm_fast::SeedingConfig cfg;
    cfg.mode = mal_abm_fast::SeedingMode::RANDOM_VIABLE;
    cfg.n_detections = 10;
    mal_abm_fast::Prng rng1(123);
    mal_abm_fast::Prng rng2(123);
    const auto a = mal_abm_fast::build_seed_instructions_for_patches(
        cfg, h.ids, h.lonlat, h.rowcol, rng1);
    const auto b = mal_abm_fast::build_seed_instructions_for_patches(
        cfg, h.ids, h.lonlat, h.rowcol, rng2);
    ASSERT_EQ(a.size(), b.size());
    for (size_t i = 0; i < a.size(); ++i) {
        EXPECT_EQ(a[i].patch_id, b[i].patch_id);
    }
}

TEST(MalAbmFastSeeding, RandomViableSetsLonLatFromPatch) {
    auto h = make_fake_habitat();
    mal_abm_fast::SeedingConfig cfg;
    cfg.mode = mal_abm_fast::SeedingMode::RANDOM_VIABLE;
    cfg.n_detections = 1;
    mal_abm_fast::Prng rng(7);
    const auto out = mal_abm_fast::build_seed_instructions_for_patches(
        cfg, h.ids, h.lonlat, h.rowcol, rng);
    ASSERT_EQ(out.size(), 1u);
    // The instruction's (row, col) and (lon, lat) must match the
    // patch they refer to in the fake habitat.
    const int32_t pid = out[0].patch_id;
    EXPECT_EQ(out[0].row, h.rowcol[static_cast<size_t>(pid)][0]);
    EXPECT_EQ(out[0].col, h.rowcol[static_cast<size_t>(pid)][1]);
    EXPECT_DOUBLE_EQ(out[0].lon, h.lonlat[static_cast<size_t>(pid)][0]);
    EXPECT_DOUBLE_EQ(out[0].lat, h.lonlat[static_cast<size_t>(pid)][1]);
}

TEST(MalAbmFastSeeding, RandomViableEmptyViableListReturnsEmpty) {
    // Edge case: no viable patches.
    mal_abm_fast::SeedingConfig cfg;
    cfg.mode = mal_abm_fast::SeedingMode::RANDOM_VIABLE;
    cfg.n_detections = 5;
    mal_abm_fast::Prng rng(1);
    const auto out = mal_abm_fast::build_seed_instructions_for_patches(
        cfg, /*viable_patch_ids*/ {}, /*lonlat*/ {}, /*rowcol*/ {},
        rng);
    EXPECT_TRUE(out.empty());
}

// ---------------------------------------------------------------------------
// build_seed_instructions — EXPLICIT mode
// ---------------------------------------------------------------------------

TEST(MalAbmFastSeeding, ExplicitSinglePointSnapsToNearest) {
    auto h = make_fake_habitat();
    mal_abm_fast::SeedingConfig cfg;
    cfg.mode = mal_abm_fast::SeedingMode::EXPLICIT;
    cfg.detection_radius_km = 50.0;  // large radius so the snap always works
    // Point at (1.5, 2.5) — should snap to patch_id 21 (row=2, col=1).
    mal_abm_fast::DetectionPoint dp;
    dp.lat = 2.5;
    dp.lon = 1.5;
    dp.n_adults = 7;
    dp.n_larvae = 3;
    cfg.detections.push_back(dp);
    mal_abm_fast::Prng rng(1);
    const auto out = mal_abm_fast::build_seed_instructions_for_patches(
        cfg, h.ids, h.lonlat, h.rowcol, rng);
    ASSERT_EQ(out.size(), 1u);
    EXPECT_EQ(out[0].patch_id, 21);
    EXPECT_EQ(out[0].row, 2);
    EXPECT_EQ(out[0].col, 1);
    EXPECT_DOUBLE_EQ(out[0].lon, 1.5);
    EXPECT_DOUBLE_EQ(out[0].lat, 2.5);
    EXPECT_EQ(out[0].n_adults, 7);
    EXPECT_EQ(out[0].n_larvae, 3);
}

TEST(MalAbmFastSeeding, ExplicitPointOutsideRadiusDropsSilently) {
    auto h = make_fake_habitat();
    mal_abm_fast::SeedingConfig cfg;
    cfg.mode = mal_abm_fast::SeedingMode::EXPLICIT;
    cfg.detection_radius_km = 0.001;  // ~1 m — no patch close enough
    // Place the point mid-cell (0.55, 0.55) so the nearest patch
    // (at (0.5, 0.5)) is ~7.87 km away (sqrt(2) * 0.05 * 111.32 km).
    mal_abm_fast::DetectionPoint dp;
    dp.lat = 0.55;
    dp.lon = 0.55;
    cfg.detections.push_back(dp);
    mal_abm_fast::Prng rng(1);
    const auto out = mal_abm_fast::build_seed_instructions_for_patches(
        cfg, h.ids, h.lonlat, h.rowcol, rng);
    EXPECT_TRUE(out.empty());
}

TEST(MalAbmFastSeeding, ExplicitMultiplePointsSomeDropped) {
    auto h = make_fake_habitat();
    mal_abm_fast::SeedingConfig cfg;
    cfg.mode = mal_abm_fast::SeedingMode::EXPLICIT;
    cfg.detection_radius_km = 1.0;  // ~0.009 deg
    // In-grid points (snaps to nearest).
    mal_abm_fast::DetectionPoint p1; p1.lat = 0.5; p1.lon = 0.5;
    mal_abm_fast::DetectionPoint p2; p2.lat = 9.5; p2.lon = 9.5;
    // Out-of-grid point with 1.0 km radius: 0.5 deg from any patch
    // is ~55 km away — should be dropped.
    mal_abm_fast::DetectionPoint p3; p3.lat = 50.0; p3.lon = 50.0;
    cfg.detections.push_back(p1);
    cfg.detections.push_back(p2);
    cfg.detections.push_back(p3);
    mal_abm_fast::Prng rng(1);
    const auto out = mal_abm_fast::build_seed_instructions_for_patches(
        cfg, h.ids, h.lonlat, h.rowcol, rng);
    // p1 snaps to (0,0)=pid 0; p2 snaps to (9,9)=pid 99; p3 dropped.
    ASSERT_EQ(out.size(), 2u);
    EXPECT_EQ(out[0].patch_id, 0);
    EXPECT_EQ(out[1].patch_id, 99);
}

TEST(MalAbmFastSeeding, ExplicitNoDetectionPointsReturnsEmpty) {
    auto h = make_fake_habitat();
    mal_abm_fast::SeedingConfig cfg;
    cfg.mode = mal_abm_fast::SeedingMode::EXPLICIT;
    cfg.detections.clear();
    mal_abm_fast::Prng rng(1);
    const auto out = mal_abm_fast::build_seed_instructions_for_patches(
        cfg, h.ids, h.lonlat, h.rowcol, rng);
    EXPECT_TRUE(out.empty());
}

TEST(MalAbmFastSeeding, ExplicitFallsBackToConfigCounts) {
    // Per-point n_adults/n_larvae = 0 -> use config defaults.
    auto h = make_fake_habitat();
    mal_abm_fast::SeedingConfig cfg;
    cfg.mode = mal_abm_fast::SeedingMode::EXPLICIT;
    cfg.detection_radius_km = 50.0;
    cfg.n_adults_per_detection = 11;
    cfg.n_larvae_per_detection = 13;
    mal_abm_fast::DetectionPoint dp;
    dp.lat = 2.5;
    dp.lon = 1.5;
    dp.n_adults = 0;  // sentinel for "use config default"
    dp.n_larvae = 0;
    cfg.detections.push_back(dp);
    mal_abm_fast::Prng rng(1);
    const auto out = mal_abm_fast::build_seed_instructions_for_patches(
        cfg, h.ids, h.lonlat, h.rowcol, rng);
    ASSERT_EQ(out.size(), 1u);
    EXPECT_EQ(out[0].n_adults, 11);
    EXPECT_EQ(out[0].n_larvae, 13);
}

// ---------------------------------------------------------------------------
// MosquitoSubmodel detection-based constructor
// ---------------------------------------------------------------------------

TEST(MalAbmFastSeeding, SubmodelDetConstructorSeedsAdultsAndLarvae) {
    // 1 detection point: 10 adults + 5 larvae (→ eggs in cohort bank).
    std::vector<mal_abm_fast::SeedInstruction> instructions;
    mal_abm_fast::SeedInstruction inst;
    inst.patch_id = 7;
    inst.row = 1;
    inst.col = 2;
    inst.lon = 2.5;
    inst.lat = 1.5;
    inst.n_adults = 10;
    inst.n_larvae = 5;
    instructions.push_back(inst);

    mal_abm_fast::MosquitoSubmodel sub(/*n_patches*/ 100,
                                       /*k_per_patch*/ 1000,
                                       instructions, /*seed*/ 42);
    // G3: larvae are eggs in cohort bank, only adults in SoA.
    EXPECT_EQ(sub.total_agents(), 10);
    EXPECT_EQ(sub.cohort_bank().count_by_stage(mal_abm_fast::AquaticStage::EGG), 5);

    // Count adults.
    int32_t n_adults = 0;
    for (int64_t i = 0; i < sub.soa().n_alive; ++i) {
        const size_t si = static_cast<size_t>(i);
        if (sub.soa().stage[si] == 1) ++n_adults;
    }
    EXPECT_EQ(n_adults, 10);

    // All adults must be at the requested patch / cell.
    for (int64_t i = 0; i < sub.soa().n_alive; ++i) {
        const size_t si = static_cast<size_t>(i);
        EXPECT_EQ(sub.soa().patch_id[si], 7);
        EXPECT_EQ(sub.soa().row[si], 1);
        EXPECT_EQ(sub.soa().col[si], 2);
        EXPECT_FLOAT_EQ(sub.soa().lon[si], 2.5f);
        EXPECT_FLOAT_EQ(sub.soa().lat[si], 1.5f);
    }
}

TEST(MalAbmFastSeeding, SubmodelDetConstructorMultipleDetections) {
    // 3 detection points, each with 4 adults + 2 larvae (→ eggs).
    // G3: only adults in SoA = 12 total.
    std::vector<mal_abm_fast::SeedInstruction> instructions;
    for (int32_t i = 0; i < 3; ++i) {
        mal_abm_fast::SeedInstruction inst;
        inst.patch_id = i * 10;
        inst.row = i;
        inst.col = 0;
        inst.lon = 0.5;
        inst.lat = static_cast<double>(i) + 0.5;
        inst.n_adults = 4;
        inst.n_larvae = 2;
        instructions.push_back(inst);
    }
    mal_abm_fast::MosquitoSubmodel sub(100, 1000, instructions, 42);
    EXPECT_EQ(sub.total_agents(), 12);  // 3 * 4 adults only
    EXPECT_EQ(sub.cohort_bank().count_by_stage(mal_abm_fast::AquaticStage::EGG), 6);  // 3 * 2 eggs
}

TEST(MalAbmFastSeeding, SubmodelDetConstructorEmptyIsEmpty) {
    // Empty instructions -> zero agents.
    mal_abm_fast::MosquitoSubmodel sub(100, 1000,
                                       /*instructions*/ {}, /*seed*/ 42);
    EXPECT_EQ(sub.total_agents(), 0);
}

TEST(MalAbmFastSeeding, SubmodelLegacyConstructorStillWorks) {
    // Backward compat: the original 4-arg constructor must still
    // produce seeding. G3: 10% adults + 90% eggs in cohort bank.
    mal_abm_fast::MosquitoSubmodel sub(100, 1000, 0.3f, 42);
    EXPECT_EQ(sub.total_agents(), 3000);  // 10% of 30000
    EXPECT_EQ(sub.cohort_bank().count_by_stage(mal_abm_fast::AquaticStage::EGG), 27000);
}

// ---------------------------------------------------------------------------
// End-to-end: build instructions + construct submodel
// ---------------------------------------------------------------------------

TEST(MalAbmFastSeeding, EndToEndRandomViableBuildsSeededSubmodel) {
    auto h = make_fake_habitat();
    mal_abm_fast::SeedingConfig cfg;
    cfg.mode = mal_abm_fast::SeedingMode::RANDOM_VIABLE;
    cfg.n_detections = 4;
    cfg.n_adults_per_detection = 25;
    cfg.n_larvae_per_detection = 15;
    mal_abm_fast::Prng rng(99);
    const auto instructions = mal_abm_fast::build_seed_instructions_for_patches(
        cfg, h.ids, h.lonlat, h.rowcol, rng);
    ASSERT_EQ(instructions.size(), 4u);

    mal_abm_fast::MosquitoSubmodel sub(100, 1000, instructions, 7);
    // G3: 4 * 25 = 100 adults in SoA; 4 * 15 = 60 eggs in cohort bank.
    EXPECT_EQ(sub.total_agents(), 100);
    EXPECT_EQ(sub.cohort_bank().count_by_stage(mal_abm_fast::AquaticStage::EGG), 60);

    // Exactly 4 distinct patch_ids should have adults.
    std::set<int64_t> pids;
    for (int64_t i = 0; i < sub.soa().n_alive; ++i) {
        pids.insert(sub.soa().patch_id[static_cast<size_t>(i)]);
    }
    EXPECT_EQ(pids.size(), 4u);
}
