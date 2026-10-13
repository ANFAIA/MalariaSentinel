// SPDX-License-Identifier: MIT
// climate.cpp — ClimateEngine implementation (env NC -> flat bands).
//
// The ClimateEngine is a thin wrapper over the env_reader helper: it
// delegates the actual file IO to `env_reader::read_env_nc` and
// stores the resulting flat bands in row-major float32 vectors.
// (The legacy `load_from_env_tif` COG path was removed — the env
// input contract is NC-only; see docs/specs/abm/spec.md INV-6.)
//
// `*_at(row, col)` accessors are bounds-checked; out-of-bounds returns
// 0 (rain/water) or the border cell's temperature for temp (clamped
// edge lookup — NaN pixels were imputed at load time, see
// impute_temp_nans below, so no per-lookup fallback constant exists).
#include "climate.hpp"

#include <cmath>
#include <cstdint>
#include <iostream>
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

// Impute NaN temperature pixels by iterative neighbor-mean imputation
// (a grassfire wavefront expanding from the finite boundary).
//
// Each NaN cell is filled once with the mean of its currently-finite
// 8-neighborhood; filling a cell enqueues its still-NaN neighbors, so
// the fill propagates one cell layer per wave until the whole NaN
// region is covered. This is the O(N_nan) equivalent of repeated
// onion-peel passes and needs no linear-algebra solver: the env
// temperature field is smooth at ~1 km resolution, and the mean-based
// fill tracks the same day's spatial field — the imputed values
// follow the seasonal cycle instead of pinning a fixed fallback.
// (The old per-cell constant — ADULT_TEMP_FALLBACK_C, 25 deg C — was
// removed on 2026-10-13 in favour of this imputation.)
//
// NaN components with no finite cell anywhere in the slice (an
// entirely out-of-coverage slice) get the slice's finite mean; if
// there is no finite cell at all the NaNs are left in place and
// ClimateEngine::temp_at serves its degenerate-engine guard.
void impute_temp_nans(float* T, int32_t h, int32_t w) {
    if (h <= 0 || w <= 0) return;
    const int32_t n = h * w;

    // Seed the wavefront: NaN cells with at least one finite 8-neighbor.
    std::vector<int32_t> queue;
    queue.reserve(static_cast<size_t>(n) / 8);
    for (int32_t i = 0; i < n; ++i) {
        if (!std::isnan(T[i])) continue;
        const int32_t r = i / w, c = i % w;
        bool seedable = false;
        for (int32_t dr = -1; dr <= 1 && !seedable; ++dr) {
            for (int32_t dc = -1; dc <= 1 && !seedable; ++dc) {
                if (dr == 0 && dc == 0) continue;
                const int32_t rr = r + dr, cc = c + dc;
                if (rr < 0 || rr >= h || cc < 0 || cc >= w) continue;
                if (!std::isnan(T[Idx(rr, cc, w)])) seedable = true;
            }
        }
        if (seedable) queue.push_back(i);
    }
    if (queue.empty()) return;  // no imputable NaNs

    // Breadth-first fill: each cell imputed once with the mean of its
    // currently-finite neighbors (already-filled NaN neighbors count,
    // so the wave carries values deep into the region). Duplicate
    // enqueues are fine — the isnan check on pop skips stale entries.
    size_t head = 0;
    while (head < queue.size()) {
        const int32_t i = queue[head++];
        float* p = T + i;
        if (!std::isnan(*p)) continue;
        const int32_t r = i / w, c = i % w;
        float sum = 0.0f;
        int cnt = 0;
        for (int32_t dr = -1; dr <= 1; ++dr) {
            for (int32_t dc = -1; dc <= 1; ++dc) {
                if (dr == 0 && dc == 0) continue;
                const int32_t rr = r + dr, cc = c + dc;
                if (rr < 0 || rr >= h || cc < 0 || cc >= w) continue;
                const float v = T[Idx(rr, cc, w)];
                if (!std::isnan(v)) { sum += v; ++cnt; }
            }
        }
        if (cnt == 0) continue;  // unreachable for seeded cells; defensive
        *p = sum / static_cast<float>(cnt);
        for (int32_t dr = -1; dr <= 1; ++dr) {
            for (int32_t dc = -1; dc <= 1; ++dc) {
                if (dr == 0 && dc == 0) continue;
                const int32_t rr = r + dr, cc = c + dc;
                if (rr < 0 || rr >= h || cc < 0 || cc >= w) continue;
                const int32_t j = rr * w + cc;
                if (std::isnan(T[j])) queue.push_back(j);
            }
        }
    }

    // Leftovers: NaN components that never touched a finite cell (the
    // whole slice out of coverage). Give them the slice's finite mean.
    float gsum = 0.0f;
    int64_t gcnt = 0;
    for (int32_t i = 0; i < n; ++i) {
        if (!std::isnan(T[i])) { gsum += T[i]; ++gcnt; }
    }
    if (gcnt > 0) {
        const float gmean = gsum / static_cast<float>(gcnt);
        for (int32_t i = 0; i < n; ++i) {
            if (std::isnan(T[i])) T[i] = gmean;
        }
    }
    // gcnt == 0: no finite cell anywhere — leave NaN; temp_at() serves
    // its degenerate guard (25 deg C literal) for this all-NaN case.
}

}  // namespace

