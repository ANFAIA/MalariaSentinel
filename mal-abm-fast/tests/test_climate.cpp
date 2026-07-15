// SPDX-License-Identifier: MIT
// test_climate.cpp — GoogleTest for ClimateEngine::load_from_env_tif
// and the *_at(row, col) accessors.
//
// Writes a 4x4 env COG, calls load_from_env_tif, and asserts:
//   * h_ / w_
//   * rain_at / temp_at / water_frac_at at a sample point
//   * out-of-bounds row/col returns 0 (rain, water) and 25 (temp)
//   * the temp_suitability band was Mordecai-inverted

#include <gtest/gtest.h>

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <string>
#include <vector>

#include "gdal.h"

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
