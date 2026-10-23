// SPDX-License-Identifier: MIT
// test_climate_single_band.cpp — regression tests for the single-band
// (`--days 1`) climate path.
//
// Bug (round 4, D12): `ClimateEngine::set_day` early-returned whenever
// `n_days_ <= 1`, and `clone_for_thread` started its thread-local
// accessors at 0.0 rain / 25.0 C. A one-day run therefore simulated a
// fabricated climate day (25 C) instead of NC band 0 (5.5 C for
// accra 2024-01-01), which changed the aquatic cohort counts. These
// tests pin the two halves of the fix:
//   1. the clone carries the base band instead of the placeholders;
//   2. set_day(0) on a single-band engine still copies band 0.
// It also pins the multi-band semantics (base_day / warm-up offset) that
// must not regress.
//
// The synthetic NetCDF writer mirrors tests/test_climate.cpp: two bands
// with clearly distinguishable values so 0.0 / 25.0 defaults can never
// be mistaken for a real band.

#include <gtest/gtest.h>

#include <algorithm>
#include <cstdlib>
#include <filesystem>
#include <string>
#include <vector>

#include <netcdf.h>

#include "climate.hpp"
#include "wire.hpp"

namespace {

namespace fs = std::filesystem;

constexpr int kH = 4;
constexpr int kW = 4;

// Band 0: the "accra 2024-01-01" style values the bug hid.
constexpr float kBand0Rain = 12.5f;
constexpr float kBand0Temp = 5.5f;
// Band 1: deliberately different from band 0 and from the old defaults.
constexpr float kBand1Rain = 0.0f;
constexpr float kBand1Temp = 30.0f;

fs::path MakeTmpEnvNC() {
    const char* base = std::getenv("TMPDIR");
    fs::path dir = (base && *base) ? fs::path(base) : fs::temp_directory_path();
    return dir / ("mal_abm_fast_test_climate_single_band_" +
                  std::to_string(static_cast<long>(::getpid())) + ".nc");
}

void WriteTwoBandEnvNC(const fs::path& path) {
    int ncid = -1, dimid_time = -1, dimid_y = -1, dimid_x = -1;
    int vid_rain = -1, vid_temp = -1;

    ASSERT_EQ(nc_create(path.string().c_str(), NC_CLOBBER | NC_NETCDF4,
                        &ncid), NC_NOERR);
    ASSERT_EQ(nc_def_dim(ncid, "time", NC_UNLIMITED, &dimid_time), NC_NOERR);
    ASSERT_EQ(nc_def_dim(ncid, "y", kH, &dimid_y), NC_NOERR);
    ASSERT_EQ(nc_def_dim(ncid, "x", kW, &dimid_x), NC_NOERR);
    const int dimids[3] = {dimid_time, dimid_y, dimid_x};
    ASSERT_EQ(nc_def_var(ncid, "rainfall", NC_FLOAT, 3, dimids, &vid_rain),
              NC_NOERR);
    ASSERT_EQ(nc_def_var(ncid, "air_temp_c", NC_FLOAT, 3, dimids, &vid_temp),
              NC_NOERR);
    ASSERT_EQ(nc_put_att_text(ncid, NC_GLOBAL, "Conventions", 6, "CF-1.8"),
              NC_NOERR);
    ASSERT_EQ(nc_enddef(ncid), NC_NOERR);

    const float values[2][2] = {{kBand0Rain, kBand0Temp},
                                {kBand1Rain, kBand1Temp}};
    float buf[kH * kW];
    for (int d = 0; d < 2; ++d) {
        size_t start[3] = {static_cast<size_t>(d), 0, 0};
        size_t count[3] = {1, static_cast<size_t>(kH),
                           static_cast<size_t>(kW)};
        std::fill(buf, buf + kH * kW, values[d][0]);
        ASSERT_EQ(nc_put_vara_float(ncid, vid_rain, start, count, buf),
                  NC_NOERR);
        std::fill(buf, buf + kH * kW, values[d][1]);
        ASSERT_EQ(nc_put_vara_float(ncid, vid_temp, start, count, buf),
                  NC_NOERR);
    }
    ASSERT_EQ(nc_close(ncid), NC_NOERR);
}

mal_abm_fast::AOI MakeAoi() {
    mal_abm_fast::AOI a;
    a.west = -3.5; a.south = 4.5; a.east = 1.5; a.north = 11.5;
    a.crs = "EPSG:4326"; a.slug = "test"; a.resolution_m = 1000;
    a.scale = "regional";
    return a;
}

}  // namespace

