// SPDX-License-Identifier: MIT
// test_smoke.cpp — GoogleTest smoke for mal_abm_fast F1.a
#include <gtest/gtest.h>

#include <cmath>

#include "eip.hpp"
#include "prng.hpp"

TEST(MalAbmFastSmoke, VersionConstant) {
    // Compile-time assertion that the EIP constants are pinned at the M1.5 values.
    EXPECT_DOUBLE_EQ(mal_abm_fast::EIP_BASE_C, 16.0);
    EXPECT_DOUBLE_EQ(mal_abm_fast::EIP_THRESHOLD_GD, 110.0);
}

TEST(MalAbmFastSmoke, PrngStub) {
    mal_abm_fast::xoshiro256pp rng;
    rng.seed_from(42);
    // F1.c: real xoshiro256** (replaces the F1.a stub that returned 0).
    // Property check: the stream is deterministic and non-degenerate.
    // The exact value is implementation-defined (Vigna's reference
    // produces 64-bit outputs that depend on the splitmix64 expansion);
    // the F1.e parity test pins the value byte-for-byte against a
    // saved reference. Here we only assert the F1.a→F1.c transition:
    // same seed -> same sequence, non-zero, and different seeds ->
    // different sequences.
    const uint64_t a1 = rng.next();
    const uint64_t a2 = rng.next();
    EXPECT_NE(a1, 0u);
    EXPECT_NE(a1, a2);
    mal_abm_fast::xoshiro256pp rng2;
    rng2.seed_from(42);
    EXPECT_EQ(rng2.next(), a1);
    EXPECT_EQ(rng2.next(), a2);
    mal_abm_fast::xoshiro256pp rng3;
    rng3.seed_from(43);
    EXPECT_NE(rng3.next(), a1);
}

TEST(MalAbmFastSmoke, EipAccumulate) {
    // Below base temperature → no GDD accumulation.
    EXPECT_DOUBLE_EQ(mal_abm_fast::accumulate_eip(0.0, 10.0), 0.0);
    // Above base → positive GDD.
    EXPECT_DOUBLE_EQ(mal_abm_fast::accumulate_eip(0.0, 26.0), 10.0);
    // NaN-safe.
    const double nan = std::nan("");
    EXPECT_DOUBLE_EQ(mal_abm_fast::accumulate_eip(50.0, nan), 50.0);
}
