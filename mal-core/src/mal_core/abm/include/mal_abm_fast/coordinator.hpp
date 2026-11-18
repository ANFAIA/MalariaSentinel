/**
 * SPDX-License-Identifier: MIT
 * coordinator.hpp — Mesa-Geo half of the C++ ABM (the spatial layer).
 *
 * Contract v3.0 (proxy_habitat_v1): the coordinator owns
 *   * the AOI (cell geometry + transform)
 *   * the ClimateEngine (env NC reader: daily rainfall + air temperature,
 *     five static habitat planes)
 *   * the HabitatEngine (candidate-patch gpkg reader)
 *   * a Prng (the per-rollout sub-stream; derived from `--seed`)
 *   * the shared temporal responses (one pluvial state z per cell,
 *     warm-up-integrated causally over the env-NC bands before the
 *     simulation start) and the per-cell species-neutral daily
 *     capacity K[i, t] = K_ref * cell_area_km2 * S[i, t]
 *
 * There is NO per-patch water-balance solver, NO TWI gate, NO urban
 * mm-floor and NO ndvi channel (plan docs/plans/in-process/redesign/
 * 01-retirada-hidrologia-dem-escorrentia.md §6-§8).
 *
 * Per-day contract (matching the retired Python engine's surface):
 *   1. coordinator.update_habitat_day()      — z/S/K update from rain
 *   2. patch_states = coordinator.to_dataframe()
 *   3. submodel.advance_day(aoi, patch_states)
 *   4. density/suitability aggregation
 *   5. coordinator.write_state_cog(...)
 */
#pragma once

#include <array>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <memory>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

#include "aoi.hpp"
#include "climate.hpp"
#include "habitat_availability.hpp"
#include "habitat_engine.hpp"
#include "host_landscape.hpp"
#include "prng.hpp"
#include "seeding.hpp"
#include "wire.hpp"

namespace mal_abm_fast {

/// Forward declaration — see mosquito_submodel.hpp.
class MosquitoSubmodel;

/// Hash functor for (row, col) pairs (used by the candidate-patch
/// registry). Packs the two int32s into an int64 then hashes that.
struct PairHash {
    /// Hash a grid cell (row, col) pair for the candidate-patch registry:
    /// packs the two int32 coordinates into one int64 and hashes it.
    std::size_t operator()(const std::pair<int32_t, int32_t>& p) const noexcept {
        const std::uint64_t packed =
            (static_cast<std::uint64_t>(static_cast<std::uint32_t>(p.first)) << 32) |
             static_cast<std::uint32_t>(p.second);
        return std::hash<std::uint64_t>{}(packed);
    }
};

/// The engine's spatial façade (the Mesa-Geo half of the ABM). It owns the
/// AOI geometry, the env-NC climate reader, the candidate-patch habitat
/// registry and the per-rollout PRNG, and serves the per-day habitat
/// update, the seeding plans and the state-COG output.
class CoordinatorModel {
public:
    CoordinatorModel() = default;

    /// Construct a coordinator for (AOI, climate, habitat, seed, start
    /// date). `day_offset` is the absolute NC band index of the start
    /// date (pluvial warm-up reads bands before it).
    CoordinatorModel(AOI aoi, std::shared_ptr<ClimateEngine> climate,
                     HabitatEngine habitat,
                     int32_t seed, std::chrono::sys_days start_date);

    /// Accessors. The Prng is mutable (submodel.advance_day advances
    /// it) so `rng()` is non-const.
    const AOI&            aoi()        const { return aoi_; }
    /// The env-NC climate reader (daily rainfall, daily air temperature and
    /// the static habitat planes); valid for the coordinator's lifetime.
    const ClimateEngine&  climate()    const { return *climate_; }
    /// The candidate-patch habitat registry read from the habitat gpkg;
    /// valid for the coordinator's lifetime.
    const HabitatEngine&  habitat()    const { return habitat_; }
    /// The calendar date (day resolution) of the simulated day. The Engine
    /// advances it by one day at the end of every step, so after a step it
    /// already holds the date of the *next* day.
    std::chrono::sys_days current_date() const { return current_date_; }
    /// Mutable calendar date of the simulated day; the Engine uses it to
    /// advance the simulation by one day at the end of each step.
    std::chrono::sys_days& current_date()       { return current_date_; }
    /// The per-rollout PRNG sub-stream (derived from `--seed`). It is
    /// advanced by the seeding planners and by `MosquitoSubmodel::advance_day`.
    Prng&                 rng()              { return rng_; }

