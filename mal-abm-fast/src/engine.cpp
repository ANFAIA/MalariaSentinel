// SPDX-License-Identifier: MIT
// engine.cpp — Engine facade implementation.
//
// Mirrors `mal_ghana_sim.abm.AnophelesABM` from the Python engine.
// The facade owns a `ClimateEngine`, a `HabitatEngine`, a
// `CoordinatorModel`, and a `MosquitoSubmodel`, and orchestrates the
// per-day contract:
//
//   step()      — coord.activate_patches + to_dataframe +
//                 sub.advance_day + advance date
//   snapshot()  — build density/suitability grids from the submodel
//                 via the coordinator, then write the 2-band state
//                 COG + sidecar JSON
//
// The CLI in `main.cpp` is the only public caller; tests in
// `tests/test_engine.cpp` exercise the same contract against
// synthetic env COG + habitat gpkg inputs.
#include "engine.hpp"

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <memory>
#include <stdexcept>
#include <string>
#include <utility>

#include "prng.hpp"
#include "wire.hpp"

namespace mal_abm_fast {

Engine::Engine(AOI aoi,
               const std::string& env_path,
               const std::string& habitat_path,
               Prng& rng,
               std::chrono::sys_days start_date)
    : aoi_(std::move(aoi)),
      current_date_(start_date) {
    // Build the IO engines first. Either IO failure throws here, so
    // we surface the path that failed in the message.
    // Detect file extension: .nc -> daily NetCDF loader, else -> COG/TIF loader.
    auto climate = std::make_unique<ClimateEngine>();
    try {
        const bool is_nc = env_path.size() >= 3
            && env_path.substr(env_path.size() - 3) == ".nc";
        if (is_nc) {
            climate->load_from_env_nc(env_path, aoi_);
        } else {
            climate->load_from_env_tif(env_path, aoi_);
        }
    } catch (const std::exception& e) {
        throw std::runtime_error(
            "Engine: ClimateEngine load failed for '" +
            env_path + "': " + e.what());
    }
    climate_ = std::move(climate);

    auto habitat = std::make_unique<HabitatEngine>();
    try {
        habitat->load_from_gpkg(habitat_path, aoi_);
    } catch (const std::exception& e) {
        throw std::runtime_error(
            "Engine: HabitatEngine::load_from_gpkg failed for '" +
            habitat_path + "': " + e.what());
    }
    habitat_ = std::move(habitat);

    // Derive two independent sub-stream seeds from the master Prng.
    // We don't store `rng` as a member — only consume a few draws to
    // extract the seeds. This is what enables per-rollout Prng
    // isolation: the CLI in main.cpp creates a fresh `Prng` per
    // rollout, and the Engine's derived sub-streams are unique to
    // that rollout.
    //
    // The derivation is deterministic: two Engines built from two
    // FRESH Prngs with the same master seed get the same coord + sub
    // seeds (so the parity test stays reproducible). It is NOT
    // idempotent over a shared Prng: a second Engine built from a
    // Prng that has already been used will get different sub-seeds
    // (the Prng state has advanced). The CLI's fresh-Prng-per-rollout
    // pattern avoids this. The order is: peek_state()[0],
    // uniform_double() (advances), peek_state()[0] — so the two
    // seeds are independent draws of the master stream.
    const uint64_t coord_seed = rng.peek_state()[0];
    (void)rng.uniform_double();
    const uint64_t sub_seed   = rng.peek_state()[0];

    // The coordinator owns the AOI copy, the climate / habitat refs,
    // a Prng seeded with the derived coord seed, and the per-day
    // date. The coord Prng is not consumed in daily ops in F1.b but
    // is held as a per-module sub-stream (see prng.hpp).
    const int32_t coord_seed32 = static_cast<int32_t>(coord_seed);
    coord_ = std::make_unique<CoordinatorModel>(
        aoi_, *climate_, *habitat_, coord_seed32, current_date_);

    // The submodel is seeded with the derived sub_seed and the
    // count of pre-existing patches. An empty gpkg is allowed (M2
    // combined, C2: dynamic patches emerge from the PLUVIAL_POOL
    // rule); the submodel's population is then driven by births in
    // those dynamic cells. We log a soft warning here when
    // n_patches == 0 so the CLI output surfaces the case for the
    // test harness.
    const int32_t n_patches = static_cast<int32_t>(habitat_->patches().size());
    sub_ = std::make_unique<MosquitoSubmodel>(
        n_patches, K_PER_PATCH_DEFAULT, INIT_FRAC, sub_seed);
}

void Engine::step() {
    // 1. Coordinator updates patch.activated from the current
    //    climate. The implementation subagent decides whether to
    //    consume current_date_ (for M1 the env is monthly, so
    //    activate_patches is a no-op for the daily call).
    coord_->activate_patches();

    // 2. Build the per-patch state vector for today. The coordinator
    //    caches it in cached_states_; the engine reads it back via
    //    patch_states_today() on the next call.
    coord_->to_dataframe();

    // 3. Submodel advances one day using the cached per-patch
    //    state. This calls the 5 per-day ops in order (larva
    //    mortality, growth, EIP, dispersal, birth).
    sub_->advance_day(aoi_, coord_->patch_states_today());

    // 4. Advance the simulation date by one day. Mirrors
    //    `AnophelesABM.step()` step 5 in the Python engine.
    coord_->current_date() += std::chrono::days{1};
    current_date_ = coord_->current_date();
}

void Engine::snapshot(const std::string& path,
                      int32_t year,
                      int32_t month,
                      int32_t seed,
                      int32_t n_rollouts,
                      int32_t rollout_index) {
    // Build the (H, W) density grid (mosquitoes / K_MAX, clipped to
    // [0, 1]) and the (H, W) suitability grid (per-cell adult
    // density / K_MAX, clipped to [0, 1]) from the submodel, then
    // delegate to the coordinator's writer. The coordinator handles
    // the StateCogMetadata construction and calls
    // write_state_cog + write_state_sidecar.
    //
    // F1.c: n_rollouts / rollout_index are propagated to the sidecar
    // so each rollout's COG is self-describing.
    const DensityGrid density =
        coord_->aggregate_density(*sub_, K_MAX);
    const SuitabilityGrid suit =
        coord_->suitability_grid(*sub_, K_MAX);
    coord_->write_state_cog(path, density, suit, year, month, seed,
                            n_rollouts, rollout_index);
}

int64_t Engine::total_agents() const {
    return sub_ ? sub_->total_agents() : 0;
}

}  // namespace mal_abm_fast
