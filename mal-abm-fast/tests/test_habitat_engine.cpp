// SPDX-License-Identifier: MIT
// test_habitat_engine.cpp — GoogleTest for HabitatEngine::load_from_gpkg.
//
// Writes a 4-row synthetic gpkg (hab_type='pluvial_pool', K=1000,
// twi_value=9.0, row=[1,2,3,4], col=[1,1,1,1], geometry=Point) to a
// tmp file, calls load_from_gpkg, and asserts the patch list shape
// and the first patch's row/col/twi_value.

#include <gtest/gtest.h>

#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <string>
#include <vector>

#include "gdal.h"
#include "ogr_api.h"
#include "ogr_srs_api.h"

#include "habitat_engine.hpp"
#include "wire.hpp"

namespace {

namespace fs = std::filesystem;

// Build a dummy AOI; the gpkg path doesn't depend on it (the loader
// uses the gpkg's pre-computed row/col directly) but the API requires
// one.
mal_abm_fast::AOI MakeAoi() {
    mal_abm_fast::AOI a;
    a.west = -3.5; a.south = 4.5; a.east = 1.5; a.north = 11.5;
    a.crs = "EPSG:4326"; a.slug = "test"; a.resolution_m = 1000;
    a.scale = "regional";
    return a;
}

fs::path MakeTmpGpkg() {
    const char* base = std::getenv("TMPDIR");
    fs::path dir = (base && *base) ? fs::path(base) : fs::temp_directory_path();
    return dir / "mal_abm_fast_test_habitat_engine.gpkg";
}

// Write a 4-row gpkg of pluvial_pool Point features. One patch per row
// of a 4x4 grid, with a varying row index and constant col=1.
void WriteSyntheticGpkg(const fs::path& path) {
    GDALAllRegister();

    // Use the GPKG driver; it is built into libgdal on the test image.
    GDALDriverH driver = GDALGetDriverByName("GPKG");
    ASSERT_NE(driver, nullptr);

    // Overwrite any pre-existing test file.
    if (fs::exists(path)) {
        GDALDeleteDataset(driver, path.string().c_str());
    }

    GDALDatasetH ds = GDALCreate(
        driver, path.string().c_str(),
        0, 0, 0, GDT_Unknown, nullptr);
    ASSERT_NE(ds, nullptr);

    OGRSpatialReferenceH srs = OSRNewSpatialReference(nullptr);
    OSRImportFromEPSG(srs, 4326);

    // Single layer named "patches" with the schema:
    //   hab_type : String
    //   K        : Integer (int32)
    //   twi_value: Real    (float)
    //   row      : Integer
    //   col      : Integer
    //   geometry : Point (EPSG:4326)
    char** layer_opts = nullptr;
    OGRLayerH layer = GDALDatasetCreateLayer(
        ds, "patches", srs, wkbPoint, layer_opts);
    ASSERT_NE(layer, nullptr);
    OSRDestroySpatialReference(srs);

    OGRFieldDefnH ftype = OGR_Fld_Create("hab_type", OFTString);
    OGR_Fld_SetWidth(ftype, 32);
    OGR_L_CreateField(layer, ftype, TRUE);
    OGR_Fld_Destroy(ftype);

    OGRFieldDefnH fK = OGR_Fld_Create("K", OFTInteger);
    OGR_L_CreateField(layer, fK, TRUE);
    OGR_Fld_Destroy(fK);

    OGRFieldDefnH ftwi = OGR_Fld_Create("twi_value", OFTReal);
    OGR_L_CreateField(layer, ftwi, TRUE);
    OGR_Fld_Destroy(ftwi);

    OGRFieldDefnH frow = OGR_Fld_Create("row", OFTInteger);
    OGR_L_CreateField(layer, frow, TRUE);
    OGR_Fld_Destroy(frow);

    OGRFieldDefnH fcol = OGR_Fld_Create("col", OFTInteger);
    OGR_L_CreateField(layer, fcol, TRUE);
    OGR_Fld_Destroy(fcol);

    // 4 patches at AOI-relative points. The exact (lon, lat) values
    // are not asserted — only (row, col, twi_value, K).
    const double points[4][2] = {
        {-3.0,  5.0}, {-2.0,  5.0},
        {-1.0,  5.0}, { 0.0,  5.0},
    };

    for (int i = 0; i < 4; ++i) {
        OGRFeatureH feat = OGR_F_Create(
            OGR_L_GetLayerDefn(layer));
        ASSERT_NE(feat, nullptr);
        OGR_F_SetFieldString(feat,
            OGR_FD_GetFieldIndex(
                OGR_L_GetLayerDefn(layer), "hab_type"),
            "pluvial_pool");
        OGR_F_SetFieldInteger(feat,
            OGR_FD_GetFieldIndex(
                OGR_L_GetLayerDefn(layer), "K"),
            1000);
        OGR_F_SetFieldDouble(feat,
            OGR_FD_GetFieldIndex(
                OGR_L_GetLayerDefn(layer), "twi_value"),
            9.0);
        OGR_F_SetFieldInteger(feat,
            OGR_FD_GetFieldIndex(
                OGR_L_GetLayerDefn(layer), "row"),
            i + 1);  // rows 1..4
        OGR_F_SetFieldInteger(feat,
            OGR_FD_GetFieldIndex(
                OGR_L_GetLayerDefn(layer), "col"),
            1);     // all in column 1

        OGRGeometryH pt = OGR_G_CreateGeometry(wkbPoint);
        OGR_G_SetPoint_2D(pt, 0, points[i][0], points[i][1]);
        OGR_F_SetGeometryDirectly(feat, pt);

        EXPECT_EQ(OGR_L_CreateFeature(layer, feat), OGRERR_NONE);
        OGR_F_Destroy(feat);
    }

    GDALClose(ds);
}

}  // namespace