// -- public API ---------------------------------------------------------------

float ClimateEngine::rain_at(int32_t row, int32_t col) const {
    if (h_ <= 0 || w_ <= 0) return 0.0f;
    if (row < 0 || row >= h_ || col < 0 || col >= w_) return 0.0f;
    return rain_[Idx(row, col, w_)];
}

float ClimateEngine::temp_at(int32_t row, int32_t col) const {
    if (h_ <= 0 || w_ <= 0) return 25.0f;
    // Off-grid (row, col) inherits the border cell's temperature
    // (clamped edge lookup). After the load-time imputation the border
    // cell is always a real, seasonally-consistent value.
    if (row < 0) row = 0;
    if (row >= h_) row = h_ - 1;
    if (col < 0) col = 0;
    if (col >= w_) col = w_ - 1;
    const float T = temp_[Idx(row, col, w_)];
    // Out-of-coverage / sea-mask pixels were NaN in the env NC and are
    // imputed from same-day neighbors at load time (impute_temp_nans in
    // load_from_env_nc), so they track the seasonal field instead of a
    // fixed fallback. The previous ADULT_TEMP_FALLBACK_C constant
    // (25 deg C per NaN/bounds miss) was removed on 2026-10-13.
    // A NaN surviving here means a degenerate all-NaN slice (no finite
    // cell anywhere in the env) or an unloaded engine: 25 deg C is the
    // Lardeux optimum (p_d = ADULT_DAILY_MORT_BASAL exactly) and keeps
    // both the mortality and EIP submodels in their calibrated regime.
    if (!std::isfinite(static_cast<double>(T))) return 25.0f;
    return T;
}

float ClimateEngine::water_frac_at(int32_t row, int32_t col) const {
    if (h_ <= 0 || w_ <= 0) return 0.0f;
    if (row < 0 || row >= h_ || col < 0 || col >= w_) return 0.0f;
    return water_[Idx(row, col, w_)];
}

float ClimateEngine::salinity_at(int32_t row, int32_t col) const {
    // Empty salinity_ => no salinity data (pre-salinity NC): every
    // cell is freshwater (0.0 psu), the legacy behaviour.
    if (salinity_.empty()) return 0.0f;
    if (h_ <= 0 || w_ <= 0) return 0.0f;
    if (row < 0 || row >= h_ || col < 0 || col >= w_) return 0.0f;
    return salinity_[Idx(row, col, w_)];
}

// -- Daily NetCDF support ----------------------------------------------------

