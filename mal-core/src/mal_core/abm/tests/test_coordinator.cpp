// SPDX-License-Identifier: MIT
// test_coordinator.cpp — GoogleTest for mal_abm_fast CoordinatorModel
// (contract v3.0).
//
// Exercises the per-day orchestrator (update_habitat_day → to_dataframe →
// sub.advance_day → aggregate_density → write_state_cog) plus the
// candidate floor, the pluvial daily toggle and the salinity gate.
#include <gtest/gtest.h>

#include <algorithm>
#include <chrono>
#include <cmath>
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
#include "habitat_availability.hpp"
#include "mosquito_submodel.hpp"
#include "output_contract.hpp"
#include "wire.hpp"

namespace {

mal_abm_fast::AOI make_aoi_4x4() {
    // (0.04 deg x 0.04 deg) at 1000m → cells_per_side() = 5 with the
    // WGS84 constant + ceil rounding (matches the Python AOI).
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

std::filesystem::path MakeTmpEnvNC() {
    // Review-a3 item 10 (flaky fix): gtest_discover_tests runs each TEST
    // as its own ctest PROCESS, and WriteSyntheticEnvNC ASSERTs a fixed
    // filename below — two CoordinatorModel tests in parallel both open
    // the same path and one loses (nc_create EEXIST / half-written). The
    // filename is now unique per process (pid) so isolated test runs
    // don't share the file.
    const char* base = std::getenv("TMPDIR");
    std::filesystem::path dir =
        (base && *base) ? std::filesystem::path(base)
                        : std::filesystem::temp_directory_path();
    return dir / ("mal_abm_fast_test_coordinator_" +
                  std::to_string(static_cast<long>(::getpid())) + ".nc");
}

// Contract v3.0 env NC: rainfall + air_temp_c daily, the five static
// habitat planes, optional daily salinity. Rain pattern 60/40 mm.
void WriteSyntheticEnvNC(const std::filesystem::path& path, int n_days,
                         int h = 4, int w = 4,
                         const std::vector<float>& sal_vals = {}) {
    int ncid, dimids[3], vid[2], vidsal;
    int dimid_time, dimid_y, dimid_x;

    ASSERT_EQ(nc_create(path.string().c_str(),
                        NC_CLOBBER | NC_NETCDF4, &ncid), NC_NOERR);
    ASSERT_EQ(nc_def_dim(ncid, "time", NC_UNLIMITED, &dimid_time), NC_NOERR);
    ASSERT_EQ(nc_def_dim(ncid, "y", h, &dimid_y), NC_NOERR);
    ASSERT_EQ(nc_def_dim(ncid, "x", w, &dimid_x), NC_NOERR);
    dimids[0] = dimid_time; dimids[1] = dimid_y; dimids[2] = dimid_x;

    ASSERT_EQ(nc_def_var(ncid, "rainfall", NC_FLOAT, 3, dimids, &vid[0]), NC_NOERR);
    ASSERT_EQ(nc_def_var(ncid, "air_temp_c", NC_FLOAT, 3, dimids, &vid[1]), NC_NOERR);
    const bool with_salinity = !sal_vals.empty();
    if (with_salinity) {
        ASSERT_EQ(nc_def_var(ncid, "salinity_ppt", NC_FLOAT, 3, dimids, &vidsal), NC_NOERR);
    }
    ASSERT_EQ(nc_put_att_text(ncid, NC_GLOBAL, "Conventions", 6, "CF-1.8"), NC_NOERR);

    // Static habitat planes (2-D): a wetland-heavy cell so candidates exist.
    auto def_static = [&](const char* name, float value) {
        int dids[2] = {dimid_y, dimid_x};
        int varid = -1;
        ASSERT_EQ(nc_def_var(ncid, name, NC_FLOAT, 2, dids, &varid), NC_NOERR);
        ASSERT_EQ(nc_enddef(ncid), NC_NOERR);
        std::vector<float> plane(static_cast<size_t>(h) * w, value);
        ASSERT_EQ(nc_put_var_float(ncid, varid, plane.data()), NC_NOERR);
        ASSERT_EQ(nc_redef(ncid), NC_NOERR);
    };
    def_static("jrc_persistent",      0.2f);
    def_static("lc_built",            0.0f);
    def_static("lc_wetland",          0.3f);
    def_static("lc_open_plus_water",  0.3f);
    def_static("lc_crop",             0.0f);

    const float rain_vals[] = {60.0f, 40.0f};
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
        if (with_salinity) {
            std::fill(buf.begin(), buf.end(), sal_vals[d % sal_vals.size()]);
            ASSERT_EQ(nc_put_vara_float(ncid, vidsal, start, count, buf.data()), NC_NOERR);
        }
    }
    ASSERT_EQ(nc_close(ncid), NC_NOERR);
}

// Write a single candidate habitat patch (gpkg) at (row, col).
std::string write_hab_gpkg(const std::string& tag, const mal_abm_fast::AOI& aoi,
                           int row, int col, double potential = 0.9) {
    const std::string hab_path = temp_dir(tag) + "/hab.gpkg";
    std::filesystem::create_directories(
        std::filesystem::path(hab_path).parent_path());
    GDALAllRegister();
    GDALDriver* drv = GetGDALDriverManager()->GetDriverByName("GPKG");
    EXPECT_NE(drv, nullptr);
    GDALDataset* ds = drv->Create(hab_path.c_str(), 0, 0, 0, GDT_Unknown, nullptr);
    if (ds == nullptr) return hab_path;
    OGRLayer* lyr = ds->CreateLayer("habitat", ds->GetSpatialRef(), wkbPoint, nullptr);
    if (lyr == nullptr) { GDALClose(ds); return hab_path; }
    OGRFieldDefn fpot("habitat_potential", OFTReal);
    lyr->CreateField(&fpot);
    OGRFieldDefn frow("row", OFTInteger);
    lyr->CreateField(&frow);
    OGRFieldDefn fcol("col", OFTInteger);
    lyr->CreateField(&fcol);
    OGRFeature* f = OGRFeature::CreateFeature(lyr->GetLayerDefn());
    f->SetField("habitat_potential", potential);
    f->SetField("row", row);
    f->SetField("col", col);
    OGRPoint pt(aoi.west + (col + 0.5) * (aoi.east - aoi.west) / 4,
                aoi.north - (row + 0.5) * (aoi.north - aoi.south) / 4);
    f->SetGeometry(&pt);
    lyr->CreateFeature(f);
    OGRFeature::DestroyFeature(f);
    GDALClose(ds);
    return hab_path;
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
    GDALAllRegister();

    AOI aoi = make_aoi_4x4();
    EXPECT_EQ(aoi.cells_per_side(), 5);
    EXPECT_EQ(cells_per_side_h(aoi), 5);

    const auto nc_path = MakeTmpEnvNC();
    if (std::filesystem::exists(nc_path)) std::filesystem::remove(nc_path);
    WriteSyntheticEnvNC(nc_path, 1);
    const std::string env_path = nc_path.string();
    auto climate = std::make_shared<ClimateEngine>();
    climate->load_from_env_nc(env_path, aoi);

    const std::string hab_path = write_hab_gpkg("coordinator_hab", aoi, 2, 2);
    HabitatEngine habitat;
    habitat.load_from_gpkg(hab_path, aoi);
    ASSERT_EQ(habitat.patches().size(), 1u);

    MosquitoSubmodel sub(
        /*n_patches=*/1,
        std::vector<SeedInstruction>{
            SeedInstruction{/*patch_id=*/0, /*row=*/0, /*col=*/0,
                            /*lon=*/0.0, /*lat=*/0.0,
                            /*n_adults=*/30, /*n_larvae=*/270}},
        /*seed=*/uint64_t{42});
    ASSERT_EQ(sub.total_agents(), 30);

    CoordinatorModel coord(
        std::move(aoi), climate, std::move(habitat),
        /*seed=*/int32_t{1}, make_date(2024, 1, 1));

    coord.update_habitat_day();
    auto states = coord.to_dataframe();
    EXPECT_FALSE(states.empty());

    sub.advance_day(coord.aoi(), states);

    auto density = coord.aggregate_density(sub);
    EXPECT_GT(density.h, 0);
    EXPECT_GT(density.w, 0);
    EXPECT_EQ(density.data.size(),
              static_cast<size_t>(density.h) * static_cast<size_t>(density.w));

    auto suit = coord.suitability_grid(sub);
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
    GDALAllRegister();

    AOI aoi = make_aoi_4x4();
    auto climate = std::make_shared<ClimateEngine>();
    HabitatEngine habitat;
    CoordinatorModel coord(
        std::move(aoi), climate, std::move(habitat),
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

TEST(CoordinatorModel, CandidateFloorDropsEmptyCells) {
    using namespace mal_abm_fast;
    GDALAllRegister();

    //_zero-feature gpkg: candidates must come from the static planes.
    const auto nc_path = MakeTmpEnvNC();
    if (std::filesystem::exists(nc_path)) std::filesystem::remove(nc_path);
    WriteSyntheticEnvNC(nc_path, 1);

    AOI aoi = make_aoi_4x4();
    auto climate = std::make_shared<ClimateEngine>();
    climate->load_from_env_nc(nc_path.string(), aoi);

    HabitatEngine habitat;  // empty gpkg — the union comes from statics
    CoordinatorModel coord(
        std::move(aoi), climate, std::move(habitat),
        /*seed=*/int32_t{1}, make_date(2024, 1, 1));

    coord.update_habitat_day();
    auto states = coord.to_dataframe();
    // Static planes sum: 0.8 >= candidate floor → every grid cell
    // (4x4 = 16) is a candidate.
    EXPECT_EQ(states.size(), 16u);
    for (const auto& s : states) {
        EXPECT_GT(s.habitat_avail, 0.0f);
        EXPECT_GT(s.k_habitat, 0.0f);
        EXPECT_STREQ(species_name(SpeciesId::COLUZZII), "coluzzii");
    }
    std::filesystem::remove(nc_path);
}

TEST(CoordinatorModel, PatchAccuracyTogglesWithRain) {
    using namespace mal_abm_fast;
    GDALAllRegister();

    const auto nc_path = MakeTmpEnvNC();
    if (std::filesystem::exists(nc_path)) std::filesystem::remove(nc_path);
    WriteSyntheticEnvNC(nc_path, 2);

    AOI aoi = make_aoi_4x4();
    auto climate = std::make_shared<ClimateEngine>();
    climate->load_from_env_nc(nc_path.string(), aoi);
    ASSERT_EQ(climate->n_days(), 2);

    const std::string hab_path = write_hab_gpkg("coordinator_daily_hab",
                                                aoi, 2, 2);
    HabitatEngine habitat;
    habitat.load_from_gpkg(hab_path, aoi);
    ASSERT_EQ(habitat.patches().size(), 1u);

    CoordinatorModel coord0(
        std::move(aoi), climate, std::move(habitat),
        /*seed=*/int32_t{1}, make_date(2024, 1, 1));

    // Day 0: heavy rain raises z; both days remain biologically active
    // via the static persistent planes.
    climate->set_day(0);
    coord0.update_habitat_day();
    auto states0 = coord0.to_dataframe();
    bool saw_patch = false;
    for (const auto& s : states0) {
        if (s.patch_id == 0) {
            saw_patch = true;
            EXPECT_FLOAT_EQ(s.rain_d, 60.0f);
            EXPECT_TRUE(s.activated);
            EXPECT_EQ(s.habitat_dry_days, 0);
        }
    }
    EXPECT_TRUE(saw_patch);

    // Day 1: rain 40 mm — the pluvial z keeps decaying; dry streak off
    // (static persistent weighting keeps S above the activation min).
    climate->set_day(1);
    coord0.update_habitat_day();
    auto states1 = coord0.to_dataframe();
    for (const auto& s : states1) {
        if (s.patch_id == 0) {
            EXPECT_FLOAT_EQ(s.rain_d, 40.0f);
            EXPECT_TRUE(s.activated);
        }
    }

    std::filesystem::remove(nc_path);
    std::filesystem::remove_all(temp_dir("coordinator_daily_hab"));
}

TEST(CoordinatorModel, SalinityAboveHiTolDeactivatesPatch) {
    using namespace mal_abm_fast;
    GDALAllRegister();

    // Salinity per day: 35 psu (brackish, > coluzzii 30.0 default hi_tol)
    // then 5 psu (<= hi_tol, breeding allowed).
    const auto nc_path = MakeTmpEnvNC();
    if (std::filesystem::exists(nc_path)) std::filesystem::remove(nc_path);
    WriteSyntheticEnvNC(nc_path, 2, /*h=*/4, /*w=*/4, {35.0f, 5.0f});

    AOI aoi = make_aoi_4x4();
    auto climate = std::make_shared<ClimateEngine>();
    climate->load_from_env_nc(nc_path.string(), aoi);
    ASSERT_EQ(climate->n_days(), 2);

    const std::string hab_path = write_hab_gpkg("coordinator_salinity_hab",
                                                aoi, 2, 2);
    HabitatEngine habitat;
    habitat.load_from_gpkg(hab_path, aoi);
    ASSERT_EQ(habitat.patches().size(), 1u);

    // Day 0: salinity 35 psu > default hi_tol 30 -> patch cannot breed.
    climate->set_day(0);
    CoordinatorModel coord0(
        std::move(aoi), climate, std::move(habitat),
        /*seed=*/int32_t{1}, make_date(2024, 1, 1));
    coord0.update_habitat_day();
    auto states0 = coord0.to_dataframe();
    ASSERT_EQ(states0.size(), 16u);
    for (const auto& s : states0) {
        EXPECT_FLOAT_EQ(s.salinity_ppt, 35.0f);
        EXPECT_FALSE(s.activated)
            << "patch above salinity_hi_tol_ppt must be deactivated";
    }

    // Day 1: salinity 5 psu <= hi_tol -> activated through the static
    // persistent planes (S > ACTIVATION_MIN, no pool rule involved).
    climate->set_day(1);
    coord0.update_habitat_day();
    auto states1 = coord0.to_dataframe();
    ASSERT_EQ(states1.size(), 16u);
    for (const auto& s : states1) {
        EXPECT_FLOAT_EQ(s.salinity_ppt, 5.0f);
        EXPECT_TRUE(s.activated);
    }

    // Raising the species' hi_tol re-enables the brackish patch.
    climate->set_day(0);
    HabitatEngine habitat_high;
    habitat_high.load_from_gpkg(hab_path, make_aoi_4x4());
    CoordinatorModel coord_high(
        make_aoi_4x4(), climate, std::move(habitat_high),
        /*seed=*/int32_t{1}, make_date(2024, 1, 1));
    coord_high.set_salinity_hi_tol_ppt(40.0f);
    coord_high.update_habitat_day();
    auto states_high = coord_high.to_dataframe();
    bool saw_patch = false;
    for (const auto& s : states_high) {
        if (s.patch_id == 0) saw_patch = true;
        EXPECT_FLOAT_EQ(s.salinity_ppt, 35.0f);
        EXPECT_TRUE(s.activated);
    }
    EXPECT_TRUE(saw_patch);

    std::filesystem::remove(nc_path);
    std::filesystem::remove_all(temp_dir("coordinator_salinity_hab"));
}
