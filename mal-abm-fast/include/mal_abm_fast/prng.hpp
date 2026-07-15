// SPDX-License-Identifier: MIT
// prng.hpp — xoshiro256** + splitmix64 (stub; F1.c implements)
#pragma once

#include <cstdint>

namespace mal_abm_fast {

// xoshiro256** generator. Will be fleshed out in F1.c.
struct xoshiro256pp {
    uint64_t s[4];

    void seed_from(uint64_t s0);
    uint64_t next();
    double uniform();    // uniform [0, 1)
    double normal();     // Box-Muller on uniform()
    int32_t binomial(int32_t n, double p);
};

// splitmix64 — 64-bit avalanche mixer used to derive sub-seeds.
uint64_t splitmix64(uint64_t& state);

}  // namespace mal_abm_fast