// `--days 1`: the shared climate is loaded with max_days = 1, so it holds a
// single band. The thread clone must carry that band, not 0.0 / 25.0.
TEST(ClimateEngineSingleBand, CloneForThreadKeepsBaseBand) {
    const fs::path path = MakeTmpEnvNC();
    if (fs::exists(path)) fs::remove(path);
    WriteTwoBandEnvNC(path);

    mal_abm_fast::ClimateEngine eng;
    eng.load_from_env_nc(path.string(), MakeAoi(), /*max_days=*/1);
    ASSERT_EQ(eng.n_days(), 1);

    auto clone = eng.clone_for_thread();
    ASSERT_NE(clone, nullptr);
    EXPECT_EQ(clone->n_days(), 1);
    // Every cell, not just (0, 0): the placeholder fill was uniform.
    for (int r = 0; r < kH; ++r) {
        for (int c = 0; c < kW; ++c) {
            EXPECT_FLOAT_EQ(clone->rain_at(r, c), kBand0Rain)
                << "clone rain at (" << r << "," << c << ")";
            EXPECT_FLOAT_EQ(clone->temp_at(r, c), kBand0Temp)
                << "clone temp at (" << r << "," << c << ")";
        }
    }
    fs::remove(path);
}

// set_day(0) used to early-return for n_days_ <= 1. After the clone (whose
// arrays the previous test pins) the call must still land on band 0, so a
// one-day run sees exactly what day 1 of a longer run sees.
TEST(ClimateEngineSingleBand, SetDayZeroCopiesBandZero) {
    const fs::path path = MakeTmpEnvNC();
    if (fs::exists(path)) fs::remove(path);
    WriteTwoBandEnvNC(path);

    mal_abm_fast::ClimateEngine eng;
    eng.load_from_env_nc(path.string(), MakeAoi(), /*max_days=*/1);
    ASSERT_EQ(eng.n_days(), 1);

    auto clone = eng.clone_for_thread();
    clone->set_day(0);
    EXPECT_FLOAT_EQ(clone->rain_at(0, 0), kBand0Rain);
    EXPECT_FLOAT_EQ(clone->temp_at(0, 0), kBand0Temp);

    // Any out-of-range day on a single-band env clamps to band 0 rather
    // than leaving stale values.
    clone->set_day(7);
    EXPECT_FLOAT_EQ(clone->rain_at(0, 0), kBand0Rain);
    EXPECT_FLOAT_EQ(clone->temp_at(0, 0), kBand0Temp);
    clone->set_day(-3);
    EXPECT_FLOAT_EQ(clone->rain_at(0, 0), kBand0Rain);
    EXPECT_FLOAT_EQ(clone->temp_at(0, 0), kBand0Temp);

    fs::remove(path);
}

// Guard the multi-band semantics the fix must not disturb: with two bands
// loaded and base_day_ = 1 (the warm-up offset main.cpp passes), set_day(0)
// reads band 1 and set_day(-1) reads the warm-up band 0.
TEST(ClimateEngineSingleBand, MultiBandBaseDayUnchanged) {
    const fs::path path = MakeTmpEnvNC();
    if (fs::exists(path)) fs::remove(path);
    WriteTwoBandEnvNC(path);

    mal_abm_fast::ClimateEngine eng;
    eng.load_from_env_nc(path.string(), MakeAoi(), /*max_days=*/2);
    ASSERT_EQ(eng.n_days(), 2);
    eng.set_base_day(1);

    auto clone = eng.clone_for_thread();
    clone->set_day(0);
    EXPECT_FLOAT_EQ(clone->rain_at(0, 0), kBand1Rain);
    EXPECT_FLOAT_EQ(clone->temp_at(0, 0), kBand1Temp);

    clone->set_day(-1);
    EXPECT_FLOAT_EQ(clone->rain_at(0, 0), kBand0Rain);
    EXPECT_FLOAT_EQ(clone->temp_at(0, 0), kBand0Temp);

    fs::remove(path);
}
