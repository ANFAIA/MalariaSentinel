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
    // F1.a: stub returns 0. F1.c will replace with a real xoshiro256**.
    EXPECT_EQ(rng.next(), 0u);
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
