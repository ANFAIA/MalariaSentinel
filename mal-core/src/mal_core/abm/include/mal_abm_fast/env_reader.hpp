// SPDX-License-Identifier: MIT
// env_reader.hpp — NetCDF4 daily env reader (contract v3.0).
//
// Daily bands: rainfall (mm/day), air_temp_c (2 m daily mean).
// Static planes: the six-habitat feature contract — jrc_persistent,
// lc_built, lc_wetland, lc_open_plus_water, lc_crop — plus the optional
// salinity_ppt daily variable.
// (The retired v2 variables water_frac / ndvi / twi /
// k_capacity_mult / catchment_ratio / permanent_water_mask are NOT read;
// contract docs/plans/in-process/redesign/01-*-*.md §6.)
#pragma once

#include <array>
#include <cstdint>
#include <string>
#include <vector>

namespace mal_abm_fast {
namespace env_reader {

// Multi-day bands: each vector is n_days * h * w (row-major per-day slices).
struct DailyEnvBands {
    std::vector<float> rainfall;     // mm/day
    std::vector<float> air_temp_c;   // deg C (2 m daily mean)
    // Static habitat features (h*w, single plane):
    std::vector<float> jrc_persistent;     // JRC fraction of >=80%-occurrence watert
    std::vector<float> lc_built;           // ESA WorldCover built-up fraction
    std::vector<float> lc_wetland;         // wetland+mangrove fraction
    std::vector<float> lc_open_plus_water; // open/low-veg + bare + water fraction
    std::vector<float> lc_crop;            // cropland fraction
    std::vector<float> salinity_ppt;  // psu; empty if the NC has no salinity_ppt
    int32_t             n_days = 0;
    int32_t             h      = 0;
    int32_t             w      = 0;
    std::array<double, 6> transform;    // GDAL affine
    std::string         crs;
};

// Open `path` with GDAL, read `rainfall` + `air_temp_c` across the
// whole time axis (or the first `max_days` bands when > 0), and the
// five static habitat planes. A missing static variable is a warning;
// missing `air_temp_c` is a hard contract error. `salinity_ppt` stays
// empty when the NC predates it (freshwater everywhere). Throws
// std::runtime_error on any IO or shape error.
DailyEnvBands read_env_nc(const std::string& path, int32_t max_days = 0);

}  // namespace env_reader
}  // namespace mal_abm_fast
