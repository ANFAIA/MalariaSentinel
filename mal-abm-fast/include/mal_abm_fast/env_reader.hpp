// SPDX-License-Identifier: MIT
// env_reader.hpp — env COG reader (4 bands + optional 5th TWI band).
//
// This is the thin helper namespace the IO subagent (F1.b) implements
// against GDAL. The ClimateEngine delegates the actual file IO to
// `read_env_tif` and just stores the resulting flat bands.
//
// The struct fields are named after the band descriptions in the env
// COG (per docs/wire-spec.md §2):
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

}  // namespace env_reader
}  // namespace mal_abm_fast
