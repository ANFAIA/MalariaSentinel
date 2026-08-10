// SPDX-License-Identifier: MIT
// oviposition_seeking.cpp — Spatial oviposition-site-seeking kernel implementation.
//
// The attraction kernel uses an exponential distance decay with
// water-vapour scale (50m) and multiplies by TWI × water_frac
// to rank breeding sites by suitability.

#include "oviposition_seeking.hpp"

#include <algorithm>
#include <cmath>
#include <limits>
#include <utility>
#include <vector>

#include "aoi.hpp"
#include "habitat_engine.hpp"
#include "wire.hpp"

namespace mal_abm_fast {

OvipositionSeekingModel::OvipositionSeekingModel(double scale_m, double radius_m)
    : scale_m_(scale_m), radius_m_(radius_m) {}

std::vector<BreedingAttraction> OvipositionSeekingModel::compute_attraction(
    int32_t row, int32_t col,
    const HabitatEngine& hab,
    const std::vector<PatchState>& patch_states,
    const AOI& aoi,
    float search_radius_m) const
{
    std::vector<BreedingAttraction> result;

    if (search_radius_m < 0.0f) {
        search_radius_m = static_cast<float>(radius_m_);
    }

    const float cell_size_m = static_cast<float>(aoi.resolution_m);

    // Build a lookup from (row, col) → PatchState for activated patches.
    // O(N_patches) per call; acceptable for daily oviposition checks.
    struct ActivatedPatch {
        int64_t patch_id;
        int32_t row;
        int32_t col;
        float   water_frac;
    };
    std::vector<ActivatedPatch> activated;
    for (const auto& ps : patch_states) {
        if (!ps.activated) continue;
        activated.push_back({ps.patch_id, ps.row, ps.col, ps.water_frac});
    }

    // For each activated patch, compute attraction.
    for (const auto& ap : activated) {
        const float dy = (static_cast<float>(ap.row) - static_cast<float>(row)) * cell_size_m;
        const float dx = (static_cast<float>(ap.col) - static_cast<float>(col)) * cell_size_m;
        const float dist_m = std::sqrt(dx * dx + dy * dy);

        if (dist_m > search_radius_m) continue;

        // Look up the static TWI from HabitatPatch.
        float twi = 0.0f;
        try {
            const auto& patch = hab.patch_by_id(ap.patch_id);
            twi = patch.twi_value;
        } catch (...) {
            continue;  // patch not found — skip
        }

        // Water-vapour plume decay.
        const float decay = std::exp(-dist_m / static_cast<float>(scale_m_));

        // Attraction = TWI × water_frac × decay.
        // TWI > 8 is the habitat threshold (wire.hpp HABITAT_MIN_TWI).
        // water_frac > 0 means open water present.
        const float att = twi * ap.water_frac * decay;
        if (att <= 0.0f) continue;

        BreedingAttraction entry;
        entry.distance_m = dist_m;
        entry.attraction = att;
        entry.patch_id   = ap.patch_id;
        entry.row        = ap.row;
        entry.col        = ap.col;
        result.push_back(entry);
    }

    // Sort by descending attraction (best site first).
    std::sort(result.begin(), result.end(),
        [](const BreedingAttraction& a, const BreedingAttraction& b) {
            return a.attraction > b.attraction;
        });

    return result;
}

std::optional<std::pair<int32_t, int32_t>> OvipositionSeekingModel::detect_breeding_cell(
    int32_t row, int32_t col,
    const HabitatEngine& hab,
    const std::vector<PatchState>& patch_states,
    const AOI& aoi,
    double range_m) const
{
    auto attractions = compute_attraction(
        row, col, hab, patch_states, aoi, static_cast<float>(range_m));

    if (attractions.empty()) return std::nullopt;

    // Best site must exceed minimum attraction threshold.
    if (attractions[0].attraction <= 0.3f) return std::nullopt;

    return std::make_pair(attractions[0].row, attractions[0].col);
}

std::pair<int32_t, int32_t> OvipositionSeekingModel::step_toward(
    int32_t from_row, int32_t from_col,
    int32_t target_row, int32_t target_col,
    const AOI& aoi,
    float step_size_m) const
{
    const float cell_size_m = static_cast<float>(aoi.resolution_m);

    const float dy_cells = static_cast<float>(target_row - from_row);
    const float dx_cells = static_cast<float>(target_col - from_col);
    const float dist_m = std::sqrt(
        (dy_cells * cell_size_m) * (dy_cells * cell_size_m) +
        (dx_cells * cell_size_m) * (dx_cells * cell_size_m));

    if (dist_m <= 0.0f) {
        return {from_row, from_col};
    }

    // Step in metres, clamped.
    const float step_m = std::min(step_size_m, dist_m);

    // Convert step to grid cells.
    const float step_r = step_m * dy_cells / dist_m;
    const float step_c = step_m * dx_cells / dist_m;

    // Round to nearest cell.
    int32_t new_row = from_row + static_cast<int32_t>(std::round(step_r));
    int32_t new_col = from_col + static_cast<int32_t>(std::round(step_c));

    return {new_row, new_col};
}

}  // namespace mal_abm_fast
