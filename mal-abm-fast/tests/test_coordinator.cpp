// SPDX-License-Identifier: MIT
// test_coordinator.cpp — GoogleTest for mal_abm_fast CoordinatorModel (F1.b).
//
// Exercises the full per-day orchestrator (activate_patches → to_dataframe
// → sub.advance_day → aggregate_density → suitability_grid → write_state_cog)
// against default-constructed engines (the cross-module IO is stubbed
// in the F1.b worktree; the integration step pulls in the real
// implementations).
#include <gtest/gtest.h>

#include <chrono>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <string>
#include <utility>
#include <vector>

#include <gdal.h>
#include <gdal_priv.h>
#include <cpl_string.h>
#include <ogr_api.h>
#include <ogr_srs_api.h>
#include <ogrsf_frmts.h>
#include <netcdf.h>

#include "aoi.hpp"
#include "climate.hpp"
#include "coordinator.hpp"
#include "habitat_engine.hpp"
#include "mosquito_submodel.hpp"
#include "output_contract.hpp"
#include "wire.hpp"

namespace {

mal_abm_fast::AOI make_aoi_4x4() {
    // (0.04 deg x 0.04 deg) at 1000m → cells_per_side() = 5 with the
    // WGS84 constant + ceil rounding (matches the Python AOI). The
    // helper is named "make_aoi_4x4" for historical reasons; the
    // assertion in Aoi4x4 below expects 5, the W and H of the grid.
    mal_abm_fast::AOI aoi;
    aoi.west = 0.0;
    aoi.east = 0.04;
    aoi.south = 0.0;
    aoi.north = 0.04;
    aoi.crs = "EPSG:4326";
    aoi.slug = "test-aoi";
    aoi.resolution_m = 1000;
    aoi.scale = "regional";
    return aoi;
}

std::string temp_dir(const std::string& tag) {
    const std::filesystem::path p =
        std::filesystem::temp_directory_path() /
        ("mal_abm_fast_test_" + tag);
    std::filesystem::create_directories(p);
    return p.string();
}

std::chrono::sys_days make_date(int year, unsigned month, unsigned day) {
    return std::chrono::sys_days{std::chrono::year_month_day{
        std::chrono::year{year},
        std::chrono::month{month},
        std::chrono::day{day}}};
}

std::string sidecar_path_for(const std::string& tif_path) {
    if (tif_path.size() > 4 &&
        tif_path.compare(tif_path.size() - 4, 4, ".tif") == 0) {
        return tif_path.substr(0, tif_path.size() - 4) + ".json";
    }
    return tif_path + ".json";
}

std::string read_file(const std::string& path) {
    std::ifstream f(path);
    std::stringstream buf;
    buf << f.rdbuf();
    return buf.str();
}

}  // namespace

TEST(MalAbmFastCoordinator, Aoi4x4) {
    using namespace mal_abm_fast;
    AOI aoi = make_aoi_4x4();
    // (0.04 deg x 0.04 deg) at 1000m → 5x5 cells (WGS84 + ceil).
    EXPECT_EQ(aoi.cells_per_side(), 5);
    EXPECT_EQ(cells_per_side_h(aoi), 5);
}

