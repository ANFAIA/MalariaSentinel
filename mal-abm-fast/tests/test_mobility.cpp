// SPDX-License-Identifier: MIT
// test_mobility.cpp — GoogleTest for SparseOD and MobilitySchedule.
#include <gtest/gtest.h>

#include <cmath>
#include <cstring>
#include <fstream>
#include <string>
#include <vector>

#include "mobility_schedule.hpp"

namespace {

// Build a 3x3 identity CSR file in tmp.
std::string write_identity_csr(const std::string& path, int32_t n) {
    std::ofstream f(path, std::ios::binary);
    f.write(reinterpret_cast<const char*>(&n), 4);
    f.write(reinterpret_cast<const char*>(&n), 4);
    const int32_t nnz = n;
    f.write(reinterpret_cast<const char*>(&nnz), 4);
    for (int32_t i = 0; i <= n; ++i) {
        int32_t v = i;
        f.write(reinterpret_cast<const char*>(&v), 4);
    }
    for (int32_t i = 0; i < n; ++i) {
        f.write(reinterpret_cast<const char*>(&i), 4);
    }
    for (int32_t i = 0; i < n; ++i) {
        float v = 1.0f;
        f.write(reinterpret_cast<const char*>(&v), 4);
    }
    f.close();
    return path;
}

// Build a simple 2x2 OD: row 0 -> {0:0.6, 1:0.4}, row 1 -> {0:0.3, 1:0.7}
std::string write_simple_csr(const std::string& path) {
    const int32_t nr = 2, nc = 2, nnz = 4;
    std::vector<int32_t> rp = {0, 2, 4};
    std::vector<int32_t> ci = {0, 1, 0, 1};
    std::vector<float>   vl = {0.6f, 0.4f, 0.3f, 0.7f};

    std::ofstream f(path, std::ios::binary);
    f.write(reinterpret_cast<const char*>(&nr), 4);
    f.write(reinterpret_cast<const char*>(&nc), 4);
    f.write(reinterpret_cast<const char*>(&nnz), 4);
    f.write(reinterpret_cast<const char*>(rp.data()), 4 * (nr + 1));
    f.write(reinterpret_cast<const char*>(ci.data()), 4 * nnz);
    f.write(reinterpret_cast<const char*>(vl.data()), 4 * nnz);
    f.close();
    return path;
}

}  // namespace

// ---------------------------------------------------------------------------
// SparseOD tests
// ---------------------------------------------------------------------------

TEST(SparseOD, DefaultConstructIsEmpty) {
    mal_abm_fast::SparseOD od;
    EXPECT_EQ(od.n_rows, 0);
    EXPECT_EQ(od.n_cols, 0);
    EXPECT_EQ(od.nnz(), 0);
}

TEST(SparseOD, IdentityMatrix) {
    auto od = mal_abm_fast::SparseOD::identity(4);
    EXPECT_EQ(od.n_rows, 4);
    EXPECT_EQ(od.n_cols, 4);
    EXPECT_EQ(od.nnz(), 4);
    for (int32_t i = 0; i < 4; ++i) {
        auto dests = od.destinations(i);
        ASSERT_EQ(dests.size(), 1u);
        EXPECT_EQ(dests[0].first, i);
        EXPECT_FLOAT_EQ(dests[0].second, 1.0f);
    }
}

TEST(SparseOD, DestinationsForValidRow) {
    auto od = mal_abm_fast::SparseOD::identity(3);
    auto dests = od.destinations(1);
    ASSERT_EQ(dests.size(), 1u);
    EXPECT_EQ(dests[0].first, 1);
}

TEST(SparseOD, DestinationsForOutOfBoundsRow) {
    auto od = mal_abm_fast::SparseOD::identity(3);
    auto dests = od.destinations(5);
    EXPECT_TRUE(dests.empty());
}

TEST(SparseOD, LoadFromCsrRoundTrip) {
    const std::string path = "/tmp/mal_test_od_roundtrip.csr";
    write_simple_csr(path);
    auto od = mal_abm_fast::SparseOD::load_from_csr(path);
    EXPECT_EQ(od.n_rows, 2);
    EXPECT_EQ(od.n_cols, 2);
    EXPECT_EQ(od.nnz(), 4);

    auto d0 = od.destinations(0);
    ASSERT_EQ(d0.size(), 2u);
    EXPECT_FLOAT_EQ(d0[0].second, 0.6f);
    EXPECT_FLOAT_EQ(d0[1].second, 0.4f);

    auto d1 = od.destinations(1);
    ASSERT_EQ(d1.size(), 2u);
    EXPECT_FLOAT_EQ(d1[0].second, 0.3f);
    EXPECT_FLOAT_EQ(d1[1].second, 0.7f);
}

TEST(SparseOD, ValidateRejectsBadRowSum) {
    // Row 0 sums to 1.5 (bad)
    std::vector<int32_t> rp = {0, 2, 4};
    std::vector<int32_t> ci = {0, 1, 0, 1};
    std::vector<float>   vl = {0.8f, 0.7f, 0.3f, 0.7f};  // row 0 sums to 1.5
    EXPECT_THROW(
        mal_abm_fast::SparseOD(rp, ci, vl, 2, 2),
        std::runtime_error);
}

