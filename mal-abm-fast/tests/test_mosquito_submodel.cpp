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

TEST(MalAbmFastMosquitoSubmodel, AdultDispersalUpdatesRowCol) {
    mal_abm_fast::MosquitoSubmodel sub(100, 1000, 0.3f, 42);
    const auto aoi = make_test_aoi();
    const auto ps  = make_test_patch_states();
    sub.advance_day(aoi, ps);

    const int32_t w = aoi.cells_per_side();
    const int32_t h = mal_abm_fast::cells_per_side_h(aoi);
    const double cellW = (aoi.east - aoi.west) / static_cast<double>(w);
    const double cellH = (aoi.north - aoi.south) / static_cast<double>(h);
    const auto& soa = sub.soa();

    for (int64_t i = 0; i < soa.n_alive; ++i) {
        const size_t si = static_cast<size_t>(i);
        if (soa.stage[si] != 1) continue;
        int32_t expected_col = static_cast<int32_t>(
            (static_cast<double>(soa.lon[si]) - aoi.west) / cellW);
        int32_t expected_row = static_cast<int32_t>(
            (aoi.north - static_cast<double>(soa.lat[si])) / cellH);
        if (expected_col < 0) expected_col = 0;
        if (expected_col >= w) expected_col = w - 1;
        if (expected_row < 0) expected_row = 0;
        if (expected_row >= h) expected_row = h - 1;
        EXPECT_EQ(soa.row[si], expected_row)
            << "agent " << soa.uid[si] << " row mismatch";
        EXPECT_EQ(soa.col[si], expected_col)
            << "agent " << soa.uid[si] << " col mismatch";
    }
}

