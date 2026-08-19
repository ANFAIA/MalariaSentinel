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
//   scale           = 100m (CO₂ + body-odour plume, Plan D)
//
// Biological basis:
//   - CO₂ plume: ~60m detection (Giraldo 2023), significant at 70m
//     (Okumu 2013), activates at 100m (Okumu 2013)
//   - Body odour: >CO₂ for long-range (Giraldo 2023)
//   - 300m: 94% malaria reduction when habitats removed (Yang 2009)
//   - Host preference: de facto anthropophily (Takken et al. 1998)
#pragma once

#include <cstdint>
#include <optional>
#include <utility>
#include <vector>

#include "aoi.hpp"
#include "gonotrophic_cycle.hpp"
#include "host_landscape.hpp"
#include "mobility_schedule.hpp"
#include "prng.hpp"
#include "species_params.hpp"

namespace mal_abm_fast {

/// Activity-epsilon for the phase gate (Fase 4).
inline constexpr float kPhaseActivityEpsilon = 0.001f;

/// Phase-activity gate (Fase 4): true iff the species is active in the
/// given phase, i.e. `sp.activity_weights[phase] > epsilon`.  Callers
/// (engine step per phase) use this to decide whether host-seeking and
/// directed movement run during a phase for a species.
inline bool phase_active(const SpeciesParams& sp, TimePhase phase) {
    return sp.activity_weights[static_cast<size_t>(phase)] > kPhaseActivityEpsilon;
}

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
    ///
    /// `search_radius_m` defaults to a -1.0f sentinel: when species
    /// params are set (set_species_params) the species
    /// `host_seeking_radius_m` is used; otherwise 300m
    /// (HOST_SEEKING_RADIUS_M).  Any positive value overrides both.
    std::vector<HostAttraction> compute_attraction(
        int32_t mosquito_row, int32_t mosquito_col,
        const HostLandscape& landscape,
        const AOI& aoi,
        float search_radius_m = -1.0f) const;

    /// Configure the model with per-species host preferences and
    /// host-seeking kernel (Fase 3/4).  Rebuilds the internal
    /// HostPreference from `sp.pref_human / pref_cattle / pref_goat /
    /// pref_sheep / pref_wildlife`, uses `sp.host_seeking_scale_m` for
    /// the distance decay, and `sp.host_seeking_radius_m` as the
    /// default compute_attraction radius.  The default HostPreference
    /// path remains the fallback until this is called (backward compat).
    void set_species_params(const SpeciesParams& sp);

    /// True after set_species_params() has been called.
    bool has_species_params() const { return has_species_params_; }

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

    /// Detect the best host cell within `range_m` of the mosquito.
    /// Returns the (row, col) of the cell with highest attraction
    /// where attraction > 0.5, or nullopt if no host found.
    /// O(N) per call; caches results per (row, col, day).
    std::optional<std::pair<int32_t, int32_t>> detect_host_cell(
        int32_t mosquito_row, int32_t mosquito_col,
        const HostLandscape& landscape,
        const AOI& aoi,
        double range_m = 2000.0) const;

    /// One directed movement step toward the strongest detected host
    /// cell (Fase 3: "movimiento dirigido del mosquito", no external
    /// Plan D dependency).  Reuses detect_host_cell (range 2000m) and
    /// approach_vector (step_size_m, default 50m): if a host cell is
    /// detected, returns the new (row, col) after one step (rounded to
    /// the nearest cell, clamped to the grid); else nullopt.  Pure
    /// function — the integration calls it once per phase for
    /// HOST_SEEKING mosquitoes within detection range.
    std::optional<std::pair<int32_t, int32_t>> step_toward_host(
        int32_t row, int32_t col,
        const HostLandscape& eff_landscape,
        const AOI& aoi,
        float step_size_m = 50.0f) const;

private:
    HostPreference pref_;
    SpeciesParams species_;
    bool has_species_params_ = false;
    float scale_m_ = HOST_SEEKING_SCALE_M;

    /// Compute per-host-type attraction for one cell.
    float cell_attraction(
        const HostCell& cell, float dist_m) const;

    /// Find the dominant host type in a cell.
    HostType dominant_host(const HostCell& cell) const;
};

}  // namespace mal_abm_fast
