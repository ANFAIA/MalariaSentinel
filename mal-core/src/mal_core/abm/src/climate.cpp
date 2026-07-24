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

#include <cmath>
#include <cstdint>
#include <stdexcept>
#include <string>
#include <utility>

#include "env_reader.hpp"
#include "wire.hpp"

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
    if (h_ <= 0 || w_ <= 0) return ADULT_TEMP_FALLBACK_C;
    if (row < 0 || row >= h_ || col < 0 || col >= w_) return ADULT_TEMP_FALLBACK_C;
    const float T = temp_[Idx(row, col, w_)];
    // Out-of-coverage / land-mask pixels are NaN in the env COG.
    // The Lardeux mortality step falls back to ADULT_DAILY_MORT_BASE
    // (= 0.90, a 10% survival rate) when it sees a NaN, and the EIP
    // accumulator skips the daily GDD step (larvae never mature).
    // Substituting a real temperature (25 deg C) keeps both
    // submodels in their calibrated regime and avoids the
    // population crash.
    if (!std::isfinite(static_cast<double>(T))) return ADULT_TEMP_FALLBACK_C;
    return T;
}

float ClimateEngine::water_frac_at(int32_t row, int32_t col) const {
    if (h_ <= 0 || w_ <= 0) return 0.0f;
    if (row < 0 || row >= h_ || col < 0 || col >= w_) return 0.0f;
    return water_[Idx(row, col, w_)];
}

// -- Daily NetCDF support ----------------------------------------------------

void ClimateEngine::load_from_env_nc(const std::string& path,
                                     const AOI& aoi,
                                     int32_t max_days) {
    (void)aoi;
    env_reader::DailyEnvBands bands = env_reader::read_env_nc(path, max_days);

    h_      = bands.h;
    w_      = bands.w;
    n_days_ = bands.n_days;
    cur_day_ = 0;

    // Wrap multi-day buffers in shared_ptr for thread-safe sharing
    rain_nc_       = std::make_shared<std::vector<float>>(std::move(bands.rainfall));
    water_temp_nc_ = std::make_shared<std::vector<float>>(std::move(bands.water_temp_c));
    water_frac_nc_ = std::make_shared<std::vector<float>>(std::move(bands.water_frac));
    ndvi_nc_       = std::make_shared<std::vector<float>>(std::move(bands.ndvi));

    // Populate single-day accessors for day 0 (backwards compat).
    rain_.assign(h_ * w_, 0.0f);
    temp_.assign(h_ * w_, 25.0f);
    water_.assign(h_ * w_, 0.0f);
    ndvi_.assign(h_ * w_, 0.0f);

    const size_t slice = static_cast<size_t>(h_) * static_cast<size_t>(w_);
    for (size_t i = 0; i < slice; ++i) {
        rain_[i]  = (*rain_nc_)[i];
        temp_[i]  = (*water_temp_nc_)[i];
        water_[i] = (*water_frac_nc_)[i];
        ndvi_[i]  = (*ndvi_nc_)[i];
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
        rain_[i]  = (*rain_nc_)[offset + i];
        temp_[i]  = (*water_temp_nc_)[offset + i];
        water_[i] = (*water_frac_nc_)[offset + i];
        ndvi_[i]  = (*ndvi_nc_)[offset + i];
    }
}

std::shared_ptr<ClimateEngine> ClimateEngine::clone_for_thread() const {
    auto clone = std::make_shared<ClimateEngine>();
    clone->h_ = h_;
    clone->w_ = w_;
    clone->n_days_ = n_days_;
    clone->cur_day_ = 0;
    
    // Share the multi-day data (read-only, thread-safe)
    clone->rain_nc_ = rain_nc_;
    clone->water_temp_nc_ = water_temp_nc_;
    clone->water_frac_nc_ = water_frac_nc_;
    clone->ndvi_nc_ = ndvi_nc_;
    
    // Independent single-day arrays (thread-local)
    clone->rain_.assign(h_ * w_, 0.0f);
    clone->temp_.assign(h_ * w_, 25.0f);
    clone->water_.assign(h_ * w_, 0.0f);
    clone->ndvi_.assign(h_ * w_, 0.0f);
    
    // Initialize day 0
    if (n_days_ > 0 && rain_nc_) {
        const size_t slice = static_cast<size_t>(h_) * static_cast<size_t>(w_);
        for (size_t i = 0; i < slice; ++i) {
            clone->rain_[i]  = (*rain_nc_)[i];
            clone->temp_[i]  = (*water_temp_nc_)[i];
            clone->water_[i] = (*water_frac_nc_)[i];
            clone->ndvi_[i]  = (*ndvi_nc_)[i];
        }
    } else {
        // COG-loaded engine: no multi-day NetCDF data, so rain_nc_ is
        // nullptr. Copy the static bands directly — otherwise the
        // clone's water_/rain_/temp_/ndvi_ vectors stay at their
        // zero/fallback defaults, and downstream code that reads them
        // (e.g. build_seed_instructions's viability filter) sees
        // water_frac=0 at every patch and produces 0 viable seeds.
        clone->rain_  = rain_;
        clone->temp_  = temp_;
        clone->water_ = water_;
        clone->ndvi_  = ndvi_;
        clone->twi_   = twi_;
    }

    return clone;
}

}  // namespace mal_abm_fast
