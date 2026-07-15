// SPDX-License-Identifier: MIT
// climate.hpp — env COG reader (4 bands: rain, temp, water, ndvi).
//
// The env COG is a single GeoTIFF with 4 (or 5) bands described by the
// following names (per `docs/abm-output-contract.md` and the Python
// `mal_ghana_sim.abm.run._load_env_dict`):
//
//   band 1  rainfall           (mm/day, float32)
//   band 2  temp_suitability    ([0, 1], Mordecai parabolic suitability)
//   band 3  water_frac          ([0, 1], open water fraction)
//   band 4  ndvi                ([0, 1], vegetation index)
//
//   optional band 5  twi        (Topographic Wetness Index, static;
//                                used by the dynamic PLUVIAL_POOL rule)
//                                If absent, the climate engine treats
//                                TWI as 0 everywhere and the dynamic
//                                rule is equivalent to
//                                `water_frac > 0 AND rain > 15`.
//
// The Mordecai inverse is applied to the temp_suitability band on
// load (the EIP code expects deg C, not [0, 1]):
//
//   T = 25 - 8 * sqrt(1 - s)            (lower branch; biologically
//                                        relevant for An. gambiae)
//
// Reading the env COG goes through GDAL (`GDALDataset::GetRasterBand`).
// A missing band is a hard error: the engine cannot fall back to a
// zero grid for a real run. The IO subagent (F1.b) implements the
// actual GDAL calls.
#pragma once

#include <cstdint>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include "wire.hpp"

namespace mal_abm_fast {

class ClimateEngine {
public:
    ClimateEngine() = default;

    // Read the env COG from `path` and populate the 4 grids + the
    // optional 5th TWI grid. The Mordecai inverse is applied to the
    // temp_suitability band on read. Throws std::runtime_error if a
    // required band is missing.
    void load_from_env_tif(const std::string& path, const AOI& aoi);

    // Grid shape (post-rotation, row-major). h() and w() are valid
    // only after a successful load_from_env_tif().
    int32_t h() const { return h_; }
    int32_t w() const { return w_; }

    // Gridded data (row-major float32, length h*w). Access by
    // `rain_daily()[r*w_ + c]`. Lifetime matches the engine.
    const std::vector<float>& rain_daily()  const { return rain_; }
    const std::vector<float>& temp_d()      const { return temp_; }
    const std::vector<float>& water_frac()  const { return water_; }
    const std::vector<float>& ndvi()        const { return ndvi_; }

    // Point lookups at (row, col). Out-of-bounds returns 0 (the env
    // is land; no patch, no rain).
    float rain_at(int32_t row, int32_t col) const;
    float temp_at(int32_t row, int32_t col) const;
    float water_frac_at(int32_t row, int32_t col) const;

    // TWI grid (per-cell, static). Setter is for the habitat engine
    // (it loads TWI from the gpkg) or the F1.b loader (it reads a
    // 5th band). Default value is an empty vector (= TWI = 0
    // everywhere).
    std::vector<float> twi_grid() const { return twi_; }
    void set_twi_grid(std::vector<float> t) { twi_ = std::move(t); }

private:
    int32_t              h_ = 0, w_ = 0;
    std::vector<float>   rain_;
    std::vector<float>   temp_;     // Mordecai-inverted deg C
    std::vector<float>   water_;
    std::vector<float>   ndvi_;
    std::vector<float>   twi_;      // optional 5th band; empty = zeros
};

}  // namespace mal_abm_fast
