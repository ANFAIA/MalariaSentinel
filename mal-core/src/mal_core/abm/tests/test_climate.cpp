// SPDX-License-Identifier: MIT
// test_climate.cpp — GoogleTest for ClimateEngine::load_from_env_nc
// and the *_at(row, col) accessors.
//
// Writes a multi-day synthetic NetCDF and exercises the daily climate
// accessors (set_day, n_days), plus the out-of-bounds and NaN-salinity
// accessor behaviour. (The legacy load_from_env_tif COG tests were
// removed with the TIF path — the env input contract is NC-only; see
// docs/specs/abm/spec.md INV-6.)

#include <gtest/gtest.h>

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <limits>
#include <string>
#include <vector>

#include <netcdf.h>

#include "climate.hpp"
#include "wire.hpp"

namespace {

namespace fs = std::filesystem;

constexpr int kH = 4;
constexpr int kW = 4;

fs::path MakeTmpEnvNC() {
    const char* base = std::getenv("TMPDIR");
    fs::path dir = (base && *base) ? fs::path(base) : fs::temp_directory_path();
    return dir / ("mal_abm_fast_test_climate_" +
                  std::to_string(static_cast<long>(::getpid())) + ".nc");
}

// Write a synthetic multi-day NetCDF using the netCDF-C API.
// nan_mode: 0 = no NaNs (finite linear temp field 20..26 = 20+r+c);
//           1 = day-1-only NaN block at (1..2, 1..2) — interior NaNs
//               surrounded by finite gradient values;
//           2 = day-1 fully NaN temperature slice (degenerate).
void WriteSyntheticEnvNC(const fs::path& path, int n_days,
                         bool with_salinity = false, int nan_mode = 0) {
    int ncid, dimids[3], vid[4], vidsal;
    int dimid_time, dimid_y, dimid_x;

    ASSERT_EQ(nc_create(path.string().c_str(),
                        NC_CLOBBER | NC_NETCDF4, &ncid), NC_NOERR);
    ASSERT_EQ(nc_def_dim(ncid, "time", NC_UNLIMITED, &dimid_time), NC_NOERR);
    ASSERT_EQ(nc_def_dim(ncid, "y", kH, &dimid_y), NC_NOERR);
    ASSERT_EQ(nc_def_dim(ncid, "x", kW, &dimid_x), NC_NOERR);
    dimids[0] = dimid_time; dimids[1] = dimid_y; dimids[2] = dimid_x;

    ASSERT_EQ(nc_def_var(ncid, "rainfall", NC_FLOAT, 3, dimids, &vid[0]), NC_NOERR);
    ASSERT_EQ(nc_def_var(ncid, "air_temp_c", NC_FLOAT, 3, dimids, &vid[1]), NC_NOERR);
    if (with_salinity) {
        ASSERT_EQ(nc_def_var(ncid, "salinity_ppt", NC_FLOAT, 3, dimids, &vidsal), NC_NOERR);
    }
    // _FillValue = NaN on water_temp_c: netCDF converts NaN writes into
    // the default fill (9.969e+36) unless a NaN _FillValue attribute is
    // declared first — the NaN payload must survive the round-trip, as
    // in the real env NCs (xarray writer).
    if (nan_mode != 0) {
        const float nanfill = std::numeric_limits<float>::quiet_NaN();
        ASSERT_EQ(nc_put_att_float(ncid, vid[1], "_FillValue", NC_FLOAT, 1,
                                   &nanfill), NC_NOERR);
    }
    ASSERT_EQ(nc_put_att_text(ncid, NC_GLOBAL, "Conventions", 6, "CF-1.8"), NC_NOERR);
    ASSERT_EQ(nc_enddef(ncid), NC_NOERR);

    // Static habitat planes (contract v3.0; 0.0 built so the open-pluvial
    // plane carries flash-pool potential alone).
    auto def_static = [&](const char* name, float value) {
        int dids[2] = {dimid_y, dimid_x};
        int varid = -1;
        ASSERT_EQ(nc_def_var(ncid, name, NC_FLOAT, 2, dids, &varid), NC_NOERR);
        ASSERT_EQ(nc_enddef(ncid), NC_NOERR);
        std::vector<float> plane(static_cast<size_t>(kH) * kW, value);
        ASSERT_EQ(nc_put_var_float(ncid, varid, plane.data()), NC_NOERR);
        ASSERT_EQ(nc_redef(ncid), NC_NOERR);
    };
    def_static("jrc_persistent",      0.2f);
    def_static("lc_built",            0.0f);
    def_static("lc_wetland",          0.2f);
    def_static("lc_open_plus_water",  0.3f);
    def_static("lc_crop",             0.0f);

    const float rain_vals[] = {60.0f, 40.0f, 55.0f};
    const float temp_vals[] = {25.0f, 20.0f, 30.0f};
    const float sal_vals[]  = {0.0f, 25.0f, 3.0f};
    float buf[kH * kW];
    size_t start[3] = {0, 0, 0};
    size_t count[3] = {1, static_cast<size_t>(kH), static_cast<size_t>(kW)};

    for (int d = 0; d < n_days; ++d) {
        start[0] = d;
        std::fill(buf, buf + kH * kW, rain_vals[d % 3]);
        ASSERT_EQ(nc_put_vara_float(ncid, vid[0], start, count, buf), NC_NOERR);
        if (nan_mode == 2 && d == 1) {
            std::fill(buf, buf + kH * kW,
                      std::numeric_limits<float>::quiet_NaN());
        } else {
            for (int i = 0; i < kH * kW; ++i) {
                const int r = i / kW, c = i % kW;
                // Day 1 NaN block (nan_mode 1): interior, fully
                // surrounded by finite gradient values.
                if (nan_mode == 1 && d == 1 && r >= 1 && r <= 2 &&
                    c >= 1 && c <= 2) {
                    buf[i] = std::numeric_limits<float>::quiet_NaN();
                } else if (nan_mode == 0) {
                    buf[i] = temp_vals[d % 3];
                } else {
                    buf[i] = 20.0f + static_cast<float>(r + c);
                }
            }
        }
        ASSERT_EQ(nc_put_vara_float(ncid, vid[1], start, count, buf), NC_NOERR);
        if (with_salinity) {
            std::fill(buf, buf + kH * kW, sal_vals[d % 3]);
            ASSERT_EQ(nc_put_vara_float(ncid, vidsal, start, count, buf), NC_NOERR);
        }
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

// -- Daily NetCDF tests (daily-env-netcdf feature) ---------------------------

TEST(ClimateEngine, LoadFromEnvNcPopulatesDailyBands) {
    const fs::path path = MakeTmpEnvNC();
    if (fs::exists(path)) fs::remove(path);
    WriteSyntheticEnvNC(path, 3);
    ASSERT_TRUE(fs::exists(path));

    mal_abm_fast::ClimateEngine eng;
    eng.load_from_env_nc(path.string(), MakeAoi());

    EXPECT_EQ(eng.n_days(), 3);
    EXPECT_EQ(eng.h(), kH);
    EXPECT_EQ(eng.w(), kW);

    // Day 0: rain=60.0 at (0,0)
    eng.set_day(0);
    EXPECT_FLOAT_EQ(eng.rain_at(0, 0), 60.0f);
    EXPECT_FLOAT_EQ(eng.temp_at(0, 0), 25.0f);

    // Day 1: rain=40.0 at (0,0)
    eng.set_day(1);
    EXPECT_FLOAT_EQ(eng.rain_at(0, 0), 40.0f);
    EXPECT_FLOAT_EQ(eng.temp_at(0, 0), 20.0f);

    // Day 2: rain=55.0 at (0,0)
    eng.set_day(2);
    EXPECT_FLOAT_EQ(eng.rain_at(0, 0), 55.0f);
    EXPECT_FLOAT_EQ(eng.temp_at(0, 0), 30.0f);

    fs::remove(path);
}

TEST(ClimateEngine, StaticBandsReachAccessor) {
    const fs::path path = MakeTmpEnvNC();
    if (fs::exists(path)) fs::remove(path);
    WriteSyntheticEnvNC(path, 3);
    ASSERT_TRUE(fs::exists(path));

    mal_abm_fast::ClimateEngine eng;
    eng.load_from_env_nc(path.string(), MakeAoi());
    EXPECT_EQ(eng.jrc_persistent().size(), 16u);
    const auto f = eng.habitat_features_at(0, 0);
    EXPECT_GT(f.lc_open_plus_water, 0.0f);
    fs::remove(path);
}

TEST(ClimateEngine, DailyRainfallReadCorrectly) {
    const fs::path path = MakeTmpEnvNC();
    if (fs::exists(path)) fs::remove(path);
    WriteSyntheticEnvNC(path, 3);
    ASSERT_TRUE(fs::exists(path));

    mal_abm_fast::ClimateEngine eng;
    eng.load_from_env_nc(path.string(), MakeAoi());

    // Verify the climate engine correctly reads the synthetic rain values.

    // Day 0: rain=60 at (0,0)
    eng.set_day(0);
    EXPECT_FLOAT_EQ(eng.rain_at(0, 0), 60.0f);

    // Day 1: rain=40 at (0,0)
    eng.set_day(1);
    EXPECT_FLOAT_EQ(eng.rain_at(0, 0), 40.0f);

    // Day 2: rain=55 at (0,0)
    eng.set_day(2);
    EXPECT_FLOAT_EQ(eng.rain_at(0, 0), 55.0f);

    fs::remove(path);
}

TEST(ClimateEngine, SetDayClampsToValidRange) {
    const fs::path path = MakeTmpEnvNC();
    if (fs::exists(path)) fs::remove(path);
    WriteSyntheticEnvNC(path, 3);
    ASSERT_TRUE(fs::exists(path));

    mal_abm_fast::ClimateEngine eng;
    eng.load_from_env_nc(path.string(), MakeAoi());

    // set_day(999) should clamp to n_days-1 (day 2)
    eng.set_day(999);
    EXPECT_FLOAT_EQ(eng.rain_at(0, 0), 55.0f);  // day 2 value

    // set_day(-1) should clamp to 0
    eng.set_day(-1);
    EXPECT_FLOAT_EQ(eng.rain_at(0, 0), 60.0f);  // day 0 value

    // set_day(1) should work normally
    eng.set_day(1);
    EXPECT_FLOAT_EQ(eng.rain_at(0, 0), 40.0f);  // day 1 value

    fs::remove(path);
}

// -- Salinity (M7.8) --------------------------------------------------------

TEST(ClimateEngine, LoadFromEnvNcWithoutSalinityDefaultsToFreshwater) {
    const fs::path path = MakeTmpEnvNC();
    if (fs::exists(path)) fs::remove(path);
    WriteSyntheticEnvNC(path, 2, /*with_salinity=*/false);
    ASSERT_TRUE(fs::exists(path));

    mal_abm_fast::ClimateEngine eng;
    eng.load_from_env_nc(path.string(), MakeAoi());

    // Pre-salinity NC: salinity accessor stays fresh-water (0.0) everywhere,
    // including out-of-bounds. The salinity factor is inert, as before.
    for (int d = 0; d < 2; ++d) {
        eng.set_day(d);
        EXPECT_FLOAT_EQ(eng.salinity_at(0, 0), 0.0f);
        EXPECT_FLOAT_EQ(eng.salinity_at(kH - 1, kW - 1), 0.0f);
    }
    EXPECT_TRUE(eng.salinity().empty());

    fs::remove(path);
}

TEST(ClimateEngine, LoadFromEnvNcWithSalinityPopulatesAccessor) {
    const fs::path path = MakeTmpEnvNC();
    if (fs::exists(path)) fs::remove(path);
    WriteSyntheticEnvNC(path, 3, /*with_salinity=*/true);
    ASSERT_TRUE(fs::exists(path));

    mal_abm_fast::ClimateEngine eng;
    eng.load_from_env_nc(path.string(), MakeAoi());

    // Day 0: salinity=0.0, Day 1: salinity=25.0, Day 2: salinity=3.0 at (0,0).
    eng.set_day(0);
    EXPECT_FLOAT_EQ(eng.salinity_at(0, 0), 0.0f);

    eng.set_day(1);
    EXPECT_FLOAT_EQ(eng.salinity_at(0, 0), 25.0f);
    EXPECT_FLOAT_EQ(eng.salinity_at(kH - 1, kW - 1), 25.0f);

    eng.set_day(2);
    EXPECT_FLOAT_EQ(eng.salinity_at(0, 0), 3.0f);

    // Out-of-bounds returns 0.0 (freshwater).
    EXPECT_FLOAT_EQ(eng.salinity_at(-1, 0), 0.0f);
    EXPECT_FLOAT_EQ(eng.salinity_at(kH, 0), 0.0f);
    EXPECT_FLOAT_EQ(eng.salinity_at(0, kW), 0.0f);

    fs::remove(path);
}

TEST(ClimateEngine, CloneForThreadPropagatesSalinity) {
    const fs::path path = MakeTmpEnvNC();
    if (fs::exists(path)) fs::remove(path);
    WriteSyntheticEnvNC(path, 3, /*with_salinity=*/true);
    ASSERT_TRUE(fs::exists(path));

    mal_abm_fast::ClimateEngine eng;
    eng.load_from_env_nc(path.string(), MakeAoi());

    auto clone = eng.clone_for_thread();
    ASSERT_NE(clone, nullptr);

    clone->set_day(1);
    EXPECT_FLOAT_EQ(clone->salinity_at(0, 0), 25.0f);

    fs::remove(path);
}

// -- Temperature NaN imputation (2026-10-13) ---------------------------------

// Interior NaN pixels are imputed at load time from same-day finite
// neighbors: temp_at() is finite everywhere, imputed values stay
// within the finite field's range, and off-grid lookups clamp to the
// border cell — no per-lookup fallback constant (ADULT_TEMP_FALLBACK_C
// was removed).
TEST(ClimateEngine, TempNanImputedFromNeighborsAtLoad) {
    const fs::path path = MakeTmpEnvNC();
    if (fs::exists(path)) fs::remove(path);
    WriteSyntheticEnvNC(path, 3, /*with_salinity=*/false, /*nan_mode=*/1);
    ASSERT_TRUE(fs::exists(path));

    mal_abm_fast::ClimateEngine eng;
    eng.load_from_env_nc(path.string(), MakeAoi());

    // Finite temp field on all days, all cells (including imputed NaNs).
    for (int d = 0; d < 3; ++d) {
        eng.set_day(d);
        for (int r = 0; r < kH; ++r) {
            for (int c = 0; c < kW; ++c) {
                const float T = eng.temp_at(r, c);
                EXPECT_TRUE(std::isfinite(static_cast<double>(T)))
                    << "day " << d << " cell (" << r << "," << c << ")";
            }
        }
    }

    // Day 1: non-NaN cells keep the exact gradient 20 + r + c.
    eng.set_day(1);
    EXPECT_FLOAT_EQ(eng.temp_at(0, 0), 20.0f);
    EXPECT_FLOAT_EQ(eng.temp_at(kH - 1, kW - 1), 26.0f);

    // Imputed interior cells (the day-1 NaN block) are finite and
    // bounded by the same-day finite field extremes [20, 26]. (The
    // wavefront mean fill is not exactly symmetric on a gradient field
    // — no point-for-point equality expected.)
    EXPECT_GE(eng.temp_at(1, 1), 20.0f);
    EXPECT_LE(eng.temp_at(1, 1), 26.0f);
    EXPECT_GE(eng.temp_at(2, 2), 20.0f);
    EXPECT_LE(eng.temp_at(2, 2), 26.0f);

    // Off-grid lookups clamp to the border cell (no fallback constant).
    EXPECT_FLOAT_EQ(eng.temp_at(-1, 0), eng.temp_at(0, 0));
    EXPECT_FLOAT_EQ(eng.temp_at(kH, 0), eng.temp_at(kH - 1, 0));
    EXPECT_FLOAT_EQ(eng.temp_at(0, kW), eng.temp_at(0, kW - 1));
    EXPECT_FLOAT_EQ(eng.temp_at(-5, -5), eng.temp_at(0, 0));

    fs::remove(path);
}

// Degenerate slice (every cell NaN — no finite cell anywhere): the NaNs
// cannot borrow neighbors, so temp_at serves the documented degenerate
// guard (25 deg C literal) — the mortality and EIP submodels stay in
// their calibrated regime.
TEST(ClimateEngine, AllNanTempSliceServesDegenerateGuard) {
    const fs::path path = MakeTmpEnvNC();
    if (fs::exists(path)) fs::remove(path);
    WriteSyntheticEnvNC(path, 3, /*with_salinity=*/false, /*nan_mode=*/2);
    ASSERT_TRUE(fs::exists(path));

    mal_abm_fast::ClimateEngine eng;
    eng.load_from_env_nc(path.string(), MakeAoi());

    eng.set_day(1);  // the fully-NaN slice
    EXPECT_FLOAT_EQ(eng.temp_at(0, 0), 25.0f);
    EXPECT_FLOAT_EQ(eng.temp_at(kH - 1, kW - 1), 25.0f);

    // Clean days keep their gradient values.
    eng.set_day(0);
    EXPECT_FLOAT_EQ(eng.temp_at(0, 0), 20.0f);

    fs::remove(path);
}