TEST(MalAbmFastCoordinator, FullDayOrchestrator) {
    using namespace mal_abm_fast;
    GDALAllRegister();  // needed for write_state_cog (GDAL GTiff driver)

    AOI aoi = make_aoi_4x4();
    EXPECT_EQ(aoi.cells_per_side(), 5);
    EXPECT_EQ(cells_per_side_h(aoi), 5);

    // Write a synthetic 4x4 env COG (rain=20, temp_suitability=1.0 [→25C],
    // water_frac=0.5, ndvi=0.5) and load it.
    const std::string env_path = temp_dir("coordinator_env") + "/env.tif";
    {
        std::filesystem::create_directories(std::filesystem::path(env_path).parent_path());
        GDALDriver* drv = GetGDALDriverManager()->GetDriverByName("GTiff");
        ASSERT_NE(drv, nullptr);
        GDALDataset* ds = drv->Create(env_path.c_str(), 4, 4, 4, GDT_Float32, nullptr);
        ASSERT_NE(ds, nullptr);
        std::vector<float> band(16, 0.0f);
        std::fill(band.begin(), band.end(), 0.5f);  // water_frac + ndvi
        ds->GetRasterBand(1)->SetDescription("water_frac");
        ds->GetRasterBand(1)->RasterIO(GF_Write, 0, 0, 4, 4, band.data(), 4, 4, GDT_Float32, 0, 0);
        std::fill(band.begin(), band.end(), 20.0f);  // rainfall
        ds->GetRasterBand(2)->SetDescription("rainfall");
        ds->GetRasterBand(2)->RasterIO(GF_Write, 0, 0, 4, 4, band.data(), 4, 4, GDT_Float32, 0, 0);
        std::fill(band.begin(), band.end(), 1.0f);  // temp_suitability (peak Mordecai → 25C)
        ds->GetRasterBand(3)->SetDescription("temp_suitability");
        ds->GetRasterBand(3)->RasterIO(GF_Write, 0, 0, 4, 4, band.data(), 4, 4, GDT_Float32, 0, 0);
        std::fill(band.begin(), band.end(), 0.5f);  // ndvi
        ds->GetRasterBand(4)->SetDescription("ndvi");
        ds->GetRasterBand(4)->RasterIO(GF_Write, 0, 0, 4, 4, band.data(), 4, 4, GDT_Float32, 0, 0);
        // Set the affine transform from the AOI bbox.
        double affine[6] = {0.01, 0.0, 0.0, 0.0, -0.01, 0.04};
        ds->SetGeoTransform(affine);
        OGRSpatialReference srs; srs.SetFromUserInput("EPSG:4326");
        ds->SetSpatialRef(&srs);
        GDALClose(ds);
    }
    ClimateEngine climate;
    climate.load_from_env_tif(env_path, aoi);

    // Write a synthetic 1-row habitat gpkg at (row=2, col=2) and load it.
    const std::string hab_path = temp_dir("coordinator_hab") + "/hab.gpkg";
    {
        std::filesystem::create_directories(std::filesystem::path(hab_path).parent_path());
        GDALDriver* drv = GetGDALDriverManager()->GetDriverByName("GPKG");
        ASSERT_NE(drv, nullptr);
        GDALDataset* ds = drv->Create(hab_path.c_str(), 0, 0, 0, GDT_Unknown, nullptr);
        ASSERT_NE(ds, nullptr);
        OGRLayer* lyr = ds->CreateLayer("habitat", ds->GetSpatialRef(), wkbPoint, nullptr);
        ASSERT_NE(lyr, nullptr);
        OGRFieldDefn hab_type("hab_type", OFTString);
        lyr->CreateField(&hab_type);
        OGRFieldDefn k("K", OFTInteger);
        lyr->CreateField(&k);
        OGRFieldDefn twi("twi_value", OFTReal);
        lyr->CreateField(&twi);
        OGRFieldDefn row("row", OFTInteger);
        lyr->CreateField(&row);
        OGRFieldDefn col("col", OFTInteger);
        lyr->CreateField(&col);
        OGRFeature* f = OGRFeature::CreateFeature(lyr->GetLayerDefn());
        f->SetField("hab_type", "pluvial_pool");
        f->SetField("K", 1000);
        f->SetField("twi_value", 9.0);
        f->SetField("row", 2);
        f->SetField("col", 2);
        OGRPoint pt(0.02, 0.02);  // centre of (2, 2) at 0.04 deg / 4 cells
        f->SetGeometry(&pt);
        lyr->CreateFeature(f);
        OGRFeature::DestroyFeature(f);
        GDALClose(ds);
    }
    HabitatEngine habitat;
    habitat.load_from_gpkg(hab_path, aoi);
    ASSERT_EQ(habitat.patches().size(), 1u);

    // Submodel with 1 patch, 30% of K seeded = 300 larvae.
    MosquitoSubmodel sub(
        /*n_patches=*/1,
        /*k_per_patch=*/K_PER_PATCH_DEFAULT,
        /*init_frac=*/INIT_FRAC,
        /*seed=*/uint64_t{42});
    ASSERT_EQ(sub.total_agents(), 300);

    CoordinatorModel coord(
        std::move(aoi), std::move(climate), std::move(habitat),
        /*seed=*/int32_t{1}, make_date(2024, 1, 1));

    coord.activate_patches();
    auto states = coord.to_dataframe();
    EXPECT_FALSE(states.empty());

    sub.advance_day(coord.aoi(), states);

    auto density = coord.aggregate_density(sub, K_MAX);
    EXPECT_GT(density.h, 0);
    EXPECT_GT(density.w, 0);
    EXPECT_EQ(density.data.size(),
              static_cast<size_t>(density.h) * static_cast<size_t>(density.w));

    auto suit = coord.suitability_grid(sub, K_MAX);
    EXPECT_GT(suit.h, 0);
    EXPECT_GT(suit.w, 0);
    EXPECT_EQ(suit.data.size(),
              static_cast<size_t>(suit.h) * static_cast<size_t>(suit.w));

    const std::string out_dir = temp_dir("coordinator_full_day");
    const std::string tif_path = out_dir + "/state.tif";
    const std::string sidecar = sidecar_path_for(tif_path);

    const std::string returned = coord.write_state_cog(
        tif_path, density, suit,
        /*year=*/2024, /*month=*/6, /*seed=*/1);
    EXPECT_EQ(returned, tif_path);
    EXPECT_TRUE(std::filesystem::exists(tif_path));
    EXPECT_TRUE(std::filesystem::exists(sidecar));

    const std::string body = read_file(sidecar);
    ASSERT_FALSE(body.empty());
    EXPECT_EQ(body.front(), '{');

    std::filesystem::remove_all(out_dir);
}

