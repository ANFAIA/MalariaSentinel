// SPDX-License-Identifier: MIT
// prng.hpp — F1.b canonical PRNG interface (and F1.a compatibility shim).
//
// Two types live here:
//
// 1. `xoshiro256pp` — the F1.a struct. Stubbed methods (`seed_from`,
//    `next`, `uniform`, `normal`, `binomial`) so the F1.a smoke test
//    keeps passing. The math subagent (F1.c) replaces the stub .cpp
//    with a real xoshiro256** implementation. The state word is the
//    4-tuple `s[0..3]`; a `next()` draw rotates the state once.
//
// 2. `Prng` — the F1.b canonical PRNG. The 4 implementation subagents
//    see ONLY this class for the per-day operations (`binomial`,
//    `normal`, `uniform_double` for `dispersal.offset_m`). It is a
//    thin wrapper over xoshiro256** (or whatever the math subagent
//    prefers) so the stream is reproducible. `peek_state()` returns
//    the raw `s[0]` word for the F1.e parity test (same seed -> same
//    stream -> same state COG).
//
// Determinism
// -----------
// The CLI seeds a `Prng` with `--seed` (uint64). Each module that
// needs a sub-stream derives a new `Prng` via `seed(derived_seed)` so
// per-module streams are independent. Two runs with the same `--seed`
// produce byte-equal state COGs.
#pragma once

#include <cstdint>

namespace mal_abm_fast {

// ---------------------------------------------------------------------------
// F1.a compatibility type — kept so the existing F1.a smoke test still
// passes. The math subagent (F1.c) replaces the stub implementations in
// prng.cpp with a real xoshiro256** (Vigna's reference implementation).
// ---------------------------------------------------------------------------
struct xoshiro256pp {
    uint64_t s[4];

    // Seed from a single 64-bit value (splitmix64-driven expansion into s[0..3]).
    void     seed_from(uint64_t s0);
    // Advance the state and return a 64-bit pseudo-random word.
    uint64_t next();
    // Uniform double in [0, 1).
    double   uniform();
    // Standard normal (Box-Muller or ratio of uniforms).
    double   normal();
    // Binomial draw (n trials, probability p). Stub returns n.
    int32_t  binomial(int32_t n, double p);
};

// splitmix64 — 64-bit avalanche mixer used to derive sub-seeds.
uint64_t splitmix64(uint64_t& state);

// ---------------------------------------------------------------------------
// F1.b canonical PRNG — the type the 4 implementation subagents use.
// ---------------------------------------------------------------------------
class Prng {
public:
    Prng() = default;
    // Construct + seed in one call.
    explicit Prng(uint64_t seed);

    // Re-seed (splitmix64 expansion under the hood).
    void seed(uint64_t s);

    // Uniform double in [0, 1). The first draw after `seed(s)` is
    // deterministic given `s` — the parity test relies on this.
    double uniform_double();

    // Standard normal draw with optional mean/sigma. The default
    // arguments give the canonical N(0, 1).
    double normal(double mu = 0.0, double sigma = 1.0);

    // Binomial draw (n trials, probability p).
    //   * For n <= 1000: sum of n Bernoulli draws via uniform_double().
    //   * For n >  1000: numpy-compatible normal approximation
    //                   (round(max(0, mu + sigma * normal())), clipped to [0, n]).
    // The stream goes through this->uniform_double() / this->normal()
    // so the parity test can replay the full sequence.
    int binomial(int n, double p);

    // Test helper: return the raw xoshiro256** s[0] state word. Used
    // by the F1.e parity test to assert the stream is reproducible.
    uint64_t peek_state() const;
};

}  // namespace mal_abm_fast
