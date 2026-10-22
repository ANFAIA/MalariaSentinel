// SPDX-License-Identifier: MIT
// coordinator.cpp — CoordinatorModel (contract v3.0, proxy_habitat_v1).
//
// The per-day spatial state is the species-neutral pair
//
//   S[i, t]  = clip(sum_g w[g] * H[i, g] * A[i, k(g), t], 0, 1)
//   K[i, t]  = K_ref * cell_area_km2 * S[i, t]           (absolute)
//
// with the pluvial state updated once per day from CHIRPS rainfall:
//   z_dry = z_prev * exp(-delta_days / DRY_MEMORY_DAYS)
//   z     = z_dry + (1 - z_dry) * (1 - exp(-rain_mm / RAIN_SCALE_MM))
//
// Warm-up: the Engine facade calls warm_up_pluvial() once — the SAME
// recursion is integrated over the NC bands before the simulation
// start (causal, no synthetic fixed-window assumption).
#include "coordinator.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <tuple>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

#include "aquatic_stress.hpp"
#include "habitat_availability.hpp"
#include "mosquito_submodel.hpp"
#include "output_contract.hpp"
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
      next_patch_id_(static_cast<int64_t>(
          habitat_.patches().size())) {
    if (!climate_) {
        throw std::runtime_error(
            "CoordinatorModel: null climate engine");
    }
    H_ = climate_->h();
    W_ = climate_->w();
    const size_t hw = static_cast<size_t>(H_) * static_cast<size_t>(W_);
    z_.assign(hw, 0.0f);
    dry_days_.assign(hw, 0);
    K_cell_.assign(hw, 0.0f);
    feats_.reserve(hw);
    for (int32_t r = 0; r < H_; ++r) {
        for (int32_t c = 0; c < W_; ++c) {
            feats_.push_back(climate_->habitat_features_at(r, c));
        }
    }
    if (climate_->jrc_persistent().empty()) {
        std::cout << "ClimateEngine: static habitat planes absent; "
                  << "habitat-driven flows down to zero. Check the env NC "
                  << "contract_version (v3.0 expected).\n";
    }
}

void CoordinatorModel::warm_up_pluvial(int32_t n_warmup_bands) {
    if (n_warmup_bands <= 0) return;
    if (!climate_) return;
    const int32_t base = climate_->base_day();
    const int32_t cold_start = std::max(0, base - n_warmup_bands);
    float z_cold = static_cast<float>(load_config().pluvial.cold_start_z);
    for (int32_t band = cold_start; band < base; ++band) {
        const std::vector<float> rain = climate_->rain_band(band);
        const size_t n = static_cast<size_t>(H_) * static_cast<size_t>(W_);
        if (z_.size() != n || rain.size() != n) return;
        for (size_t i = 0; i < n; ++i) {
            z_[i] = update_z_step(
                z_[i], std::max(0.0f, rain[i]),
                static_cast<float>(load_config().pluvial.delta_days));
        }
    }
    (void)z_cold;
}

void CoordinatorModel::update_habitat_day(float gamma_t) {
    // MVP: gamma_T = 0 keeps drying purely rain-driven (plan §6.4 —
    // temperature already acts through the aquatic development and
    // adult-survival submodels; a second penalty would double-count).
    // A future extension may scale tau with temperature when a
    // calibration cycle shows a real deficit.
    (void)gamma_t;
    const int32_t H = climate_->h();
    const int32_t W = climate_->w();
    const size_t n = static_cast<size_t>(H) * static_cast<size_t>(W);
    if (H_ != H || W_ != W) {
        // Grid may differ if a custom bbox was requested post-load.
        H_ = H;
        W_ = W;
        z_.assign(n, 0.0f);
        dry_days_.assign(n, 0);
        K_cell_.assign(n, 0.0f);
        feats_.assign(n, HabitatFeatures{});
        for (int32_t r = 0; r < H_; ++r) {
            for (int32_t c = 0; c < W_; ++c) {
                feats_[r * W_ + c] = climate_->habitat_features_at(r, c);
            }
        }
    }

    const std::array<float, 6> weights_sq = default_species_weights();

    // 1. Pluvial state advance (rain-driven only in the MVP).
    for (size_t i = 0; i < n; ++i) {
        const float rain = climate_->rain_daily()[i];
        z_[i] = update_z_step(
                z_[i], std::max(0.0f, rain),
                static_cast<float>(load_config().pluvial.delta_days));
    }

    // 2. Accuracy S and per-cell dry streaks.
    int64_t n_live = 0;
    for (int32_t r = 0; r < H; ++r) {
        const double lat_cell_deg =
            aoi_.north - (static_cast<double>(r) + 0.5) *
            (aoi_.north - aoi_.south) / H;
        const double row_area_km2 =
            cell_area_km2(lat_cell_deg, aoi_.resolution_m);
        for (int32_t c = 0; c < W; ++c) {
            const size_t idx = static_cast<size_t>(r) *
                                   static_cast<size_t>(W) +
                               static_cast<size_t>(c);
            const std::array<float, 6> h =
                habitat_potential(feats_[idx]);
            const float S = species_accuracy(h, weights_sq, z_[idx]);
            if (S >= habitat_activation_min()) {
                dry_days_[idx] = 0;
                ++n_live;
            } else {
                dry_days_[idx] += 1;
            }
            K_cell_[idx] = static_cast<float>(k_habitat(S, row_area_km2));
        }
    }
    std::cout << "coordinator: band " << climate_->base_day()
              << " live cells (S >= " << habitat_activation_min() << "): " << n_live
              << " / " << (n) << "\n";
}