    /// The per-patch state vector cached by the last `to_dataframe()` call
    /// (one PatchState per candidate cell); empty until that call runs.
    const std::vector<PatchState>& patch_states_today() const {
        return cached_states_;
    }

    /**
     * -- warm-up + per-day habitat update ------------------------------------
     */

    /// Point the climate engine at the NC band for simulation day
    /// `day_index` (relative to base_day_). Called by the engine loop.
    void set_climate_day(int32_t day_index) {
        climate_->set_day(day_index);
    }

    /// Integrate the pluvial state z causally over every env-NC band
    /// from `base_day - n_warmup_bands` to `base_day - 1`, starting from
    /// z = 0 at the cold end. Called once by the Engine facade before
    /// the daily loop (plan §6.5 warm-up Causal).
    void warm_up_pluvial(int32_t n_warmup_bands);

    /// Per-day: advance z with today's rainfall per cell, recompute the
    /// species-neutral daily accuracy S[i, t] and capacity K[i, t], and
    /// track per-cell dry-day streaks. Call AFTER climate_->set_day().
    /// `gamma_t`: temperature scaling of the pluvial drying memory —
    /// tau_eff = pluvial.dry_memory_days * (1 - gamma_T *
    /// clamp((T_opt - temp)/T_ref)) when gamma_T > 0.
    void update_habitat_day(float gamma_t = 0.0f);

    /// Species salinity high-tolerance (psu). Patches whose water
    /// salinity exceeds this cannot breed (activated=false). Engine
    /// wires the active species' `salinity_hi_tol_ppt`; the default
    /// comes from the default species row.
    void set_salinity_hi_tol_ppt(float ppt) { salinity_hi_tol_ppt_ = ppt; }
    /// Attach the host landscape (non-owning pointer) used to score candidate
    /// cells in HOST_WEIGHTED seeding; it must outlive the coordinator and may
    /// be left null, in which case HOST_WEIGHTED seeding is rejected.
    void set_host_landscape(const HostLandscape* hosts)
    { host_landscape_ = hosts; }
    /// The species salinity high-tolerance in PSU (parts per thousand):
    /// patches whose water salinity reaches it cannot breed.
    float salinity_hi_tol_ppt() const { return salinity_hi_tol_ppt_; }

    /// Legacy no-op kept for engine.step() API parity.
    void activate_patches() {}

    /**
     * -- per-patch state vector --------------------------------------------
     */

    /// Build the per-patch PatchState vector over candidate cells:
    /// the union of the gpkg patches and every grid cell whose static
    /// potential clears habitat.candidate_min_engine (contract: candidate-floor
    /// based, no TWI/water/urban gates). Stables pid per cell for site
    /// fidelity.
    std::vector<PatchState> to_dataframe();

    /// Register a grid cell that a SCENARIO places an individual or an
    /// aquatic cohort in (plan 13.3). The cell becomes a candidate, so
    /// `to_dataframe()` emits its PatchState even when it is not a habitat
    /// candidate (E07 needs a breeding site outside the candidate union).
    /// Returns the stable pid: the gpkg index when the cell carries a
    /// habitat patch, otherwise a fresh id. Same numbering rule as
    /// `to_dataframe()`, so the two paths agree.
    int64_t register_scenario_cell(int32_t row, int32_t col);

    /// Identify viable patches (potential clear of the candidate floor)
    /// and build the per-patch seed instructions for the submodel.
    /// `config.min_water_frac` / `config.min_twi` are ignored by the
    /// v3.0 contract (retired selectors); viability is potential-based.
    std::vector<SeedInstruction> build_seed_instructions(
        const SeedingConfig& config);

