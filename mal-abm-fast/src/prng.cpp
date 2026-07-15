// SPDX-License-Identifier: MIT
// prng.cpp — xoshiro256** (stub; F1.c implements)
#include "prng.hpp"

namespace mal_abm_fast {

void xoshiro256pp::seed_from(uint64_t s0) { (void)s0; for (auto& v : s) v = 0; }
uint64_t xoshiro256pp::next() { return 0; }
double xoshiro256pp::uniform() { return 0.0; }
double xoshiro256pp::normal() { return 0.0; }
int32_t xoshiro256pp::binomial(int32_t n, double p) { (void)p; return n; }

uint64_t splitmix64(uint64_t& state) { return state++; }

}  // namespace mal_abm_fast
