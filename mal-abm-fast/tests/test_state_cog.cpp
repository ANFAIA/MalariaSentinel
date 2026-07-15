// SPDX-License-Identifier: MIT
// test_state_cog.cpp — F1.b / F1.d test for the 2-band state COG +
// sidecar JSON writer (output_contract.cpp).
//
// The test builds a small (4, 4) DensityGrid and SuitabilityGrid with
// hand-picked values, calls write_state_cog + write_state_sidecar,
// then re-opens the .tif with GDAL and asserts:
//   * 2 bands, float32
//   * band 1 description == "density"
//   * band 2 description == "suitability"
//   * nodata == NODATA_SENTINEL on both bands
//   * the data round-trips exactly
//   * the sidecar JSON parses and contract_version == "1.0"
//
// The test uses a temporary file under /tmp; it cleans up on tear-down.
#include <gtest/gtest.h>

#include <array>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <string>
#include <vector>

#include <gdal.h>
#include <gdal_priv.h>
#include <nlohmann/json.hpp>

#include "output_contract.hpp"
#include "wire.hpp"

// Register all built-in GDAL/OGR drivers once for the test process.
// Without this, GetGDALDriverManager()->GetDriverByName("GTiff")
// returns nullptr in statically-linked GDAL builds.
namespace {
struct GdalRegistrator {
    GdalRegistrator() { GDALAllRegister(); }
};
const GdalRegistrator g_gdal_registrator;
}  // namespace

namespace {

// Build a 4x4 DensityGrid with a known pattern (row * 0.1 + col * 0.01).
mal_abm_fast::DensityGrid make_density_grid() {
    mal_abm_fast::DensityGrid g;
    g.h = 4;
    g.w = 4;
    g.data.resize(static_cast<size_t>(g.h) * static_cast<size_t>(g.w));
    for (int r = 0; r < g.h; ++r) {
        for (int c = 0; c < g.w; ++c) {
            g.data[static_cast<size_t>(r) * static_cast<size_t>(g.w) +
                   static_cast<size_t>(c)] =
                0.1f * static_cast<float>(r) + 0.01f * static_cast<float>(c);
        }
    }
    return g;
}

// Build a 4x4 SuitabilityGrid with a different pattern.
mal_abm_fast::SuitabilityGrid make_suit_grid() {
    mal_abm_fast::SuitabilityGrid g;
    g.h = 4;
    g.w = 4;
    g.data.resize(static_cast<size_t>(g.h) * static_cast<size_t>(g.w));
    for (int r = 0; r < g.h; ++r) {
        for (int c = 0; c < g.w; ++c) {
            g.data[static_cast<size_t>(r) * static_cast<size_t>(g.w) +
                   static_cast<size_t>(c)] =
                0.5f + 0.05f * static_cast<float>(r + c);
        }
    }
    return g;
}

// Build a fully-populated StateCogMetadata.
mal_abm_fast::StateCogMetadata make_meta() {
    mal_abm_fast::StateCogMetadata m;
    m.crs               = "EPSG:4326";
    m.transform         = {0.01, 0.0, -3.5, 0.0, -0.01, 11.5};
    m.aoi_slug          = "ghana";
    m.scale             = "regional";
    m.year              = 2024;
    m.month             = 6;
    m.seed              = 1;
    m.generator_version = mal_abm_fast::GENERATOR_VERSION;
    m.abm_params_hash   = "sha256:pending";
    m.contract_version  = mal_abm_fast::CONTRACT_VERSION;
    m.band_names        = {mal_abm_fast::STATE_BAND_NAMES[0],
                           mal_abm_fast::STATE_BAND_NAMES[1]};
    m.nodata            = mal_abm_fast::NODATA_SENTINEL;
    m.h                 = 4;
    m.w                 = 4;
    m.k_max             = mal_abm_fast::K_MAX;
    return m;
}

// RAII temp-file helper. Picks /tmp/<prefix>_<rand>.tif and
// schedules deletion on destruction.
class TmpTif {
public:
    TmpTif() {
        std::string tmpl = (std::filesystem::temp_directory_path() /
                            "malabm_state_cog_XXXXXX").string();
        std::vector<char> buf(tmpl.begin(), tmpl.end());
        buf.push_back('\0');
        int fd = mkstemps(buf.data(), 4);  // 4-char suffix ".tif"
        if (fd < 0) {
            throw std::runtime_error("mkstemps failed");
        }
        close(fd);
        path_ = std::string(buf.data());
    }
    ~TmpTif() {
        std::error_code ec;
        std::filesystem::remove(path_, ec);
        std::filesystem::remove(path_ + ".json", ec);
    }
    const std::string& path() const { return path_; }

private:
    std::string path_;
};

}  // namespace