void ClimateEngine::load_from_env_nc(const std::string& path,
                                     const AOI& aoi,
                                     int32_t max_days) {
    (void)aoi;
    env_reader::DailyEnvBands bands = env_reader::read_env_nc(path, max_days);

    // Impute NaN temperature pixels once, at load time, across every
    // day slice (out-of-coverage / sea-mask pixels are NaN in the NC).
    // O(n) wavefront fill per slice, ~1-2 ms for a Ghana-size grid:
    // after this the temperature channel is finite everywhere and
    // temp_at() needs no per-lookup fallback. Seasonally correct: each
    // imputed cell borrows the mean of its same-day neighbors.
    if (!bands.water_temp_c.empty()) {
        const size_t tslice = static_cast<size_t>(bands.h) *
                              static_cast<size_t>(bands.w);
        for (int32_t d = 0; d < bands.n_days; ++d) {
            impute_temp_nans(bands.water_temp_c.data() +
                             static_cast<size_t>(d) * tslice,
                             bands.h, bands.w);
        }
    }

    h_      = bands.h;
    w_      = bands.w;
    n_days_ = bands.n_days;
    cur_day_ = 0;

    // Wrap multi-day buffers in shared_ptr for thread-safe sharing
    rain_nc_       = std::make_shared<std::vector<float>>(std::move(bands.rainfall));
    water_temp_nc_ = std::make_shared<std::vector<float>>(std::move(bands.water_temp_c));
    water_frac_nc_ = std::make_shared<std::vector<float>>(std::move(bands.water_frac));
    ndvi_nc_       = std::make_shared<std::vector<float>>(std::move(bands.ndvi));
    if (!bands.salinity_ppt.empty()) {
        salinity_nc_ = std::make_shared<std::vector<float>>(
            std::move(bands.salinity_ppt));
    } else {
        salinity_nc_.reset();
    }
    if (!bands.permanent_water_mask.empty()) {
        permanent_water_nc_ = std::make_shared<std::vector<float>>(
            std::move(bands.permanent_water_mask));
    } else {
        permanent_water_nc_.reset();
    }

    // Optional static TWI grid (plan §6.3 pluvial-pool rules). Static:
    // single h*w plane, no time dimension.
    if (bands.twi.size() == static_cast<size_t>(bands.h) *
        static_cast<size_t>(bands.w)) {
        twi_ = std::move(bands.twi);
        std::cout << "ClimateEngine: env NC carries static TWI grid ("
                  << h_ << "x" << w_ << ")\n";
    } else {
        twi_.clear();
    }

    // Optional static per-cell capacity multiplier (M7.4.1): consumed by
    // CoordinatorModel::build_K_eff_grid to set the Beverton-Holt larval
    // cap K_patch = K_MAX × mult per cell (literature-anchored formula
    // computed at ingest time).
    if (bands.k_capacity_mult.size() == static_cast<size_t>(bands.h) *
        static_cast<size_t>(bands.w)) {
        k_capacity_mult_ = std::move(bands.k_capacity_mult);
        std::cout << "ClimateEngine: env NC carries static k_capacity_mult "
                  << "grid (" << h_ << "x" << w_ << ")\n";
    } else {
        k_capacity_mult_.clear();
    }

    // Optional static catchment-to-cell area ratio (M7.4.1): consumed by
    // CoordinatorModel's pool hydrology (catchment-runoff model).
    if (bands.catchment_ratio.size() == static_cast<size_t>(bands.h) *
        static_cast<size_t>(bands.w)) {
        catchment_ratio_ = std::move(bands.catchment_ratio);
        std::cout << "ClimateEngine: env NC carries static catchment_ratio "
                  << "grid (" << h_ << "x" << w_ << ")\n";
    } else {
        catchment_ratio_.clear();
    }

    // Populate single-day accessors for day 0 (backwards compat).
    rain_.assign(h_ * w_, 0.0f);
    temp_.assign(h_ * w_, 25.0f);
    water_.assign(h_ * w_, 0.0f);
    ndvi_.assign(h_ * w_, 0.0f);
    permanent_water_.assign(h_ * w_, 0.0f);
    if (salinity_nc_) {
        salinity_.assign(h_ * w_, 0.0f);
    } else {
        salinity_.clear();  // accessor returns 0.0 for every cell
    }

    const size_t slice = static_cast<size_t>(h_) * static_cast<size_t>(w_);
    for (size_t i = 0; i < slice; ++i) {
        rain_[i]  = (*rain_nc_)[i];
        temp_[i]  = (*water_temp_nc_)[i];
        water_[i] = (*water_frac_nc_)[i];
        ndvi_[i]  = (*ndvi_nc_)[i];
        if (permanent_water_nc_) permanent_water_[i] = (*permanent_water_nc_)[i];
        if (salinity_nc_) salinity_[i] = (*salinity_nc_)[i];
    }
}

