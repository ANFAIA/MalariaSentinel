// SPDX-License-Identifier: MIT
// engine.hpp — Engine facade for the M1.5 thin-slice ABM (mal-abm-fast).
//
// The Engine is the C++ counterpart of `mal_ghana_sim.abm.AnophelesABM`.
// It owns a `ClimateEngine`, a `HabitatEngine`, a `CoordinatorModel`,
// and a `MosquitoSubmodel`, and orchestrates the per-day contract
// (activate_patches → to_dataframe → advance_day → advance date).
//
// The CLI (`src/main.cpp`) instantiates one Engine per run, calls
// `step()` for `--days` iterations, and finally `snapshot()` to write
// the 2-band state COG and sidecar JSON.
#pragma once

#include <chrono>
#include <cstdint>
#include <memory>
#include <string>

#include "climate.hpp"
#include "coordinator.hpp"
#include "habitat_engine.hpp"
#include "mosquito_submodel.hpp"
#include "prng.hpp"
#include "wire.hpp"

namespace mal_abm_fast {

class Engine {
public:
    Engine() = default;

    // Build the engine for (AOI, env path, habitat gpkg path,
    // master Prng, start_date). Loads the env via
    // `ClimateEngine::load_from_env_tif` (for .tif) or
    // `ClimateEngine::load_from_env_nc` (for .nc), and the habitat via
    // `HabitatEngine::load_from_gpkg`, then derives independent
    // sub-stream seeds for the `CoordinatorModel` and
    // `MosquitoSubmodel` from `rng` and constructs them.
    //
    // The Prng is consumed during construction: two `peek_state()`
    // draws (with one intermediate `uniform_double()` to advance the
    // state) yield the coord + submodel seeds. The master Prng is
    // NOT cached as a member — the caller owns it. This is what
    // makes per-rollout Prng isolation work: the CLI in `main.cpp`
    // creates a fresh `Prng(seed_rollout)` per rollout, builds a new
    // Engine, runs `days` steps, and snapshots; each rollout's
    // Engine is destroyed at the end of the iteration so no Prng
    // state leaks across rollouts.
    //
    // Throws `std::runtime_error` if either IO load fails.
    Engine(AOI aoi,
           const std::string& env_path,
           const std::string& habitat_path,
           Prng& rng,
           std::chrono::sys_days start_date,
           int32_t max_days = 0);

    // Advance the model by one day. Mirrors `AnophelesABM.step()`:
    //   1. coord_->activate_patches()
    //   2. coord_->to_dataframe()
    //   3. sub_->advance_day(aoi_, coord_->patch_states_today())
    //   4. coord_->current_date() += 1 day
    void step();

    // Write the 2-band state COG + sidecar JSON to `path`. Mirrors
    // `AnophelesABM.snapshot()`: builds the density and suitability
    // grids from the submodel via the coordinator, then writes the
    // COG (band 1 = density, band 2 = suitability) and the sidecar.
    //
    // F1.c: `n_rollouts` and `rollout_index` are written into the
    // sidecar so downstream consumers can disambiguate which
    // rollout produced which COG in a multi-rollout batch. The
    // single-rollout case (n_rollouts=1, rollout_index=0) is the
    // default — the F1.b callers are unchanged.
    void snapshot(const std::string& path,
                  int32_t year,
                  int32_t month,
                  int32_t seed,
                  int32_t n_rollouts    = 1,
                  int32_t rollout_index = 0);

    // Accessors for tests and the CLI.
    const AOI&             aoi()          const { return aoi_; }
    int64_t                total_agents() const;
    std::chrono::sys_days  current_date() const { return current_date_; }
    const ClimateEngine&   climate()      const { return *climate_; }
    const HabitatEngine&   habitat()      const { return *habitat_; }
    const CoordinatorModel& coordinator() const { return *coord_; }
    const MosquitoSubmodel& submodel()    const { return *sub_; }

private:
    AOI                                     aoi_;
    std::shared_ptr<ClimateEngine>          climate_;
    std::unique_ptr<HabitatEngine>          habitat_;
    std::unique_ptr<CoordinatorModel>       coord_;
    std::unique_ptr<MosquitoSubmodel>       sub_;
    std::chrono::sys_days                   current_date_;
    std::chrono::sys_days                   start_date_;
};

}  // namespace mal_abm_fast
