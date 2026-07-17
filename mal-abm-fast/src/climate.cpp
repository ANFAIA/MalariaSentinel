// SPDX-License-Identifier: MIT
// climate.cpp — ClimateEngine implementation (env COG -> 4 flat bands).
//
// The ClimateEngine is a thin wrapper over the env_reader helper: it
// delegates the actual file IO to `env_reader::read_env_tif` and
// stores the resulting flat bands in row-major float32 vectors.
// The per-day rainfall lookup is constant across the simulation
// (the env COG is monthly; daily CHIRPS interpolation is [M7+]).
//
// `*_at(row, col)` accessors are bounds-checked; out-of-bounds returns
// 0 (rain/water) or 25 deg C (temp — a safe default that keeps the
// EIP formula max(0, T - 16) positive).
#include "climate.hpp"

#include <cstdint>
#include <stdexcept>
#include <string>
#include <utility>

#include "env_reader.hpp"

namespace mal_abm_fast {

// -- internal helpers ---------------------------------------------------------

namespace {

// Per-cell index in a row-major (H, W) buffer. Caller must ensure
// (row, col) is in range — use from the bounds-checked public accessors.
inline size_t Idx(int32_t row, int32_t col, int32_t w) noexcept {
    return static_cast<size_t>(row) * static_cast<size_t>(w)
         + static_cast<size_t>(col);
}

}  // namespace

// -- public API ---------------------------------------------------------------

void ClimateEngine::load_from_env_tif(const std::string& path,
                                      const AOI& aoi) {
    (void)aoi;  // The engine's h_/w_ are taken from the COG itself;
                // the AOI is reserved for a future validation pass
                // (e.g. assert the COG's transform matches the AOI
                // bbox). The thin slice trusts the COG producer.

    env_reader::EnvBands bands = env_reader::read_env_tif(path);

    h_ = bands.h;
    w_ = bands.w;
    rain_  = std::move(bands.rainfall);
    temp_  = std::move(bands.temp_suitability);  // already Mordecai-inverted
    water_ = std::move(bands.water_frac);
    ndvi_  = std::move(bands.ndvi);
    if (!bands.twi.empty()) {
        twi_ = std::move(bands.twi);
    } else {
        twi_.clear();
    }

    if (h_ <= 0 || w_ <= 0) {
        throw std::runtime_error(
            "ClimateEngine::load_from_env_tif: env COG has no rasters");
    }
    if (static_cast<int32_t>(rain_.size()) != h_ * w_
        || static_cast<int32_t>(temp_.size()) != h_ * w_
        || static_cast<int32_t>(water_.size()) != h_ * w_
        || static_cast<int32_t>(ndvi_.size())  != h_ * w_) {
        throw std::runtime_error(
            "ClimateEngine::load_from_env_tif: band size mismatch");
    }
}

float ClimateEngine::rain_at(int32_t row, int32_t col) const {
    if (h_ <= 0 || w_ <= 0) return 0.0f;
    if (row < 0 || row >= h_ || col < 0 || col >= w_) return 0.0f;
    return rain_[Idx(row, col, w_)];
}

float ClimateEngine::temp_at(int32_t row, int32_t col) const {
    if (h_ <= 0 || w_ <= 0) return 25.0f;
    if (row < 0 || row >= h_ || col < 0 || col >= w_) return 25.0f;
    return temp_[Idx(row, col, w_)];
}

float ClimateEngine::water_frac_at(int32_t row, int32_t col) const {
    if (h_ <= 0 || w_ <= 0) return 0.0f;
    if (row < 0 || row >= h_ || col < 0 || col >= w_) return 0.0f;
    return water_[Idx(row, col, w_)];
}

// -- Daily NetCDF support ----------------------------------------------------

void ClimateEngine::load_from_env_nc(const std::string& path,
                                     const AOI& aoi) {
    (void)aoi;
    env_reader::DailyEnvBands bands = env_reader::read_env_nc(path);

    h_      = bands.h;
    w_      = bands.w;
    n_days_ = bands.n_days;
    cur_day_ = 0;

    rain_nc_       = std::move(bands.rainfall);
    water_temp_nc_ = std::move(bands.water_temp_c);
    water_frac_nc_ = std::move(bands.water_frac);
    ndvi_nc_       = std::move(bands.ndvi);

    // Populate single-day accessors for day 0 (backwards compat).
    rain_.assign(h_ * w_, 0.0f);
    temp_.assign(h_ * w_, 25.0f);
    water_.assign(h_ * w_, 0.0f);
    ndvi_.assign(h_ * w_, 0.0f);

    const size_t slice = static_cast<size_t>(h_) * static_cast<size_t>(w_);
    for (size_t i = 0; i < slice; ++i) {
        rain_[i]  = rain_nc_[i];
        temp_[i]  = water_temp_nc_[i];
        water_[i] = water_frac_nc_[i];
        ndvi_[i]  = ndvi_nc_[i];
    }
}

void ClimateEngine::set_day(int32_t day) {
    if (n_days_ <= 1) return;  // static COG: no daily switching
    if (day < 0) day = 0;
    if (day >= n_days_) day = n_days_ - 1;
    cur_day_ = day;

    const size_t slice = static_cast<size_t>(h_) * static_cast<size_t>(w_);
    const size_t offset = static_cast<size_t>(cur_day_) * slice;
    for (size_t i = 0; i < slice; ++i) {
        rain_[i]  = rain_nc_[offset + i];
        temp_[i]  = water_temp_nc_[offset + i];
        water_[i] = water_frac_nc_[offset + i];
        ndvi_[i]  = ndvi_nc_[offset + i];
    }
}

}  // namespace mal_abm_fast
