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
    EXPLICIT        // user-provided lat/lon
};

// A user-supplied detection point. In EXPLICIT mode the (lat, lon)
// fields are required; in RANDOM_VIABLE / UNIFORM they are ignored.
// Per-point counts default to the global SeedingConfig defaults.
struct DetectionPoint {
    double  lat       = 0.0;
    double  lon       = 0.0;
    int32_t n_adults  = 50;
    int32_t n_larvae  = 30;
};

// Configuration for the detection-based seeding subsystem.
struct SeedingConfig {
    SeedingMode mode = SeedingMode::UNIFORM;

    // For RANDOM_VIABLE:
    int32_t n_detections         = 3;
    double  detection_radius_km  = 5.0;   // also used as max snap distance for EXPLICIT

    // For EXPLICIT:
    std::vector<DetectionPoint> detections;

    // For UNIFORM (legacy):
    float init_frac = 0.30f;

    // Per-detection defaults (apply to RANDOM_VIABLE; EXPLICIT can
    // override per-point via DetectionPoint).
    int32_t n_adults_per_detection = 50;
    int32_t n_larvae_per_detection = 30;

    // Viability filter (applies to RANDOM_VIABLE).
    float min_water_frac = 0.05f;
    float min_twi        = 8.0f;
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

}  // namespace mal_abm_fast
