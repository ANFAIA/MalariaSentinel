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
#include <cmath>
#include <cstdint>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include "prng.hpp"
#include "seeding.hpp"
#include "wire.hpp"

namespace mal_abm_fast {

Engine::Engine(AOI aoi,
               const std::string& env_path,
               const std::string& habitat_path,
               Prng& rng,
               std::chrono::sys_days start_date,
               int32_t max_days,
               SeedingConfig seeding_config,
               RuntimeOverrides overrides,
               const std::string& hosts_path,
               const std::string& mobility_dir)
    : aoi_(std::move(aoi)),
      current_date_(start_date),
      start_date_(start_date),
      overrides_(overrides) {
    auto climate = std::make_shared<ClimateEngine>();
    try {
        const bool is_nc = env_path.size() >= 3
            && env_path.substr(env_path.size() - 3) == ".nc";
        if (is_nc) {
            climate->load_from_env_nc(env_path, aoi_, max_days);
            if (max_days > 0 && climate->n_days() < max_days) {
                throw std::runtime_error(
                    "Engine: env NC file has " + std::to_string(climate->n_days())
                    + " days but simulation requests " + std::to_string(max_days) + " days");
            }
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
        aoi_, climate_, *habitat_, coord_seed32, current_date_);

    // The submodel is seeded with the derived sub_seed and the
    // count of pre-existing patches. An empty gpkg is allowed (M2
    // combined, C2: dynamic patches emerge from the PLUVIAL_POOL
    // rule); the submodel's population is then driven by births in
    // those dynamic cells. We log a soft warning here when
    // n_patches == 0 so the CLI output surfaces the case for the
    // test harness.
    const int32_t n_patches = static_cast<int32_t>(habitat_->patches().size());

    if (seeding_config.mode == SeedingMode::UNIFORM) {
        // Legacy path: init_frac of K in every patch.
        sub_ = std::make_unique<MosquitoSubmodel>(
            n_patches, K_PER_PATCH_DEFAULT, INIT_FRAC, sub_seed, overrides_);
    } else {
        // Detection-based path: ask the coordinator to filter
        // habitat patches by viability (water_frac / TWI) and
        // build the per-patch seed instructions, then construct
        // the submodel from the explicit list.
        const std::vector<SeedInstruction> instructions =
            coord_->build_seed_instructions(seeding_config);
        if (!instructions.empty()) {
            seeding_patch_.patch_id = instructions.front().patch_id;
            seeding_patch_.row      = instructions.front().row;
            seeding_patch_.col      = instructions.front().col;
        }
        sub_ = std::make_unique<MosquitoSubmodel>(
            n_patches, K_PER_PATCH_DEFAULT, instructions, sub_seed, overrides_);
    }

    // -- Optional host-seeking components -----------------------------------
    if (!hosts_path.empty()) {
        host_landscape_ = std::make_unique<HostLandscape>();
        host_landscape_->load_from_nc(hosts_path, aoi_);
        std::cout << "Engine: loaded HostLandscape from " << hosts_path << "\n";
    }
    if (!mobility_dir.empty()) {
        mobility_schedule_ = std::make_unique<MobilitySchedule>();
        mobility_schedule_->load_from_directory(mobility_dir, aoi_);
        if (mobility_schedule_->has_data()) {
            std::cout << "Engine: loaded MobilitySchedule (" 
                      << mobility_schedule_->n_matrices() << " matrices) from "
                      << mobility_dir << "\n";
        }
    }

    // Wire host-seeking components to the submodel.
    if (sub_ && host_landscape_) {
        sub_->set_host_landscape(host_landscape_.get());
    }
    if (sub_ && mobility_schedule_) {
        sub_->set_mobility_schedule(mobility_schedule_.get());
    }
    if (host_landscape_) {
        host_seeking_model_ = std::make_unique<HostSeekingModel>();
        sub_->set_host_seeking_model(host_seeking_model_.get());
    }
}

Engine::Engine(AOI aoi,
               std::shared_ptr<ClimateEngine> shared_climate,
               const std::string& habitat_path,
               Prng& rng,
               std::chrono::sys_days start_date,
               SeedingConfig seeding_config,
               RuntimeOverrides overrides,
               const std::string& hosts_path,
               const std::string& mobility_dir)
    : aoi_(std::move(aoi)),
      climate_(std::move(shared_climate)),
      current_date_(start_date),
      start_date_(start_date),
      overrides_(overrides) {
    // Skip climate loading - use the shared one

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
    const uint64_t coord_seed = rng.peek_state()[0];
    (void)rng.uniform_double();
    const uint64_t sub_seed   = rng.peek_state()[0];

    const int32_t coord_seed32 = static_cast<int32_t>(coord_seed);
    coord_ = std::make_unique<CoordinatorModel>(
        aoi_, climate_, *habitat_, coord_seed32, current_date_);

    const int32_t n_patches = static_cast<int32_t>(habitat_->patches().size());

    if (seeding_config.mode == SeedingMode::UNIFORM) {
        sub_ = std::make_unique<MosquitoSubmodel>(
            n_patches, K_PER_PATCH_DEFAULT, INIT_FRAC, sub_seed, overrides_);
    } else {
        const std::vector<SeedInstruction> instructions =
            coord_->build_seed_instructions(seeding_config);
        if (!instructions.empty()) {
            seeding_patch_.patch_id = instructions.front().patch_id;
            seeding_patch_.row      = instructions.front().row;
            seeding_patch_.col      = instructions.front().col;
        }
        sub_ = std::make_unique<MosquitoSubmodel>(
            n_patches, K_PER_PATCH_DEFAULT, instructions, sub_seed, overrides_);
    }

    // -- Optional host-seeking components -----------------------------------
    if (!hosts_path.empty()) {
        host_landscape_ = std::make_unique<HostLandscape>();
        host_landscape_->load_from_nc(hosts_path, aoi_);
        std::cout << "Engine: loaded HostLandscape from " << hosts_path << "\n";
    }
    if (!mobility_dir.empty()) {
        mobility_schedule_ = std::make_unique<MobilitySchedule>();
        mobility_schedule_->load_from_directory(mobility_dir, aoi_);
        if (mobility_schedule_->has_data()) {
            std::cout << "Engine: loaded MobilitySchedule ("
                      << mobility_schedule_->n_matrices() << " matrices) from "
                      << mobility_dir << "\n";
        }
    }

    // Wire host-seeking components to the submodel.
    if (sub_ && host_landscape_) {
        sub_->set_host_landscape(host_landscape_.get());
    }
    if (sub_ && mobility_schedule_) {
        sub_->set_mobility_schedule(mobility_schedule_.get());
    }
    if (host_landscape_) {
        host_seeking_model_ = std::make_unique<HostSeekingModel>();
        sub_->set_host_seeking_model(host_seeking_model_.get());
    }
}

void Engine::step() {
    const int32_t day_index = static_cast<int32_t>(
        (current_date_ - start_date_).count());
    coord_->set_climate_day(day_index);

    coord_->activate_patches();

    coord_->to_dataframe();

    // 3. Submodel advances one day using the cached per-patch
    //    state. This calls the 5 per-day ops in order (larva
    //    mortality, growth, EIP, dispersal, birth).
    sub_->advance_day(aoi_, coord_->patch_states_today());

    // Divergence checks
    const int64_t n = sub_->total_agents();
    if (n < 0) {
        throw std::runtime_error(
            "Engine::step: population is negative (" +
            std::to_string(n) + ")");
    }

    const int64_t cap = max_population_ > 0
        ? max_population_
        : static_cast<int64_t>(aoi_.cells_per_side()) *
          static_cast<int64_t>(aoi_.cells_per_side()) *
          static_cast<int64_t>(K_MAX) * 10;
    if (n > cap) {
        std::cerr << "warning: population " << n
                  << " exceeds safe threshold " << cap << "\n";
    }

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

    // NaN guards
    for (size_t i = 0; i < density.data.size(); ++i) {
        if (std::isnan(density.data[i])) {
            throw std::runtime_error(
                "Engine::snapshot: NaN in density grid at index " +
                std::to_string(i));
        }
    }
    for (size_t i = 0; i < suit.data.size(); ++i) {
        if (std::isnan(suit.data[i])) {
            throw std::runtime_error(
                "Engine::snapshot: NaN in suitability grid at index " +
                std::to_string(i));
        }
    }

    coord_->write_state_cog(path, density, suit, year, month, seed,
                            n_rollouts, rollout_index);

    // Write aquatic cohort diagnostics to a separate JSON file.
    // The diagnostic file is placed next to the state COG with
    // suffix "_aquatic.json".
    if (sub_) {
        const int32_t day_index = static_cast<int32_t>(
            (current_date_ - start_date_).count());
        std::string diag_path = path;
        // Replace .tif with _aquatic.json
        const std::string tif_ext = ".tif";
        if (diag_path.size() >= tif_ext.size() &&
            diag_path.substr(diag_path.size() - tif_ext.size()) == tif_ext) {
            diag_path = diag_path.substr(0, diag_path.size() - tif_ext.size());
        }
        diag_path += "_aquatic.json";
        sub_->cohort_bank().write_diagnostics(diag_path, day_index);
    }
}

int64_t Engine::total_agents() const {
    return sub_ ? sub_->total_agents() : 0;
}

}  // namespace mal_abm_fast