TEST(HabitatEngine, LoadsFourPluvialPoolsFromGpkg) {
    const fs::path path = MakeTmpGpkg();
    WriteSyntheticGpkg(path);
    ASSERT_TRUE(fs::exists(path));

    mal_abm_fast::HabitatEngine eng;
    eng.load_from_gpkg(path.string(), MakeAoi());

    const auto& patches = eng.patches();
    ASSERT_EQ(patches.size(), 4u);

    // First patch: row=1, col=1, twi_value=9.0, K=1000.
    EXPECT_EQ(patches[0].row, 1);
    EXPECT_EQ(patches[0].col, 1);
    EXPECT_FLOAT_EQ(patches[0].twi_value, 9.0f);
    EXPECT_EQ(patches[0].K, 1000);
    EXPECT_TRUE(patches[0].hab_pluvial_pool);
    EXPECT_EQ(patches[0].patch_id, 0);
    EXPECT_FLOAT_EQ(static_cast<float>(patches[0].lon), -3.0f);
    EXPECT_FLOAT_EQ(static_cast<float>(patches[0].lat),  5.0f);

    // Last patch: row=4, col=1.
    EXPECT_EQ(patches[3].row, 4);
    EXPECT_EQ(patches[3].col, 1);
    EXPECT_EQ(patches[3].patch_id, 3);

    // O(1) lookup via patch_by_id.
    const auto& p1 = eng.patch_by_id(1);
    EXPECT_EQ(p1.row, 2);
    EXPECT_EQ(p1.col, 1);
    EXPECT_FLOAT_EQ(p1.twi_value, 9.0f);

    // Out-of-range id throws.
    EXPECT_THROW(eng.patch_by_id(99), std::out_of_range);

    // No TWI provider set — grid is empty.
    auto aoi = MakeAoi();
    EXPECT_TRUE(eng.get_twi_grid(aoi).empty());

    // TWI provider set — grid is the provider's return.
    std::vector<float> fake_twi(static_cast<size_t>(aoi.cells_per_side())
                                * static_cast<size_t>(aoi.cells_per_side()),
                                7.0f);
    eng.set_twi_grid_provider([&fake_twi](const mal_abm_fast::AOI& a) {
        (void)a; return fake_twi;
    });
    auto out = eng.get_twi_grid(aoi);
    EXPECT_EQ(out.size(), fake_twi.size());
    EXPECT_FLOAT_EQ(out[0], 7.0f);

    GDALDriverH drv = GDALGetDriverByName("GPKG");
    if (fs::exists(path)) GDALDeleteDataset(drv, path.string().c_str());
}

TEST(HabitatEngine, NonPluvialPoolRowsAreSkipped) {
    const fs::path path = MakeTmpGpkg();
    GDALAllRegister();
    GDALDriverH driver = GDALGetDriverByName("GPKG");
    if (fs::exists(path)) GDALDeleteDataset(driver, path.string().c_str());

    GDALDatasetH ds = GDALCreate(
        driver, path.string().c_str(), 0, 0, 0, GDT_Unknown, nullptr);
    ASSERT_NE(ds, nullptr);

    OGRLayerH layer = GDALDatasetCreateLayer(
        ds, "patches", nullptr, wkbPoint, nullptr);
    ASSERT_NE(layer, nullptr);

    OGRFieldDefnH ftype = OGR_Fld_Create("hab_type", OFTString);
    OGR_Fld_SetWidth(ftype, 32);
    OGR_L_CreateField(layer, ftype, TRUE);
    OGR_Fld_Destroy(ftype);

    // One feature with hab_type = "stream_pool" (not honoured by M1.5).
    OGRFeatureH feat = OGR_F_Create(OGR_L_GetLayerDefn(layer));
    OGR_F_SetFieldString(feat,
        OGR_FD_GetFieldIndex(OGR_L_GetLayerDefn(layer), "hab_type"),
        "stream_pool");
    OGRGeometryH pt = OGR_G_CreateGeometry(wkbPoint);
    OGR_G_SetPoint_2D(pt, 0, 0.0, 5.0);
    OGR_F_SetGeometryDirectly(feat, pt);
    EXPECT_EQ(OGR_L_CreateFeature(layer, feat), OGRERR_NONE);
    OGR_F_Destroy(feat);

    GDALClose(ds);

    mal_abm_fast::HabitatEngine eng;
    eng.load_from_gpkg(path.string(), MakeAoi());
    EXPECT_EQ(eng.patches().size(), 0u);

    if (fs::exists(path)) GDALDeleteDataset(driver, path.string().c_str());
}
