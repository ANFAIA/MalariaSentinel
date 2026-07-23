// SPDX-License-Identifier: MIT
// test_env_reader.cpp — GoogleTest for env_reader::read_env_tif and
// read_env_nc.
//
// Writes a 4-band 4x4 synthetic env COG (water_frac=0.1, rainfall=0.5,
// temp_suitability=0.7, ndvi=0.4) to a tmp file, calls read_env_tif,
// and asserts the shape, the band values, and the Mordecai inverse on
// temp_suitability (0.7 -> 25 - 8*sqrt(0.3) ≈ 21.099).
//
// Also writes a multi-day synthetic NetCDF and exercises read_env_nc.

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
#include <ogr_spatialref.h>

#include "env_reader.hpp"

namespace {

namespace fs = std::filesystem;

constexpr int kH = 4;
constexpr int kW = 4;

// Returns a unique tmp path for the test env. The fixture cleans it up.
fs::path MakeTmpEnv() {
    const char* base = std::getenv("TMPDIR");
    fs::path dir = (base && *base) ? fs::path(base) : fs::temp_directory_path();
    return dir / "mal_abm_fast_test_env_reader.tif";
}

fs::path MakeTmpEnvNC() {
    const char* base = std::getenv("TMPDIR");
    fs::path dir = (base && *base) ? fs::path(base) : fs::temp_directory_path();
    return dir / "mal_abm_fast_test_env_reader.nc";
}

// Write a 4-band 4x4 GTiff. Each band is a constant float32 value,
// tagged with the description that env_reader looks up by.
void WriteSyntheticEnv(const fs::path& path) {
    GDALAllRegister();

    float water_frac[kH * kW];
    float rainfall[kH * kW];
    float temp_suitability[kH * kW];
    float ndvi[kH * kW];
    for (int i = 0; i < kH * kW; ++i) {
        water_frac[i]       = 0.1f;
        rainfall[i]         = 0.5f;
        temp_suitability[i] = 0.7f;
        ndvi[i]             = 0.4f;
    }

    GDALDriverH driver = GDALGetDriverByName("GTiff");
    ASSERT_NE(driver, nullptr);

    char** create_opts = nullptr;
    // No special options; defaults are fine for a one-shot tmp file.
    GDALDatasetH ds = GDALCreate(
        driver, path.string().c_str(),
        kW, kH, 4, GDT_Float32, create_opts);
    ASSERT_NE(ds, nullptr);

    // Set a sample affine transform (just to make the COG "valid"
    // — env_reader doesn't depend on it, but a zero transform trips
    // a few GDAL validators in some builds).
    double gt[6] = {0.0, 1.0, 0.0, 0.0, 0.0, -1.0};
    GDALSetGeoTransform(ds, gt);

    // GDALSetProjection requires a WKT string, not an EPSG code.
    // Convert EPSG:4326 to WKT via OGRSpatialReference (C++ API).
    {
        OGRSpatialReference srs;
        if (srs.SetFromUserInput("EPSG:4326") == OGRERR_NONE) {
            char* wkt = nullptr;
            if (srs.exportToWkt(&wkt) == OGRERR_NONE && wkt) {
                GDALSetProjection(ds, wkt);
                CPLFree(wkt);
            }
        }
    }

    // Band 1: water_frac
    GDALRasterBandH b1 = GDALGetRasterBand(ds, 1);
    GDALSetDescription(b1, "water_frac");
    CPLErr e1 = GDALRasterIO(b1, GF_Write, 0, 0, kW, kH,
                             (void*)water_frac, kW, kH,
                             GDT_Float32, 0, 0);
    EXPECT_EQ(e1, CE_None);

    // Band 2: rainfall
    GDALRasterBandH b2 = GDALGetRasterBand(ds, 2);
    GDALSetDescription(b2, "rainfall");
    CPLErr e2 = GDALRasterIO(b2, GF_Write, 0, 0, kW, kH,
                             (void*)rainfall, kW, kH,
                             GDT_Float32, 0, 0);
    EXPECT_EQ(e2, CE_None);

    // Band 3: temp_suitability
    GDALRasterBandH b3 = GDALGetRasterBand(ds, 3);
    GDALSetDescription(b3, "temp_suitability");
    CPLErr e3 = GDALRasterIO(b3, GF_Write, 0, 0, kW, kH,
                             (void*)temp_suitability, kW, kH,
                             GDT_Float32, 0, 0);
    EXPECT_EQ(e3, CE_None);

    // Band 4: ndvi
    GDALRasterBandH b4 = GDALGetRasterBand(ds, 4);
    GDALSetDescription(b4, "ndvi");
    CPLErr e4 = GDALRasterIO(b4, GF_Write, 0, 0, kW, kH,
                             (void*)ndvi, kW, kH,
                             GDT_Float32, 0, 0);
    EXPECT_EQ(e4, CE_None);

    GDALClose(ds);
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

        std::fill(buf, buf + kH * kW, rain);
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

TEST(EnvReader, ReadsFourBandsAndInvertsTempSuitability) {
    const fs::path path = MakeTmpEnv();
    if (fs::exists(path)) fs::remove(path);
    WriteSyntheticEnv(path);
    ASSERT_TRUE(fs::exists(path));

    mal_abm_fast::env_reader::EnvBands b =
        mal_abm_fast::env_reader::read_env_tif(path.string());

    EXPECT_EQ(b.h, kH);
    EXPECT_EQ(b.w, kW);
    EXPECT_EQ(b.water_frac.size(), static_cast<size_t>(kH * kW));
    EXPECT_EQ(b.rainfall.size(),   static_cast<size_t>(kH * kW));
    EXPECT_EQ(b.temp_suitability.size(),
              static_cast<size_t>(kH * kW));
    EXPECT_EQ(b.ndvi.size(),       static_cast<size_t>(kH * kW));
    EXPECT_TRUE(b.twi.empty());  // no twi band in the synthetic COG

    // Spot-check: every cell of water_frac is 0.1, every cell of
    // rainfall is 0.5, every cell of ndvi is 0.4.
    for (int i = 0; i < kH * kW; ++i) {
        EXPECT_FLOAT_EQ(b.water_frac[i], 0.1f);
        EXPECT_FLOAT_EQ(b.rainfall[i],   0.5f);
        EXPECT_FLOAT_EQ(b.ndvi[i],       0.4f);
    }

    // Mordecai inverse: s = 0.7 -> upper branch (s > 0.5)
    //   T = 25 + 8*sqrt(1 - 0.7)
    //     = 25 + 8*sqrt(0.3)
    //     ≈ 29.382
    // (The earlier single-branch formula T = 25 - 8*sqrt(1-s) produced
    //  ~20.618 at s=0.7, which underestimates tropical temperatures
    //  when s > 0.5. env_reader now uses the upper branch for s > 0.5
    //  to recover the correct T in [25, 33]°C.)
    const float expected = 25.0f + 8.0f * std::sqrt(1.0f - 0.7f);
    for (int i = 0; i < kH * kW; ++i) {
        EXPECT_NEAR(b.temp_suitability[i], expected, 1e-4);
    }

    // Cross-check: the upper-branch peak at s = 0.75 is T = 29.0.
    const float peak = 25.0f + 8.0f * std::sqrt(1.0f - 0.75f);
    EXPECT_NEAR(peak, 29.0f, 1e-4);

    fs::remove(path);
}

TEST(EnvReader, MissingRequiredBandThrows) {
    const fs::path path = MakeTmpEnv();
    if (fs::exists(path)) fs::remove(path);

    // Write a 3-band COG missing the `ndvi` band.
    GDALAllRegister();
    GDALDriverH driver = GDALGetDriverByName("GTiff");
    GDALDatasetH ds = GDALCreate(
        driver, path.string().c_str(), kW, kH, 3, GDT_Float32, nullptr);
    ASSERT_NE(ds, nullptr);
    float v[16] = {0};
    GDALSetDescription(GDALGetRasterBand(ds, 1), "water_frac");
    EXPECT_EQ(GDALRasterIO(GDALGetRasterBand(ds, 1), GF_Write, 0, 0, kW, kH,
                          v, kW, kH, GDT_Float32, 0, 0), CE_None);
    GDALSetDescription(GDALGetRasterBand(ds, 2), "rainfall");
    EXPECT_EQ(GDALRasterIO(GDALGetRasterBand(ds, 2), GF_Write, 0, 0, kW, kH,
                          v, kW, kH, GDT_Float32, 0, 0), CE_None);
    GDALSetDescription(GDALGetRasterBand(ds, 3), "temp_suitability");
    EXPECT_EQ(GDALRasterIO(GDALGetRasterBand(ds, 3), GF_Write, 0, 0, kW, kH,
                          v, kW, kH, GDT_Float32, 0, 0), CE_None);
    GDALClose(ds);

    EXPECT_THROW(
        mal_abm_fast::env_reader::read_env_tif(path.string()),
        std::runtime_error);

    fs::remove(path);
}

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

    // Day 0: rain=20.0 everywhere
    for (int i = 0; i < kH * kW; ++i)
        EXPECT_FLOAT_EQ(b.rainfall[0 * kH * kW + i], 20.0f);
    // Day 1: rain=5.0 everywhere
    for (int i = 0; i < kH * kW; ++i)
        EXPECT_FLOAT_EQ(b.rainfall[1 * kH * kW + i], 5.0f);
    // Day 2: rain=25.0 everywhere
    for (int i = 0; i < kH * kW; ++i)
        EXPECT_FLOAT_EQ(b.rainfall[2 * kH * kW + i], 25.0f);

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
    // Day 0: rain=20.0
    for (int i = 0; i < kH * kW; ++i)
        EXPECT_FLOAT_EQ(b.rainfall[i], 20.0f);

    fs::remove(path);
}