// ---------------------------------------------------------------------------
// MobilitySchedule tests
// ---------------------------------------------------------------------------

TEST(MobilitySchedule, DefaultHasNoData) {
    mal_abm_fast::MobilitySchedule ms;
    EXPECT_FALSE(ms.has_data());
    EXPECT_EQ(ms.n_matrices(), 0);
    EXPECT_EQ(ms.n_cells(), 0);
}

TEST(MobilitySchedule, LoadIdentityOD) {
    mal_abm_fast::MobilitySchedule ms;
    auto id = mal_abm_fast::SparseOD::identity(5);
    ms.set_human_od(id, mal_abm_fast::SparseOD::identity(5));
    EXPECT_TRUE(ms.has_data());
    EXPECT_TRUE(ms.has_human());
    EXPECT_FALSE(ms.has_livestock());
    EXPECT_EQ(ms.n_matrices(), 2);
    EXPECT_EQ(ms.n_cells(), 5);
}

TEST(MobilitySchedule, NightPhaseReturnsIdentity) {
    mal_abm_fast::MobilitySchedule ms;
    auto day_od = mal_abm_fast::SparseOD::identity(3);
    auto night_od = mal_abm_fast::SparseOD::identity(3);
    ms.set_human_od(day_od, night_od);

    auto pres = ms.get_presence(1, mal_abm_fast::TimePhase::NIGHT);
    ASSERT_EQ(pres.size(), 1u);
    EXPECT_EQ(pres[0].first, 1);
    EXPECT_FLOAT_EQ(pres[0].second, 1.0f);
}

TEST(MobilitySchedule, EffectiveHostsAtIdentity) {
    mal_abm_fast::MobilitySchedule ms;
    auto id = mal_abm_fast::SparseOD::identity(3);
    ms.set_human_od(id, mal_abm_fast::SparseOD::identity(3));

    std::vector<float> pop = {100.0f, 200.0f, 50.0f};
    float eff = ms.effective_hosts_at(1, mal_abm_fast::TimePhase::NIGHT, pop);
    EXPECT_FLOAT_EQ(eff, 200.0f);
}

TEST(MobilitySchedule, EffectiveHostsAtRedistributes) {
    mal_abm_fast::MobilitySchedule ms;
    // Simple 2x2: row 0 -> {0:0.6, 1:0.4}, row 1 -> {0:0.3, 1:0.7}
    std::vector<int32_t> rp = {0, 2, 4};
    std::vector<int32_t> ci = {0, 1, 0, 1};
    std::vector<float>   vl = {0.6f, 0.4f, 0.3f, 0.7f};
    mal_abm_fast::SparseOD day(rp, ci, vl, 2, 2);
    ms.set_human_od(day, mal_abm_fast::SparseOD::identity(2));

    std::vector<float> pop = {1000.0f, 500.0f};
    // Cell 0 at DAY: 0.6*1000 + 0.3*500 = 600 + 150 = 750
    float eff = ms.effective_hosts_at(0, mal_abm_fast::TimePhase::DAY, pop);
    EXPECT_NEAR(eff, 750.0f, 0.1f);
}

TEST(MobilitySchedule, LivestockPhaseReturnsSameMatrix) {
    mal_abm_fast::MobilitySchedule ms;
    auto live = mal_abm_fast::SparseOD::identity(4);
    ms.set_livestock_od(live);

    auto pres_day = ms.get_presence(2, mal_abm_fast::TimePhase::DAY, true);
    auto pres_night = ms.get_presence(2, mal_abm_fast::TimePhase::NIGHT, true);
    // Night uses identity, day uses the same seasonal matrix (also identity)
    ASSERT_EQ(pres_day.size(), 1u);
    ASSERT_EQ(pres_night.size(), 1u);
    EXPECT_EQ(pres_day[0].first, 2);
    EXPECT_EQ(pres_night[0].first, 2);
}

TEST(MobilitySchedule, LoadFromDirectorySkipsMissing) {
    mal_abm_fast::MobilitySchedule ms;
    mal_abm_fast::AOI aoi;
    // Non-existent directory — should be a no-op
    ms.load_from_directory("/tmp/nonexistent_dir_12345", aoi);
    EXPECT_FALSE(ms.has_data());
}

TEST(MobilitySchedule, LoadFromDirectoryLoadsCSR) {
    const std::string dir = "/tmp/mal_test_mobility_dir";
    std::filesystem::create_directories(dir);
    write_identity_csr(dir + "/human_mobility_day.csr", 3);
    write_identity_csr(dir + "/human_mobility_night.csr", 3);

    mal_abm_fast::MobilitySchedule ms;
    mal_abm_fast::AOI aoi;
    ms.load_from_directory(dir, aoi);
    EXPECT_TRUE(ms.has_human());
    EXPECT_EQ(ms.n_cells(), 3);

    std::filesystem::remove_all(dir);
}
