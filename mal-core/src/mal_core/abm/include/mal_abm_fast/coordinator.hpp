// SPDX-License-Identifier: MIT
// coordinator.hpp — Mesa-Geo half of the C++ ABM (the spatial layer).
//
// The coordinator owns:
//   * the AOI (cell geometry + transform)
//   * the ClimateEngine (env COG reader)
//   * the HabitatEngine (gpkg reader)
//   * a Prng (the per-rollout sub-stream; derived from `--seed`)
//   * the dynamic-patch registry (cells where the PLUVIAL_POOL rule
//     holds today, with stable patch_ids for site fidelity)
//
// Per-day contract (5 ops in order, matching the Python
// `coordinator.CoordinatorModel`):
//
//   1. coordinator.activate_patches()
//      Update each patch's `activated` flag from the climate for
//      the day. For M1 with monthly env, the env is constant per
//      month — the implementation may consume the day argument or
//      ignore it; the spec leaves this to the coord subagent.
//
//   2. patch_states = coordinator.to_dataframe()
//      Build the per-patch `std::vector<PatchState>`. The vector is
//      the union of pre-existing patches (loaded from the gpkg, with
//      `activated=true`) and dynamic cells where
//          TWI >  PLUVIAL_POOL_TWI_THRESHOLD
//          AND water_frac > PLUVIAL_POOL_WATER_FRAC_MIN  (strict > 0)
//          AND rain_d   > PLUVIAL_POOL_RAIN_THRESHOLD_MM
//      Dynamic patches get stable patch_ids starting at
//      `patches().size()`; the registry records them for site
//      fidelity (a cell that drops out and reactivates later reuses
//      its old patch_id).
//
//   3. submodel.advance_day(aoi, patch_states)
//      The 5 per-day operations (larva mortality, growth, EIP,
//      dispersal, birth) — see mosquito_submodel.hpp.
//
//   4. density = coordinator.aggregate_density(submodel, k_max)
//      Bincount over (row, col) of all agents by patch_id,
//      normalised by k_max, clipped to [0, 1].
//
//   5. suitability = coordinator.suitability_grid(submodel, k_max)
//      Per-cell adult density from each adult's post-dispersal
//      (lon, lat) (snapped via rowcol), normalised by k_max,
//      clipped to [0, 1].
//
//   6. coordinator.write_state_cog(path, density, suitability, ...)
//      Write the 2-band state COG + sidecar JSON (see
//      output_contract.hpp).
//
// The facade in `src/main.cpp` orchestrates the 6 steps in a loop.
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
#include "habitat_engine.hpp"
#include "host_landscape.hpp"
#include "pool_hydrology.hpp"
#include "prng.hpp"
#include "seeding.hpp"
#include "wire.hpp"

namespace mal_abm_fast {

// Forward declaration — see mosquito_submodel.hpp.
class MosquitoSubmodel;

// Hash functor for (row, col) pairs (used by the dynamic-patch
// registry). Packs the two int32s into an int64 then hashes that.
struct PairHash {
    std::size_t operator()(const std::pair<int32_t, int32_t>& p) const noexcept {
        const std::uint64_t packed =
            (static_cast<std::uint64_t>(static_cast<std::uint32_t>(p.first)) << 32) |
             static_cast<std::uint32_t>(p.second);
        return std::hash<std::uint64_t>{}(packed);
    }
};

class CoordinatorModel {
public:
    CoordinatorModel() = default;

    // Construct a coordinator for (AOI, climate, habitat, seed, start
    // date). The Prng is seeded with `seed`; per-module sub-streams
    // are derived by the implementation subagent.
    CoordinatorModel(AOI aoi, std::shared_ptr<ClimateEngine> climate,
                     HabitatEngine habitat,
                     int32_t seed, std::chrono::sys_days start_date);

    // Accessors. The Prng is mutable (submodel.advance_day advances
    // it) so `rng()` is non-const.
    const AOI&            aoi()        const { return aoi_; }
    const ClimateEngine&  climate()    const { return *climate_; }
    const HabitatEngine&  habitat()    const { return habitat_; }
    std::chrono::sys_days current_date() const { return current_date_; }
    // Mutable accessor for the per-day date advance. The Engine
    // facade advances the date on each step() with
    // `coord->current_date() += std::chrono::days{1}`. Added by the
    // f1f-engine subagent (F1.b) — see git log.
    std::chrono::sys_days& current_date()       { return current_date_; }
    Prng&                 rng()              { return rng_; }