std::vector<PatchState> CoordinatorModel::to_dataframe() {
    const int32_t H = climate_->h();
    const int32_t W = climate_->w();
    const size_t hw = static_cast<size_t>(H) * static_cast<size_t>(W);

    // Build the candidate union: gpkg patches + candidate cells from the
    // static potential (plan §8: the candidate-floor rule).
    std::unordered_set<std::pair<int32_t, int32_t>, PairHash> candidates;
    candidates.reserve(habitat_.patches().size() + hw / 8);

    for (const auto& patch : habitat_.patches()) {
        candidates.insert({patch.row, patch.col});
    }
    for (size_t i = 0; i < hw; ++i) {
        const float total = habitat_total_potential(
            habitat_potential(feats_[i]));
        if (total < habitat_candidate_min_engine()) continue;
        candidates.insert({static_cast<int32_t>(i / W),
                           static_cast<int32_t>(i % W)});
    }

    std::unordered_map<std::pair<int32_t, int32_t>, int64_t, PairHash>
        pre_rowcol_to_pid;
    pre_rowcol_to_pid.reserve(habitat_.patches().size());
    for (size_t i = 0; i < habitat_.patches().size(); ++i) {
        const auto& patch = habitat_.patches()[i];
        pre_rowcol_to_pid[{patch.row, patch.col}] = static_cast<int64_t>(i);
    }

    std::vector<PatchState> states;
    states.reserve(candidates.size());
    for (const auto& cell : candidates) {
        int64_t pid;
        auto pre_it = pre_rowcol_to_pid.find(cell);
        if (pre_it != pre_rowcol_to_pid.end()) {
            pid = pre_it->second;
            patch_registry_[cell] = pid;
        } else {
            auto reg_it = patch_registry_.find(cell);
            if (reg_it != patch_registry_.end()) {
                pid = reg_it->second;
            } else {
                pid = next_patch_id_++;
                patch_registry_[cell] = pid;
            }
        }

        const int32_t r = cell.first;
        const int32_t c = cell.second;
        const size_t idx = static_cast<size_t>(r) *
                               static_cast<size_t>(W) + static_cast<size_t>(c);
        PatchState ps;
        ps.patch_id = pid;
        ps.row = r;
        ps.col = c;
        ps.rain_d = climate_->rain_at(r, c);
        ps.temp_d = climate_->temp_at(r, c);
        ps.salinity_ppt = climate_->salinity_at(r, c);

        const auto h = habitat_potential(feats_[idx]);
        ps.habitat_avail = species_accuracy(h, default_species_weights(), z_[idx]);
        ps.activated = ps.habitat_avail >= habitat_activation_min();
        ps.habitat_dry_days = dry_days_[idx];
        ps.k_habitat = K_cell_[idx];

        // Salinity hard gate (preserved M7.8): a patch whose water
        // salinity exceeds the species' high tolerance cannot breed.
        if (ps.salinity_ppt >= salinity_hi_tol_ppt_) {
            ps.activated = false;
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
    // Contract v3.0: viability is potential-based; config.min_water_frac
    // / config.min_twi are retired gates and ignored (the SeedingConfig
    // fields are required by the legacy engine surface).
    std::vector<int32_t> viable_ids;
    std::vector<std::array<double, 2>> viable_lonlat;
    std::vector<std::array<int32_t, 2>> viable_rowcol;
    const auto& patches = habitat_.patches();
    viable_ids.reserve(patches.size());
    viable_lonlat.reserve(patches.size());
    viable_rowcol.reserve(patches.size());
    for (size_t i = 0; i < patches.size(); ++i) {
        const auto& p = patches[i];
        if (!(p.potential >= habitat_candidate_min_engine())) continue;
        viable_ids.push_back(static_cast<int32_t>(i));
        viable_lonlat.push_back({p.lon, p.lat});
        viable_rowcol.push_back({p.row, p.col});
    }

    std::vector<SeedInstruction> out;
    if (config.mode == SeedingMode::HOST_WEIGHTED) {
        if (host_landscape_ == nullptr) {
            throw std::runtime_error(
                "build_seed_instructions: HOST_WEIGHTED seeding requires "
                "--hosts (HostLandscape) to be loaded");
        }
        const int32_t gh = host_landscape_->h();
        const int32_t gw = host_landscape_->w();
        std::vector<float> cell_host_score(
            static_cast<size_t>(gh) * static_cast<size_t>(gw), 0.0f);
        const HostPrefWeights& prefs = config.host_prefs;
        for (int32_t r = 0; r < gh; ++r) {
            for (int32_t c = 0; c < gw; ++c) {
                const HostCell cell = host_landscape_->at(r, c);
                const auto& hs = load_config().host_seeking;
                const float indoor_mod = 1.0f + cell.indoor_fraction *
                    static_cast<float>(hs.indoor_attraction_add);
                const float urban_mod =
                    1.0f + static_cast<float>(hs.urbanicity_add) *
                               cell.urbanicity;
                const float mod = indoor_mod * urban_mod;
                float att = 0.0f;
                att += cell.humans_present    * prefs.human;
                att += cell.cattle_present    * prefs.cattle;
                att += cell.goats_present     * prefs.goat;
                att += cell.sheep_present     * prefs.sheep;
                att += cell.pigs_present      * prefs.cattle;   // pigs ≈ cattle
                att += cell.chickens_present  * prefs.wildlife;
                att += cell.wildlife_proxy    * prefs.wildlife;
                att *= mod;
                if (att > 0.0f) {
                    cell_host_score[static_cast<size_t>(r) *
                        static_cast<size_t>(gw) + static_cast<size_t>(c)] = att;
                }
            }
        }
        const float cell_size_m = static_cast<float>(aoi_.resolution_m);
        out = build_seed_instructions_host_weighted(
            config, viable_ids, viable_lonlat, viable_rowcol,
            cell_host_score, gh, gw, cell_size_m, rng_);
    } else {
        out = build_seed_instructions_for_patches(
            config, viable_ids, viable_lonlat, viable_rowcol, rng_);
    }

    // Contract v3.0 retired the per-seed urban capacity factor with the
    // urban floor; contract 4.0 removed the field entirely — counts
    // seed verbatim.
    return out;
}

std::vector<SeedInstruction>
CoordinatorModel::build_uniform_seed_instructions(
    int32_t n_adults, int32_t n_immatures) {
    std::vector<SeedInstruction> out;
    if (n_adults < 0 || n_immatures < 0 ||
        (n_adults == 0 && n_immatures == 0)) return out;

    // Day-0 candidate union via to_dataframe(); stable pids are
    // registered so the daily loop reuses the same numbering.
    const std::vector<PatchState> states = to_dataframe();

    const int32_t W = climate_->w() > 0 ? climate_->w() : 1;
    const int32_t H = climate_->h() > 0 ? climate_->h() : 1;
    const double pixel_w = (aoi_.east - aoi_.west) / W;
    const double pixel_h = (aoi_.north - aoi_.south) / H;

    out.reserve(states.size());
    for (const auto& ps : states) {
        SeedInstruction inst;
        inst.patch_id = static_cast<int32_t>(ps.patch_id);
        inst.row      = ps.row;
        inst.col      = ps.col;
        inst.lon      = aoi_.west + (ps.col + 0.5) * pixel_w;
        inst.lat      = aoi_.north - (ps.row + 0.5) * pixel_h;
        inst.n_adults = n_adults;
        inst.n_larvae = n_immatures;
        out.push_back(inst);
    }
    return out;
}

DensityGrid CoordinatorModel::aggregate_density(
                                                const MosquitoSubmodel& sub) const {
    // Contract 4.0: raw per-cell adult counts (individuals). Adults are
    // associated to a cell via their patch — no capacity normalization.
    const int32_t H = climate_->h();
    const int32_t W = climate_->w();
    DensityGrid grid;
    grid.h = H;
    grid.w = W;
    grid.data.assign(static_cast<size_t>(H) * static_cast<size_t>(W), 0.0f);
    if (H <= 0 || W <= 0) return grid;

    std::unordered_map<int64_t, std::pair<int32_t, int32_t>> pid_to_cell;
    pid_to_cell.reserve(habitat_.patches().size() + patch_registry_.size());
    for (size_t i = 0; i < habitat_.patches().size(); ++i) {
        const auto& patch = habitat_.patches()[i];
        pid_to_cell[static_cast<int64_t>(i)] = {patch.row, patch.col};
    }
    for (const auto& kv : patch_registry_) {
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

    // Contract 4.0: raw counts — no division, no clamp.
    for (size_t i = 0; i < flat.size(); ++i) {
        grid.data[i] = static_cast<float>(flat[i]);
    }
    return grid;
}

SuitabilityGrid CoordinatorModel::suitability_grid(
    const MosquitoSubmodel& sub) const {
    // Contract 4.0: raw per-cell adult counts at the adults' current
    // position — no capacity normalization. NOTE: this counts all
    // adults (any sex/state), not only host-seeking females.
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

    // Contract 4.0: raw counts — no division, no clamp.
    for (size_t i = 0; i < flat.size(); ++i) {
        grid.data[i] = static_cast<float>(flat[i]);
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
    meta.n_rollouts    = n_rollouts;
    meta.rollout_index = rollout_index;
    meta.h = density.h;
    meta.w = density.w;

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
