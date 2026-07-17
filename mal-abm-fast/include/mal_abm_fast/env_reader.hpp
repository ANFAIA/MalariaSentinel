// SPDX-License-Identifier: MIT
// env_reader.hpp — env COG reader (4 bands + optional 5th TWI band)
//                  and NetCDF4 daily env reader (time-series).
//
// This is the thin helper namespace the IO subagent (F1.b) implements
// against GDAL. The ClimateEngine delegates the actual file IO to
// `read_env_tif` or `read_env_nc` and just stores the resulting flat
// bands.
//
// The COG struct fields are named after the band descriptions in the
// env COG (per docs/wire-spec.md §2):
//
//   * `rainfall`           — mm/day, float32, 1 band
//   * `temp_suitability`   — Mordecai parabolic [0, 1] on disk; the
//                            reader applies the Mordecai inverse
//                            (T = 25 - 8*sqrt(1 - s), lower branch)
//                            so the in-memory vector is in deg C.
//                            The field name keeps the band description
//                            for clarity; the unit is deg C.
//   * `water_frac`         — [0, 1] open water fraction
//   * `ndvi`               — [0, 1] vegetation index
//   * `twi`                — optional static TWI grid; empty if the
//                            COG has no `twi` band
//
// `transform` is the GDAL affine 6-tuple (double[6]); `crs` is the
// WKT string. `h`/`w` are the raster's (rows, cols).
//
// The NetCDF struct holds time-series data from a CF-1.8 NetCDF4 file.
// GDAL's netCDF driver flattens dims: for (time=T, y=H, x=W) it exposes
// T raster bands per variable, each band being one time slice. Variables
// are: `rainfall`, `water_temp_c` (°C, NO Mordecai inverse), `water_frac`,
// `ndvi`, and optionally `twi` (no time dim — 1 band).
#pragma once

#include <array>
#include <cstdint>
#include <string>
#include <vector>

namespace mal_abm_fast {
namespace env_reader {

struct EnvBands {
    std::vector<float>  water_frac;
    std::vector<float>  rainfall;
    std::vector<float>  temp_suitability;  // Mordecai-inverted deg C
    std::vector<float>  ndvi;
    std::vector<float>  twi;               // optional
    int32_t             h = 0;
    int32_t             w = 0;
    std::array<double, 6> transform;       // GDAL affine
    std::string         crs;
};

// Open `path` (a GeoTIFF, COG-compatible) with GDAL and read all
// required bands by name (`water_frac`, `rainfall`, `temp_suitability`,
// `ndvi`). Apply the Mordecai inverse to `temp_suitability` in place.
// Optionally read a 5th `twi` band. Throws std::runtime_error on any
// IO error or if a required band is missing.
EnvBands read_env_tif(const std::string& path);

// ---------------------------------------------------------------------------
// Daily NetCDF reader (daily-env-netcdf feature)
// ---------------------------------------------------------------------------

// Multi-day bands: each vector is n_days * h * w (row-major per-day slices).
struct DailyEnvBands {
    std::vector<float>  rainfall;       // mm/day
    std::vector<float>  water_temp_c;   // deg C, NO Mordecai inverse
    std::vector<float>  water_frac;     // [0, 1]
    std::vector<float>  ndvi;           // [0, 1]
    int32_t             n_days = 0;
    int32_t             h      = 0;
    int32_t             w      = 0;
    std::array<double, 6> transform;    // GDAL affine
    std::string         crs;
};

// Open `path` (a NetCDF file with CF-1.8 daily env variables) with GDAL
// and read all required variables (`rainfall`, `water_temp_c`,
// `water_frac`, `ndvi`) across all time steps. The time dimension is
// UNLIMITED. Each variable is written as a multi-band raster by GDAL
// where bands map to time steps. No Mordecai inverse is applied —
// `water_temp_c` is already in deg C. Throws std::runtime_error on any
// IO error or if a required variable is missing.
DailyEnvBands read_env_nc(const std::string& path);

}  // namespace env_reader
}  // namespace mal_abm_fast
