// SPDX-License-Identifier: MIT
// mosquito_submodel.hpp — Polars-style vectorised mosquito half of the ABM.
//
// The submodel owns the entire mosquito population as a `MosquitoSoA`.
// The constructor seeds `round(n_patches * k_per_patch * init_frac)`
// larvae with round-robin patch assignment. `advance_day` is the
// per-day orchestrator; the 5 operations it calls are listed below in
// the exact order they execute (matching the Python
// `mosquito_submodel.advance_day`).
//
// Determinism
// -----------
// The submodel's `Prng` is the single RNG source for larva mortality
// (none — deterministic), larva growth (none), EIP completion (none),
// adult dispersal (clipped Gaussian draws), and birth (binomial draws
// per active patch). Two runs with the same `--seed` and the same
// `advance_day` call sequence produce identical populations.
#pragma once

#include <cstdint>
#include <tuple>
#include <utility>
#include <vector>

#include "aoi.hpp"
#include "prng.hpp"
#include "wire.hpp"
#include "mosquito_state.hpp"

namespace mal_abm_fast {

class MosquitoSubmodel {
public:
    MosquitoSubmodel() = default;

    // Seed `round(n_patches * k_per_patch * init_frac)` larvae, with
    // round-robin patch assignment. `lon`/`lat` start at 0 (a
    // placeholder — the coord subagent's `aggregate_density` only
    // reads `patch_id`, not lon/lat; the first dispersal step
    // overwrites them).
    MosquitoSubmodel(int32_t n_patches, int32_t k_per_patch,
                     float init_frac, uint64_t seed);

    // Read-only access to the SoA (the submodel owns it; the
    // coordinator reads it for density aggregation).
    const MosquitoSoA& soa() const { return soa_; }

    // Total live agent count (= soa().n_alive).
    int64_t total_agents() const { return soa_.n_alive; }

    // Per-day orchestrator. Calls the 5 ops in order:
    //   1. larva_mortality_inactive(patch_states)
    //   2. larva_growth(patch_states)
    //   3. larva_to_adult()
    //   4. adult_dispersal()
    //   5. birth(aoi, patch_states)
    void advance_day(const AOI& aoi,
                     const std::vector<PatchState>& patch_states);

    // -- 5 per-day operations -----------------------------------------------

    // 1. Remove larvae at patches that are activated=false.
    //    Adults are unaffected (they dispersed away from the patch
    //    on a previous day, so the per-patch mortality rule only
    //    applies to the in-patch larvae pool).
    void larva_mortality_inactive(const std::vector<PatchState>& patch_states);

    // 2. At active patches: stage_age += 1, eip_progress += max(0, T - EIP_BASE_C).
    //    EIP uses the post Mordecai-inverse deg C from PatchState.temp_d.
    void larva_growth(const std::vector<PatchState>& patch_states);

    // 3. Promote larva -> adult when eip_progress >= EIP_THRESHOLD_GD.
    //    The promoted agents' `lon`/`lat` are written to the patch
    //    cell centre (via aoi + transform.xy) so the next dispersal
    //    step has a valid origin.
    // 3. Promote larva -> adult when eip_progress >= EIP_THRESHOLD_GD.
    //    Also writes the promoted agent's lon/lat to the patch cell
    //    centre (via aoi + cell math) so the suitability grid places
    //    the new adult at the correct cell. Mirrors the Python
    //    reference (mosquito_submodel.py:_larva_to_adult + birth
    //    cell-centre placement).
    void larva_to_adult(const AOI& aoi,
                        const std::vector<PatchState>& patch_states);

    // 4. 20% of adults move by clipped Gaussian (2 km cap). Uses
    //    the submodel's Prng so the stream is reproducible.
    void adult_dispersal();

    // 5. binomial(K, BIRTH_RATE) per active patch; new lon/lat =
    //    patch cell centre. New agents start as larvae with
    //    eip_progress = 0, stage_age = 0, uid = soa().next_uid++.
    void birth(const AOI& aoi, const std::vector<PatchState>& patch_states);

    // -- queries used by the coordinator -----------------------------------

    // density_by_patch: vector of (patch_id, count), one row per
    // active patch with at least one agent. The coordinator uses
    // this to build the (H, W) density grid via bincount over
    // (row, col).
    std::vector<std::pair<int64_t, int64_t>>
    density_by_patch() const;

    // adult_density_by_cell: vector of (row, col, n_adults) where
    // row/col are computed by snapping each adult's post-dispersal
    // (lon, lat) to the AOI grid (clamp to grid bounds). The
    // coordinator uses this to build the (H, W) suitability grid.
    std::vector<std::tuple<int32_t, int32_t, int64_t>>
    adult_density_by_cell(const AOI& aoi) const;

private:
    MosquitoSoA  soa_;
    Prng         rng_;
    int32_t      k_per_patch_ = K_PER_PATCH_DEFAULT;
};

}  // namespace mal_abm_fast
