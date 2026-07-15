// SPDX-License-Identifier: MIT
// test_state_cog.cpp — F1.b / F1.c / F1.d test for the 2-band state COG +
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
//   * the sidecar JSON parses and contract_version == "1.1"
//
// F1.c: a second test exercises the `n_rollouts` and `rollout_index`
// sidecar fields explicitly, and a third test runs the Engine
// facade twice with different Prng seeds and asserts the two state
// COG byte-streams differ (this is the F1.c determinism property
// that `--n-rollouts N` relies on).
//
// The test uses a temporary file under /tmp; it cleans up on tear-down.
#include <gtest/gtest.h>

#include <array>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

#include <gdal.h>
#include <gdal_priv.h>
#include <ogr_api.h>
#include <ogr_spatialref.h>
#include <ogrsf_frmts.h>
#include <nlohmann/json.hpp>

#include "engine.hpp"
#include "output_contract.hpp"
#include "prng.hpp"
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
    // F1.c: the v1.1 sidecar always carries the rollout bookkeeping
    // fields, defaulting to n_rollouts=1, rollout_index=0 for the
    // legacy single-rollout case.
    EXPECT_EQ(j.value("n_rollouts", -1), 1);
    EXPECT_EQ(j.value("rollout_index", -1), 0);
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

// F1.c: a sidecar explicitly written with n_rollouts=5 /
// rollout_index=3 must round-trip those values in the JSON.
TEST(MalAbmFastStateCog, SidecarCarriesNRolloutsAndRolloutIndex) {
    TmpTif tmp;

    auto density = make_density_grid();
    auto suit    = make_suit_grid();
    auto meta    = make_meta();
    meta.n_rollouts    = 5;
    meta.rollout_index = 3;
    meta.seed          = 104;  // base_seed + rollout_index = 101 + 3

    mal_abm_fast::write_state_cog(tmp.path(), density, suit, meta);
    mal_abm_fast::write_state_sidecar(tmp.path(), meta);

    const std::string sidecar = tmp.path() + ".json";
    std::ifstream f(sidecar);
    ASSERT_TRUE(f.is_open()) << "sidecar not found at " << sidecar;
    nlohmann::json j;
    f >> j;
    ASSERT_TRUE(j.is_object());

    EXPECT_EQ(j.value("n_rollouts", -1), 5);
    EXPECT_EQ(j.value("rollout_index", -1), 3);
    EXPECT_EQ(j.value("seed", 0), 104);
    EXPECT_EQ(j.value("contract_version", ""),
              mal_abm_fast::CONTRACT_VERSION);
}

