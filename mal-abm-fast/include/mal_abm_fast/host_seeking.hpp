// SPDX-License-Identifier: MIT
// host_seeking.hpp — Spatial host-seeking kernel for An. gambiae.
//
// HostSeekingModel computes a distance-weighted attraction field over
// nearby cells and selects a host type stochastically using
// anthropophilic weights (99% human, 0.5% cattle, 0.3% goat, 0.1%
// sheep, 0.1% wildlife).
//
// Attraction formula (per cell j, per host type k):
//   A_jk = host_count_jk × indoor_modifier × urban_modifier
//          × exp(-dist_j / scale)
//
// where:
//   indoor_modifier = 1 + indoor_fraction × (endophilic_ratio - 1)
//   urban_modifier  = 1 + 0.2 × urbanicity  (urban hosts are more
//                      detectable due to concentrated CO₂)
//   scale           = 35m (baseline detection distance for CO₂ plume)
//
// Biological basis:
//   - CO₂ plume: km-scale detection, modelled by exponential decay
//   - Thermal plume: m-scale, not modelled explicitly (subsumed into
//     indoor_modifier for close-range detection)
//   - Host preference: de facto anthropophily (Takken et al. 1998)
#pragma once

#include <cstdint>
#include <utility>
#include <vector>

#include "aoi.hpp"
#include "gonotrophic_cycle.hpp"
#include "host_landscape.hpp"
#include "prng.hpp"

namespace mal_abm_fast {

/// Attraction score for one cell.  Returned by compute_attraction().
struct HostAttraction {
    float distance_m   = 0.0f;   // Euclidean distance from mosquito to cell centre
    float attraction   = 0.0f;   // combined attraction score (all host types)
    HostType primary_host = HostType::HUMAN;  // dominant host type at this cell
};

/// Anthropophilic / zoophilic weights for An. gambiae s.s.
/// Defaults: Takken et al. 1998, continuous choice experiments.
struct HostPreference {
    float human    = 0.99f;
    float cattle   = 0.005f;
    float goat     = 0.003f;
    float sheep    = 0.001f;
    float wildlife = 0.001f;
};

/// Spatial host-seeking model.
///
/// Typical usage (called from the nightly host-seeking loop):
/// ```cpp
/// HostSeekingModel model;
/// auto attractions = model.compute_attraction(mos_row, mos_col, landscape, aoi);
/// HostType host = model.select_host(attractions, rng);
/// auto [dr, dc] = model.approach_vector(mos_row, mos_col, ...);
/// ```
class HostSeekingModel {
public:
    /// Compute attraction field for cells within `search_radius_m` of
    /// the mosquito at (mosquito_row, mosquito_col).  Returns one
    /// HostAttraction per nearby cell with attraction > 0, sorted by
    /// descending attraction.
    std::vector<HostAttraction> compute_attraction(
        int32_t mosquito_row, int32_t mosquito_col,
        const HostLandscape& landscape,
        const AOI& aoi,
        float search_radius_m = 70.0f) const;

    /// Stochastically select a host type from the attraction field.
    /// Returns the dominant host type if the field is empty.
    HostType select_host(
        const std::vector<HostAttraction>& attractions,
        Prng& rng) const;

    /// Compute one step (d_row, d_col) toward a target cell.
    /// Returns (d_row, d_col) in grid units, clamped to step_size_m.
    std::pair<float, float> approach_vector(
        int32_t mosquito_row, int32_t mosquito_col,
        int32_t target_row, int32_t target_col,
        const AOI& aoi,
        float step_size_m = 50.0f) const;

    /// Mutable access to host preference weights.
    HostPreference& preference() { return pref_; }
    const HostPreference& preference() const { return pref_; }

private:
    HostPreference pref_;

    /// Compute per-host-type attraction for one cell.
    float cell_attraction(
        const HostCell& cell, float dist_m) const;

    /// Find the dominant host type in a cell.
    HostType dominant_host(const HostCell& cell) const;
};

}  // namespace mal_abm_fast
