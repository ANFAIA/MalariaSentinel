// SPDX-License-Identifier: MIT
// test_config_engine_golden.cpp — plan test 7 (constants-yaml §6/§8) as a
// CLI-driven golden run: spawn the built engine with the frozen CLI
// invocation (the one used to produce the committed pre-migration
// fixtures at commit 85d5537, seed 42) and compare the state.tif +
// sidecars byte-for-byte with the golden directory.
//
// The YAML carries exactly the pre-migration inline values as
// double→float-cast literals, so the migrated engine must stay
// byte-identical.
//
// Policy (task-01 B6): missing fixtures or a missing engine binary are
// FAILURES, never silent skips — the previous GTEST_SKIP could leave
// transmission/gonotrophic/thermal paths uncovered while CI stayed green.
// Restore the accra-coastal-test artifacts (re-downloadable; ignored by
// .gitignore) before running ctest.
//
// Second scenario (task-01 B6, unblocked by task-05 BUG-3): the same AOI
// with --enable-transmission + host_static population, 90 days, enough
// adults to complete the full S_V→E_V→I_V→bite→E_H chain. Its daily log
// is frozen byte-for-byte; the assertions below also prove the fixture
// really contains transmission (not an all-zero degenerate run).
#include <gtest/gtest.h>

#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <optional>
#include <string>
#include <vector>

namespace fs = std::filesystem;

namespace {

constexpr int kSeed = 42;
constexpr int kDays = 5;

struct Fixtures {
    fs::path repo_root;
    fs::path golden_dir;
};

std::optional<Fixtures> find_fixtures() {
    fs::path dir = fs::current_path();
    for (int i = 0; i < 8; ++i) {
        const fs::path env =
            dir / "data" / "accra-coastal-test" /
            "accra-coastal-test_regional_2024_2024_env.nc";
        const fs::path habitat =
            dir / "data" / "accra-coastal-test" /
            "accra-coastal-test_habitat_patches.gpkg";
        const fs::path golden =
            dir / "mal-core" / "src" / "mal_core" / "abm" / "tests" / "golden";
        if (fs::exists(env) && fs::exists(habitat) &&
            fs::exists(golden / "state_seed42_day5.tif")) {
            return Fixtures{dir, golden};
        }
        if (!dir.has_parent_path()) break;
        dir = dir.parent_path();
    }
    return std::nullopt;
}

fs::path engine_binary() {
#ifdef MAL_ABM_FAST_ENGINE_BIN
    return fs::path(MAL_ABM_FAST_ENGINE_BIN);
#else
    return {};
#endif
}

// Largest numeric value of `"key": <number>` in a JSON text file (-1 if
// the key never appears). Used to prove the frozen transmission log
// actually carries the SEIR-SEI chain.
double max_field_value(const fs::path& json_path, const std::string& key) {
    std::ifstream in(json_path);
    if (!in.good()) return -1.0;
    const std::string text((std::istreambuf_iterator<char>(in)),
                           std::istreambuf_iterator<char>());
    const std::string needle = "\"" + key + "\":";
    double best = -1.0;
    for (size_t pos = text.find(needle);
         pos != std::string::npos;
         pos = text.find(needle, pos + needle.size())) {
        const char* start = text.c_str() + pos + needle.size();
        char* end = nullptr;
        const double value = std::strtod(start, &end);
        if (end != start && value > best) best = value;
    }
    return best;
}

void expect_files_equal(const fs::path& produced, const fs::path& golden) {
    ASSERT_TRUE(fs::exists(produced))
        << "produced file missing: " << produced;
    ASSERT_TRUE(fs::exists(golden)) << "golden missing: " << golden;
    std::ifstream a(produced, std::ios::binary);
    std::ifstream b(golden, std::ios::binary);
    ASSERT_TRUE(a.good() && b.good());
    for (long long offset = 0;; ++offset) {
        const int ca = a.get();
        const int cb = b.get();
        EXPECT_EQ(ca, cb) << "byte " << offset
                          << " of " << produced.filename().string()
                          << " differs from golden";
        if (ca < 0 || cb < 0) break;
    }
}

}  // namespace

