// SPDX-License-Identifier: MIT
// habitat_engine.hpp — habitat patches reader (stub; F1.b implements)
#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace mal_abm_fast {

// One habitat patch (or dynamic patch cell). Matches the M1.5 thin slice.
struct HabitatPatchRecord {
    int64_t patch_id   = 0;
    int32_t row        = 0;
    int32_t col        = 0;
    int32_t K          = 1000;     // carrying capacity
    bool    activated  = false;    // rain_24h > 15 mm (PLUVIAL_POOL)
    // Float32 to match the M1.5 wire schema in
    // mal-ghana-sim/src/mal_ghana_sim/abm/patch_state.py (Float32 for all 3).
    // F1.b will load these directly from the Polars source — no narrowing cast.
    float   rain_d     = 0.0f;     // daily rainfall at the patch (mm)
    float   temp_d     = 25.0f;    // daily water temperature (C)
    float   water_frac = 0.0f;     // open water fraction in the cell
};

struct HabitatPatches {
    std::vector<HabitatPatchRecord> records;
};

// Load habitat patches from a gpkg (stub returns empty in F1.a).
HabitatPatches load_habitat_patches(const std::string& habitat_gpkg_path);

}  // namespace mal_abm_fast
