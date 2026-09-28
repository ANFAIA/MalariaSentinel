// SPDX-License-Identifier: MIT
// test_env_reader.cpp — GoogleTest for env_reader::read_env_nc.
//
// Writes a multi-day synthetic NetCDF and exercises read_env_nc: shape,
// per-day values, the vertical-gradient row-order check, the missing-
// variable error, and the single-day case.
// (The legacy COG/TIF reader tests were removed with read_env_tif — the
// env input contract is NC-only; see docs/specs/abm/spec.md INV-6.)

#include <gtest/gtest.h>

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <string>
#include <vector>

#include <netcdf.h>

#include "env_reader.hpp"

namespace {

namespace fs = std::filesystem;

constexpr int kH = 4;
constexpr int kW = 4;

fs::path MakeTmpEnvNC() {
    const char* base = std::getenv("TMPDIR");
    fs::path dir = (base && *base) ? fs::path(base) : fs::temp_directory_path();
    return dir / "mal_abm_fast_test_env_reader.nc";
}

// Write a synthetic multi-day NetCDF file using the netCDF-C API.
// Creates a CF-compliant file with 4 variables (rainfall, water_temp_c,
// water_frac, ndvi), each with UNLIMITED time dimension.
//
// Per-day constant values:
//   day 0: rain=20.0, temp=25.0
//   day 1: rain=5.0,  temp=20.0
//   day 2: rain=25.0, temp=30.0
//   water_frac=0.5, ndvi=0.4 (constant across all days)
void WriteSyntheticEnvNC(const fs::path& path, int n_days) {
    int ncid, dimids[3], vid[4];
    int dimid_time, dimid_y, dimid_x;

    ASSERT_EQ(nc_create(path.string().c_str(),
                        NC_CLOBBER | NC_NETCDF4, &ncid), NC_NOERR);

    ASSERT_EQ(nc_def_dim(ncid, "time", NC_UNLIMITED, &dimid_time), NC_NOERR);
    ASSERT_EQ(nc_def_dim(ncid, "y", kH, &dimid_y), NC_NOERR);
    ASSERT_EQ(nc_def_dim(ncid, "x", kW, &dimid_x), NC_NOERR);
    dimids[0] = dimid_time;
    dimids[1] = dimid_y;
    dimids[2] = dimid_x;

    ASSERT_EQ(nc_def_var(ncid, "rainfall", NC_FLOAT, 3, dimids, &vid[0]), NC_NOERR);
    ASSERT_EQ(nc_def_var(ncid, "water_temp_c", NC_FLOAT, 3, dimids, &vid[1]), NC_NOERR);
    ASSERT_EQ(nc_def_var(ncid, "water_frac", NC_FLOAT, 3, dimids, &vid[2]), NC_NOERR);
    ASSERT_EQ(nc_def_var(ncid, "ndvi", NC_FLOAT, 3, dimids, &vid[3]), NC_NOERR);

    ASSERT_EQ(nc_put_att_text(ncid, NC_GLOBAL, "Conventions", 6, "CF-1.8"), NC_NOERR);
    ASSERT_EQ(nc_enddef(ncid), NC_NOERR);

    const float rain_vals[] = {20.0f, 5.0f, 25.0f};
    const float temp_vals[] = {25.0f, 20.0f, 30.0f};
    float buf[kH * kW];

    size_t start[3] = {0, 0, 0};
    size_t count[3] = {1, static_cast<size_t>(kH), static_cast<size_t>(kW)};

    for (int d = 0; d < n_days; ++d) {
        start[0] = d;
        const float rain = rain_vals[d % 3];
        const float temp = temp_vals[d % 3];

        for (int r = 0; r < kH; ++r) {
            for (int c = 0; c < kW; ++c) {
                buf[r * kW + c] = rain + static_cast<float>(r);
            }
        }
        ASSERT_EQ(nc_put_vara_float(ncid, vid[0], start, count, buf), NC_NOERR);

        std::fill(buf, buf + kH * kW, temp);
        ASSERT_EQ(nc_put_vara_float(ncid, vid[1], start, count, buf), NC_NOERR);

        std::fill(buf, buf + kH * kW, 0.5f);
        ASSERT_EQ(nc_put_vara_float(ncid, vid[2], start, count, buf), NC_NOERR);

        std::fill(buf, buf + kH * kW, 0.4f);
        ASSERT_EQ(nc_put_vara_float(ncid, vid[3], start, count, buf), NC_NOERR);
    }

    ASSERT_EQ(nc_close(ncid), NC_NOERR);
}

}  // namespace

// -- the actual tests --------------------------------------------------------

// -- NetCDF tests (daily-env-netcdf feature) ---------------------------------

