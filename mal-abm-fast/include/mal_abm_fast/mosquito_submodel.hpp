// SPDX-License-Identifier: MIT
// mosquito_submodel.hpp — Vectorised mosquito half of the ABM.
//
// The submodel owns the mosquito population as a `MosquitoSoA`
// (adults only) and an `AquaticCohortBank` (eggs, larvae, pupas).
// The constructor seeds adults + eggs. `advance_day` is the
// per-day orchestrator:
//
//   1. aquatic_cohort_bank.advance_day() — egg/larva/pupa lifecycle
//   2. aquatic_cohort_bank.collect_emergence() — pupa → adult
//   3. Add emerged adults to MosquitoSoA
//   4. adult_dispersal()
//   5. adult_mortality()
//
// Determinism
// -----------
// The submodel's `Prng` is the single RNG source for adult dispersal
// (clipped Gaussian draws). Aquatic lifecycle uses deterministic
// development rates and binomial mortality.
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
#include "aquatic_stages.hpp"
#include "aquatic_cohort_bank.hpp"

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
    int64_t n_females       = 0;
    int64_t n_males         = 0;
    int64_t n_host_seeking  = 0;
    float   eip_frac        = 0.0f;  // fraction of adults with eip >= threshold
    int64_t n_eggs          = 0;     // aquatic cohort bank: egg count
    int64_t n_pupae         = 0;     // aquatic cohort bank: pupa count
    int64_t n_emerged       = 0;     // adults emerged this day
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
                     float init_frac, uint64_t seed,
                     RuntimeOverrides overrides = {});

    // Detection-based constructor: seed a mix of adults and
    // larvae at specific patches via the supplied SeedInstruction
    // list. Adults start with `development_progress = EIP_THRESHOLD_GD` so
    // they are ready to disperse on day 1; larvae start with
    // `development_progress = 0` and must accumulate growing-degree-days
    // before promotion. The `k_per_patch` is still required for
    // the per-day `birth()` step (binomial draw per active patch).
    MosquitoSubmodel(int32_t n_patches, int32_t k_per_patch,
                     const std::vector<SeedInstruction>& instructions,
                     uint64_t seed,
                     RuntimeOverrides overrides = {});

    // Read-only access to the SoA (the submodel owns it; the
    // coordinator reads it for density aggregation).
    const MosquitoSoA& soa() const { return soa_; }

    // Read-only access to the aquatic cohort bank.
    const AquaticCohortBank& cohort_bank() const { return cohort_bank_; }

    // Mutable access to the aquatic cohort bank (for seeding eggs).
    AquaticCohortBank& cohort_bank_mutable() { return cohort_bank_; }

    // Total live agent count (= soa().n_alive).
    int64_t total_agents() const { return soa_.n_alive; }

    // Per-day orchestrator. New G3 lifecycle flow:
    //   1. cohort_bank_.advance_day() — aquatic development + mortality
    //   2. cohort_bank_.collect_emergence() — pupa → adult events
    //   3. Add emerged adults to MosquitoSoA
    //   4. adult_dispersal()
    //   5. adult_mortality()
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

    // -- per-day operations -----------------------------------------------

    // 1. Adult dispersal: 5% of adults move by clipped Gaussian.
    void adult_dispersal(const AOI& aoi);

    // 2. Adult mortality — Lardeux thermo-dependent daily survival.
    void adult_mortality(const std::vector<PatchState>& patch_states);

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
    AquaticCohortBank cohort_bank_;
    Prng         rng_;
    int32_t      k_per_patch_ = K_PER_PATCH_DEFAULT;
    RuntimeOverrides overrides_;

    DailyStats last_day_stats_{};

    // -- debug instrumentation state (see set_debug_population) -----
    bool     debug_population_      = false;
    int64_t  day_counter_           = 0;
    int64_t  debug_seeding_pid_     = -1;
    int32_t  debug_seeding_row_     = 0;
    int32_t  debug_seeding_col_     = 0;
};

}  // namespace mal_abm_fast