    // The per-day patch-state vector as cached by to_dataframe().
    // The Engine facade reads this after to_dataframe() to pass into
    // MosquitoSubmodel::advance_day. Added by the f1f-engine subagent
    // (F1.b) — see git log.
    const std::vector<PatchState>& patch_states_today() const {
        return cached_states_;
    }

    // -- per-day: activation -------------------------------------------------

    void set_climate_day(int32_t day_index);

    // Species salinity high-tolerance (psu). Patches whose water
    // salinity exceeds this cannot breed (activated=false). The Engine
    // passes the active species' `salinity_hi_tol_ppt` during wiring;
    // default = coluzzii 30.0 psu (freshwater runs are unchanged).
    void set_salinity_hi_tol_ppt(float ppt) { salinity_hi_tol_ppt_ = ppt; }
    void set_host_landscape(const HostLandscape* hosts) { host_landscape_ = hosts; }
    float salinity_hi_tol_ppt() const { return salinity_hi_tol_ppt_; }

    // Urban rule setters (plan §6.3-6.6). All values have constexpr
    // defaults in wire.hpp; these setters let calibration override them
    // without recompiling.
    void set_urban_b_min(float v)             { urban_b_min_ = v; }
    void set_urban_r_min_mm(float v)          { urban_r_min_mm_ = v; }
    void set_urban_twi_min(float v)           { urban_twi_min_ = v; }
    void set_urban_density_cap(float v)       { urban_density_cap_ = v; }

    // Update the trailing 7-day antecedent rainfall buffer. Called once
    // per step() by the Engine with today's per-cell rainfall vector.
    // The buffer holds the last 7 days (inclusive of today).
    void update_rain_antecedent(const std::vector<float>& today_rain_mm);
    // Sum of the trailing 7-day rainfall buffer at (row, col), in mm.
    float rain_7d_at(int32_t row, int32_t col) const;

    // Update patch.activated from climate. For M1 with monthly env,
    // day is constant per month and may be ignored. The
    // implementation subagent decides whether to consume
    // `current_date_`.
    void activate_patches();

    // Build the per-patch K_eff array once, from static host data.
    //
    // M17.4 PR-C (plan §3 / §6.4): for each cell (r, c), K_eff[r, c]
    // equals `clamp(building_fraction, URBAN_CAPACITY_FLOOR,
    // URBAN_CAPACITY_CEIL)` if `urban_class == URBAN_CLASS_THRESHOLD`,
    // else 1.0 (terrain default). The grid is row-major float[H*W]
    // and never changes after build (host data is static). Aquatic
    // stages consume it via `K_eff_grid_view()`. Must be called after
    // `set_host_landscape()` — throws otherwise.
    void build_K_eff_grid();

    // Read-only view of the K_eff grid (ptr + W). Null/0 if not
    // built yet. Designed to be passed once to consumers at wiring
    // time, then read in hot loops as a flat array indexed by
    // `r * W + c` (O(1), cache-friendly).
    struct KEffView {
        const float* data = nullptr;
        int32_t     width = 0;
        int32_t     height = 0;
    };
    KEffView k_eff_grid_view() const { return {K_eff_grid_.data(), W_, H_}; }
    // K_eff at (row, col), or 1.0 if the grid is uninitialised. Used
    // by tests + diagnostics; production paths use the view directly.
    float K_eff_at(int32_t row, int32_t col) const;

    // -- per-day: per-patch state vector ------------------------------------

    // Build the per-patch state vector. The output is the union of
    // pre-existing patches (with activated=true) and dynamic cells
    // where the PLUVIAL_POOL rule holds. Dynamic patches get stable
    // patch_ids starting at `patches().size()`; the registry records
    // them for site fidelity.
    std::vector<PatchState> to_dataframe();

