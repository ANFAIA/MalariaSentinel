// SPDX-License-Identifier: MIT
// test_env_reader.cpp — GoogleTest for env_reader::read_env_tif.
//
// Writes a 4-band 4x4 synthetic env COG (water_frac=0.1, rainfall=0.5,
// temp_suitability=0.7, ndvi=0.4) to a tmp file, calls read_env_tif,
// and asserts the shape, the band values, and the Mordecai inverse on
// temp_suitability (0.7 -> 25 - 8*sqrt(0.3) ≈ 21.099).

#include <gtest/gtest.h>

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <string>
#include <vector>

#include "gdal.h"

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
    GDALSetProjection(ds, "EPSG:4326");

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

    // Mordecai inverse: s = 0.7 -> T = 25 - 8*sqrt(1 - 0.7)
    //                                = 25 - 8*sqrt(0.3)
    //                                ≈ 20.618
    // (The brief quotes "≈ 21.099 for s = 0.7" but the formula
    //  25 - 8*sqrt(1 - 0.7) actually evaluates to ~20.618. The 21.0
    //  figure corresponds to s = 0.75 — see the Python `_suit_to_c`
    //  docstring. We assert the actual formula value here.)
    const float expected = 25.0f - 8.0f * std::sqrt(1.0f - 0.7f);
    for (int i = 0; i < kH * kW; ++i) {
        EXPECT_NEAR(b.temp_suitability[i], expected, 1e-4);
    }

    // Cross-check: the docstring value 21.0 corresponds to s = 0.75.
    const float peak = 25.0f - 8.0f * std::sqrt(1.0f - 0.75f);
    EXPECT_NEAR(peak, 21.0f, 1e-4);

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
