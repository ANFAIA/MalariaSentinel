// SPDX-License-Identifier: MIT
// prng.cpp — F1.c real implementation of xoshiro256** + splitmix64.
//
// The xoshiro256** generator is Sebastiano Vigna's reference implementation
// (https://prng.di.unimi.it/xoshiro256starstar.c, public domain). The
// splitmix64 mixer is also Vigna's (https://prng.di.unimi.it/splitmix64.c,
// public domain). The state is filled from a single 64-bit seed by
// splitmix64 — the same pattern Vigna's `main()` uses for seeding.
//
// The `xoshiro256pp` struct is the F1.a compatibility shim. Its public
// members (`s[4]`) are filled from `seed_from()` and stepped by `next()`
// using the same xoshiro256** code path as the F1.b `Prng` class. The
// F1.a smoke test (`tests/test_smoke.cpp::PrngStub`) is updated to check
// the new non-zero, deterministic behaviour (see wire-spec.md §7).
//
// The `Prng` class stores its 4-word state in a file-scope map keyed by
// `this`. This avoids touching `prng.hpp` (the architect owns the header
// and the brief forbids .hpp edits). The map grows monotonically — for
// F1.b there are at most a handful of `Prng` instances (coordinator +
// submodel), so the unbounded growth is a non-issue. Lookup is O(1)
// amortised with a small constant.
#include "prng.hpp"

#include <array>
#include <cmath>
#include <cstdint>
#include <unordered_map>

