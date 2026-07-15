// SPDX-License-Identifier: MIT
// mosquito_state.hpp — Structure-of-Arrays mosquito population.
//
// One element per agent across all 9 SoA vectors. The "packed" layout
// is critical for SIMD: only indices [0, n_alive) are valid, and
// operations (mortality, growth, EIP, dispersal, birth) rewrite the
// vectors in place by compacting survivors to the front.
//
// `uid` is the unique_id (stable for the agent's lifetime). `stage`
// is 0 for larva, 1 for adult. The `lon`/`lat` floats are EPSG:4326
// degrees; for newly born larvae the coord subagent writes the patch
// cell centre, and for adults the dispersal step overwrites the
// (lon, lat) with a clipped-Gaussian draw.
//
// `next_uid` is the next unique_id to allocate; it monotonically
// increases over the rollout and is never reused. Two `MosquitoSoA`s
// with the same construction parameters and the same RNG draw order
// produce identical UIDs in the same order.
#pragma once

#include <cstdint>
#include <vector>

namespace mal_abm_fast {

struct MosquitoSoA {
    std::vector<int64_t>  uid;          // unique_id (stable for the agent's life)
    std::vector<int64_t>  patch_id;     // join key with PatchState
    std::vector<int32_t>  row;          // current cell (row, col)
    std::vector<int32_t>  col;
    std::vector<uint8_t>  stage;        // 0 = larva, 1 = adult
    std::vector<float>    lon;          // EPSG:4326 deg (0 = not yet set)
    std::vector<float>    lat;          // EPSG:4326 deg (0 = not yet set)
    std::vector<float>    eip_progress; // growing-degree-days accumulated
    std::vector<int32_t>  stage_age;    // days in the current stage

    int64_t n_alive  = 0;   // valid prefix length of all SoA vectors
    int64_t next_uid = 0;   // next unique_id to allocate
};

}  // namespace mal_abm_fast
