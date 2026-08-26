// SPDX-License-Identifier: MIT
// test_human_state.cpp — Unit tests for spatial HumanCompartmentGrid (SEIR).
#include <gtest/gtest.h>
#include <vector>
#include <cmath>

#include "mal_abm_fast/human_state.hpp"
#include "mal_abm_fast/prng.hpp"

namespace mal_abm_fast {
namespace {

TEST(HumanState, InitializationWithoutInfection) {
    HumanCompartmentGrid grid;
    std::vector<float> density = {100.0f, 200.0f, 0.0f, 50.0f};
    grid.init(2, 2, density, 12, 20, 180, false, 0.0);

    EXPECT_EQ(grid.h(), 2);
    EXPECT_EQ(grid.w(), 2);
    EXPECT_DOUBLE_EQ(grid.pop_at(0, 0), 100.0);
    EXPECT_DOUBLE_EQ(grid.s_at(0, 0), 100.0);
    EXPECT_DOUBLE_EQ(grid.e_at(0, 0), 0.0);
    EXPECT_DOUBLE_EQ(grid.i_at(0, 0), 0.0);
    EXPECT_DOUBLE_EQ(grid.r_at(0, 0), 0.0);
    EXPECT_DOUBLE_EQ(grid.prev_at(0, 0), 0.0);

    EXPECT_TRUE(grid.validate_invariants());
    const auto stats = grid.compute_stats();
    EXPECT_DOUBLE_EQ(stats.total_population, 350.0);
    EXPECT_DOUBLE_EQ(stats.total_susceptible, 350.0);
    EXPECT_DOUBLE_EQ(stats.total_infectious, 0.0);
}

TEST(HumanState, InitializationWithPrevalence) {
    HumanCompartmentGrid grid;
    std::vector<float> density = {100.0f, 200.0f};
    grid.init(1, 2, density, 10, 20, 180, false, 0.10);

    EXPECT_NEAR(grid.i_at(0, 0), 10.0, 1e-4);
    EXPECT_NEAR(grid.s_at(0, 0), 90.0, 1e-4);
    EXPECT_NEAR(grid.prev_at(0, 0), 0.10, 1e-4);

    EXPECT_NEAR(grid.i_at(0, 1), 20.0, 1e-4);
    EXPECT_NEAR(grid.s_at(0, 1), 180.0, 1e-4);

    EXPECT_TRUE(grid.validate_invariants());
}

TEST(HumanState, IncubationQueueExactTiming) {
    HumanCompartmentGrid grid;
    std::vector<float> density = {100.0f};
    const int32_t incubation_days = 5;
    const int32_t infectious_days = 10;
    grid.init(1, 1, density, incubation_days, infectious_days, 180, false, 0.0);

    Prng rng(42);

    // Day 1: Apply force of infection
    std::vector<double> lambda = {0.10};  // 10% exposed
    grid.advance_day(lambda, rng);

    const double initial_exp = grid.e_at(0, 0);
    EXPECT_GT(initial_exp, 0.0);
    EXPECT_DOUBLE_EQ(grid.i_at(0, 0), 0.0);  // None infectious yet on day 1

    // Days 2 to incubation_days: exposed cohort stays in E_H
    std::vector<double> zero_lambda = {0.0};
    for (int day = 2; day <= incubation_days; ++day) {
        grid.advance_day(zero_lambda, rng);
        EXPECT_NEAR(grid.e_at(0, 0), initial_exp, 1e-5) << "Day " << day;
        EXPECT_DOUBLE_EQ(grid.i_at(0, 0), 0.0) << "Day " << day;
    }

    // Day incubation_days + 1: exposed cohort graduates to I_H
    grid.advance_day(zero_lambda, rng);
    EXPECT_DOUBLE_EQ(grid.e_at(0, 0), 0.0);
    EXPECT_NEAR(grid.i_at(0, 0), initial_exp, 1e-5);
    EXPECT_TRUE(grid.validate_invariants());
}

TEST(HumanState, InfectiousDurationAndRecoveryWithoutImmunity) {
    HumanCompartmentGrid grid;
    std::vector<float> density = {100.0f};
    const int32_t incubation_days = 2;
    const int32_t infectious_days = 4;
    grid.init(1, 1, density, incubation_days, infectious_days, 180, false, 0.0);

    Prng rng(123);
    grid.seed_infections(0, 0, 20.0);
    EXPECT_NEAR(grid.i_at(0, 0), 20.0, 1e-5);
    EXPECT_NEAR(grid.s_at(0, 0), 80.0, 1e-5);

    std::vector<double> zero_lambda = {0.0};
    // Advance infectious_days
    grid.advance_day(zero_lambda, rng);
    EXPECT_NEAR(grid.i_at(0, 0), 20.0, 1e-5);
    for (int d = 2; d <= infectious_days; ++d) {
        grid.advance_day(zero_lambda, rng);
    }

    // After infectious_days without new exposure, all recover directly to S_H (no immunity)
    EXPECT_NEAR(grid.i_at(0, 0), 0.0, 1e-5);
    EXPECT_NEAR(grid.s_at(0, 0), 100.0, 1e-5);
    EXPECT_DOUBLE_EQ(grid.r_at(0, 0), 0.0);
    EXPECT_TRUE(grid.validate_invariants());
}

TEST(HumanState, ImmunityWaningCycle) {
    HumanCompartmentGrid grid;
    std::vector<float> density = {100.0f};
    const int32_t incubation_days = 2;
    const int32_t infectious_days = 2;
    const int32_t immunity_days = 3;
    grid.init(1, 1, density, incubation_days, infectious_days, immunity_days, true, 0.0);

    Prng rng(999);
    grid.seed_infections(0, 0, 40.0);

    std::vector<double> zero_lambda = {0.0};
    // Step through infectious period (2 days) -> moves to R_H
    for (int d = 1; d <= infectious_days; ++d) {
        grid.advance_day(zero_lambda, rng);
    }
    EXPECT_NEAR(grid.i_at(0, 0), 0.0, 1e-5);
    EXPECT_NEAR(grid.r_at(0, 0), 40.0, 1e-5);
    EXPECT_NEAR(grid.s_at(0, 0), 60.0, 1e-5);

    // Step through immunity period (3 days) -> moves from R_H back to S_H
    for (int d = 1; d <= immunity_days; ++d) {
        grid.advance_day(zero_lambda, rng);
    }
    EXPECT_NEAR(grid.r_at(0, 0), 0.0, 1e-5);
    EXPECT_NEAR(grid.s_at(0, 0), 100.0, 1e-5);
    EXPECT_TRUE(grid.validate_invariants());
}

TEST(HumanState, ConservationUnderHighTransmission) {
    HumanCompartmentGrid grid;
    std::vector<float> density = {500.0f, 1000.0f, 250.0f, 0.0f};
    grid.init(2, 2, density, 8, 14, 60, true, 0.20);

    Prng rng(777);
    std::vector<double> high_lambda = {0.5, 0.8, 0.3, 0.0};

    for (int day = 1; day <= 90; ++day) {
        grid.advance_day(high_lambda, rng);
        ASSERT_TRUE(grid.validate_invariants()) << "Failed on day " << day;
    }
}

}  // namespace
}  // namespace mal_abm_fast
