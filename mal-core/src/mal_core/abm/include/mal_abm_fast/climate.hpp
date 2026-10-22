// SPDX-License-Identifier: MIT
// climate.hpp — daily env NetCDF reader (contract v3.0).
//
// Daily channels: `rainfall` (mm/day) and `air_temp_c` (2 m daily mean, deg C).
// Static planes: the six-habitat feature contract (see env_reader.hpp) and
// optional `salinity_ppt` (psu; absent = freshwater everywhere).
//
// Reading goes through GDAL's netCDF driver (see env_reader.hpp). A missing
// daily variable is a hard error: the engine cannot fall back to a zero
// grid for a real run. Retired v2 channels (water_frac / ndvi / twi /
// k_capacity_mult / catchment_ratio / permanent_water_mask) are NOT read.
#pragma once

#include <algorithm>
#include <cstdint>
#include <memory>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include "habitat_availability.hpp"
#include "wire.hpp"

namespace mal_abm_fast {

class ClimateEngine {
public:
    ClimateEngine() = default;

    // Grid shape (post-rotation, row-major). h() and w() are valid
    // only after a successful load_from_env_nc().
    int32_t h() const { return h_; }
    int32_t w() const { return w_; }

    // Gridded data (row-major float32, length h*w). Access by
    // `rain_daily()[r*w_ + c]`. Lifetime matches the engine.
    const std::vector<float>& rain_daily()  const { return rain_; }
    const std::vector<float>& temp_d()      const { return temp_; }
    const std::vector<float>& salinity()    const { return salinity_; }

    // Static habitat features (contract v3.0). Each is h*w or empty.
    const std::vector<float>& jrc_persistent()     const { return jrc_persistent_; }
    const std::vector<float>& lc_built()           const { return lc_built_; }
    const std::vector<float>& lc_wetland()         const { return lc_wetland_; }
    const std::vector<float>& lc_open_plus_water() const { return lc_open_plus_water_; }
    const std::vector<float>& lc_crop()            const { return lc_crop_; }

    // Per-cell static features bundle for the coordinator (bounds-clamped).
    HabitatFeatures habitat_features_at(int32_t row, int32_t col) const {
        auto clamped = [&](const std::vector<float>& g, float fallback) -> float {
            if (g.empty()) return fallback;
            if (row < 0 || row >= h_ || col < 0 || col >= w_) return fallback;
            return std::max(0.0f, g[static_cast<size_t>(row) *
                                   static_cast<size_t>(w_) + col]);
        };
        return HabitatFeatures{clamped(jrc_persistent_, 0.0f),
                               clamped(lc_built_, 0.0f),
                               clamped(lc_wetland_, 0.0f),
                               clamped(lc_open_plus_water_, 0.0f),
                               clamped(lc_crop_, 0.0f)};
    }

    // Point lookups at (row, col). Out-of-bounds returns 0 (the env
    // is land; no patch, no rain).
    float rain_at(int32_t row, int32_t col) const;
    float temp_at(int32_t row, int32_t col) const;
    // Salinity (psu). Out-of-bounds returns 0.0 (freshwater). When no
    // salinity data was loaded (a pre-salinity NC), every
    // cell reads 0.0 — the salinity factor is inert, as before.
    float salinity_at(int32_t row, int32_t col) const;

    // -- Daily NetCDF support -------------------------------------------------

    // Read a NetCDF daily env file and populate multi-day bands. The NC
    // file must contain variables `rainfall` and `air_temp_c` with a
    // UNLIMITED time dimension. If `max_days > 0`, only the first
    // `max_days` time steps are loaded (extend the horizon for warm-up).
    void load_from_env_nc(const std::string& path, const AOI& aoi,
                          int32_t max_days = 0);

    // Base day index inside the NC for simulation day 0 (the coordinator
    // warm-up reads bands [base - n_warmup, base)). Default 0.
    void set_base_day(int32_t band_index);
    int32_t base_day() const { return base_day_; }

    // Switch the active day slice (0-based, RELATIVE to base_day).
    // Clamps to [-n_warmup_days_, n_days_ - 1 - base_day_]? Actually the
    // accepted range is [-base_day_, n_days_ - 1 - base_day_]: negative
    // relative days reach into the warm-up window (rain-only reads).
    void set_day(int32_t day);

    // Raw band accessor for the pluvial warm-up: copy the rainfall grid
    // of absolute band `band_index` (clamped). Does not disturb the
    // per-day accessor arrays.
    std::vector<float> rain_band(int32_t band_index) const;

    // Number of time steps loaded by load_from_env_nc.
    int32_t n_days() const { return n_days_; }

    // Create a thread-safe clone for parallel rollouts. The multi-day
    // NetCDF buffers are shared via shared_ptr to avoid duplicating the
    // env tensor for every rollout; single-day accessors are per-clone.
    std::shared_ptr<ClimateEngine> clone_for_thread() const;

private:
    int32_t              h_ = 0, w_ = 0;
    std::vector<float>   rain_;      // current-day band
    std::vector<float>   temp_;      // deg C (air_temp_c from the NC)
    std::vector<float>   salinity_;  // psu; empty = freshwater everywhere
    // Static habitat features:
    std::vector<float>   jrc_persistent_;
    std::vector<float>   lc_built_;
    std::vector<float>   lc_wetland_;
    std::vector<float>   lc_open_plus_water_;
    std::vector<float>   lc_crop_;
    // Daily NC state - shared across threads via shared_ptr
    std::shared_ptr<std::vector<float>>   rain_nc_;      // n_days * h * w
    std::shared_ptr<std::vector<float>>   air_temp_nc_;  // n_days * h * w (deg C)
    std::shared_ptr<std::vector<float>>   salinity_nc_;  // n_days * h * w (psu)
    int32_t              n_days_ = 1;
    int32_t              base_day_ = 0;
    int32_t              cur_day_ = 0;  // absolute band index
};

}  // namespace mal_abm_fast
