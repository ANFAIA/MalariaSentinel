// SPDX-License-Identifier: MIT
// mosquito_submodel.hpp — Polars-style vectorised mosquito half of the ABM.
//
// The submodel owns the entire mosquito population as a `MosquitoSoA`.
// The constructor seeds `round(n_patches * k_per_patch * init_frac)`
// larvae with round-robin patch assignment. `advance_day` is the
// per-day orchestrator; the 7 operations it calls are listed below in
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
#include "seeding.hpp"
#include "wire.hpp"
#include "mosquito_state.hpp"

namespace mal_abm_fast {

/// Per-day population statistics, populated by advance_day().
struct DailyStats {
    int64_t day             = 0;
    int64_t n_alive         = 0;
    int64_t n_adults        = 0;
    int64_t n_larvae        = 0;
    int64_t n_births        = 0;
    int64_t n_deaths        = 0;
    int64_t n_maturation    = 0;
    float   eip_frac        = 0.0f;  // fraction of adults with eip >= threshold
};

class MosquitoSubmodel {
public:
    MosquitoSubmodel() = default;

    // Legacy / backward-compat constructor: seed
    // `round(n_patches * k_per_patch * init_frac)` larvae, with
    // round-robin patch assignment. `lon`/`lat` start at 0 (a
    // placeholder — the coord subagent's `aggregate_density` only
    // reads `patch_id`, not lon/lat; the first dispersal step
    // overwrites them).
    MosquitoSubmodel(int32_t n_patches, int32_t k_per_patch,
                     float init_frac, uint64_t seed);

    // Detection-based constructor: seed a mix of adults and
    // larvae at specific patches via the supplied SeedInstruction
    // list. Adults start with `eip_progress = EIP_THRESHOLD_GD` so
    // they are ready to disperse on day 1; larvae start with
    // `eip_progress = 0` and must accumulate growing-degree-days
    // before promotion. The `k_per_patch` is still required for
    // the per-day `birth()` step (binomial draw per active patch).
    MosquitoSubmodel(int32_t n_patches, int32_t k_per_patch,
                     const std::vector<SeedInstruction>& instructions,
                     uint64_t seed);

    // Read-only access to the SoA (the submodel owns it; the
    // coordinator reads it for density aggregation).
    const MosquitoSoA& soa() const { return soa_; }

    // Total live agent count (= soa().n_alive).
    int64_t total_agents() const { return soa_.n_alive; }

    // Per-day orchestrator. Calls the 7 ops in order:
    //   1. larva_mortality_inactive(patch_states)
    //   2.5. larva_mortality_density(patch_states)
    //   2. larva_growth(patch_states)
    //   3. larva_to_adult()
    //   4. adult_dispersal()
    //   6. adult_mortality(patch_states)
    //   5. birth(aoi, patch_states)
    void advance_day(const AOI& aoi,
                     const std::vector<PatchState>& patch_states);

    /// Per-day stats from the most recent advance_day() call.
    const DailyStats& last_day_stats() const { return last_day_stats_; }

    // -- debug instrumentation (M7.0 population-crash investigation) -----
    // When enabled, advance_day() writes one stderr line per day with
    // the day's population counts, the Lardeux p_d at the seeding
    // patch (a strong proxy for whether the calibrated mortality
    // model is being applied vs. the 0.90 fallback), and the
    // per-day births / deaths / larva-to-adult maturations. Rate-
    // limited: every day for the first 10 days, then every 5 days.
    // Default off — does not change the per-day RNG stream or the
    // state COG output. Use for diagnosing crashes like M7.0's
    // "500 adults → 20-24 in 30 days" without rerunning the ABM.
    void set_debug_population(bool on) { debug_population_ = on; }

    // Record the (patch_id, row, col) used for the most recent
    // detection-based seeding pass. The advance_day() debug log
    // reports the Lardeux p_d at this cell on each logged day, which
    // pinpoints whether the seeding patch is hitting the mortality
    // floor (T too low / NaN) or the calibrated Lardeux curve.
    void set_debug_seeding_patch(int64_t patch_id, int32_t row, int32_t col) {
        debug_seeding_pid_  = patch_id;
        debug_seeding_row_  = row;
        debug_seeding_col_  = col;
    }

    // -- 7 per-day operations -----------------------------------------------

    // 1. Remove larvae at patches that are activated=false.
    //    Adults are unaffected (they dispersed away from the patch
    //    on a previous day, so the per-patch mortality rule only
    //    applies to the in-patch larvae pool).
    void larva_mortality_inactive(const std::vector<PatchState>& patch_states);

    // 2.5. Density-dependent larva mortality (Beverton-Holt) at active patches.
    void larva_mortality_density(const std::vector<PatchState>& patch_states);

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
    void adult_dispersal(const AOI& aoi);

    // 6. Adult mortality — Lardeux thermo-dependent daily survival.
    void adult_mortality(const std::vector<PatchState>& patch_states);

    // 5. binomial(n_adults/2, BIRTH_FECUNDITY) per active patch; new lon/lat =
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

    DailyStats last_day_stats_{};

    // -- debug instrumentation state (see set_debug_population) -----
    bool     debug_population_      = false;
    int64_t  day_counter_           = 0;
    int64_t  debug_seeding_pid_     = -1;
    int32_t  debug_seeding_row_     = 0;
    int32_t  debug_seeding_col_     = 0;
};

}  // namespace mal_abm_fast