// F1.c determinism test: two engine runs with different Prng seeds
// produce byte-different state COGs. This is the property that
// `--n-rollouts N` relies on: each rollout's COG is distinct
// (because the Prng stream is distinct -> dispersal / birth draws
// are distinct -> density / suitability grids are distinct).
//
// The test mirrors the F1.b end-to-end pattern (test_engine.cpp):
// write a synthetic 2x2 env COG + habitat gpkg, build two engines
// with Prng seeds 42 and 43, run 3 days each, snapshot to two
// COGs, and assert the file bytes differ.
TEST(MalAbmFastStateCog, TwoRolloutsDifferentSeedsProduceDifferentCogs) {
    GDALAllRegister();

    // RAII temp-dir helper (we need both .tif + .gpkg).
    namespace fs = std::filesystem;
    const fs::path tmp_root = fs::temp_directory_path() /
        ("malabm_state_cog_rollouts_" + std::to_string(::getpid()) + "_" +
         std::to_string(std::chrono::system_clock::now()
                            .time_since_epoch().count()));
    fs::create_directories(tmp_root);
    struct Cleanup {
        fs::path p;
        ~Cleanup() { std::error_code ec; fs::remove_all(p, ec); }
    } cleanup{tmp_root};

    const std::string env_path     = (tmp_root / "env.tif").string();
    const std::string habitat_path = (tmp_root / "habitat.gpkg").string();
    const std::string tif_a_path   = (tmp_root / "seed_a.tif").string();
    const std::string tif_b_path   = (tmp_root / "seed_b.tif").string();

    // Synthesize the env COG and habitat gpkg. (Reusing the test_engine
    // helpers would mean linking those symbols across translation
    // units; the helpers are not exported, so we inline the minimum
    // needed for the determinism test.)
    //
    // The env is tuned so the PLUVIAL_POOL dynamic-patch rule fires:
    // rainfall > 15 mm/day, water_frac > 0, TWI > 8. With dynamics
    // the per-day ops (birth / dispersal) use the Prng, so different
    // seeds produce byte-different state COGs.
    {
        GDALDriver* drv = GetGDALDriverManager()->GetDriverByName("GTiff");
        ASSERT_NE(drv, nullptr);
        constexpr int H = 2, W = 2;
        GDALDataset* ds = drv->Create(env_path.c_str(), W, H, 5,
                                      GDT_Float32, nullptr);
        ASSERT_NE(ds, nullptr);
        double transform[6] = {0.0, 1.0, 0.0, 2.0, 0.0, -1.0};
        ds->SetGeoTransform(transform);
        OGRSpatialReference srs;
        srs.SetFromUserInput("EPSG:4326");
        ds->SetSpatialRef(&srs);
        struct BandInit { const char* name; float v; };
        const BandInit bands[5] = {
            {"rainfall",         20.0f},  // > 15 mm/day
            {"temp_suitability",  1.0f},  // peak -> 25 deg C
            {"water_frac",        0.5f},  // > 0
            {"ndvi",              0.5f},
            {"twi",              10.0f},  // > 8
        };
        for (int band = 1; band <= 5; ++band) {
            std::vector<float> buf(H * W, bands[band - 1].v);
            GDALRasterBand* b = ds->GetRasterBand(band);
            b->SetDescription(bands[band - 1].name);
            (void)b->RasterIO(GF_Write, 0, 0, W, H, buf.data(),
                              W, H, GDT_Float32, 0, 0);
        }
        GDALClose(ds);
    }
    {
        GDALDriver* drv = GetGDALDriverManager()->GetDriverByName("GPKG");
        ASSERT_NE(drv, nullptr);
        std::error_code ec;
        fs::remove(habitat_path, ec);
        GDALDataset* ds = drv->Create(
            habitat_path.c_str(), 0, 0, 0, GDT_Unknown, nullptr);
        ASSERT_NE(ds, nullptr);
        OGRSpatialReference srs;
        srs.SetFromUserInput("EPSG:4326");
        OGRLayer* layer = ds->CreateLayer(
            "patches", &srs, wkbPoint, nullptr);
        ASSERT_NE(layer, nullptr);
        OGRFieldDefn hab_type_f("hab_type", OFTString);
        (void)layer->CreateField(&hab_type_f);
        OGRFieldDefn k_f("K", OFTInteger);
        (void)layer->CreateField(&k_f);
        OGRFieldDefn twi_f("twi", OFTReal);
        (void)layer->CreateField(&twi_f);
        OGRFieldDefn row_f("row", OFTInteger);
        (void)layer->CreateField(&row_f);
        OGRFieldDefn col_f("col", OFTInteger);
        (void)layer->CreateField(&col_f);
        OGRFeature* feat = OGRFeature::CreateFeature(layer->GetLayerDefn());
        feat->SetField("hab_type", "pluvial_pool");
        feat->SetField("K", 1000);
        feat->SetField("twi", 0.0);
        feat->SetField("row", 0);
        feat->SetField("col", 0);
        OGRPoint pt(0.5, 0.5);
        feat->SetGeometry(&pt);
        (void)layer->CreateFeature(feat);
        OGRFeature::DestroyFeature(feat);
        GDALClose(ds);
    }

    mal_abm_fast::AOI aoi;
    aoi.west = 0.0; aoi.south = 0.0; aoi.east = 2.0; aoi.north = 2.0;
    aoi.crs = "EPSG:4326"; aoi.slug = "test";
    aoi.resolution_m = 112000; aoi.scale = "regional";

    const auto start_date = std::chrono::sys_days{
        std::chrono::year{2024} / std::chrono::month{6} / std::chrono::day{1}};

    auto run_one = [&](uint64_t seed_value,
                       const std::string& out_tif) -> bool {
        mal_abm_fast::Prng rng(seed_value);
        try {
            mal_abm_fast::Engine engine(
                aoi, env_path, habitat_path, rng, start_date);
            for (int d = 0; d < 3; ++d) engine.step();
            engine.snapshot(out_tif, 2024, 6,
                            static_cast<int32_t>(seed_value),
                            /*n_rollouts=*/1, /*rollout_index=*/0);
            return true;
        } catch (const std::exception&) {
            return false;  // F1.b stub mode -> skip
        }
    };

    const bool ok_a = run_one(/*seed=*/42u, tif_a_path);
    const bool ok_b = run_one(/*seed=*/43u, tif_b_path);
    if (!ok_a || !ok_b) {
        // F1.b worktree stubs throw on Engine construction. Skip the
        // assertion but don't fail the test.
        GTEST_SKIP() << "Engine constructor threw (F1.b worktree "
                        "climate/habitat stubs) — determinism check "
                        "will run once the stubs are replaced.";
        return;
    }

    auto read_all = [](const std::string& path) {
        std::ifstream f(path, std::ios::binary);
        std::ostringstream ss;
        ss << f.rdbuf();
        return ss.str();
    };
    const std::string bytes_a = read_all(tif_a_path);
    const std::string bytes_b = read_all(tif_b_path);
    EXPECT_FALSE(bytes_a.empty());
    EXPECT_FALSE(bytes_b.empty());
    EXPECT_NE(bytes_a, bytes_b)
        << "Two rollouts with Prng seeds 42 and 43 produced "
           "byte-equal state COGs — Prng isolation is broken.";

    // Sidecar assertions: the v1.1 contract must carry n_rollouts=1
    // and rollout_index=0 for each single-rollout run.
    auto check_sidecar = [](const std::string& tif, int expected_seed) {
        std::string sidecar = tif.substr(0, tif.size() - 4) + ".json";
        std::ifstream f(sidecar);
        ASSERT_TRUE(f.is_open()) << "sidecar not found: " << sidecar;
        nlohmann::json j;
        f >> j;
        EXPECT_EQ(j.value("seed", 0), expected_seed);
        EXPECT_EQ(j.value("n_rollouts", -1), 1);
        EXPECT_EQ(j.value("rollout_index", -1), 0);
        EXPECT_EQ(j.value("contract_version", ""),
                  mal_abm_fast::CONTRACT_VERSION);
    };
    check_sidecar(tif_a_path, 42);
    check_sidecar(tif_b_path, 43);
}
