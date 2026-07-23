// SPDX-License-Identifier: MIT
// host_seeking.cpp — Spatial host-seeking kernel implementation.
//
// The attraction kernel uses an exponential distance decay:
//   A_j = Σ_k (host_count_jk × pref_k × indoor_mod × urban_mod × exp(-d/scale))
//
// Host selection uses weighted roulette: cumulative sum of attraction
// scores, uniform draw, binary search.
//
// Approach vector: one step toward the target cell, clamped to step_size_m.

#include "host_seeking.hpp"

#include <algorithm>
#include <cmath>
#include <utility>
#include <vector>

#include "aoi.hpp"
#include "gonotrophic_cycle.hpp"
#include "host_landscape.hpp"
#include "prng.hpp"
#include "wire.hpp"

namespace mal_abm_fast {

// ---------------------------------------------------------------------------
// Private helpers
// ---------------------------------------------------------------------------

float HostSeekingModel::cell_attraction(
    const HostCell& cell, float dist_m) const
{
    // Exponential distance decay: scale = 35m (CO₂ plume detection).
    constexpr float kScale = 35.0f;
    const float decay = std::exp(-dist_m / kScale);

    // Indoor modifier: endophilic species get a boost indoors.
    // An. gambiae: 72% endophilic → indoor modifier = 1 + indoor_frac × 0.72
    const float indoor_mod = 1.0f + cell.indoor_fraction * 0.72f;

    // Urban modifier: concentrated CO₂ in settlements.
    const float urban_mod = 1.0f + 0.2f * cell.urbanicity;

    // Weighted sum across host types.
    float att = 0.0f;
    att += cell.humans_present  * pref_.human    * indoor_mod * urban_mod;
    att += cell.cattle_present  * pref_.cattle   * indoor_mod * urban_mod;
    att += cell.goats_present   * pref_.goat     * indoor_mod * urban_mod;
    att += cell.sheep_present   * pref_.sheep    * indoor_mod * urban_mod;
    att += cell.wildlife_proxy  * pref_.wildlife * indoor_mod * urban_mod;

    return att * decay;
}

HostType HostSeekingModel::dominant_host(const HostCell& cell) const {
    // Find the host type with the highest count × preference.
    struct Score { HostType type; float score; };
    Score scores[] = {
        {HostType::HUMAN,  cell.humans_present  * pref_.human},
        {HostType::CATTLE, cell.cattle_present  * pref_.cattle},
        {HostType::GOAT,   cell.goats_present   * pref_.goat},
        {HostType::SHEEP,  cell.sheep_present   * pref_.sheep},
        {HostType::OTHER,  cell.wildlife_proxy  * pref_.wildlife},
    };
    HostType best = HostType::HUMAN;
    float best_score = 0.0f;
    for (const auto& s : scores) {
        if (s.score > best_score) {
            best_score = s.score;
            best = s.type;
        }
    }
    return best;
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

std::vector<HostAttraction> HostSeekingModel::compute_attraction(
    int32_t mosquito_row, int32_t mosquito_col,
    const HostLandscape& landscape,
    const AOI& aoi,
    float search_radius_m) const
{
    std::vector<HostAttraction> result;

    const int32_t grid_h = landscape.h();
    const int32_t grid_w = landscape.w();
    if (grid_h <= 0 || grid_w <= 0) return result;

    // Cell size in metres.
    const float cell_size_m = static_cast<float>(
        aoi.resolution_m);

    // Convert search radius to grid cells (integer window).
    const int32_t search_cells = static_cast<int32_t>(
        std::ceil(search_radius_m / cell_size_m));

    const int32_t r_min = std::max(0, mosquito_row - search_cells);
    const int32_t r_max = std::min(grid_h - 1, mosquito_row + search_cells);
    const int32_t c_min = std::max(0, mosquito_col - search_cells);
    const int32_t c_max = std::min(grid_w - 1, mosquito_col + search_cells);

    for (int32_t r = r_min; r <= r_max; ++r) {
        for (int32_t c = c_min; c <= c_max; ++c) {
            const HostCell cell = landscape.at(r, c);

            // Centre-to-centre distance in metres.
            const float dy = (static_cast<float>(r) - static_cast<float>(mosquito_row)) * cell_size_m;
            const float dx = (static_cast<float>(c) - static_cast<float>(mosquito_col)) * cell_size_m;
            const float dist_m = std::sqrt(dx * dx + dy * dy);

            if (dist_m > search_radius_m) continue;

            const float att = cell_attraction(cell, dist_m);
            if (att <= 0.0f) continue;

            HostAttraction entry;
            entry.distance_m   = dist_m;
            entry.attraction   = att;
            entry.primary_host = dominant_host(cell);
            result.push_back(entry);
        }
    }

    // Sort by descending attraction (highest first).
    std::sort(result.begin(), result.end(),
        [](const HostAttraction& a, const HostAttraction& b) {
            return a.attraction > b.attraction;
        });

    return result;
}

HostType HostSeekingModel::select_host(
    const std::vector<HostAttraction>& attractions,
    Prng& rng) const
{
    if (attractions.empty()) {
        return HostType::HUMAN;  // fallback
    }

    // Weighted roulette: cumulative sum of attraction scores.
    float total = 0.0f;
    for (const auto& a : attractions) {
        total += a.attraction;
    }
    if (total <= 0.0f) {
        return attractions[0].primary_host;
    }

    const float draw = static_cast<float>(rng.uniform_double() * total);
    float cumulative = 0.0f;
    for (const auto& a : attractions) {
        cumulative += a.attraction;
        if (cumulative >= draw) {
            return a.primary_host;
        }
    }

    // Fallback (floating-point edge case).
    return attractions.back().primary_host;
}

std::pair<float, float> HostSeekingModel::approach_vector(
    int32_t mosquito_row, int32_t mosquito_col,
    int32_t target_row, int32_t target_col,
    const AOI& aoi,
    float step_size_m) const
{
    const float cell_size_m = static_cast<float>(aoi.resolution_m);

    const float dy_cells = static_cast<float>(target_row - mosquito_row);
    const float dx_cells = static_cast<float>(target_col - mosquito_col);
    const float dist_m = std::sqrt(
        (dy_cells * cell_size_m) * (dy_cells * cell_size_m) +
        (dx_cells * cell_size_m) * (dx_cells * cell_size_m));

    if (dist_m <= 0.0f) {
        return {0.0f, 0.0f};
    }

    // Step in metres, clamped.
    const float step_m = std::min(step_size_m, dist_m);

    // Return step in grid cells along the direction toward target.
    return {
        step_m * dy_cells / dist_m,
        step_m * dx_cells / dist_m
    };
}

}  // namespace mal_abm_fast