TEST(EnvReader, ReadsDailyNetCDF) {
    const fs::path path = MakeTmpEnvNC();
    if (fs::exists(path)) fs::remove(path);
    WriteSyntheticEnvNC(path, 3);
    ASSERT_TRUE(fs::exists(path));

    mal_abm_fast::env_reader::DailyEnvBands b =
        mal_abm_fast::env_reader::read_env_nc(path.string());

    EXPECT_EQ(b.n_days, 3);
    EXPECT_EQ(b.h, kH);
    EXPECT_EQ(b.w, kW);
    EXPECT_EQ(b.rainfall.size(),     static_cast<size_t>(3 * kH * kW));
    EXPECT_EQ(b.water_temp_c.size(), static_cast<size_t>(3 * kH * kW));
    EXPECT_EQ(b.water_frac.size(),   static_cast<size_t>(3 * kH * kW));
    EXPECT_EQ(b.ndvi.size(),         static_cast<size_t>(3 * kH * kW));

    // Vertical gradients verify NetCDF rows remain aligned with producer
    // row-major order after GDAL's north-up conversion.
    for (int d = 0; d < 3; ++d) {
        const float base = d == 0 ? 20.0f : (d == 1 ? 5.0f : 25.0f);
        for (int r = 0; r < kH; ++r)
            for (int c = 0; c < kW; ++c)
                EXPECT_FLOAT_EQ(b.rainfall[d * kH * kW + r * kW + c],
                                base + static_cast<float>(r));
    }

    // Water temp in °C (NO Mordecai inverse applied)
    // Day 0: 25.0, Day 1: 20.0, Day 2: 30.0
    for (int i = 0; i < kH * kW; ++i)
        EXPECT_FLOAT_EQ(b.water_temp_c[0 * kH * kW + i], 25.0f);
    for (int i = 0; i < kH * kW; ++i)
        EXPECT_FLOAT_EQ(b.water_temp_c[1 * kH * kW + i], 20.0f);
    for (int i = 0; i < kH * kW; ++i)
        EXPECT_FLOAT_EQ(b.water_temp_c[2 * kH * kW + i], 30.0f);

    // water_frac constant across all days
    for (int d = 0; d < 3; ++d)
        for (int i = 0; i < kH * kW; ++i)
            EXPECT_FLOAT_EQ(b.water_frac[d * kH * kW + i], 0.5f);

    // ndvi constant across all days
    for (int d = 0; d < 3; ++d)
        for (int i = 0; i < kH * kW; ++i)
            EXPECT_FLOAT_EQ(b.ndvi[d * kH * kW + i], 0.4f);

    fs::remove(path);
}

TEST(EnvReader, MissingRequiredVariableThrows) {
    const fs::path path = MakeTmpEnvNC();
    if (fs::exists(path)) fs::remove(path);

    // Write a netCDF with only rainfall (missing water_frac, etc.)
    int ncid, dimids[3], vid;
    int dimid_time, dimid_y, dimid_x;
    ASSERT_EQ(nc_create(path.string().c_str(),
                        NC_CLOBBER | NC_NETCDF4, &ncid), NC_NOERR);
    ASSERT_EQ(nc_def_dim(ncid, "time", NC_UNLIMITED, &dimid_time), NC_NOERR);
    ASSERT_EQ(nc_def_dim(ncid, "y", kW, &dimid_y), NC_NOERR);
    ASSERT_EQ(nc_def_dim(ncid, "x", kW, &dimid_x), NC_NOERR);
    dimids[0] = dimid_time; dimids[1] = dimid_y; dimids[2] = dimid_x;
    ASSERT_EQ(nc_def_var(ncid, "rainfall", NC_FLOAT, 3, dimids, &vid), NC_NOERR);
    ASSERT_EQ(nc_put_att_text(ncid, NC_GLOBAL, "Conventions", 6, "CF-1.8"), NC_NOERR);
    ASSERT_EQ(nc_enddef(ncid), NC_NOERR);
    float buf[16] = {0};
    size_t start[3] = {0, 0, 0};
    size_t count[3] = {1, 4, 4};
    ASSERT_EQ(nc_put_vara_float(ncid, vid, start, count, buf), NC_NOERR);
    ASSERT_EQ(nc_close(ncid), NC_NOERR);

    EXPECT_THROW(
        mal_abm_fast::env_reader::read_env_nc(path.string()),
        std::runtime_error);

    fs::remove(path);
}

TEST(EnvReader, NetCDFSingleDay) {
    const fs::path path = MakeTmpEnvNC();
    if (fs::exists(path)) fs::remove(path);
    WriteSyntheticEnvNC(path, 1);
    ASSERT_TRUE(fs::exists(path));

    mal_abm_fast::env_reader::DailyEnvBands b =
        mal_abm_fast::env_reader::read_env_nc(path.string());

    EXPECT_EQ(b.n_days, 1);
    EXPECT_EQ(b.h, kH);
    EXPECT_EQ(b.w, kW);
    EXPECT_EQ(b.rainfall.size(), static_cast<size_t>(kH * kW));
    // Day 0: vertical gradient starts at 20.0 in producer row order.
    for (int r = 0; r < kH; ++r)
        for (int c = 0; c < kW; ++c)
            EXPECT_FLOAT_EQ(b.rainfall[r * kW + c],
                            20.0f + static_cast<float>(r));

    fs::remove(path);
}
