// SPDX-License-Identifier: MIT
// aoi.hpp — AOI helpers (inline).
//
// The AOI struct is declared in wire.hpp; the cells_per_side() method is
// defined inline in wire.hpp (right after the struct). This header is the
// home for *additional* AOI helpers (e.g. cells_per_side_h) that need
// <cmath> but are not methods on the struct.
//
// Formula (EPSG:4326, M1.5 thin slice):
//   centroid_lat_rad  = ((north + south) / 2) * pi / 180
//   width_m           = (east - west) * kMetresPerDegLat() * cos(centroid_lat_rad)
//   cells_per_side    = round(width_m / resolution_m)         (W)
//
// Height is computed the same way without the cos factor:
//   height_m          = (north - south) * kMetresPerDegLat()
//   H                 = round(height_m / resolution_m)
//
// kMetresPerDegLat() comes from geodesy.metres_per_deg_lat in
// model_constants.yaml (pi * earth_radius_m / 180, validated there).
//
// Both directions are clamped to a minimum of 1 cell so the resulting
// grid is always at least 1x1.
#pragma once

#include <cmath>

#include "wire.hpp"

namespace mal_abm_fast {

// Number of cells along the north-south axis (H). Symmetric to
// AOI::cells_per_side() (which is the W dimension) but without the
// cos(lat) factor. Not a method on AOI per the wire.hpp spec, but exposed
// here as a free function for the coordinator / output writer to derive H.
// Uses the kMetresPerDegLat() constant from wire.hpp. Uses std::ceil to
// match the Python AOI.cells_per_side (mal_commonlib.aoi).
inline int32_t cells_per_side_h(const AOI& aoi) noexcept {
    const double height_m = (aoi.north - aoi.south) * kMetresPerDegLat();
    const double cells_d  = height_m / static_cast<double>(aoi.resolution_m);
    int32_t cells = static_cast<int32_t>(std::ceil(cells_d));
    if (cells < 1) cells = 1;
    return cells;
}

// ---- Local metric frame (plan §1) ------------------------------------------
// Metres from the SOUTH-WEST corner of the AOI: x grows east, y grows north.
// Row 0 is the northernmost row, so cell (row, col) spans
//   x in [col*res, (col+1)*res), y in [(H-1-row)*res, (H-row)*res).
// Degrees use geodesy.metres_per_deg_lat (kMetresPerDegLat()) with the
// cos(lat) factor on longitude -- the same convention as the AOI width.

struct XY { double x = 0.0; double y = 0.0; };
struct LonLat { double lon = 0.0; double lat = 0.0; };

inline LonLat xy_to_lonlat(const AOI& aoi, double x, double y) noexcept {
    const double mpd = kMetresPerDegLat();
    const double lat = aoi.south + y / mpd;
    const double c = std::cos(lat * 3.14159265358979323846 / 180.0);
    return {aoi.west + x / (mpd * (c > 1e-6 ? c : 1e-6)), lat};
}

inline XY lonlat_to_xy(const AOI& aoi, double lon, double lat) noexcept {
    const double mpd = kMetresPerDegLat();
    const double c = std::cos(lat * 3.14159265358979323846 / 180.0);
    return {(lon - aoi.west) * mpd * (c > 1e-6 ? c : 1e-6),
            (lat - aoi.south) * mpd};
}

/// Grid cell of a metric position, clamped into the grid.
inline void xy_to_cell(const AOI& aoi, double x, double y,
                       int32_t& row, int32_t& col) noexcept {
    const int32_t W = aoi.cells_per_side();
    const int32_t H = cells_per_side_h(aoi);
    const double res = static_cast<double>(aoi.resolution_m);
    int32_t c = static_cast<int32_t>(std::floor(x / res));
    int32_t r = H - 1 - static_cast<int32_t>(std::floor(y / res));
    col = c < 0 ? 0 : (c >= W ? W - 1 : c);
    row = r < 0 ? 0 : (r >= H ? H - 1 : r);
}

}  // namespace mal_abm_fast
