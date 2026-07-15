// SPDX-License-Identifier: MIT
// coordinator.cpp — F1.b CoordinatorModel implementation.
//
// Per-day orchestrator that activates patches from the climate, builds
// the per-patch state vector (union of pre-existing patches + dynamic
// PLUVIAL_POOL cells), and aggregates the submodel's per-patch /
// per-cell counts into the (H, W) state COG bands. Mirrors the Python
// `mal_ghana_sim.abm.coordinator.CoordinatorModel` 1:1 so the F1.e
// parity test can compare the C++ and Python engine outputs.
#include "coordinator.hpp"

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <stdexcept>
#include <tuple>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

#include "aoi.hpp"
#include "climate.hpp"
#include "habitat_engine.hpp"
#include "mosquito_submodel.hpp"
#include "output_contract.hpp"
#include "wire.hpp"

namespace mal_abm_fast {

CoordinatorModel::CoordinatorModel(AOI aoi, ClimateEngine climate,
                                   HabitatEngine habitat, int32_t seed,
                                   std::chrono::sys_days start_date)
    : aoi_(std::move(aoi)),
      climate_(std::move(climate)),
      habitat_(std::move(habitat)),
      rng_(static_cast<uint64_t>(seed)),
      current_date_(start_date),
      next_dynamic_patch_id_(
          static_cast<int64_t>(habitat_.patches().size())) {}

void CoordinatorModel::activate_patches() {
    // F1.b note: the activation check is re-done in to_dataframe()
    // (line 75-77 below) which constructs PatchState with
    // `activated = (climate.rain_at(row, col) > PLUVIAL_POOL_RAIN_THRESHOLD_MM)`
    // for every pre-existing patch cell. The HabitatPatch struct has no
    // `activated` field in the M1.5 thin slice (per the wire-spec.md
    // design — activation is derived from today's climate, not stored
    // on the patch), so this function is a no-op for F1.b. The per-day
    // contract still calls it (so the engine.step() API matches the
    // Python AnophelesABM.step()); F2 will revisit when patch.activated
    // becomes a mutable field (e.g. for site-fidelity extensions).
}

std::vector<PatchState> CoordinatorModel::to_dataframe() {
    const int32_t H = climate_.h();
    const int32_t W = climate_.w();
    const size_t hw = static_cast<size_t>(H) * static_cast<size_t>(W);

    std::vector<PatchState> states;
    states.reserve(habitat_.patches().size() + hw);

    std::unordered_map<std::pair<int32_t, int32_t>, int64_t, PairHash>
        pre_rowcol_to_pid;
    pre_rowcol_to_pid.reserve(habitat_.patches().size());
    for (size_t i = 0; i < habitat_.patches().size(); ++i) {
        const auto& patch = habitat_.patches()[i];
        pre_rowcol_to_pid[{patch.row, patch.col}] =
            static_cast<int64_t>(i);
    }

    std::unordered_set<std::pair<int32_t, int32_t>, PairHash> union_cells;
    union_cells.reserve(pre_rowcol_to_pid.size() + hw);

    for (const auto& patch : habitat_.patches()) {
        if (climate_.rain_at(patch.row, patch.col) >
            PLUVIAL_POOL_RAIN_THRESHOLD_MM) {
            union_cells.insert({patch.row, patch.col});
        }
    }

    const std::vector<float> twi = climate_.twi_grid();
    const bool has_twi = (twi.size() == hw);
    for (int32_t r = 0; r < H; ++r) {
        for (int32_t c = 0; c < W; ++c) {
            const size_t idx = static_cast<size_t>(r) *
                                   static_cast<size_t>(W) +
                               static_cast<size_t>(c);
            const float twi_val = has_twi ? twi[idx] : 0.0f;
            const float water_frac_val = climate_.water_frac_at(r, c);
            const float rain_val = climate_.rain_at(r, c);
            if (twi_val > PLUVIAL_POOL_TWI_THRESHOLD &&
                water_frac_val > PLUVIAL_POOL_WATER_FRAC_MIN &&
                rain_val > PLUVIAL_POOL_RAIN_THRESHOLD_MM) {
                union_cells.insert({r, c});
            }
        }
    }

    for (const auto& cell : union_cells) {
        int64_t pid;
        auto pre_it = pre_rowcol_to_pid.find(cell);
        if (pre_it != pre_rowcol_to_pid.end()) {
            pid = pre_it->second;
            dynamic_patch_registry_[cell] = pid;
        } else {
            auto reg_it = dynamic_patch_registry_.find(cell);
            if (reg_it != dynamic_patch_registry_.end()) {
                pid = reg_it->second;
            } else {
                pid = next_dynamic_patch_id_++;
                dynamic_patch_registry_[cell] = pid;
            }
        }
        PatchState ps;
        ps.patch_id = pid;
        ps.row = cell.first;
        ps.col = cell.second;
        ps.activated = true;
        ps.rain_d = climate_.rain_at(cell.first, cell.second);
        ps.temp_d = climate_.temp_at(cell.first, cell.second);
        ps.water_frac = climate_.water_frac_at(cell.first, cell.second);
        states.push_back(ps);
    }

    std::sort(states.begin(), states.end(),
              [](const PatchState& a, const PatchState& b) {
                  if (a.row != b.row) return a.row < b.row;
                  if (a.col != b.col) return a.col < b.col;
                  return a.patch_id < b.patch_id;
              });

    cached_states_ = states;
    return states;
}

DensityGrid CoordinatorModel::aggregate_density(const MosquitoSubmodel& sub,
                                                int32_t k_max) const {
    const int32_t H = climate_.h();
    const int32_t W = climate_.w();
    DensityGrid grid;
    grid.h = H;
    grid.w = W;
    grid.data.assign(static_cast<size_t>(H) * static_cast<size_t>(W), 0.0f);
    if (H <= 0 || W <= 0) return grid;

    std::unordered_map<int64_t, std::pair<int32_t, int32_t>> pid_to_cell;
    pid_to_cell.reserve(habitat_.patches().size() +
                        dynamic_patch_registry_.size());
    for (size_t i = 0; i < habitat_.patches().size(); ++i) {
        const auto& patch = habitat_.patches()[i];
        pid_to_cell[static_cast<int64_t>(i)] = {patch.row, patch.col};
    }
    for (const auto& kv : dynamic_patch_registry_) {
        pid_to_cell[kv.second] = kv.first;
    }

    std::vector<double> flat(static_cast<size_t>(H) *
                                 static_cast<size_t>(W),
                             0.0);
    for (const auto& pr : sub.density_by_patch()) {
        const int64_t pid = pr.first;
        const int64_t count = pr.second;
        auto it = pid_to_cell.find(pid);
        if (it == pid_to_cell.end()) continue;
        const int32_t row = it->second.first;
        const int32_t col = it->second.second;
        if (row < 0 || row >= H || col < 0 || col >= W) continue;
        flat[static_cast<size_t>(row) * static_cast<size_t>(W) +
             static_cast<size_t>(col)] += static_cast<double>(count);
    }

    const double kmax_d = (k_max > 0) ? static_cast<double>(k_max) : 1.0;
    for (size_t i = 0; i < flat.size(); ++i) {
        float v = static_cast<float>(flat[i] / kmax_d);
        if (v < 0.0f) v = 0.0f;
        if (v > 1.0f) v = 1.0f;
        grid.data[i] = v;
    }
    return grid;
}

SuitabilityGrid CoordinatorModel::suitability_grid(
    const MosquitoSubmodel& sub, int32_t k_max) const {
    const int32_t H = climate_.h();
    const int32_t W = climate_.w();
    SuitabilityGrid grid;
    grid.h = H;
    grid.w = W;
    grid.data.assign(static_cast<size_t>(H) * static_cast<size_t>(W), 0.0f);
    if (H <= 0 || W <= 0) return grid;

    std::vector<double> flat(static_cast<size_t>(H) *
                                 static_cast<size_t>(W),
                             0.0);
    for (const auto& t : sub.adult_density_by_cell(aoi_)) {
        const int32_t row = std::get<0>(t);
        const int32_t col = std::get<1>(t);
        const int64_t n_adults = std::get<2>(t);
        if (row < 0 || row >= H || col < 0 || col >= W) continue;
        flat[static_cast<size_t>(row) * static_cast<size_t>(W) +
             static_cast<size_t>(col)] += static_cast<double>(n_adults);
    }

    const double kmax_d = (k_max > 0) ? static_cast<double>(k_max) : 1.0;
    for (size_t i = 0; i < flat.size(); ++i) {
        float v = static_cast<float>(flat[i] / kmax_d);
        if (v < 0.0f) v = 0.0f;
        if (v > 1.0f) v = 1.0f;
        grid.data[i] = v;
    }
    return grid;
}

std::string CoordinatorModel::write_state_cog(const std::string& path,
                                               const DensityGrid& density,
                                               const SuitabilityGrid& suit,
                                               int32_t year, int32_t month,
                                               int32_t seed) const {
    StateCogMetadata meta;
    meta.crs = aoi_.crs;
    meta.aoi_slug = aoi_.slug;
    meta.scale = aoi_.scale;
    meta.year = year;
    meta.month = month;
    meta.seed = seed;
    meta.h = density.h;
    meta.w = density.w;

    // Parity with the Python reference (coordinator.py:545): the transform
    // is derived from `aoi.cells_per_side()` (the AOI-derived dimensions),
    // not from the density grid's dimensions. This makes the sidecar JSON
    // transform independent of the env COG's actual shape (which can be
    // smaller than the AOI when the user passes a custom --bbox).
    const int32_t W_aoi = aoi_.cells_per_side();
    const int32_t H_aoi = cells_per_side_h(aoi_);
    const double safe_w = (W_aoi > 0) ? static_cast<double>(W_aoi) : 1.0;
    const double safe_h = (H_aoi > 0) ? static_cast<double>(H_aoi) : 1.0;
    const double pixel_w = (aoi_.east - aoi_.west) / safe_w;
    const double pixel_h = (aoi_.north - aoi_.south) / safe_h;
    meta.transform = {pixel_w, 0.0, aoi_.west, 0.0, -pixel_h, aoi_.north};

    ::mal_abm_fast::write_state_cog(path, density, suit, meta);
    write_state_sidecar(path, meta);
    return path;
}

}  // namespace mal_abm_fast
