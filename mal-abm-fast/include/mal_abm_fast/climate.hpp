// SPDX-License-Identifier: MIT
// climate.hpp — env COG reader (stub; F1.b implements)
#pragma once

#include <cstdint>
#include <string>

namespace mal_abm_fast {

// Minimal in-memory climate grid for one (aoi, year, month).
struct ClimateGrid {
    int h = 0;
    int w = 0;
    // Float32 arrays, row-major. (h, w) shape.
    float* rain_daily     = nullptr;  // mm/day
    float* water_temp_c   = nullptr;  // deg C
    float* water_frac     = nullptr;  // [0, 1]
    float* ndvi           = nullptr;  // [0, 1]
};

// Load a 4-band env COG from disk (stub returns empty grid in F1.a).
ClimateGrid load_climate_grid(const std::string& env_tif_path);

}  // namespace mal_abm_fast