TEST(MalAbmFastCoordinator, WriteStateCogReturnsPathAndCreatesSidecar) {
    using namespace mal_abm_fast;
    GDALAllRegister();  // needed for write_state_cog (GDAL GTiff driver)

    AOI aoi = make_aoi_4x4();
    ClimateEngine climate;
    HabitatEngine habitat;
    CoordinatorModel coord(
        std::move(aoi), std::move(climate), std::move(habitat),
        /*seed=*/int32_t{7}, make_date(2024, 1, 1));

    DensityGrid density;
    density.h = 5;
    density.w = 5;
    density.data.assign(static_cast<size_t>(25), 0.0f);

    SuitabilityGrid suit;
    suit.h = 5;
    suit.w = 5;
    suit.data.assign(static_cast<size_t>(25), 0.0f);

    const std::string out_dir = temp_dir("write_state");
    const std::string tif_path = out_dir + "/state.tif";
    const std::string sidecar = sidecar_path_for(tif_path);

    const std::string returned = coord.write_state_cog(
        tif_path, density, suit,
        /*year=*/2024, /*month=*/6, /*seed=*/7);
    EXPECT_EQ(returned, tif_path);
    EXPECT_TRUE(std::filesystem::exists(tif_path));
    EXPECT_TRUE(std::filesystem::exists(sidecar));

    const std::string body = read_file(sidecar);
    ASSERT_FALSE(body.empty());
    EXPECT_EQ(body.front(), '{');

    std::filesystem::remove_all(out_dir);
}

// -- Daily NetCDF coordinator test (daily-env-netcdf feature) -----------------

namespace {

std::filesystem::path MakeTmpEnvNC() {
    const char* base = std::getenv("TMPDIR");
    std::filesystem::path dir =
        (base && *base) ? std::filesystem::path(base)
                        : std::filesystem::temp_directory_path();
    return dir / "mal_abm_fast_test_coordinator.nc";
}

void WriteSyntheticEnvNC(const std::filesystem::path& path, int n_days,
                         int h = 4, int w = 4) {
    int ncid, dimids[3], vid[4];
    int dimid_time, dimid_y, dimid_x;

    ASSERT_EQ(nc_create(path.string().c_str(),
                        NC_CLOBBER | NC_NETCDF4, &ncid), NC_NOERR);
    ASSERT_EQ(nc_def_dim(ncid, "time", NC_UNLIMITED, &dimid_time), NC_NOERR);
    ASSERT_EQ(nc_def_dim(ncid, "y", h, &dimid_y), NC_NOERR);
    ASSERT_EQ(nc_def_dim(ncid, "x", w, &dimid_x), NC_NOERR);
    dimids[0] = dimid_time; dimids[1] = dimid_y; dimids[2] = dimid_x;

    ASSERT_EQ(nc_def_var(ncid, "rainfall", NC_FLOAT, 3, dimids, &vid[0]), NC_NOERR);
    ASSERT_EQ(nc_def_var(ncid, "water_temp_c", NC_FLOAT, 3, dimids, &vid[1]), NC_NOERR);
    ASSERT_EQ(nc_def_var(ncid, "water_frac", NC_FLOAT, 3, dimids, &vid[2]), NC_NOERR);
    ASSERT_EQ(nc_def_var(ncid, "ndvi", NC_FLOAT, 3, dimids, &vid[3]), NC_NOERR);
    ASSERT_EQ(nc_put_att_text(ncid, NC_GLOBAL, "Conventions", 6, "CF-1.8"), NC_NOERR);
    ASSERT_EQ(nc_enddef(ncid), NC_NOERR);

    // Day 0: rain=20 (>15 threshold), Day 1: rain=5 (<15)
    const float rain_vals[] = {20.0f, 5.0f};
    const float temp_vals[] = {25.0f, 20.0f};
    std::vector<float> buf(h * w);
    size_t start[3] = {0, 0, 0};
    size_t count[3] = {1, static_cast<size_t>(h), static_cast<size_t>(w)};

    for (int d = 0; d < n_days; ++d) {
        start[0] = d;
        std::fill(buf.begin(), buf.end(), rain_vals[d % 2]);
        ASSERT_EQ(nc_put_vara_float(ncid, vid[0], start, count, buf.data()), NC_NOERR);
        std::fill(buf.begin(), buf.end(), temp_vals[d % 2]);
        ASSERT_EQ(nc_put_vara_float(ncid, vid[1], start, count, buf.data()), NC_NOERR);
        std::fill(buf.begin(), buf.end(), 0.5f);
        ASSERT_EQ(nc_put_vara_float(ncid, vid[2], start, count, buf.data()), NC_NOERR);
        std::fill(buf.begin(), buf.end(), 0.4f);
        ASSERT_EQ(nc_put_vara_float(ncid, vid[3], start, count, buf.data()), NC_NOERR);
    }
    ASSERT_EQ(nc_close(ncid), NC_NOERR);
}

}  // namespace

