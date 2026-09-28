// SPDX-License-Identifier: MIT
// env_reader.hpp — NetCDF4 daily env reader (time-series).
//
// This is the thin helper namespace the IO subagent (F1.b) implements
// against GDAL. The ClimateEngine delegates the actual file IO to
// `read_env_nc` and just stores the resulting flat bands.
//
// The NetCDF struct holds time-series data from a CF-1.8 NetCDF4 file.
// GDAL's netCDF driver flattens dims: for (time=T, y=H, x=W) it exposes
// T raster bands per variable, each band being one time slice. Variables
// are: `rainfall`, `water_temp_c` (°C, NO Mordecai inverse), `water_frac`,
// `ndvi`, and optionally `twi` (no time dim — 1 band).
// (The legacy 4-band COG reader `read_env_tif` was removed — the env
// input contract is NC-only; see docs/specs/abm/spec.md INV-6.)
#pragma once

#include <array>
#include <cstdint>
#include <string>
#include <vector>

namespace mal_abm_fast {
namespace env_reader {

// ---------------------------------------------------------------------------
// Daily NetCDF reader (daily-env-netcdf feature)
// ---------------------------------------------------------------------------

// Multi-day bands: each vector is n_days * h * w (row-major per-day slices).
struct DailyEnvBands {
    std::vector<float>  rainfall;       // mm/day
    std::vector<float>  water_temp_c;   // deg C, NO Mordecai inverse
    std::vector<float>  water_frac;     // [0, 1]
    std::vector<float>  ndvi;           // [0, 1]
    std::vector<float>  salinity_ppt;   // psu; empty if the NC has no
                                        // salinity_ppt variable (= freshwater)
    std::vector<float>  permanent_water_mask; // optional 0..1 mask
    std::vector<float>  twi;            // optional static TWI grid (h*w);
                                        // empty if the NC has no twi variable
                                        // (pluvial-pool urban rule falls back)
    std::vector<float>  k_capacity_mult; // optional static per-cell capacity
    std::vector<float>  catchment_ratio; // optional static catchment-to-cell area ratio
                                        // multiplier (h*w); K_patch =
                                        // K_MAX × mult. Empty = legacy.
    int32_t             n_days = 0;
    int32_t             h      = 0;
    int32_t             w      = 0;
    std::array<double, 6> transform;    // GDAL affine
    std::string         crs;
};

// Open `path` (a NetCDF file with CF-1.8 daily env variables) with GDAL
// and read required variables (`rainfall`, `water_temp_c`, `water_frac`,
// `ndvi`) across time steps. If `max_days > 0`, only the first `max_days`
// time steps are loaded (useful for large multi-year files). The time
// dimension is UNLIMITED. Each variable is written as a multi-band raster
// by GDAL where bands map to time steps. No Mordecai inverse is applied —
// `water_temp_c` is already in deg C. Optionally reads a `salinity_ppt`
// variable (psu); if absent, `salinity_ppt` stays empty (= freshwater,
// the legacy behaviour). Throws std::runtime_error on any IO error or if
// a required variable is missing.
DailyEnvBands read_env_nc(const std::string& path, int32_t max_days = 0);

}  // namespace env_reader
}  // namespace mal_abm_fast