TEST(ConfigEngineGolden, AccraSeed42FiveDaysBitIdentical) {
    auto fixtures = find_fixtures();
    ASSERT_TRUE(fixtures.has_value())
        << "golden fixtures missing: data/accra-coastal-test/*_env.nc + "
           "*_habitat_patches.gpkg + tests/golden/state_seed42_day5.tif "
           "must exist under a parent of " << fs::current_path()
        << " (restore the accra-coastal-test artifacts; task-01 B6 makes "
           "this a failure, not a skip)";
    const fs::path bin = engine_binary();
    ASSERT_FALSE(bin.empty()) << "MAL_ABM_FAST_ENGINE_BIN not defined";
    ASSERT_TRUE(fs::exists(bin)) << "engine binary not linked: " << bin;

    const fs::path out_dir = fs::temp_directory_path() /
                             ("mal_abm_golden_" + std::to_string(::getpid()));
    fs::create_directories(out_dir);
    const std::string out_tif = (out_dir / "state.tif").string();

    std::string cmd = bin.string() +
        " run --bbox 0.05,5.35,0.60,5.75 --crs EPSG:4326"
        " --resolution-m 1000 --year 2024 --month 1"
        " --seed " + std::to_string(kSeed) +
        " --days " + std::to_string(kDays) +
        " --env " + (fixtures->repo_root / "data" / "accra-coastal-test" /
                     "accra-coastal-test_regional_2024_2024_env.nc").string() +
        " --habitat " + (fixtures->repo_root / "data" / "accra-coastal-test" /
                         "accra-coastal-test_habitat_patches.gpkg").string() +
        " --output " + out_tif;
    const int rc = std::system(cmd.c_str());
    ASSERT_EQ(rc, 0) << "engine run failed: " << cmd;

    // Byte-vs-byte against the golden (state.tif + both sidecars).
    expect_files_equal(out_tif,
                       fixtures->golden_dir / "state_seed42_day5.tif");
    expect_files_equal(out_dir / "state.json",
                       fixtures->golden_dir / "state_seed42_day5.json");
    expect_files_equal(out_dir / "state_aquatic.json",
                       fixtures->golden_dir / "state_seed42_day5_aquatic.json");
}

// task-01 B6: transmission scenario. Task-05 BUG-3 fix (bfd672c) made the
// chain stable; the fixture was regenerated after it. The scenario needs
// the host_static raster (concentrated human population) — without it the
// settlement has no cell with pop >= 50 and random-viable seeding never
// fires.
TEST(ConfigEngineGolden, AccraSeed42TransmissionChainBitIdentical) {
    auto fixtures = find_fixtures();
    ASSERT_TRUE(fixtures.has_value())
        << "golden fixtures missing: data/accra-coastal-test/* must exist "
           "under a parent of " << fs::current_path()
        << " (restore the accra-coastal-test artifacts; task-01 B6 makes "
           "this a failure, not a skip)";
    const fs::path bin = engine_binary();
    ASSERT_FALSE(bin.empty()) << "MAL_ABM_FAST_ENGINE_BIN not defined";
    ASSERT_TRUE(fs::exists(bin)) << "engine binary not linked: " << bin;

    const fs::path data_dir =
        fixtures->repo_root / "data" / "accra-coastal-test";
    const fs::path out_dir = fs::temp_directory_path() /
        ("mal_abm_golden_tx_" + std::to_string(::getpid()));
    fs::create_directories(out_dir);
    const std::string out_tif = (out_dir / "state.tif").string();
    const std::string tx_log = (out_dir / "transmission_log.json").string();

    std::string cmd = bin.string() +
        " run --bbox 0.05,5.35,0.60,5.75 --crs EPSG:4326"
        " --resolution-m 1000 --year 2024 --month 1"
        " --seed " + std::to_string(kSeed) +
        " --days 90 --n-adults-per-detection 1000"
        " --enable-transmission"
        " --env " +
        (data_dir / "accra-coastal-test_regional_2024_2024_env.nc").string() +
        " --habitat " +
        (data_dir / "accra-coastal-test_habitat_patches.gpkg").string() +
        " --hosts " +
        (data_dir / "accra-coastal-test_host_static.nc").string() +
        " --output " + out_tif +
        " --emit-transmission-log " + tx_log;
    const int rc = std::system(cmd.c_str());
    ASSERT_EQ(rc, 0) << "engine transmission run failed: " << cmd;

    expect_files_equal(
        tx_log, fixtures->golden_dir / "transmission_seed42_day90.json");

    // Guard against a degenerate all-zero fixture: the frozen log must
    // carry the full chain (human→vector→EIP→bites→human).
    EXPECT_GT(max_field_value(tx_log, "E_V"), 0.0);
    EXPECT_GT(max_field_value(tx_log, "I_V"), 0.0);
    EXPECT_GT(max_field_value(tx_log, "infectious_bites"), 0.0);
    EXPECT_GT(max_field_value(tx_log, "E_H"), 0.0);
}
