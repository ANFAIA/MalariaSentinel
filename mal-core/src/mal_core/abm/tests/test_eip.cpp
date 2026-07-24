// SPDX-License-Identifier: MIT
// test_eip.cpp — F1.c unit tests for the EIP (growing-degree-day)
// accumulator and the `is_infective` threshold.
//
// The header `eip.hpp` is header-only with `inline` defs; this test
// file pins the behaviour that the wire-spec.md §4 table promises:
//
//     * daily_gd       = max(0, T - EIP_BASE_C)
//     * eip_progress'  = eip_progress + daily_gd     (NaN-safe)
//     * is_infective   = eip_progress >= EIP_THRESHOLD_GD
//
// The F1.a smoke test (`tests/test_smoke.cpp::EipAccumulate`) already
// pins the below-base, above-base, and NaN cases; we add coverage for
// the multi-day trajectory (11/12/13 days at T=25) and the wire.hpp
// constants.
#include <gtest/gtest.h>

#include <cmath>

#include "eip.hpp"
#include "wire.hpp"

TEST(MalAbmFastEip, BelowBaseNoGdd) {
    // T <= 16 -> no GDD accumulation, eip_progress unchanged.
    EXPECT_FLOAT_EQ(mal_abm_fast::accumulate_eip(0.0f, 10.0f), 0.0f);
    EXPECT_FLOAT_EQ(mal_abm_fast::accumulate_eip(0.0f, 16.0f), 0.0f);
    EXPECT_FLOAT_EQ(mal_abm_fast::accumulate_eip(50.0f, 15.0f), 50.0f);
}

TEST(MalAbmFastEip, AboveBaseAddsGdd) {
    // T=26 -> 10 GD; T=25 -> 9 GD.
    EXPECT_FLOAT_EQ(mal_abm_fast::accumulate_eip(0.0f, 26.0f), 10.0f);
    EXPECT_FLOAT_EQ(mal_abm_fast::accumulate_eip(0.0f, 25.0f),  9.0f);
    EXPECT_FLOAT_EQ(mal_abm_fast::accumulate_eip(0.0f, 30.0f), 14.0f);
}

TEST(MalAbmFastEip, NanSafe) {
    // NaN temperature -> eip_progress unchanged.
    const float nan = std::nanf("");
    EXPECT_FLOAT_EQ(mal_abm_fast::accumulate_eip(0.0f,  nan), 0.0f);
    EXPECT_FLOAT_EQ(mal_abm_fast::accumulate_eip(50.0f, nan), 50.0f);
    EXPECT_FLOAT_EQ(mal_abm_fast::accumulate_eip(109.0f, nan), 109.0f);
}

TEST(MalAbmFastEip, MultiDayTrajectory) {
    // The brief's pin: 11 days at T=25 -> 99 GD; 12 -> 108; 13 -> 117.
    float eip = 0.0f;
    for (int day = 0; day < 11; ++day) {
        eip = mal_abm_fast::accumulate_eip(eip, 25.0f);
    }
    EXPECT_FLOAT_EQ(eip, 99.0f);
    EXPECT_FALSE(mal_abm_fast::is_infective(eip));

    eip = mal_abm_fast::accumulate_eip(eip, 25.0f);  // day 12
    EXPECT_FLOAT_EQ(eip, 108.0f);
    EXPECT_FALSE(mal_abm_fast::is_infective(eip));

    eip = mal_abm_fast::accumulate_eip(eip, 25.0f);  // day 13
    EXPECT_FLOAT_EQ(eip, 117.0f);
    EXPECT_TRUE(mal_abm_fast::is_infective(eip));
}

TEST(MalAbmFastEip, InfectiveThreshold) {
    EXPECT_FALSE(mal_abm_fast::is_infective(0.0f));
    EXPECT_FALSE(mal_abm_fast::is_infective(109.0f));
    EXPECT_TRUE (mal_abm_fast::is_infective(110.0f));
    EXPECT_TRUE (mal_abm_fast::is_infective(150.0f));
}

TEST(MalAbmFastEip, WireConstantsPinned) {
    EXPECT_FLOAT_EQ(mal_abm_fast::EIP_BASE_C,         16.0f);
    EXPECT_FLOAT_EQ(mal_abm_fast::EIP_THRESHOLD_GD,   110.0f);
}

TEST(MalAbmFastEip, MixedTemperatureDays) {
    // Mix of below-base and above-base days. Below-base days must
    // not contribute to eip_progress.
    float eip = 0.0f;
    eip = mal_abm_fast::accumulate_eip(eip, 25.0f);  // +9
    eip = mal_abm_fast::accumulate_eip(eip, 15.0f);  // +0 (below base)
    eip = mal_abm_fast::accumulate_eip(eip, 20.0f);  // +4
    eip = mal_abm_fast::accumulate_eip(eip, std::nanf(""));  // +0 (NaN)
    EXPECT_FLOAT_EQ(eip, 13.0f);
}
