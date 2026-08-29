// SPDX-License-Identifier: MIT
// seeding.hpp — detection-based initial seeding for the ABM.
//
// The default constructor of `MosquitoSubmodel` (uniform seeding)
// distributes larvae evenly across every patch. That is convenient
// for warm starts but unrealistic: mosquitoes are first detected at
// specific surveillance points (a village, a trap, a sentinel site)
// and spread from there. This header introduces a small "build a
// list of per-patch seeding instructions" facility with three modes:
//
//   * `UNIFORM`        — legacy path. No instructions are emitted;
//                        the submodel uses `init_frac` for every
//                        patch (backward compatible).
//   * `RANDOM_VIABLE`  — pick N random patch_ids from the
//                        "viable" set (water_frac > 0.05 AND
//                        twi > 8). Each chosen patch gets a
//                        configurable mix of adults and larvae.
//   * `EXPLICIT`       — user provides lat/lon points. For each
//                        point, find the nearest patch within
//                        `detection_radius_km` (Euclidean metric on
//                        the lon/lat grid; a proper geodesic metric
//                        is a future improvement).
//
// Each emitted `SeedInstruction` carries a (patch_id, row, col,
// lon, lat, n_adults, n_larvae) tuple. The adult count is placed
// with `eip_progress = EIP_THRESHOLD_GD` so the new agents are
// ready to disperse on day 1. Larvae start at `eip_progress = 0`
// and must accumulate growing-degree-days before promotion.
#pragma once

#include <array>
#include <cstdint>
#include <vector>

#include "prng.hpp"

namespace mal_abm_fast {

enum class SeedingMode {
    UNIFORM,        // backward compat: init_frac of K in all patches
    RANDOM_VIABLE,  // N random points from viable patches
    EXPLICIT,       // user-provided lat/lon
    HOST_WEIGHTED   // N viable patches sampled ∝ nearby host abundance
                    // weighted by species host preferences (mirrors
                    // HostSeekingModel::cell_attraction, no decay cap).
                    // Places the initial population where blood meals
                    // actually are; subsequent dispersal/oviposition
                    // behaviour is the model's own (M7.4.1 iteration).
};

// A user-supplied detection point. In EXPLICIT mode the (lat, lon)
// fields are required; in RANDOM_VIABLE / UNIFORM they are ignored.
// Per-point counts default to the global SeedingConfig defaults.
struct DetectionPoint {
    double  lat       = 0.0;
    double  lon       = 0.0;
    int32_t n_adults  = 500;
    int32_t n_larvae  = 200;
};

// Species host preference weights used by HOST_WEIGHTED seeding.
// Mirror of the SpeciesParams pref_* model attraction weights (plan §5.3).
// Defaults are ZERO on purpose: the canonical values live in the C++
// registry `species_params_for()` (species_params.cpp, literature-sourced)
// and the Engine always stamps them in from `species_params_` — the same
// object that drives runtime host-seeking. Zero defaults make an
// unfilled config fail loudly (nothing seeded) instead of silently
// seeding with stale copies of species constants.
struct HostPrefWeights {
    float human    = 0.0f;
    float cattle   = 0.0f;
    float goat     = 0.0f;
    float sheep    = 0.0f;
    float wildlife = 0.0f;
};

// Configuration for the detection-based seeding subsystem.
struct SeedingConfig {
    SeedingMode mode = SeedingMode::UNIFORM;

    // For RANDOM_VIABLE:
    int32_t n_detections         = 1;
    double  detection_radius_km  = 5.0;   // also used as max snap distance for EXPLICIT

    // For EXPLICIT:
    std::vector<DetectionPoint> detections;

    // For UNIFORM (legacy):
    float init_frac = 0.30f;

    // Per-detection defaults (apply to RANDOM_VIABLE; EXPLICIT can
    // override per-point via DetectionPoint).
    int32_t n_adults_per_detection = 500;
    int32_t n_larvae_per_detection = 200;

    // Viability filter (applies to RANDOM_VIABLE).
    float min_water_frac = 0.05f;
    float min_twi        = 8.0f;

    // For HOST_WEIGHTED:
    double host_weight_radius_km = 5.0;  // search radius around each patch
    float  host_seeking_scale_m  = 100.0f;  // Gaussian decay scale (metres);
                                            // mirror SpeciesParams::host_seeking_scale_m
    HostPrefWeights host_prefs;          // species host preferences
};

// Per-patch seeding instruction. Built by the coordinator and
// consumed by the submodel constructor.
struct SeedInstruction {
    int32_t patch_id = 0;
    int32_t row      = 0;
    int32_t col      = 0;
    double  lon      = 0.0;
    double  lat      = 0.0;
    int32_t n_adults = 0;
    int32_t n_larvae = 0;
    // Urban capacity factor (plan §6.4, M17.4 PR-A): in
    // [URBAN_CAPACITY_FLOOR, URBAN_CAPACITY_CEIL] for urban-sourced
    // patches, 1.0 for terrain patches. Mirrors PatchState::urban_capacity_factor.
    // Carried here so the submodel's seed loop can cap adult counts
    // by K_MAX * factor (per-patch) rather than the global K_MAX.
    float   urban_capacity_factor = 1.0f;
};

// Build a list of SeedInstructions from a SeedingConfig + habitat info.
//
//   `viable_patch_ids` — patch_ids that pass the viability filter
//                         (water_frac > min_water_frac AND twi > min_twi).
//                         Pass the full set in UNIFORM mode (it is unused).
//   `patch_lonlat`     — per-patch [lon, lat] (parallel to viable_patch_ids).
//   `patch_rowcol`     — per-patch [row, col] (parallel to viable_patch_ids).
//   `rng`              — used for random selection in RANDOM_VIABLE mode.
//
// Returns an empty vector for UNIFORM mode (the submodel uses
// init_frac for every patch — the legacy path).
//
// NOTE: the function is named `build_seed_instructions_for_patches`
// to avoid clashing with `CoordinatorModel::build_seed_instructions`,
// which is a higher-level wrapper that filters the habitat patches
// first and then calls this free function.
std::vector<SeedInstruction> build_seed_instructions_for_patches(
    const SeedingConfig& config,
    const std::vector<int32_t>& viable_patch_ids,
    const std::vector<std::array<double, 2>>& patch_lonlat,
    const std::vector<std::array<int32_t, 2>>& patch_rowcol,
    Prng& rng);

// HOST_WEIGHTED mode builder.
//
// `cell_host_score` — flat (h × w) per-cell host attractiveness:
//   Σ_k hosts_k(x) · pref_k · indoor_mod · urban_mod   (no decay yet;
//   decay is applied per-patch below). Computed by the coordinator
//   from the HostLandscape using config.host_prefs.
//
// Patch weight W_p = Σ_{c within radius} score(c) · exp(-dist(p,c)/scale).
// Patches are sampled without replacement ∝ W_p (roulette with removal),
// up to config.n_detections; each chosen patch receives
// n_adults_per_detection adults + n_larvae_per_detection larvae.
// Patches with zero weight (no hosts within radius) are never sampled.
std::vector<SeedInstruction> build_seed_instructions_host_weighted(
    const SeedingConfig& config,
    const std::vector<int32_t>& viable_patch_ids,
    const std::vector<std::array<double, 2>>& patch_lonlat,
    const std::vector<std::array<int32_t, 2>>& patch_rowcol,
    const std::vector<float>& cell_host_score,
    int32_t grid_h,
    int32_t grid_w,
    float cell_size_m,
    Prng& rng);

}  // namespace mal_abm_fast
