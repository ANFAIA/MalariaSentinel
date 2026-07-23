// SPDX-License-Identifier: MIT
// test_grid_spec.cpp — GoogleTest for GridSpec spatial contract validation.

#include <gtest/gtest.h>

#include "grid_spec.hpp"

namespace {

mal_abm_fast::GridSpec make_spec() {
    mal_abm_fast::GridSpec gs;
    gs.crs = "EPSG:4326";
    gs.transform = {0.008983152841195, 0.0, -1.746, 0.0, -0.008983152841195, 7.786};
    gs.width  = 100;
    gs.height = 200;
    gs.resolution_x = 0.008983152841195;
    gs.resolution_y = -0.008983152841195;
    gs.nodata = -9999.0;
    return gs;
}

}  // namespace

TEST(GridSpec, DefaultInit) {
    mal_abm_fast::GridSpec gs;
    EXPECT_EQ(gs.width, 0);
    EXPECT_EQ(gs.height, 0);
    EXPECT_DOUBLE_EQ(gs.resolution_x, 0.0);
    EXPECT_DOUBLE_EQ(gs.resolution_y, 0.0);
    EXPECT_DOUBLE_EQ(gs.nodata, -9999.0);
}

TEST(GridSpec, Bounds) {
    mal_abm_fast::GridSpec gs = make_spec();
    EXPECT_DOUBLE_EQ(gs.west(),  -1.746);
    EXPECT_DOUBLE_EQ(gs.north(), 7.786);
    EXPECT_DOUBLE_EQ(gs.east(),  -1.746 + 100 * 0.008983152841195);
    EXPECT_DOUBLE_EQ(gs.south(), 7.786  + 200 * (-0.008983152841195));
}

TEST(GridSpec, CompatibleWithSelf) {
    mal_abm_fast::GridSpec a = make_spec();
    mal_abm_fast::GridSpec b = make_spec();
    EXPECT_NO_THROW(mal_abm_fast::GridSpec::validate_compatible(a, b));
}

TEST(GridSpec, ThrowsOnCrsMismatch) {
    mal_abm_fast::GridSpec a = make_spec();
    mal_abm_fast::GridSpec b = make_spec();
    b.crs = "EPSG:32630";
    EXPECT_THROW(
        mal_abm_fast::GridSpec::validate_compatible(a, b),
        std::runtime_error);
}

TEST(GridSpec, ThrowsOnTransformMismatch) {
    mal_abm_fast::GridSpec a = make_spec();
    mal_abm_fast::GridSpec b = make_spec();
    b.transform[2] += 1.0;  // shift origin
    EXPECT_THROW(
        mal_abm_fast::GridSpec::validate_compatible(a, b),
        std::runtime_error);
}

TEST(GridSpec, ThrowsOnDimensionMismatch) {
    mal_abm_fast::GridSpec a = make_spec();
    mal_abm_fast::GridSpec b = make_spec();
    b.width = 99;
    EXPECT_THROW(
        mal_abm_fast::GridSpec::validate_compatible(a, b),
        std::runtime_error);
}

TEST(GridSpec, ThrowsOnNodataMismatch) {
    mal_abm_fast::GridSpec a = make_spec();
    mal_abm_fast::GridSpec b = make_spec();
    b.nodata = -1.0;
    EXPECT_THROW(
        mal_abm_fast::GridSpec::validate_compatible(a, b),
        std::runtime_error);
}

TEST(GridSpec, FromAOI) {
    mal_abm_fast::AOI aoi;
    aoi.west  = -1.746;
    aoi.south =  5.998;
    aoi.east  = -0.848;
    aoi.north =  7.786;
    aoi.resolution_m = 1000;

    mal_abm_fast::GridSpec gs = mal_abm_fast::GridSpec::from_aoi(aoi, 100, 200);
    EXPECT_EQ(gs.crs, "EPSG:4326");
    EXPECT_EQ(gs.width, 100);
    EXPECT_EQ(gs.height, 200);
    EXPECT_DOUBLE_EQ(gs.west(),  -1.746);
    EXPECT_DOUBLE_EQ(gs.north(), 7.786);
    EXPECT_DOUBLE_EQ(gs.resolution_x, 1000.0 / mal_abm_fast::kMetresPerDegLat);
    EXPECT_DOUBLE_EQ(gs.nodata, -9999.0);
}

TEST(GridSpec, TransformTolerance) {
    mal_abm_fast::GridSpec a = make_spec();
    mal_abm_fast::GridSpec b = make_spec();
    // Small perturbation within tolerance
    b.transform[2] += 1e-7;
    EXPECT_NO_THROW(mal_abm_fast::GridSpec::validate_compatible(a, b));
    // Perturbation just outside tolerance
    b.transform[2] += 1e-5;
    EXPECT_THROW(
        mal_abm_fast::GridSpec::validate_compatible(a, b),
        std::runtime_error);
}