    // Identify viable patches from the habitat (water_frac >
    // `config.min_water_frac` AND twi > `config.min_twi`) and build
    // the per-patch seed instructions for the submodel. Used by
    // the Engine during construction to wire the detection-based
    // seeding modes (RANDOM_VIABLE, EXPLICIT). Returns an empty
    // vector in UNIFORM mode (the submodel uses init_frac for
    // every patch — the legacy path).
    std::vector<SeedInstruction> build_seed_instructions(
        const SeedingConfig& config);

    // UNIFORM-mode seeding over the day-0 patch union: every
    // pre-existing habitat patch PLUS the dynamic urban-persistent
    // baseline patches (urban_class == 30 && building_fraction >=
    // URBAN_B_MIN). Per-patch counts match the legacy round-robin
    // path (init_frac * k_per_patch agents, 10% adults / 90% eggs).
    // Rain-day-only dynamic patches are intentionally NOT seeded:
    // they are naturally colonised during the wet season. Without
    // this, urban-baseline patches start empty and can never be
    // colonised (adult dispersal max 2 km leaves them unreachable
    // from distant permanent water — the Accra dry-season failure).
    std::vector<SeedInstruction> build_uniform_seed_instructions(
        float init_frac, int32_t k_per_patch);

    // -- density aggregation ------------------------------------------------

    // (H, W) density grid: bincount over (row, col) of all agents by
    // patch_id, normalised by k_max, clipped to [0, 1].
    DensityGrid aggregate_density(const MosquitoSubmodel& sub,
                                  int32_t k_max) const;

    // (H, W) suitability grid: per-cell adult density from each
    // adult's post-dispersal (lon, lat) (snapped via rowcol),
    // normalised by k_max, clipped to [0, 1].
    SuitabilityGrid suitability_grid(const MosquitoSubmodel& sub,
                                     int32_t k_max) const;

    // -- output -------------------------------------------------------------

    // Write the 2-band state COG and sidecar JSON. Returns the
    // .tif path. The implementation subagent uses GDAL to write a
    // COG (tiled, deflate, 128x128 blocks, nodata = NODATA_SENTINEL)
    // and nlohmann::json for the sidecar.
    //
    // F1.c: `n_rollouts` and `rollout_index` are written into the
    // sidecar (defaults: 1, 0 — single-rollout case, unchanged from
    // F1.b).
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
    std::unordered_map<std::pair<int32_t, int32_t>, int64_t, PairHash> dynamic_patch_registry_;
    int64_t                              next_dynamic_patch_id_ = 0;
    std::vector<PatchState>                   cached_states_;  // per-day snapshot
    // Species salinity high-tolerance (psu); default = coluzzii 30.0.
    float                                     salinity_hi_tol_ppt_ = 30.0f;
    const HostLandscape*                      host_landscape_ = nullptr;
    // Urban rule config (plan §6.3-6.6); overridable via setters.
    float                                     urban_b_min_      = URBAN_B_MIN;
    float                                     urban_r_min_mm_   = URBAN_R_MIN_MM;
    float                                     urban_twi_min_    = URBAN_TWI_MIN;
    float                                     urban_density_cap_= URBAN_DENSITY_CAP_FRACTION;
    // Trailing 7-day per-cell rainfall buffer (plan §6.3 antecedent_rain_7d).
    // Outer dim = day-slot (0=today, 6=6-days-ago); inner dim = row-major cells.
    // Slots are circular: oldest slot overwritten each update_rain_antecedent().
    std::array<std::vector<float>, 7>         rain_7d_buffer_{};
    int32_t                                   rain_7d_count_    = 0;
    // Pool hydrology (M14): per-patch water state, keyed by patch_id.
    std::unordered_map<int64_t, PoolState>     pool_states_;
    // M17.4 PR-C: per-cell K_eff array (row-major float[H*W]).
    // Built once by `build_K_eff_grid()` after `set_host_landscape()`
    // (host data is static). Empty until built; consumers must check
    // for emptiness or fall back to K_MAX.
    std::vector<float>                         K_eff_grid_;
    int32_t                                    H_ = 0;
    int32_t                                    W_ = 0;
};

}  // namespace mal_abm_fast
