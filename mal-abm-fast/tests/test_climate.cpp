// SPDX-License-Identifier: MIT
// test_climate.cpp — GoogleTest for ClimateEngine::load_from_env_tif,
// load_from_env_nc, and the *_at(row, col) accessors.
//
// Writes a 4x4 env COG, calls load_from_env_tif, and asserts:
//   * h_ / w_
//   * rain_at / temp_at / water_frac_at at a sample point
//   * out-of-bounds row/col returns 0 (rain, water) and 25 (temp)
//   * the temp_suitability band was Mordecai-inverted
//
// Also writes a multi-day synthetic NetCDF and exercises the daily
// climate accessors (set_day, n_days).

#include <gtest/gtest.h>

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <string>
#include <vector>

#include "gdal.h"
#include "cpl_string.h"
#include <netcdf.h>

#include "climate.hpp"
#include "wire.hpp"

namespace {

namespace fs = std::filesystem;

constexpr int kH = 4;
constexpr int kW = 4;

fs::path MakeTmpEnv() {
    const char* base = std::getenv("TMPDIR");
    fs::path dir = (base && *base) ? fs::path(base) : fs::temp_directory_path();
    return dir / "mal_abm_fast_test_climate.tif";
}

fs::path MakeTmpEnvNC() {
    const char* base = std::getenv("TMPDIR");
    fs::path dir = (base && *base) ? fs::path(base) : fs::temp_directory_path();
    return dir / "mal_abm_fast_test_climate.nc";
}

void WriteSyntheticEnv(const fs::path& path) {
    GDALAllRegister();
    GDALDriverH driver = GDALGetDriverByName("GTiff");
    ASSERT_NE(driver, nullptr);

    float v_water_frac[kH * kW];
    float v_rainfall[kH * kW];
    float v_temp_suitability[kH * kW];
    float v_ndvi[kH * kW];
    for (int i = 0; i < kH * kW; ++i) {
        v_water_frac[i]       = 0.1f;
        v_rainfall[i]         = 0.5f;
        v_temp_suitability[i] = 0.7f;
        v_ndvi[i]             = 0.4f;
    }

    GDALDatasetH ds = GDALCreate(
        driver, path.string().c_str(), kW, kH, 4, GDT_Float32, nullptr);
    ASSERT_NE(ds, nullptr);
    double gt[6] = {0.0, 1.0, 0.0, 0.0, 0.0, -1.0};
    GDALSetGeoTransform(ds, gt);
    GDALSetProjection(ds, "EPSG:4326");

    auto write_band = [&](int idx, const char* name, const float* v) {
        GDALRasterBandH b = GDALGetRasterBand(ds, idx);
        GDALSetDescription(b, name);
        EXPECT_EQ(GDALRasterIO(b, GF_Write, 0, 0, kW, kH,
                               const_cast<float*>(v), kW, kH,
                               GDT_Float32, 0, 0), CE_None);
    };
    write_band(1, "water_frac",       v_water_frac);
    write_band(2, "rainfall",         v_rainfall);
    write_band(3, "temp_suitability", v_temp_suitability);
    write_band(4, "ndvi",             v_ndvi);
    GDALClose(ds);
}

// Write a synthetic multi-day NetCDF using the netCDF-C API.
void WriteSyntheticEnvNC(const fs::path& path, int n_days) {
    int ncid, dimids[3], vid[4];
    int dimid_time, dimid_y, dimid_x;

    ASSERT_EQ(nc_create(path.string().c_str(),
                        NC_CLOBBER | NC_NETCDF4, &ncid), NC_NOERR);
    ASSERT_EQ(nc_def_dim(ncid, "time", NC_UNLIMITED, &dimid_time), NC_NOERR);
    ASSERT_EQ(nc_def_dim(ncid, "y", kH, &dimid_y), NC_NOERR);
    ASSERT_EQ(nc_def_dim(ncid, "x", kW, &dimid_x), NC_NOERR);
    dimids[0] = dimid_time; dimids[1] = dimid_y; dimids[2] = dimid_x;

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
        std::fill(buf, buf + kH * kW, rain_vals[d % 3]);
        ASSERT_EQ(nc_put_vara_float(ncid, vid[0], start, count, buf), NC_NOERR);
        std::fill(buf, buf + kH * kW, temp_vals[d % 3]);
        ASSERT_EQ(nc_put_vara_float(ncid, vid[1], start, count, buf), NC_NOERR);
        std::fill(buf, buf + kH * kW, 0.5f);
        ASSERT_EQ(nc_put_vara_float(ncid, vid[2], start, count, buf), NC_NOERR);
        std::fill(buf, buf + kH * kW, 0.4f);
        ASSERT_EQ(nc_put_vara_float(ncid, vid[3], start, count, buf), NC_NOERR);
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

TEST(ClimateEngine, LoadFromEnvTifPopulatesBands) {
    const fs::path path = MakeTmpEnv();
    if (fs::exists(path)) fs::remove(path);
    WriteSyntheticEnv(path);
    ASSERT_TRUE(fs::exists(path));

    mal_abm_fast::ClimateEngine eng;
    eng.load_from_env_tif(path.string(), MakeAoi());

    EXPECT_EQ(eng.h(), kH);
    EXPECT_EQ(eng.w(), kW);
    EXPECT_EQ(eng.rain_daily().size(), static_cast<size_t>(kH * kW));
    EXPECT_EQ(eng.temp_d().size(),     static_cast<size_t>(kH * kW));
    EXPECT_EQ(eng.water_frac().size(), static_cast<size_t>(kH * kW));
    EXPECT_EQ(eng.ndvi().size(),       static_cast<size_t>(kH * kW));

    // Sample point lookups at (0, 0).
    EXPECT_FLOAT_EQ(eng.rain_at(0, 0), 0.5f);
    EXPECT_FLOAT_EQ(eng.water_frac_at(0, 0), 0.1f);
    const float expected_temp = 25.0f - 8.0f * std::sqrt(1.0f - 0.7f);
    EXPECT_NEAR(eng.temp_at(0, 0), expected_temp, 1e-4);

    // Sample at (3, 3).
    EXPECT_FLOAT_EQ(eng.rain_at(3, 3), 0.5f);
    EXPECT_NEAR(eng.temp_at(3, 3), expected_temp, 1e-4);

    // Out-of-bounds returns 0 (rain, water) / 25 (temp).
    EXPECT_FLOAT_EQ(eng.rain_at(-1, 0), 0.0f);
    EXPECT_FLOAT_EQ(eng.rain_at(kH, 0), 0.0f);
    EXPECT_FLOAT_EQ(eng.rain_at(0, kW), 0.0f);
    EXPECT_FLOAT_EQ(eng.water_frac_at(-1, 0), 0.0f);
    EXPECT_FLOAT_EQ(eng.temp_at(-1, 0), 25.0f);
    EXPECT_FLOAT_EQ(eng.temp_at(0, kW), 25.0f);

    fs::remove(path);
}

TEST(ClimateEngine, SetTwiGridOverridesDefault) {
    mal_abm_fast::ClimateEngine eng;
    EXPECT_TRUE(eng.twi_grid().empty());
    std::vector<float> t(16, 9.5f);
    eng.set_twi_grid(std::move(t));
    EXPECT_EQ(eng.twi_grid().size(), 16u);
    EXPECT_FLOAT_EQ(eng.twi_grid()[0], 9.5f);
    EXPECT_FLOAT_EQ(eng.twi_grid()[15], 9.5f);
}

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

    // Day 0: rain=20.0 at (0,0)
    eng.set_day(0);
    EXPECT_FLOAT_EQ(eng.rain_at(0, 0), 20.0f);
    EXPECT_FLOAT_EQ(eng.temp_at(0, 0), 25.0f);

    // Day 1: rain=5.0 at (0,0)
    eng.set_day(1);
    EXPECT_FLOAT_EQ(eng.rain_at(0, 0), 5.0f);
    EXPECT_FLOAT_EQ(eng.temp_at(0, 0), 20.0f);

    // Day 2: rain=25.0 at (0,0)
    eng.set_day(2);
    EXPECT_FLOAT_EQ(eng.rain_at(0, 0), 25.0f);
    EXPECT_FLOAT_EQ(eng.temp_at(0, 0), 30.0f);

    // water_frac constant across all days
    for (int d = 0; d < 3; ++d) {
        eng.set_day(d);
        EXPECT_FLOAT_EQ(eng.water_frac_at(0, 0), 0.5f);
    }

    fs::remove(path);
}

TEST(ClimateEngine, DailyRainfallTogglesAtThreshold) {
    const fs::path path = MakeTmpEnvNC();
    if (fs::exists(path)) fs::remove(path);
    WriteSyntheticEnvNC(path, 3);
    ASSERT_TRUE(fs::exists(path));

    mal_abm_fast::ClimateEngine eng;
    eng.load_from_env_nc(path.string(), MakeAoi());

    // Day 0: rain=20 (>15, PLUVIAL_POOL_RAIN_THRESHOLD_MM)
    eng.set_day(0);
    EXPECT_GT(eng.rain_at(0, 0),
              mal_abm_fast::PLUVIAL_POOL_RAIN_THRESHOLD_MM);

    // Day 1: rain=5 (<15, inactive)
    eng.set_day(1);
    EXPECT_LT(eng.rain_at(0, 0),
              mal_abm_fast::PLUVIAL_POOL_RAIN_THRESHOLD_MM);

    // Day 2: rain=25 (>15, active again)
    eng.set_day(2);
    EXPECT_GT(eng.rain_at(0, 0),
              mal_abm_fast::PLUVIAL_POOL_RAIN_THRESHOLD_MM);

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
    EXPECT_FLOAT_EQ(eng.rain_at(0, 0), 25.0f);  // day 2 value

    // set_day(-1) should clamp to 0
    eng.set_day(-1);
    EXPECT_FLOAT_EQ(eng.rain_at(0, 0), 20.0f);  // day 0 value

    // set_day(1) should work normally
    eng.set_day(1);
    EXPECT_FLOAT_EQ(eng.rain_at(0, 0), 5.0f);   // day 1 value

    fs::remove(path);
}
