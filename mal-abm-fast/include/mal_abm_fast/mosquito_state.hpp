// SPDX-License-Identifier: MIT
// mosquito_state.hpp — Structure-of-Arrays mosquito population (stub; F1.c implements)
#pragma once

#include <cstdint>
#include <vector>

#include "prng.hpp"

namespace mal_abm_fast {

// SoA layout for the mosquito population. One element per agent.
// Sized by .patch_id.size() == n().
struct MosquitoState {
    std::vector<int64_t>  unique_id;     // stable across the lifetime
    std::vector<int64_t>  patch_id;      // join key with patch_state
    std::vector<int32_t>  row;           // current cell (row, col)
    std::vector<int32_t>  col;
    std::vector<uint8_t>  stage;         // 0 = larva, 1 = adult
    std::vector<float>    lon;           // post-dispersal lon (M2 combined C1)
    std::vector<float>    lat;
    std::vector<float>    eip_progress;  // growing-degree-days accumulated
    std::vector<int32_t>  stage_age;     // days in the current stage

    xoshiro256pp           rng;          // per-rollout sub-stream (F1.c seeds it)
    int32_t K_MAX = 1000;

    int32_t n() const { return static_cast<int32_t>(patch_id.size()); }
};

}  // namespace mal_abm_fast
