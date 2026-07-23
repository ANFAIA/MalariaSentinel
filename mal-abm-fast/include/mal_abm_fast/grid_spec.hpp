// SPDX-License-Identifier: MIT
// grid_spec.hpp — Spatial contract validation for multi-layer raster inputs.
//
// GridSpec captures the spatial metadata that every input raster (climate,
// habitat, state COG) must share.  `validate_compatible` is called at
// engine startup to catch CRS / transform / resolution mismatches before
// the simulation runs.
//
// This header is intentionally header-only (inline definitions) so that
// every translation unit pulling in grid_spec.hpp sees the definitions
// without needing a separate .cpp translation unit.
#pragma once

#include <array>
#include <cmath>
#include <cstdint>
#include <stdexcept>
#include <string>

#include "wire.hpp"

namespace mal_abm_fast {

// Spatial metadata for a single raster layer.  Two layers are
// "compatible" when their GridSpecs agree on CRS, affine transform,
// dimensions, and nodata sentinel.
struct GridSpec {
    std::string             crs;               // e.g. "EPSG:4326"
    std::array<double, 6>   transform{};       // GDAL affine 6-tuple
    int32_t                 width  = 0;
    int32_t                 height = 0;
    double                  resolution_x = 0.0; // cell size in CRS units (degrees or metres)
    double                  resolution_y = 0.0;
    double                  nodata = NODATA_SENTINEL;

    // Derive bounds from transform + width/height.
    double west()  const noexcept { return transform[2]; }
    double north() const noexcept { return transform[5]; }
    double east()  const noexcept { return west()  + width  * transform[0]; }
    double south() const noexcept { return north() + height * transform[4]; }

    // Throw std::runtime_error if `a` and `b` are not spatially compatible.
    static void validate_compatible(const GridSpec& a, const GridSpec& b) {
        if (a.crs != b.crs) {
            throw std::runtime_error(
                "GridSpec::validate_compatible: CRS mismatch ('" +
                a.crs + "' vs '" + b.crs + "')");
        }
        for (int i = 0; i < 6; ++i) {
            if (std::abs(a.transform[i] - b.transform[i]) > 1e-6) {
                throw std::runtime_error(
                    "GridSpec::validate_compatible: transform element " +
                    std::to_string(i) + " differs (" +
                    std::to_string(a.transform[i]) + " vs " +
                    std::to_string(b.transform[i]) + ")");
            }
        }
        if (a.width != b.width || a.height != b.height) {
            throw std::runtime_error(
                "GridSpec::validate_compatible: dimension mismatch (" +
                std::to_string(a.width) + "x" + std::to_string(a.height) +
                " vs " + std::to_string(b.width) + "x" +
                std::to_string(b.height) + ")");
        }
        if (a.nodata != b.nodata) {
            throw std::runtime_error(
                "GridSpec::validate_compatible: nodata mismatch (" +
                std::to_string(a.nodata) + " vs " +
                std::to_string(b.nodata) + ")");
        }
    }

    // Build a GridSpec from an AOI and explicit raster dimensions.
    // The transform places the origin at (west, north) with cells
    // of size (resolution_x, -resolution_y) in GDAL convention.
    static GridSpec from_aoi(const AOI& aoi, int32_t w, int32_t h) {
        GridSpec gs;
        gs.crs    = aoi.crs;
        gs.width  = w;
        gs.height = h;

        // Resolution in CRS units (degrees for EPSG:4326).
        gs.resolution_x = static_cast<double>(aoi.resolution_m) / kMetresPerDegLat;
        gs.resolution_y = -gs.resolution_x;  // negative in GDAL convention

        // GDAL affine: [pixel_width, 0, origin_x, 0, -pixel_height, origin_y]
        gs.transform[0] =  gs.resolution_x;
        gs.transform[1] =  0.0;
        gs.transform[2] =  aoi.west;
        gs.transform[3] =  0.0;
        gs.transform[4] = -gs.resolution_x;  // north-up image, rows go south
        gs.transform[5] =  aoi.north;

        gs.nodata = NODATA_SENTINEL;
        return gs;
    }
};

}  // namespace mal_abm_fast