void ClimateEngine::set_day(int32_t day) {
    if (n_days_ <= 1) return;  // single-day env: no daily switching
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
        if (permanent_water_nc_) permanent_water_[i] = (*permanent_water_nc_)[offset + i];
        if (salinity_nc_) salinity_[i] = (*salinity_nc_)[offset + i];
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
    clone->salinity_nc_ = salinity_nc_;
    clone->permanent_water_nc_ = permanent_water_nc_;
    
    // Independent single-day arrays (thread-local)
    clone->rain_.assign(h_ * w_, 0.0f);
    clone->temp_.assign(h_ * w_, 25.0f);
    clone->water_.assign(h_ * w_, 0.0f);
    clone->ndvi_.assign(h_ * w_, 0.0f);
    clone->permanent_water_.assign(h_ * w_, 0.0f);
    if (salinity_nc_) {
        clone->salinity_.assign(h_ * w_, 0.0f);
    } else {
        clone->salinity_.clear();
    }
    
    // Initialize day 0
    if (n_days_ > 0 && rain_nc_) {
        const size_t slice = static_cast<size_t>(h_) * static_cast<size_t>(w_);
        for (size_t i = 0; i < slice; ++i) {
            clone->rain_[i]  = (*rain_nc_)[i];
            clone->temp_[i]  = (*water_temp_nc_)[i];
            clone->water_[i] = (*water_frac_nc_)[i];
            clone->ndvi_[i]  = (*ndvi_nc_)[i];
            if (permanent_water_nc_) clone->permanent_water_[i] = (*permanent_water_nc_)[i];
            if (salinity_nc_) clone->salinity_[i] = (*salinity_nc_)[i];
        }
    } else {
        // Static-band engine (env loaded without multi-day NC data, e.g.
        // a default-constructed engine): rain_nc_ is nullptr. Copy the
        // static bands directly — otherwise the
        // clone's water_/rain_/temp_/ndvi_ vectors stay at their
        // zero/fallback defaults, and downstream code that reads them
        // (e.g. build_seed_instructions's viability filter) sees
        // water_frac=0 at every patch and produces 0 viable seeds.
        clone->rain_  = rain_;
        clone->temp_  = temp_;
        clone->water_ = water_;
        clone->ndvi_  = ndvi_;
        clone->salinity_ = salinity_;
        clone->permanent_water_ = permanent_water_;
    }

    // Static grids are shared read-only with the clone (M7.4.1).
    // NOTE: twi_/k_capacity_mult_ may come from either the env NC
    // (load_from_env_nc on the shared engine) or the habitat engine — copy
    // them unconditionally so both branches behave identically.
    clone->twi_ = twi_;
    clone->k_capacity_mult_ = k_capacity_mult_;
    clone->catchment_ratio_ = catchment_ratio_;

    return clone;
}

float ClimateEngine::permanent_water_at(int32_t row, int32_t col) const {
    if (row < 0 || col < 0 || row >= h_ || col >= w_ || permanent_water_.empty()) return 0.0f;
    return permanent_water_[static_cast<size_t>(row) * static_cast<size_t>(w_) + static_cast<size_t>(col)];
}

}  // namespace mal_abm_fast
