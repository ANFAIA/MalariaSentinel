// SPDX-License-Identifier: MIT
// oviposition_seeking.hpp — Spatial oviposition-site-seeking kernel.
//
// OvipositionSeekingModel computes a distance-weighted attraction
// field over nearby activated habitat patches for gravid female
// mosquitoes. The kernel uses water-vapour + VOC plume decay
// (Okal 2013, Lindh 2015) to model active site detection.
//
// Attraction formula (per patch j):
//   A_j = twi_value_j × water_frac_j × exp(-dist_j / scale)
//
// where:
//   scale = 50m (water-vapour plume decay, Okal 2013)
//   twi_value = static Topographic Wetness Index from HabitatPatch
//   water_frac = dynamic open-water fraction from PatchState
//
// Biological basis:
//   - Water vapour: ≥5m detection (Okal 2013 semi-field)
//   - Cedrol/VOCs: 9+m attraction (Lindh 2015 semi-field)
//   - Visual cues: polarised light from water surfaces
//   - 500m search radius: scaled from semi-field to landscape
#pragma once

#include <cstdint>
#include <optional>
#include <utility>
#include <vector>

#include "aoi.hpp"
#include "habitat_engine.hpp"
#include "wire.hpp"

namespace mal_abm_fast {

/// Forward declaration — PatchState is in wire.hpp.
struct PatchState;

/// Attraction score for one breeding site.
struct BreedingAttraction {
    float   distance_m = 0.0f;
    float   attraction = 0.0f;
    int64_t patch_id   = -1;
    int32_t row        = 0;
    int32_t col        = 0;
};

/// Spatial oviposition-site-seeking model.
///
/// Typical usage (called from the nightly oviposition loop):
/// ```cpp
/// OvipositionSeekingModel model(50.0, 500.0);
/// auto target = model.detect_breeding_cell(row, col, hab, patch_states, aoi, 2000.0);
/// if (target) {
///     auto [dr, dc] = model.step_toward(row, col, target->first, target->second, aoi);
/// }
/// ```
class OvipositionSeekingModel {
public:
    explicit OvipositionSeekingModel(
        double scale_m = OVIPOSITION_SCALE_M,
        double radius_m = OVIPOSITION_RADIUS_M);

    /// Compute attraction field for patches within `search_radius_m`
    /// of the mosquito at (row, col). Uses HabitatPatch TWI and
    /// PatchState water_frac for each activated patch.
    std::vector<BreedingAttraction> compute_attraction(
        int32_t row, int32_t col,
        const HabitatEngine& hab,
        const std::vector<PatchState>& patch_states,
        const AOI& aoi,
        float search_radius_m = -1.0f) const;

    /// Detect the best breeding site within `range_m`.
    /// Returns the (row, col) of the patch with highest attraction
    /// where attraction > 0.3, or nullopt if no site found.
    std::optional<std::pair<int32_t, int32_t>> detect_breeding_cell(
        int32_t row, int32_t col,
        const HabitatEngine& hab,
        const std::vector<PatchState>& patch_states,
        const AOI& aoi,
        double range_m = 2000.0) const;

    /// Compute one step toward a target breeding site.
    /// Returns (new_row, new_col) in grid units, clamped to step_size_m.
    std::pair<int32_t, int32_t> step_toward(
        int32_t from_row, int32_t from_col,
        int32_t target_row, int32_t target_col,
        const AOI& aoi,
        float step_size_m = 50.0f) const;

private:
    double scale_m_;
    double radius_m_;
};

}  // namespace mal_abm_fast
