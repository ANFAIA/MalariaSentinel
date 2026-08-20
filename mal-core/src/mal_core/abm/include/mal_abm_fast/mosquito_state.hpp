// SPDX-License-Identifier: MIT
// mosquito_state.hpp — Structure-of-Arrays mosquito population.
//
// One element per agent across all SoA vectors. The "packed" layout
// is critical for SIMD: only indices [0, n_alive) are valid, and
// operations (mortality, growth, EIP, dispersal, birth) rewrite the
// vectors in place by compacting survivors to the front.
//
// `uid` is the unique_id (stable for the agent's lifetime). `stage`
// is 0 for immature/aquatic, 1 for adult. The new `aquatic_stage`
// field provides finer granularity (EGG/LARVA/PUPA) within stage 0.
// `sex` is MALE=0 / FEMALE=1; only females take blood meals.
// `development_progress` tracks egg→adult maturation (GDD accumulated).
// `parasite_eip_progress` tracks Plasmodium development in adult
// females only (starts at 0; meaningful from M7.2 onwards).
#pragma once

#include <cstdint>
#include <vector>

#include "gonotrophic_cycle.hpp"

namespace mal_abm_fast {

struct MosquitoSoA {
    std::vector<int64_t>  uid;                    // unique_id (stable for the agent's life)
    std::vector<int64_t>  patch_id;               // join key with PatchState
    std::vector<int32_t>  row;                    // current cell (row, col)
    std::vector<int32_t>  col;
    std::vector<uint8_t>  stage;                  // 0 = immature/aquatic, 1 = adult
    std::vector<uint8_t>  sex;                    // 0 = MALE, 1 = FEMALE
    std::vector<float>    lon;                    // EPSG:4326 deg (0 = not yet set)
    std::vector<float>    lat;                    // EPSG:4326 deg (0 = not yet set)
    std::vector<float>    development_progress;   // egg→larva→pupa→adult growing-degree-days
    std::vector<float>    parasite_eip_progress;  // Plasmodium EIP in adult females only
    std::vector<uint8_t>  aquatic_stage;          // EGG=0, LARVA=1, PUPA=2 (stage==0 only)
    std::vector<uint8_t>  larval_instar;          // 1–4 instar (LARVA stage only)
    std::vector<int32_t>  stage_age;              // days in the current stage
    std::vector<int32_t>  days_since_active;      // days since patch was active (desiccation)

    // G4: Gonotrophic cycle fields (females only; males keep defaults).
    std::vector<uint8_t>  gonotrophic_state;      // GonotrophicState enum
    std::vector<int32_t>  gonotrophic_timer;      // days in current state
    std::vector<int32_t>  gonotrophic_cycles;     // completed gonotrophic cycles (first = 0)
    std::vector<float>    feeding_success;         // 1.0 if fed today, 0.0 otherwise
    std::vector<uint8_t>  species_id;              // MosquitoSpeciesId (0 = ANOPHELES_COLUZZII)

    // Patch tracking cache (Plan D Phase 4): last (row, col) passed to
    // update_patch_id(). If the agent hasn't moved since the last call,
    // update_patch_id() is O(1) instead of O(N_patches).
    std::vector<int32_t>  last_patch_update_row;
    std::vector<int32_t>  last_patch_update_col;

    int64_t n_alive  = 0;   // valid prefix length of all SoA vectors
    int64_t next_uid = 0;   // next unique_id to allocate
};

}  // namespace mal_abm_fast
