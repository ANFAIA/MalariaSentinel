// SPDX-License-Identifier: MIT
// test_config_engine_golden.cpp — plan test 7 (constants-yaml §6/§8) as a
// CLI-driven golden run: spawn the built engine with the frozen CLI
// invocation (the one used to produce the committed pre-migration
// fixtures at commit 85d5537, seed 42) and compare the state.tif +
// sidecars byte-for-byte with the golden directory.
//
// The YAML carries exactly the pre-migration inline values as
// double→float-cast literals, so the migrated engine must stay
// byte-identical. Skipped when the accra data/fixtures are absent.
#include <gtest/gtest.h>

#include <cstdio>
#include <filesystem>
#include <fstream>
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
    if (!fixtures) {
        GTEST_SKIP() << "accra fixtures / golden dir not available";
    }
    const fs::path bin = engine_binary();
    if (bin.empty() || !fs::exists(bin)) {
        GTEST_SKIP() << "engine binary not linked into the test";
    }

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