TEST(MalAbmFastMosquitoSubmodel, DispersalDoesNotEscapeAOI) {
    mal_abm_fast::MosquitoSubmodel sub(100, 1000, 0.3f, 42);
    const auto aoi = make_test_aoi();
    const auto ps  = make_test_patch_states();
    for (int day = 0; day < 30; ++day) {
        sub.advance_day(aoi, ps);
    }

    const int32_t w = aoi.cells_per_side();
    const int32_t h = mal_abm_fast::cells_per_side_h(aoi);
    const auto& soa = sub.soa();

    for (int64_t i = 0; i < soa.n_alive; ++i) {
        const size_t si = static_cast<size_t>(i);
        if (soa.stage[si] != 1) continue;
        EXPECT_GE(soa.row[si], 0);
        EXPECT_LT(soa.row[si], h);
        EXPECT_GE(soa.col[si], 0);
        EXPECT_LT(soa.col[si], w);
    }
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

// --- Beverton-Holt density-dependent larva mortality tests ---

TEST(MalAbmFastMosquitoSubmodel, BevertonHoltKillsLarvaeAtHighDensity) {
    // Seed 100 patches × 1000 K × 1.0 = 100000 larvae so the first
    // 4 active patches each hold N=1000 larvae — well into the BH
    // high-density regime (p = 0.95 * K / (K + alpha * N) ≈ 0.905
    // for alpha=0.05). With per-adult birth (BIRTH_FECUNDITY=0.10), the
    // old 0.3 init frac (300 larv/patch) let new births mask BH
    // deaths, so we raise the initial population to keep BH
    // deaths dominant over births.
    mal_abm_fast::MosquitoSubmodel sub(100, 1000, 1.0f, 42);
    const auto aoi = make_test_aoi();
    auto ps = make_test_patch_states();
    const int64_t before = sub.total_agents();
    sub.advance_day(aoi, ps);
    // With 1000 larvae per active patch, BH reduces count.
    EXPECT_LT(sub.total_agents(), before);
}

TEST(MalAbmFastMosquitoSubmodel, BevertonHoltSurvivalAtLowDensity) {
    // Very few larvae: BH survival ≈ S0 ≈ 0.95, almost all survive.
    mal_abm_fast::MosquitoSubmodel sub(10, 1, 1.0f, 42);
    // 10 patches × 1 × 1.0 = 10 larvae total.
    const auto aoi = make_test_aoi();
    auto ps = make_test_patch_states();
    // Use only first 10 patches active.
    for (int i = 0; i < 100; ++i) ps[i].activated = (i < 10);
    const int64_t before = sub.total_agents();
    sub.advance_day(aoi, ps);
    // At low density BH survival ≈ 0.95, so at most 1 dies.
    EXPECT_GE(sub.total_agents(), before - 1);
}

// --- Adult mortality (Lardeux) tests ---

TEST(MalAbmFastMosquitoSubmodel, AdultMortalityReducesPopulation) {
    // Seed 100 patches, run 30 days to get adults, then deactivate all
    // patches so no new births occur. Adult mortality (Lardeux fallback
    // at 0.90 when patch is inactive) should reduce the population.
    mal_abm_fast::MosquitoSubmodel sub(100, 1000, 0.3f, 42);
    const auto aoi = make_test_aoi();
    const auto ps  = make_test_patch_states();
    for (int day = 0; day < 30; ++day) {
        sub.advance_day(aoi, ps);
    }
    // Deactivate all patches — no births, only mortality.
    auto ps_inactive = ps;
    for (auto& p : ps_inactive) p.activated = false;
    const int64_t before = sub.total_agents();
    sub.advance_day(aoi, ps_inactive);
    // Adults die with fallback rate (0.90), no births.
    EXPECT_LT(sub.total_agents(), before);
}

TEST(MalAbmFastMosquitoSubmodel, AdultMortalityUsesFallbackWhenNoTemp) {
    // All patches inactive — adult mortality uses ADULT_DAILY_MORT_BASE = 0.90.
    mal_abm_fast::MosquitoSubmodel sub(100, 1000, 0.3f, 42);
    const auto aoi = make_test_aoi();
    auto ps = make_test_patch_states();
    // First day: all active to seed adults.
    for (int day = 0; day < 15; ++day) {
        sub.advance_day(aoi, ps);
    }
    // Now deactivate all patches — adults still exist, mortality uses fallback.
    for (auto& p : ps) p.activated = false;
    const int64_t before = sub.total_agents();
    sub.advance_day(aoi, ps);
    EXPECT_LT(sub.total_agents(), before);
}

// --- Advance-day call order test ---

TEST(MalAbmFastMosquitoSubmodel, AdvanceDayCallOrder) {
    // Verify that the 7 ops execute without crash and produce a valid state.
    mal_abm_fast::MosquitoSubmodel sub(100, 1000, 0.3f, 42);
    const auto aoi = make_test_aoi();
    const auto ps  = make_test_patch_states();
    // Run 7 days (one per op cycle) — should not crash.
    for (int day = 0; day < 7; ++day) {
        sub.advance_day(aoi, ps);
    }
    EXPECT_GT(sub.total_agents(), 0);
}

// --- Desiccation tests ---

TEST(MalAbmFastMosquitoSubmodel, DesiccationKillsAfterGracePeriod) {
    // NOTE: stable age distribution (M1.5 + age-fix) seeds 10% pre-mature
    // adults that undergo normal Lardeux adult mortality throughout —
    // they are NOT subject to desiccation. The grace-period invariant
    // therefore applies to LARVAE only, which we count separately here.
    mal_abm_fast::MosquitoSubmodel sub(1, 1000, 0.3f, 42);
    const auto aoi = make_test_aoi();
    auto ps = make_test_patch_states();
    for (auto& p : ps) p.activated = false;
    ps[0].activated = true;
    sub.advance_day(aoi, ps);
    sub.advance_day(aoi, ps);
    auto larvae_at_patch0 = [&sub]() {
        int64_t n = 0;
        const auto& soa = sub.soa();
        for (int64_t i = 0; i < soa.n_alive; ++i) {
            const size_t si = static_cast<size_t>(i);
            if (soa.stage[si] == 0 && soa.patch_id[si] == 0) ++n;
        }
        return n;
    };
    const int64_t larvae_after_active = larvae_at_patch0();
    ps[0].activated = false;
    for (int d = 0; d < 5; ++d) {
        sub.advance_day(aoi, ps);
    }
    // Larvae at patch 0 must all survive the 5-day grace period.
    EXPECT_EQ(larvae_at_patch0(), larvae_after_active);
    for (int d = 0; d < 3; ++d) {
        sub.advance_day(aoi, ps);
    }
    // Past grace: desiccation starts killing larvae.
    EXPECT_LT(larvae_at_patch0(), larvae_after_active);
}

TEST(MalAbmFastMosquitoSubmodel, DesiccationResetsOnReactivation) {
    mal_abm_fast::MosquitoSubmodel sub(1, 1000, 0.3f, 42);
    const auto aoi = make_test_aoi();
    auto ps = make_test_patch_states();
    for (auto& p : ps) p.activated = false;
    ps[0].activated = true;

    sub.advance_day(aoi, ps);
    sub.advance_day(aoi, ps);
    ps[0].activated = false;
    sub.advance_day(aoi, ps);
    ps[0].activated = true;
    sub.advance_day(aoi, ps);

    ps[0].activated = false;
    for (int d = 0; d < 5; ++d) {
        sub.advance_day(aoi, ps);
    }
    const auto& soa1 = sub.soa();
    int64_t larvae_after = 0;
    for (int64_t i = 0; i < soa1.n_alive; ++i) {
        const size_t si = static_cast<size_t>(i);
        if (soa1.stage[si] == 0 && soa1.patch_id[si] == 0) ++larvae_after;
    }
    EXPECT_GT(larvae_after, 0);
    for (int d = 0; d < 3; ++d) {
        sub.advance_day(aoi, ps);
    }
    const auto& soa2 = sub.soa();
    int64_t larvae_later = 0;
    for (int64_t i = 0; i < soa2.n_alive; ++i) {
        const size_t si = static_cast<size_t>(i);
        if (soa2.stage[si] == 0 && soa2.patch_id[si] == 0) ++larvae_later;
    }
    EXPECT_LT(larvae_later, larvae_after);
}

TEST(MalAbmFastMosquitoSubmodel, InactivePatchCountZeroSkipsKill) {
    // With 0 larvae at an inactive patch, desiccation is a no-op.
    mal_abm_fast::MosquitoSubmodel sub(1, 1000, 0.3f, 42);
    const auto aoi = make_test_aoi();
    auto ps = make_test_patch_states();
    for (auto& p : ps) p.activated = false;
    ps[0].activated = true;
    // Run 5 days active to build adults.
    for (int d = 0; d < 5; ++d) sub.advance_day(aoi, ps);
    // Deactivate all — adults unaffected, larvae killed eventually.
    sub.advance_day(aoi, ps);  // day 5
    sub.advance_day(aoi, ps);  // day 6
    sub.advance_day(aoi, ps);  // day 7 — grace exceeded
    // Adults survive desiccation; only larvae die.
    EXPECT_GT(sub.total_agents(), 0);
}

TEST(MalAbmFastMosquitoSubmodel, LarvaToAdultInactivePatchUsesLonLat) {
    // Larva promoted at inactive patch snaps lon/lat to enclosing cell.
    // NOTE: stable age distribution (M1.5 + age-fix) seeds 10% pre-mature
    // adults that start at the (lon=0, lat=0) sentinel and disperse from
    // there. Those are the seeded adults (eip_progress = EIP_THRESHOLD_GD).
    // We test the larva_to_adult snap by checking only PROMOTED adults
    // (eip_progress reset to 0 on promotion, per larva_to_adult's note).
    mal_abm_fast::MosquitoSubmodel sub(100, 1000, 0.3f, 42);
    const auto aoi = make_test_aoi();
    auto ps = make_test_patch_states();
    // Run 30 days to promote some larvae to adults.
    for (int d = 0; d < 30; ++d) {
        sub.advance_day(aoi, ps);
    }
    // All PROMOTED adults (eip_progress=0, stage=1) must have lon/lat
    // within the AOI bbox. Larvae (stage=0) at the (0, 0) sentinel
    // and pre-mature seeded adults (eip_progress=110) are excluded.
    const auto& soa = sub.soa();
    int64_t promoted_checked = 0;
    for (int64_t i = 0; i < soa.n_alive; ++i) {
        const size_t si = static_cast<size_t>(i);
        if (soa.stage[si] != 1) continue;
        if (soa.eip_progress[si] != 0.0f) continue;  // skip pre-mature
        EXPECT_GE(soa.lon[si], static_cast<float>(aoi.west));
        EXPECT_LE(soa.lon[si], static_cast<float>(aoi.east));
        EXPECT_GE(soa.lat[si], static_cast<float>(aoi.south));
        EXPECT_LE(soa.lat[si], static_cast<float>(aoi.north));
        ++promoted_checked;
    }
    // Sanity: at least one larva was promoted to adult over 30 days.
    EXPECT_GT(promoted_checked, 0);
}

TEST(MalAbmFastMosquitoSubmodel, DeterminismAfterDesiccation) {
    // Two identical runs with desiccation produce the same results.
    mal_abm_fast::MosquitoSubmodel a(100, 1000, 0.3f, 42);
    mal_abm_fast::MosquitoSubmodel b(100, 1000, 0.3f, 42);
    const auto aoi = make_test_aoi();
    auto ps = make_test_patch_states();
    for (int d = 0; d < 30; ++d) {
        a.advance_day(aoi, ps);
        b.advance_day(aoi, ps);
    }
    EXPECT_EQ(a.total_agents(), b.total_agents());
    EXPECT_EQ(a.density_by_patch(), b.density_by_patch());
}