    /// UNIFORM-mode seeding: every candidate habitat cell (patch union
    /// at day 0) receives the explicit `n_adults` + `n_immatures`
    /// counts (contract 4.0; the retired init_frac × K_MAX product is
    /// replaced by direct counts).
    std::vector<SeedInstruction> build_uniform_seed_instructions(
        int32_t n_adults, int32_t n_immatures);

    /**
     * -- per-cell daily capacity view --------------------------------------
     */

    /// Read-only view of the per-cell daily capacity K (ABSOLUTE
    /// Beverton-Holt capacity in individual-equivalent units, computed
    /// per day by update_habitat_day; plan §5.4). Null until the first
    /// update_habitat_day().
    struct JetView {
        /// Per-cell capacity K, row-major H*W floats; zero until the first update_habitat_day().
        const float* data = nullptr;
        /// Grid width in cells (columns of K).
        int32_t     width = 0;
        /// Grid height in cells (rows of K).
        int32_t     height = 0;
    };
    /// The read-only per-cell capacity K view for the current day, in
    /// absolute Beverton-Holt capacity units (individual-equivalent).
    JetView J_view() const { return {K_cell_.data(), W_, H_}; }

    /// Read-only per-cell pluvial state z in [0,1] (plan 04 §2.3 — the GIF
    /// inset reads the SAME grid the coordinator integrates, so the inset
    /// cannot drift from the engine). Row-major (H,W) matching
    /// ClimateEngine::h()/w(); empty until the first update_habitat_day().
    const std::vector<float>& z_grid() const { return z_; }

    /// -- adult count aggregation --------------------------------------------
    ///
    /// Contract 4.0: both grids carry RAW per-cell adult counts
    /// (individuals). No K_MAX division, no [0,1] clamp.

    DensityGrid aggregate_density(const MosquitoSubmodel& sub) const;
    /// Per-cell raw adult counts at the adults' current position (state COG
    /// band 2, `adult_cell_count`); counts every adult regardless of sex or
    /// physiological state.
    SuitabilityGrid suitability_grid(const MosquitoSubmodel& sub) const;

    /// -- output -------------------------------------------------------------

    std::string write_state_cog(const std::string& path,
                                const DensityGrid& density,
                                const SuitabilityGrid& suit,
                                int32_t year, int32_t month,
                                int32_t seed,
                                int32_t n_rollouts    = 1,
                                int32_t rollout_index = 0) const;

private:
    AOI                                       aoi_;
    std::shared_ptr<ClimateEngine>            climate_;
    HabitatEngine                             habitat_;
    Prng                                      rng_;
    std::chrono::sys_days                     current_date_;
    std::unordered_map<std::pair<int32_t, int32_t>, int64_t, PairHash>
        patch_registry_;   ///< stable pid per (row, col) candidate cell
    /// Cells forced into the candidate union by a scenario (see
    /// `register_scenario_cell`). Duplicates are harmless: the union is a set.
    std::vector<std::pair<int32_t, int32_t>> scenario_cells_;
    int64_t                              next_patch_id_ = 0;
    std::vector<PatchState>                   cached_states_;
    /// Species salinity high-tolerance (psu); default from the default species row.
    float salinity_hi_tol_ppt_ = static_cast<float>(
        load_config()
            .species.rows.at(load_config().species.default_species)
            .salinity_hi_tol_ppt);
    const HostLandscape*                      host_landscape_ = nullptr;
    ///_PROXY habitat v1 state:
    int32_t                                   H_ = 0;
    int32_t                                   W_ = 0;
    std::vector<float>                        z_;         ///< pluvial state per cell [0,1]
    std::vector<HabitatFeatures>              feats_;     ///< static features per cell
    std::vector<int>                          dry_days_;  ///< consecutive days S <= habitat.activation_min_engine
    std::vector<float>                        K_cell_;    ///< daily capacity per cell (absolute units)
    bool                                      dry_count_configured_ = false;
};

}  // namespace mal_abm_fast
