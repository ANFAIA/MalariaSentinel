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
//   width_m           = (east - west) * 111320 * cos(centroid_lat_rad)
//   cells_per_side    = round(width_m / resolution_m)         (W)
//
// Height is computed the same way without the cos factor:
//   height_m          = (north - south) * 111320
//   H                 = round(height_m / resolution_m)
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
// Uses the kMetresPerDegLat constant from wire.hpp. Uses std::ceil to
// match the Python AOI.cells_per_side (mal_commonlib.aoi).
inline int32_t cells_per_side_h(const AOI& aoi) noexcept {
    const double height_m = (aoi.north - aoi.south) * kMetresPerDegLat;
    const double cells_d  = height_m / static_cast<double>(aoi.resolution_m);
    int32_t cells = static_cast<int32_t>(std::ceil(cells_d));
    if (cells < 1) cells = 1;
    return cells;
}

}  // namespace mal_abm_fast
