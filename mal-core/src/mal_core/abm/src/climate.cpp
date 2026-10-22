// SPDX-License-Identifier: MIT
// climate.cpp — ClimateEngine implementation (contract v3.0 env NC).
//
// The ClimateEngine is a thin wrapper over the env_reader helper: it
// delegates the actual file IO to `env_reader::read_env_nc` and
// stores the resulting flat bands in row-major float32 vectors.
//
// `*_at(row, col)` accessors are bounds-checked; out-of-bounds returns
// 0 (rain) or the border cell's temperature for temp (clamped edge
// lookup — NaN pixels were imputed at load time, see impute_temp_nans).
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
// region is covered. (The elderly per-cell constant fallback was
// removed on 2026-10-13; preserve imputation — the imputed values
// follow the seasonal cycle instead of pinning a fixed fallback.)
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
    // its degenerate guard for this all-NaN case.
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
    if (!std::isfinite(static_cast<double>(T))) return 25.0f;
    return T;
}

float ClimateEngine::salinity_at(int32_t row, int32_t col) const {
    // Empty salinity_ => no salinity data (pre-salinity NC): every cell
    // uses the configured freshwater anchor (aquatic_stages.
    // salinity_missing_psu; review-a3 P1-3).
    const float missing = static_cast<float>(
        load_config().aquatic_stages.salinity_missing_psu);
    if (salinity_.empty()) return missing;
    if (h_ <= 0 || w_ <= 0) return missing;
    if (row < 0 || row >= h_ || col < 0 || col >= w_) return missing;
    return salinity_[Idx(row, col, w_)];
}

void ClimateEngine::load_from_env_nc(const std::string& path,
                                     const AOI& aoi,
                                     int32_t max_days) {
    (void)aoi;
    env_reader::DailyEnvBands bands = env_reader::read_env_nc(path, max_days);

    // Impute NaN temperature pixels once, at load time, across every
    // day slice (out-of-coverage / sea-mask pixels are NaN in the NC).
    if (!bands.air_temp_c.empty()) {
        const size_t tslice = static_cast<size_t>(bands.h) *
                              static_cast<size_t>(bands.w);
        for (int32_t d = 0; d < bands.n_days; ++d) {
            impute_temp_nans(bands.air_temp_c.data() +
                             static_cast<size_t>(d) * tslice,
                             bands.h, bands.w);
        }
    }

    h_      = bands.h;
    w_      = bands.w;
    n_days_ = bands.n_days;
    base_day_ = 0;
    cur_day_ = 0;

    // Wrap multi-day buffers in shared_ptr for thread-safe sharing
    rain_nc_      = std::make_shared<std::vector<float>>(std::move(bands.rainfall));
    air_temp_nc_  = std::make_shared<std::vector<float>>(std::move(bands.air_temp_c));
    if (!bands.salinity_ppt.empty()) {
        salinity_nc_ = std::make_shared<std::vector<float>>(
            std::move(bands.salinity_ppt));
    } else {
        salinity_nc_.reset();
    }

    // Static habitat features — bound exactly when they match the grid.
    auto move_static = [&](std::vector<float>& src, std::vector<float>& dst,
                           const char* name) {
        if (src.size() == static_cast<size_t>(h_) * static_cast<size_t>(w_)) {
            dst = std::move(src);
        } else {
            dst.clear();
            std::cout << "ClimateEngine: static band '" << name
                      << "' missing or mis-shaped; treated as 0.\n";
        }
    };
    move_static(bands.jrc_persistent,     jrc_persistent_,     "jrc_persistent");
    move_static(bands.lc_built,           lc_built_,           "lc_built");
    move_static(bands.lc_wetland,         lc_wetland_,         "lc_wetland");
    move_static(bands.lc_open_plus_water, lc_open_plus_water_, "lc_open_plus_water");
    move_static(bands.lc_crop,            lc_crop_,            "lc_crop");
    if (!jrc_persistent_.empty()) {
        std::cout << "ClimateEngine: env NC carries the five static habitat "
                  << "planes (" << h_ << "x" << w_ << ")\n";
    }

    // Populate single-day accessors for absolute band 0.
    const size_t slice = static_cast<size_t>(h_) * static_cast<size_t>(w_);
    rain_.assign(slice, 0.0f);
    temp_.assign(slice, 25.0f);
    salinity_.assign(salinity_nc_ ? slice : 0, 0.0f);
    for (size_t i = 0; i < slice; ++i) {
        rain_[i] = (*rain_nc_)[i];
        temp_[i] = (*air_temp_nc_)[i];
        if (salinity_nc_) salinity_[i] = (*salinity_nc_)[i];
    }
}

void ClimateEngine::set_base_day(int32_t band_index) {
    if (band_index < 0) band_index = 0;
    if (band_index > n_days_ - 1) band_index = n_days_ - 1;
    base_day_ = band_index;
}

void ClimateEngine::set_day(int32_t day) {
    if (n_days_ <= 1) return;  // single-day env: no daily switching
    // `day` is relative to base_day_: negative values read warm-up
    // bands, values >= 0 read simulation bands.
    int32_t band = base_day_ + day;
    if (band < 0) band = 0;
    if (band >= n_days_) band = n_days_ - 1;
    cur_day_ = band;

    const size_t slice = static_cast<size_t>(h_) * static_cast<size_t>(w_);
    const size_t offset = static_cast<size_t>(cur_day_) * slice;
    for (size_t i = 0; i < slice; ++i) {
        rain_[i] = (*rain_nc_)[offset + i];
        temp_[i] = (*air_temp_nc_)[offset + i];
        if (salinity_nc_) salinity_[i] = (*salinity_nc_)[offset + i];
    }
}

std::vector<float> ClimateEngine::rain_band(int32_t band_index) const {
    const size_t slice = static_cast<size_t>(h_) * static_cast<size_t>(w_);
    std::vector<float> out(slice, 0.0f);
    if (!rain_nc_ || slice == 0) return out;
    if (band_index < 0) band_index = 0;
    if (band_index >= n_days_) band_index = n_days_ - 1;
    const size_t offset = static_cast<size_t>(band_index) * slice;
    for (size_t i = 0; i < slice; ++i) out[i] = (*rain_nc_)[offset + i];
    return out;
}

std::shared_ptr<ClimateEngine> ClimateEngine::clone_for_thread() const {
    auto clone = std::make_shared<ClimateEngine>();
    clone->h_ = h_;
    clone->w_ = w_;
    clone->n_days_ = n_days_;
    clone->base_day_ = base_day_;
    clone->cur_day_ = 0;

    // Share the multi-day data (read-only, thread-safe)
    clone->rain_nc_ = rain_nc_;
    clone->air_temp_nc_ = air_temp_nc_;
    clone->salinity_nc_ = salinity_nc_;

    // Independent single-day arrays (thread-local)
    const size_t slice = static_cast<size_t>(h_) * static_cast<size_t>(w_);
    clone->rain_.assign(slice, 0.0f);
    clone->temp_.assign(slice, 25.0f);
    if (salinity_nc_) {
        clone->salinity_.assign(slice, 0.0f);
    } else {
        clone->salinity_.clear();
    }

    // static features are read-only; share by copy (bounded memory: 5 planes)
    clone->jrc_persistent_ = jrc_persistent_;
    clone->lc_built_ = lc_built_;
    clone->lc_wetland_ = lc_wetland_;
    clone->lc_open_plus_water_ = lc_open_plus_water_;
    clone->lc_crop_ = lc_crop_;
    return clone;
}

}  // namespace mal_abm_fast