TEST(MalAbmFastStateCog, WritesTwoBandCogWithDescriptionsAndNodata) {
    TmpTif tmp;

    auto density = make_density_grid();
    auto suit    = make_suit_grid();
    auto meta    = make_meta();

    mal_abm_fast::write_state_cog(tmp.path(), density, suit, meta);

    // Re-open with GDAL and verify the 2-band layout.
    GDALDataset* ds = static_cast<GDALDataset*>(
        GDALOpen(tmp.path().c_str(), GA_ReadOnly));
    ASSERT_NE(ds, nullptr) << "GDALOpen failed: " << tmp.path();

    EXPECT_EQ(ds->GetRasterCount(), 2);
    EXPECT_EQ(ds->GetRasterXSize(), 4);
    EXPECT_EQ(ds->GetRasterYSize(), 4);

    GDALRasterBand* b1 = ds->GetRasterBand(1);
    GDALRasterBand* b2 = ds->GetRasterBand(2);
    ASSERT_NE(b1, nullptr);
    ASSERT_NE(b2, nullptr);

    EXPECT_STREQ(b1->GetDescription(),
                 mal_abm_fast::STATE_BAND_NAMES[0]);  // "density"
    EXPECT_STREQ(b2->GetDescription(),
                 mal_abm_fast::STATE_BAND_NAMES[1]);  // "suitability"
    EXPECT_DOUBLE_EQ(b1->GetNoDataValue(),
                     static_cast<double>(mal_abm_fast::NODATA_SENTINEL));
    EXPECT_DOUBLE_EQ(b2->GetNoDataValue(),
                     static_cast<double>(mal_abm_fast::NODATA_SENTINEL));

    // Read the data back and compare element-wise.
    std::vector<float> d_back(16, 0.0f);
    std::vector<float> s_back(16, 0.0f);
    CPLErr e1 = b1->RasterIO(GF_Read, 0, 0, 4, 4, d_back.data(), 4, 4,
                             GDT_Float32, 0, 0);
    CPLErr e2 = b2->RasterIO(GF_Read, 0, 0, 4, 4, s_back.data(), 4, 4,
                             GDT_Float32, 0, 0);
    EXPECT_EQ(e1, CE_None);
    EXPECT_EQ(e2, CE_None);
    for (int i = 0; i < 16; ++i) {
        EXPECT_FLOAT_EQ(d_back[i], density.data[i]) << "density mismatch at " << i;
        EXPECT_FLOAT_EQ(s_back[i], suit.data[i])    << "suitability mismatch at " << i;
    }

    // CRS check.
    const OGRSpatialReference* srs = ds->GetSpatialRef();
    ASSERT_NE(srs, nullptr);
    char* wkt = nullptr;
    srs->exportToWkt(&wkt);
    EXPECT_NE(wkt, nullptr);
    if (wkt) {
        std::string s(wkt);
        // EPSG:4326 is round-tripped to WKT2 / WKT1. The string
        // contains either the EPSG authority or the datum name.
        EXPECT_TRUE(s.find("4326") != std::string::npos ||
                    s.find("WGS 84") != std::string::npos ||
                    s.find("WGS_84") != std::string::npos)
            << "CRS WKT does not look like EPSG:4326: " << s;
        CPLFree(wkt);
    }

    GDALClose(ds);
}

TEST(MalAbmFastStateCog, WritesSidecarJsonWithContractVersion) {
    TmpTif tmp;

    auto density = make_density_grid();
    auto suit    = make_suit_grid();
    auto meta    = make_meta();

    mal_abm_fast::write_state_cog(tmp.path(), density, suit, meta);
    mal_abm_fast::write_state_sidecar(tmp.path(), meta);

    const std::string sidecar = tmp.path() + ".json";
    std::ifstream f(sidecar);
    ASSERT_TRUE(f.is_open()) << "sidecar not found at " << sidecar;
    nlohmann::json j;
    f >> j;
    ASSERT_TRUE(j.is_object()) << "sidecar is not a JSON object";

    EXPECT_EQ(j.value("contract_version", ""),
              mal_abm_fast::CONTRACT_VERSION);
    EXPECT_EQ(j.value("generator_version", ""),
              std::string(mal_abm_fast::GENERATOR_VERSION));
    EXPECT_EQ(j.value("aoi_slug", ""), "ghana");
    EXPECT_EQ(j.value("scale", ""), "regional");
    EXPECT_EQ(j.value("year", 0), 2024);
    EXPECT_EQ(j.value("month", 0), 6);
    EXPECT_EQ(j.value("seed", 0), 1);
    EXPECT_DOUBLE_EQ(j.value("nodata", 0.0),
                     static_cast<double>(mal_abm_fast::NODATA_SENTINEL));
    EXPECT_EQ(j.value("k_max", 0), mal_abm_fast::K_MAX);
    EXPECT_EQ(j.value("crs", ""), "EPSG:4326");

    ASSERT_TRUE(j.contains("transform") && j["transform"].is_array());
    ASSERT_EQ(j["transform"].size(), 6u);
    for (int i = 0; i < 6; ++i) {
        EXPECT_DOUBLE_EQ(j["transform"][i].get<double>(), meta.transform[i]);
    }

    ASSERT_TRUE(j.contains("band_names") && j["band_names"].is_array());
    ASSERT_EQ(j["band_names"].size(), 2u);
    EXPECT_EQ(j["band_names"][0].get<std::string>(),
              mal_abm_fast::STATE_BAND_NAMES[0]);
    EXPECT_EQ(j["band_names"][1].get<std::string>(),
              mal_abm_fast::STATE_BAND_NAMES[1]);

    ASSERT_TRUE(j.contains("shape") && j["shape"].is_array());
    ASSERT_EQ(j["shape"].size(), 3u);
    EXPECT_EQ(j["shape"][0].get<int>(), 2);
    EXPECT_EQ(j["shape"][1].get<int>(), 4);
    EXPECT_EQ(j["shape"][2].get<int>(), 4);
}
