// SPDX-License-Identifier: MIT
// test_transmission_output.cpp — Unit tests for 4-band transmission GeoTIFF and JSON writers.
#include <gtest/gtest.h>
#include <filesystem>
#include <fstream>
#include <vector>

#include <gdal.h>
#include <gdal_priv.h>
#include <nlohmann/json.hpp>

#include "mal_abm_fast/transmission_output.hpp"

namespace mal_abm_fast {
namespace {

TEST(TransmissionOutput, WritesFourBandCogAndSidecar) {
    GDALAllRegister();
    const std::string tmp_dir = "/tmp/mal_abm_test_trans_out";
    std::filesystem::create_directories(tmp_dir);
    const std::string tif_path = tmp_dir + "/transmission_test.tif";
    const std::string json_path = tmp_dir + "/transmission_test.json";

    HumanCompartmentGrid grid;
    std::vector<float> pop = {100.0f, 200.0f, 300.0f, 400.0f};
    grid.init(2, 2, pop, 12, 20, 180, false, 0.10);

    std::vector<float> press = {5.0f, 10.0f, 0.0f, 2.0f};

    TransmissionCogMetadata meta;
    meta.crs = "EPSG:4326";
    meta.transform = {0.01, 0.0, -1.0, 0.0, -0.01, 6.0};
    meta.aoi_slug = "test_aoi";
    meta.scale = "regional";
    meta.year = 2024;
    meta.month = 6;
    meta.day = 15;
    meta.seed = 42;
    meta.h = 2;
    meta.w = 2;
    meta.stats.total_humans = 1000.0;
    meta.stats.human_i = 100.0;
    meta.stats.human_prevalence = 0.10;

    write_transmission_cog(tif_path, grid, press, 0.01f, meta);
    write_transmission_sidecar(tif_path, meta);

    // Verify GeoTIFF
    GDALAllRegister();
    GDALDataset* ds = static_cast<GDALDataset*>(GDALOpen(tif_path.c_str(), GA_ReadOnly));
    ASSERT_NE(ds, nullptr);
    EXPECT_EQ(ds->GetRasterCount(), 4);
    EXPECT_EQ(ds->GetRasterXSize(), 2);
    EXPECT_EQ(ds->GetRasterYSize(), 2);

    for (int b = 1; b <= 4; ++b) {
        GDALRasterBand* band = ds->GetRasterBand(b);
        ASSERT_NE(band, nullptr);
        EXPECT_STREQ(band->GetDescription(), TRANSMISSION_BAND_NAMES[b - 1]);
        EXPECT_FLOAT_EQ(static_cast<float>(band->GetNoDataValue()), NODATA_SENTINEL);
    }
    GDALClose(ds);

    // Verify Sidecar JSON
    ASSERT_TRUE(std::filesystem::exists(json_path));
    std::ifstream ifs(json_path);
    nlohmann::json j;
    ifs >> j;
    EXPECT_EQ(j["aoi_slug"], "test_aoi");
    EXPECT_EQ(j["contract_version"], "2.0-transmission");
    EXPECT_EQ(j["shape"][0], 4);
    EXPECT_EQ(j["shape"][1], 2);
    EXPECT_EQ(j["shape"][2], 2);
    EXPECT_DOUBLE_EQ(j["total_human_population"], 1000.0);
    EXPECT_DOUBLE_EQ(j["mean_prevalence"], 0.10);

    // Clean up
    std::filesystem::remove_all(tmp_dir);
}

TEST(TransmissionOutput, WritesDailyTransmissionLog) {
    const std::string log_path = "/tmp/mal_abm_test_trans_log.json";

    std::vector<TransmissionDailyStats> history;
    for (int d = 1; d <= 3; ++d) {
        TransmissionDailyStats s;
        s.day = d;
        s.total_humans = 500.0;
        s.human_s = 450.0 - d * 10;
        s.human_e = 10.0 + d * 5;
        s.human_i = 40.0 + d * 5;
        s.human_r = 0.0;
        s.human_incidence = 5.0 * d;
        s.human_prevalence = s.human_i / s.total_humans;
        s.vector_s = 1000 - d * 20;
        s.vector_e = 50 + d * 10;
        s.vector_i = 20 + d * 10;
        s.vector_total = 1070;
        s.infectious_bites = 30 * d;
        s.r_eff_approx = 1.25;
        history.push_back(s);
    }

    write_transmission_log(log_path, history, 3);
    ASSERT_TRUE(std::filesystem::exists(log_path));

    std::ifstream ifs(log_path);
    nlohmann::json j;
    ifs >> j;
    EXPECT_EQ(j["n_days"], 3);
    ASSERT_TRUE(j["daily"].is_array());
    EXPECT_EQ(j["daily"].size(), 3u);
    EXPECT_EQ(j["daily"][0]["day"], 1);
    EXPECT_EQ(j["daily"][2]["day"], 3);

    std::filesystem::remove(log_path);
}

}  // namespace
}  // namespace mal_abm_fast