TEST(CoordinatorModel, PatchActivationTogglesDaily) {
    using namespace mal_abm_fast;
    GDALAllRegister();

    const auto nc_path = MakeTmpEnvNC();
    if (std::filesystem::exists(nc_path)) std::filesystem::remove(nc_path);
    WriteSyntheticEnvNC(nc_path, 2);

    AOI aoi = make_aoi_4x4();
    ClimateEngine climate;
    climate.load_from_env_nc(nc_path.string(), aoi);
    ASSERT_EQ(climate.n_days(), 2);

    // Write a synthetic habitat gpkg at (row=2, col=2)
    const std::string hab_path = temp_dir("coordinator_daily_hab") + "/hab.gpkg";
    {
        std::filesystem::create_directories(
            std::filesystem::path(hab_path).parent_path());
        GDALDriver* drv = GetGDALDriverManager()->GetDriverByName("GPKG");
        ASSERT_NE(drv, nullptr);
        GDALDataset* ds = drv->Create(hab_path.c_str(), 0, 0, 0, GDT_Unknown, nullptr);
        ASSERT_NE(ds, nullptr);
        OGRLayer* lyr = ds->CreateLayer("habitat", ds->GetSpatialRef(), wkbPoint, nullptr);
        ASSERT_NE(lyr, nullptr);
        OGRFieldDefn hab_type("hab_type", OFTString);
        lyr->CreateField(&hab_type);
        OGRFieldDefn k("K", OFTInteger);
        lyr->CreateField(&k);
        OGRFieldDefn twi("twi_value", OFTReal);
        lyr->CreateField(&twi);
        OGRFieldDefn row("row", OFTInteger);
        lyr->CreateField(&row);
        OGRFieldDefn col("col", OFTInteger);
        lyr->CreateField(&col);
        OGRFeature* f = OGRFeature::CreateFeature(lyr->GetLayerDefn());
        f->SetField("hab_type", "pluvial_pool");
        f->SetField("K", 1000);
        f->SetField("twi_value", 9.0);
        f->SetField("row", 2);
        f->SetField("col", 2);
        OGRPoint pt(0.02, 0.02);
        f->SetGeometry(&pt);
        lyr->CreateFeature(f);
        OGRFeature::DestroyFeature(f);
        GDALClose(ds);
    }
    HabitatEngine habitat;
    habitat.load_from_gpkg(hab_path, aoi);
    ASSERT_EQ(habitat.patches().size(), 1u);

    MosquitoSubmodel sub(
        /*n_patches=*/1,
        /*k_per_patch=*/K_PER_PATCH_DEFAULT,
        /*init_frac=*/INIT_FRAC,
        /*seed=*/uint64_t{42});

    // Day 0: rain=20 (>15 threshold) -> patches should be active
    climate.set_day(0);
    CoordinatorModel coord0(
        std::move(aoi), std::move(climate), std::move(habitat),
        /*seed=*/int32_t{1}, make_date(2024, 1, 1));

    coord0.activate_patches();
    auto states0 = coord0.to_dataframe();
    EXPECT_FALSE(states0.empty()) << "Day 0: patches should be active (rain=20)";

    // Verify patch has rain > threshold
    for (const auto& s : states0) {
        EXPECT_GT(s.rain_d, PLUVIAL_POOL_RAIN_THRESHOLD_MM);
    }

    std::filesystem::remove(nc_path);
    std::filesystem::remove_all(temp_dir("coordinator_daily_hab"));
}
