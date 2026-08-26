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
#include <array>
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
#include "pool_hydrology.hpp"
#include "seeding.hpp"
#include "wire.hpp"

namespace mal_abm_fast {

CoordinatorModel::CoordinatorModel(AOI aoi, std::shared_ptr<ClimateEngine> climate,
                                   HabitatEngine habitat, int32_t seed,
                                   std::chrono::sys_days start_date)
    : aoi_(std::move(aoi)),
      climate_(std::move(climate)),
      habitat_(std::move(habitat)),
      rng_(static_cast<uint64_t>(seed)),
      current_date_(start_date),
      next_dynamic_patch_id_(
          static_cast<int64_t>(habitat_.patches().size())) {}

void CoordinatorModel::set_climate_day(int32_t day_index) {
    climate_->set_day(day_index);
}

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

void CoordinatorModel::update_rain_antecedent(
    const std::vector<float>& today_rain_mm) {
    const size_t n = today_rain_mm.size();
    // Shift older slots: oldest is index 6, we drop it.
    for (int32_t slot = 6; slot > 0; --slot) {
        rain_7d_buffer_[slot] = std::move(rain_7d_buffer_[slot - 1]);
    }
    rain_7d_buffer_[0] = today_rain_mm;  // today = slot 0
    if (rain_7d_count_ < 7) ++rain_7d_count_;
}

float CoordinatorModel::rain_7d_at(int32_t row, int32_t col) const {
    const ClimateEngine* ce = climate_.get();
    const int32_t W = ce->w();
    const size_t idx = static_cast<size_t>(row) * static_cast<size_t>(W) +
                       static_cast<size_t>(col);
    float sum = 0.0f;
    const int32_t n = rain_7d_count_;
    for (int32_t slot = 0; slot < n; ++slot) {
        if (idx < rain_7d_buffer_[slot].size()) {
            sum += rain_7d_buffer_[slot][idx];
        }
    }
    return sum;
}

std::vector<PatchState> CoordinatorModel::to_dataframe() {
    // Use the current day for daily climate lookups.
    // climate_->set_day() is called by the engine step loop before
    // to_dataframe(); the accessors below read the daily band slice.
    const int32_t H = climate_->h();
    const int32_t W = climate_->w();
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

    // Pre-existing habitat patches (rivers, lakes, wetlands from gpkg).
    // They share the same water-balance rule; permanent water bodies
    // maintain water_mm >= W_BREED because their water_frac is high.
    for (const auto& patch : habitat_.patches()) {
        union_cells.insert({patch.row, patch.col});
    }

    // Dynamic ephemeral pool rule: terrain (TWI + water_frac) or urban
    // (building_fraction + GHS-SMOD urban_class) plus rain. Permanent
    // water bypasses the rain gate (plan §5.3).
    const std::vector<float> twi = climate_->twi_grid();
    const bool has_twi = (twi.size() == hw);
    for (int32_t r = 0; r < H; ++r) {
        for (int32_t c = 0; c < W; ++c) {
            const size_t idx = static_cast<size_t>(r) *
                                   static_cast<size_t>(W) +
                               static_cast<size_t>(c);
            const float twi_val = has_twi ? twi[idx] : 0.0f;
            const float water_frac_val = climate_->water_frac_at(r, c);
            const float rain_val = climate_->rain_at(r, c);
            const float rain_7d_val = rain_7d_at(r, c);

            const bool permanent = climate_->permanent_water_at(r, c) > 0.0f;
            const bool terrain_candidate = twi_val > PLUVIAL_POOL_TWI_THRESHOLD &&
                water_frac_val > PLUVIAL_POOL_WATER_FRAC_MIN;
            // Urban rule per plan §6.3: GHS-SMOD urban (== 30) AND
            // building_fraction >= B_min AND (rain >= R_min OR
            // antecedent_rain_7d >= R_min) AND TWI >= TWI_urban_min.
            // The TWI term uses the urban-specific lower threshold
            // because drainage is imperfect in built-up cells.
            bool urban_candidate = false;
            if (host_landscape_ != nullptr) {
                const HostCell hc = host_landscape_->at(r, c);
                urban_candidate = hc.urban_class == URBAN_CLASS_THRESHOLD &&
                    hc.building_fraction >= urban_b_min_ &&
                    (rain_val >= urban_r_min_mm_ ||
                     rain_7d_val >= urban_r_min_mm_) &&
                    twi_val >= urban_twi_min_;
            }

            if (permanent || ((terrain_candidate || urban_candidate) &&
                              rain_val > PLUVIAL_POOL_RAIN_THRESHOLD_MM)) {
                union_cells.insert({r, c});
            }
        }
    }

    // Urban density cap (plan §6.6): at most URBAN_DENSITY_CAP_FRACTION
    // of grid cells can be urban-sourced patches. Applied post-loop so
    // we always pick the highest-building_fraction urban cells first
    // (deterministic priority — not random sampling, which would make
    // calibration noisy).
    const size_t grid_total = static_cast<size_t>(H) * static_cast<size_t>(W);
    const size_t urban_cap_count = static_cast<size_t>(
        static_cast<float>(grid_total) * urban_density_cap_);
    if (urban_cap_count > 0 && host_landscape_ != nullptr) {
        // Collect urban candidate cells with their building_fraction.
        std::vector<std::tuple<int32_t, int32_t, float>> urban_cells;
        for (int32_t r = 0; r < H; ++r) {
            for (int32_t c = 0; c < W; ++c) {
                const HostCell hc = host_landscape_->at(r, c);
                if (hc.urban_class == URBAN_CLASS_THRESHOLD &&
                    hc.building_fraction >= urban_b_min_) {
                    const auto cell = std::make_pair(r, c);
                    if (union_cells.count(cell) > 0) {
                        urban_cells.emplace_back(r, c,
                                                 hc.building_fraction);
                    }
                }
            }
        }
        if (urban_cells.size() > urban_cap_count) {
            // Keep top urban_cap_count by building_fraction.
            std::sort(urban_cells.begin(), urban_cells.end(),
                      [](const auto& a, const auto& b) {
                          return std::get<2>(a) > std::get<2>(b);
                      });
            std::unordered_set<std::pair<int32_t, int32_t>, PairHash>
                keep_urbans;
            for (size_t i = 0; i < urban_cap_count; ++i) {
                keep_urbans.insert({std::get<0>(urban_cells[i]),
                                    std::get<1>(urban_cells[i])});
            }
            for (auto it = union_cells.begin(); it != union_cells.end(); ) {
                const HostCell hc = host_landscape_->at(it->first,
                                                        it->second);
                if (hc.urban_class == URBAN_CLASS_THRESHOLD &&
                    keep_urbans.count(*it) == 0) {
                    it = union_cells.erase(it);
                } else {
                    ++it;
                }
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

        // Advance pool hydrology for this patch.
        const float rain_val = climate_->rain_at(cell.first, cell.second);
        const float temp_val = climate_->temp_at(cell.first, cell.second);
        DailyForcing forcing{rain_val, temp_val};

        auto pool_it = pool_states_.find(pid);
        const bool pre_existing = (pre_it != pre_rowcol_to_pid.end());
        const bool is_permanent = pre_existing
            ? habitat_.patches()[static_cast<size_t>(pid)].is_permanent
            : climate_->permanent_water_at(cell.first, cell.second) > 0.0f;
        if (is_permanent) {
            // Permanent water is not governed by the temporary-pool drying model.
            PoolState stable;
            stable.water_mm = POOL_WATER_MAX_MM;
            stable.days_dry = 0;
            stable.days_since_fill = 0;
            pool_states_[pid] = stable;
        } else if (pool_it == pool_states_.end()) {
            // First day this patch is tracked — initialise from rain.
            PoolState init;
            init.water_mm = rain_val;
            init.days_dry = (rain_val < POOL_WATER_DRY_MM) ? 1 : 0;
            init.days_since_fill = (rain_val > PLUVIAL_POOL_RAIN_THRESHOLD_MM)
                ? 0 : 1;
            pool_states_[pid] = init;
        } else {
            pool_states_[pid] = advance_pool(pool_it->second, forcing);
        }

        const PoolState& pool = pool_states_[pid];

        PatchState ps;
        ps.patch_id = pid;
        ps.row = cell.first;
        ps.col = cell.second;
        ps.activated = (pool.water_mm >= POOL_WATER_BREED_MM);
        ps.rain_d = rain_val;
        ps.temp_d = temp_val;
        ps.water_frac = climate_->water_frac_at(cell.first, cell.second);
        ps.salinity_ppt = climate_->salinity_at(cell.first, cell.second);
        // Salinity hard gate (M7.8): a patch whose water salinity
        // exceeds the species' high tolerance cannot breed. This
        // deactivates coastal brackish cells for freshwater-limited
        // species and also disables oviposition site search (which
        // reads ps.activated) at those cells.
        if (ps.salinity_ppt >= salinity_hi_tol_ppt_) {
            ps.activated = false;
        }
        ps.pool_water_mm = pool.water_mm;
        ps.pool_days_dry = pool.days_dry;
        ps.is_permanent = is_permanent;
        // Urban capacity scaling (plan §6.4): f(building_fraction) clamped
        // to [URBAN_CAPACITY_FLOOR, URBAN_CAPACITY_CEIL]. For non-urban
        // patches the factor stays at 1.0.
        if (host_landscape_ != nullptr) {
            const HostCell hc = host_landscape_->at(cell.first, cell.second);
            if (hc.urban_class == URBAN_CLASS_THRESHOLD) {
                ps.urban_capacity_factor = std::clamp(
                    hc.building_fraction, URBAN_CAPACITY_FLOOR,
                    URBAN_CAPACITY_CEIL);
            }
        }
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

std::vector<SeedInstruction> CoordinatorModel::build_seed_instructions(
    const SeedingConfig& config) {
    // 1. Filter habitat patches by the viability rule:
    //      water_frac > config.min_water_frac (default 0.05)
    //      twi        > config.min_twi        (default 8.0)
    // The current Ghana dataset has water_frac=1.0 and TWI > 8 on
    // all 19,424 patches, so the filter is a no-op today. The
    // criteria are present so the future datasets (where some
    // cells are dry / low-TWI) drop out cleanly.
    std::vector<int32_t> viable_ids;
    std::vector<std::array<double, 2>> viable_lonlat;
    std::vector<std::array<int32_t, 2>> viable_rowcol;
    const auto& patches = habitat_.patches();
    viable_ids.reserve(patches.size());
    viable_lonlat.reserve(patches.size());
    viable_rowcol.reserve(patches.size());
    for (size_t i = 0; i < patches.size(); ++i) {
        const auto& p = patches[i];
        // The HabitatPatch struct only carries twi_value; the
        // water_frac is read from the climate's per-cell band
        // (same source the dynamic-patch rule uses). We fall
        // back to `p.water_frac_value` (a future field) when
        // the climate lookup is unavailable; for now, the
        // climate->water_frac_at(p.row, p.col) is the canonical
        // source.
        const float water_frac = (climate_ != nullptr)
            ? climate_->water_frac_at(p.row, p.col)
            : 1.0f;  // optimistic default: treat as viable
        if (!(water_frac > config.min_water_frac)) continue;
        if (!(p.twi_value > config.min_twi)) continue;
        viable_ids.push_back(static_cast<int32_t>(i));
        viable_lonlat.push_back({p.lon, p.lat});
        viable_rowcol.push_back({p.row, p.col});
    }

    // 2. Delegate to the free function in seeding.cpp. The
    //    coordinator owns the per-rollout Prng, so the random
    //    selection in RANDOM_VIABLE mode goes through it (keeping
    //    the stream reproducible).
    return build_seed_instructions_for_patches(config, viable_ids,
                                               viable_lonlat, viable_rowcol,
                                               rng_);
}

DensityGrid CoordinatorModel::aggregate_density(const MosquitoSubmodel& sub,
                                                int32_t k_max) const {
    const int32_t H = climate_->h();
    const int32_t W = climate_->w();
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
    const int32_t H = climate_->h();
    const int32_t W = climate_->w();
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
                                               int32_t seed,
                                               int32_t n_rollouts,
                                               int32_t rollout_index) const {
    StateCogMetadata meta;
    meta.crs = aoi_.crs;
    meta.aoi_slug = aoi_.slug;
    meta.scale = aoi_.scale;
    meta.year = year;
    meta.month = month;
    meta.seed = seed;
    // F1.c: propagate the per-rollout metadata to the sidecar.
    meta.n_rollouts    = n_rollouts;
    meta.rollout_index = rollout_index;
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