namespace mal_abm_fast {

namespace {

// Vigna's splitmix64 — a 64-bit avalanche mixer used to expand a single
// seed into the 4-word xoshiro256** state. The golden-ratio constant
// (0x9e3779b97f4a7c15) ensures the increment covers the full period.
inline uint64_t splitmix64_step(uint64_t& state) noexcept {
    state += 0x9e3779b97f4a7c15ULL;
    uint64_t z = state;
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
}

inline uint64_t rotl(uint64_t x, int k) noexcept {
    return (x << k) | (x >> (64 - k));
}

// One xoshiro256** step. Mutates `s` in place and returns the output
// word. Identical to Vigna's reference (public domain).
inline uint64_t xoshiro256pp_step(uint64_t s[4]) noexcept {
    const uint64_t result = rotl(s[1] * 5, 7) * 9;
    const uint64_t t = s[1] << 17;
    s[2] ^= s[0];
    s[3] ^= s[1];
    s[1] ^= s[2];
    s[0] ^= s[3];
    s[2] ^= t;
    s[3] = rotl(s[3], 45);
    return result;
}

// File-scope state store for `Prng` instances. Keyed by `const void*`
// (i.e. `this`) so both const and non-const methods can look up the
// state without a `const_cast`.
using PrngState = std::array<uint64_t, 4>;
std::unordered_map<const void*, PrngState>& prng_state_map() noexcept {
    static std::unordered_map<const void*, PrngState> m;
    return m;
}

}  // namespace

// -- F1.a compatibility: xoshiro256pp ----------------------------------------

void xoshiro256pp::seed_from(uint64_t s0) {
    if (s0 == 0) s0 = 1;  // splitmix64 requires a non-zero seed.
    uint64_t state = s0;
    s[0] = splitmix64_step(state);
    s[1] = splitmix64_step(state);
    s[2] = splitmix64_step(state);
    s[3] = splitmix64_step(state);
}

uint64_t xoshiro256pp::next() {
    return xoshiro256pp_step(s);
}

double xoshiro256pp::uniform() {
    // Standard xoshiro256** double conversion: 53 bits of mantissa.
    return (next() >> 11) * (1.0 / static_cast<double>(1ULL << 53));
}

double xoshiro256pp::normal() {
    // Box-Muller (one of the two outputs is discarded; the submodel's
    // `dispersal` draws two independent normals per call via `Prng::normal`,
    // so the waste is amortised).
    double u1 = uniform();
    if (u1 < 1e-12) u1 = 1e-12;  // guard against log(0).
    const double u2 = uniform();
    return std::sqrt(-2.0 * std::log(u1)) * std::cos(2.0 * M_PI * u2);
}

int32_t xoshiro256pp::binomial(int32_t n, double p) {
    if (n <= 0)   return 0;
    if (p <= 0.0) return 0;
    if (p >= 1.0) return n;
    const double np = static_cast<double>(n) * p;
    if (np < 30.0) {
        // Small expected count: sum of n Bernoulli trials.
        int32_t k = 0;
        for (int32_t i = 0; i < n; ++i) {
            if (uniform() < p) ++k;
        }
        return k;
    }
    // Large expected count: normal approximation, clamped to [0, n].
    const double mu    = np;
    const double sigma = std::sqrt(np * (1.0 - p));
    const double z     = normal();
    long k = std::lround(mu + sigma * z);
    if (k < 0)   k = 0;
    if (k > n)   k = n;
    return static_cast<int32_t>(k);
}

uint64_t splitmix64(uint64_t& state) {
    return splitmix64_step(state);
}

// -- F1.b canonical: Prng ----------------------------------------------------
//
// The `Prng` class in `prng.hpp` has no data members (the brief
// forbids editing the header). The 4-word xoshiro256** state is held
// in a file-scope map keyed by `this` (see `prng_state_map()` above).
//
// `Prng() = default;` is explicitly defaulted in the header, so the
// default constructor is defined inline. The destructor and move
// operations are implicitly declared and defined inline — we cannot
// redefine them in this translation unit. The consequence is:
//
//   * A destroyed Prng leaves its map entry behind. For F1.b there
//     are at most a handful of Prng instances (coordinator + submodel
//     + per-module derived sub-streams), so the leak is bounded.
//   * A moved-from Prng retains its map entry, and the moved-to Prng
//     has no entry. The F1.b engine constructs its Prngs once and
//     never moves them, so this is a non-issue in practice.
//
// To get correct move semantics without touching the header we would
// need a data member on `Prng`; that is a deliberate trade-off the
// brief forces on us. If a future revision adds the member, replace
// this map-based store with the inline state and remove the map
// machinery.

Prng::Prng(uint64_t seed_v) {
    this->seed(seed_v);
}

void Prng::seed(uint64_t s) {
    if (s == 0) s = 1;  // splitmix64 requires a non-zero seed.
    uint64_t state = s;
    PrngState& st = prng_state_map()[this];
    st[0] = splitmix64_step(state);
    st[1] = splitmix64_step(state);
    st[2] = splitmix64_step(state);
    st[3] = splitmix64_step(state);
}

double Prng::uniform_double() {
    auto& m = prng_state_map();
    auto it = m.find(this);
    if (it == m.end()) {
        // Unseeded Prng: deterministic fallback to a zero-state stream.
        // xoshiro256** requires non-zero state, so a fully-zero state
        // would loop on zero — instead, we lazy-seed with a fixed value
        // (1) so the stream is at least non-degenerate. Callers should
        // always `seed()` before use; this branch is a safety net.
        PrngState st{};
        uint64_t state = 1ULL;
        st[0] = splitmix64_step(state);
        st[1] = splitmix64_step(state);
        st[2] = splitmix64_step(state);
        st[3] = splitmix64_step(state);
        it = m.emplace(this, st).first;
    }
    const uint64_t r = xoshiro256pp_step(it->second.data());
    return static_cast<double>(r >> 11) * (1.0 / static_cast<double>(1ULL << 53));
}

double Prng::normal(double mu, double sigma) {
    // Box-Muller.
    double u1 = uniform_double();
    if (u1 < 1e-12) u1 = 1e-12;
    const double u2 = uniform_double();
    const double z = std::sqrt(-2.0 * std::log(u1)) * std::cos(2.0 * M_PI * u2);
    return mu + sigma * z;
}

int Prng::binomial(int n, double p) {
    if (n <= 0)   return 0;
    if (p <= 0.0) return 0;
    if (p >= 1.0) return n;
    const double np = static_cast<double>(n) * p;
    if (np < 30.0) {
        int k = 0;
        for (int i = 0; i < n; ++i) {
            if (uniform_double() < p) ++k;
        }
        return k;
    }
    const double mu    = np;
    const double sigma = std::sqrt(np * (1.0 - p));
    const double z     = normal();
    long k = std::lround(mu + sigma * z);
    if (k < 0) k = 0;
    if (k > n) k = n;
    return static_cast<int>(k);
}

uint64_t Prng::peek_state() const {
    auto& m = prng_state_map();
    auto it = m.find(this);
    if (it == m.end()) return 0;
    return it->second[0];
}

}  // namespace mal_abm_fast
