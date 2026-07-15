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
#include "wire.hpp"

namespace mal_abm_fast {

class Engine {
public:
    Engine() = default;

    // Build the engine for (AOI, env COG path, habitat gpkg path, seed,
    // start_date). Loads the env via `ClimateEngine::load_from_env_tif`
    // and the habitat via `HabitatEngine::load_from_gpkg`, then
    // constructs the `CoordinatorModel` and `MosquitoSubmodel`.
    //
    // Throws `std::runtime_error` if either IO load fails.
    Engine(AOI aoi,
           const std::string& env_path,
           const std::string& habitat_path,
           uint64_t seed,
           std::chrono::sys_days start_date);

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
    void snapshot(const std::string& path,
                  int32_t year,
                  int32_t month,
                  int32_t seed);

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
    std::unique_ptr<ClimateEngine>          climate_;
    std::unique_ptr<HabitatEngine>          habitat_;
    std::unique_ptr<CoordinatorModel>       coord_;
    std::unique_ptr<MosquitoSubmodel>       sub_;
    std::chrono::sys_days                   current_date_;
};

}  // namespace mal_abm_fast
