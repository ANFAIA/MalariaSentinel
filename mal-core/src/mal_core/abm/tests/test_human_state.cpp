// SPDX-License-Identifier: MIT
// test_human_state.cpp — Unit tests for the individual human population (SEIR).
//
// Plan Paso 2a: people are individuals with a stable id, a fixed position in
// their cell and a SEIR state with a discrete timer; advance_day() moves
// timers only; infection happens through expose(), on one person.
#include <gtest/gtest.h>
#include <algorithm>
#include <cmath>
#include <set>
#include <vector>

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
    EXPECT_EQ(grid.n_people(), 350);
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

    EXPECT_DOUBLE_EQ(grid.i_at(0, 0), 10.0);
    EXPECT_DOUBLE_EQ(grid.s_at(0, 0), 90.0);
    EXPECT_NEAR(grid.prev_at(0, 0), 0.10, 1e-12);

    EXPECT_DOUBLE_EQ(grid.i_at(0, 1), 20.0);
    EXPECT_DOUBLE_EQ(grid.s_at(0, 1), 180.0);

    EXPECT_TRUE(grid.validate_invariants());
}

// -- individuals ------------------------------------------------------------

TEST(HumanIndividuals, NumberOfPeopleIsTheRoundedDensityOfEachCell) {
    HumanCompartmentGrid grid;
    // 0.4 rounds to nobody; no SLOTS_PER_CELL, no empty slots.
    grid.init(1, 4, {3.0f, 0.4f, 7.6f, 0.0f}, 5, 5, 5, false, 0.0);
    EXPECT_EQ(grid.n_people(), 3 + 0 + 8 + 0);
    EXPECT_EQ(grid.cell_begin(0), 0);
    EXPECT_EQ(grid.cell_begin(1), 3);
    EXPECT_EQ(grid.cell_begin(2), 3);
    EXPECT_EQ(grid.cell_begin(3), 11);
    EXPECT_EQ(grid.cell_begin(4), 11);
}

TEST(HumanIndividuals, IdsAreUniqueStableAndIndependentOfOtherCells) {
    HumanCompartmentGrid a, b;
    a.init(2, 2, {5.0f, 6.0f, 7.0f, 8.0f}, 5, 5, 5, false, 0.0, 1000.0, 42);
    // Same cell 3 population, different populations everywhere else.
    b.init(2, 2, {1.0f, 0.0f, 20.0f, 8.0f}, 5, 5, 5, false, 0.0, 1000.0, 42);

    std::set<int64_t> ids(a.people().human_id.begin(), a.people().human_id.end());
    EXPECT_EQ(ids.size(), static_cast<size_t>(a.n_people()));

    // The people of cell 3 have the same ids and positions in both runs.
    for (int64_t k = 0; k < 8; ++k) {
        const size_t ia = static_cast<size_t>(a.cell_begin(3) + k);
        const size_t ib = static_cast<size_t>(b.cell_begin(3) + k);
        EXPECT_EQ(a.people().human_id[ia], b.people().human_id[ib]);
        EXPECT_FLOAT_EQ(a.people().home_x[ia], b.people().home_x[ib]);
        EXPECT_FLOAT_EQ(a.people().home_y[ia], b.people().home_y[ib]);
    }
}

TEST(HumanIndividuals, PositionsAreInsideTheirCellAndFollowTheSeed) {
    const double cell_m = 1000.0;
    HumanCompartmentGrid g1, g2, g3;
    const std::vector<float> density = {400.0f, 400.0f, 400.0f, 400.0f, 400.0f, 400.0f};
    g1.init(2, 3, density, 5, 5, 5, false, 0.0, cell_m, 7);
    g2.init(2, 3, density, 5, 5, 5, false, 0.0, cell_m, 7);
    g3.init(2, 3, density, 5, 5, 5, false, 0.0, cell_m, 8);

    ASSERT_TRUE(g1.validate_invariants());   // checks "inside its home cell" per person
    double sum_x = 0.0, sum_y = 0.0;
    const auto& p = g1.people();
    for (int64_t i = g1.cell_begin(0); i < g1.cell_begin(1); ++i) {   // cell (row 0, col 0)
        sum_x += p.home_x[static_cast<size_t>(i)];
        sum_y += p.home_y[static_cast<size_t>(i)];
    }
    // Row 0 is the north row: its cell spans y in [1000, 2000) of a 2-row grid.
    EXPECT_NEAR(sum_x / 400.0, 500.0, 60.0);
    EXPECT_NEAR(sum_y / 400.0, 1500.0, 60.0);

    EXPECT_EQ(g1.people().home_x, g2.people().home_x);     // same seed, same layout
    EXPECT_EQ(g1.people().home_y, g2.people().home_y);
    EXPECT_NE(g1.people().home_x, g3.people().home_x);     // other seed, other layout
    EXPECT_EQ(g1.people().cur_x, g1.people().home_x);      // no mobility yet
}

TEST(HumanIndividuals, ScenarioPeopleReplaceThePopulationAtTheirPositions) {
    HumanCompartmentGrid grid;
    grid.init(10, 10, std::vector<float>(100, 50.0f), 5, 10, 30, false, 0.0, 1000.0, 1);
    ASSERT_EQ(grid.n_people(), 5000);

    HumanSeed a, b, c;
    a.x = 5400; a.y = 5200;                       // one person
    b.x = 5500; b.y = 5300;                       // same cell as `a`
    c.x = 100;  c.y = 9900; c.state = HumanState::INFECTIOUS; c.timer_days = 3;
    grid.set_individuals({a, b, c});

    EXPECT_EQ(grid.n_people(), 3);
    EXPECT_TRUE(grid.validate_invariants());
    // x = 5400 m -> col 5; y = 5200 m -> row 10 - 1 - 5 = 4.
    EXPECT_DOUBLE_EQ(grid.pop_at(4, 5), 2.0);
    EXPECT_DOUBLE_EQ(grid.pop_at(0, 0), 1.0);     // y = 9900 m -> row 0
    EXPECT_DOUBLE_EQ(grid.i_at(0, 0), 1.0);
    EXPECT_DOUBLE_EQ(grid.pop_at(1, 1), 0.0);
    EXPECT_FLOAT_EQ(grid.people().home_x[static_cast<size_t>(grid.cell_begin(45))], 5400.0f);
    EXPECT_EQ(grid.people().timer[0], 3);          // declared remaining days

    HumanSeed out; out.x = 20000; out.y = 0;
    EXPECT_THROW(grid.set_individuals({out}), std::runtime_error);
}

// -- timers -------------------------------------------------------------------

TEST(HumanState, ExposedBecomesInfectiousAfterExactlyTheIncubationPeriod) {
    HumanCompartmentGrid grid;
    const int32_t incubation_days = 5;
    grid.init(1, 1, {100.0f}, incubation_days, 10, 180, false, 0.0);

    ASSERT_TRUE(grid.expose(7));
    EXPECT_DOUBLE_EQ(grid.e_at(0, 0), 1.0);
    EXPECT_DOUBLE_EQ(grid.inc_at(0, 0), 1.0);        // counted as today's incidence
    EXPECT_FALSE(grid.expose(7));                    // not susceptible any more
    EXPECT_DOUBLE_EQ(grid.inc_at(0, 0), 1.0);

    for (int day = 1; day <= incubation_days - 1; ++day) {
        grid.advance_day();
        EXPECT_DOUBLE_EQ(grid.e_at(0, 0), 1.0) << "Day " << day;
        EXPECT_DOUBLE_EQ(grid.i_at(0, 0), 0.0) << "Day " << day;
    }
    grid.advance_day();                              // the incubation_days-th day
    EXPECT_DOUBLE_EQ(grid.e_at(0, 0), 0.0);
    EXPECT_DOUBLE_EQ(grid.i_at(0, 0), 1.0);
    EXPECT_DOUBLE_EQ(grid.inc_at(0, 0), 0.0);        // incidence is reset every day
    EXPECT_TRUE(grid.validate_invariants());
}

TEST(HumanState, InfectiousDurationAndRecoveryWithoutImmunity) {
    HumanCompartmentGrid grid;
    const int32_t infectious_days = 4;
    grid.init(1, 1, {100.0f}, 2, infectious_days, 180, false, 0.0);

    grid.seed_infections(0, 0, 20.0);
    EXPECT_DOUBLE_EQ(grid.i_at(0, 0), 20.0);
    EXPECT_DOUBLE_EQ(grid.s_at(0, 0), 80.0);

    for (int d = 1; d < infectious_days; ++d) {
        grid.advance_day();
        EXPECT_DOUBLE_EQ(grid.i_at(0, 0), 20.0) << "Day " << d;
    }
    grid.advance_day();

    // After infectious_days, all recover directly to S (no immunity).
    EXPECT_DOUBLE_EQ(grid.i_at(0, 0), 0.0);
    EXPECT_DOUBLE_EQ(grid.s_at(0, 0), 100.0);
    EXPECT_DOUBLE_EQ(grid.r_at(0, 0), 0.0);
    EXPECT_TRUE(grid.validate_invariants());
}

TEST(HumanState, ImmunityWaningCycle) {
    HumanCompartmentGrid grid;
    const int32_t infectious_days = 2;
    const int32_t immunity_days = 3;
    grid.init(1, 1, {100.0f}, 2, infectious_days, immunity_days, true, 0.0);

    grid.seed_infections(0, 0, 40.0);

    for (int d = 1; d <= infectious_days; ++d) grid.advance_day();
    EXPECT_DOUBLE_EQ(grid.i_at(0, 0), 0.0);
    EXPECT_DOUBLE_EQ(grid.r_at(0, 0), 40.0);
    EXPECT_DOUBLE_EQ(grid.s_at(0, 0), 60.0);

    for (int d = 1; d <= immunity_days; ++d) grid.advance_day();
    EXPECT_DOUBLE_EQ(grid.r_at(0, 0), 0.0);
    EXPECT_DOUBLE_EQ(grid.s_at(0, 0), 100.0);
    EXPECT_TRUE(grid.validate_invariants());
}

TEST(HumanState, AdvanceDayAppliesNoInfectionByItself) {
    HumanCompartmentGrid grid;
    grid.init(1, 1, {1000.0f}, 8, 14, 60, true, 0.0);
    for (int day = 1; day <= 30; ++day) grid.advance_day();
    EXPECT_DOUBLE_EQ(grid.s_at(0, 0), 1000.0);       // nobody infected without a bite
}

// -- infection happens on one person ---------------------------------------

TEST(HumanState, ExposeInfectsExactlyThePersonAndNobodyElse) {
    HumanCompartmentGrid grid;
    grid.init(1, 2, {50.0f, 50.0f}, 5, 10, 30, false, 0.0);
    Prng rng(5);

    const int64_t who = grid.pick_person(0, 1, rng);
    ASSERT_GE(who, grid.cell_begin(1));
    ASSERT_LT(who, grid.cell_begin(2));
    ASSERT_TRUE(grid.expose(who));

    int64_t exposed = 0;
    for (int64_t i = 0; i < grid.n_people(); ++i) {
        if (grid.people().state[static_cast<size_t>(i)] ==
            static_cast<uint8_t>(HumanState::EXPOSED)) {
            ++exposed;
            EXPECT_EQ(i, who);
        }
    }
    EXPECT_EQ(exposed, 1);
    EXPECT_DOUBLE_EQ(grid.e_at(0, 0), 0.0);          // the other cell is untouched
    EXPECT_DOUBLE_EQ(grid.e_at(0, 1), 1.0);
    EXPECT_TRUE(grid.validate_invariants());
}

TEST(HumanState, PickPersonOnEmptyCellOrOutsideTheGridReturnsMinusOne) {
    HumanCompartmentGrid grid;
    grid.init(1, 2, {0.0f, 10.0f}, 5, 10, 30, false, 0.0);
    Prng rng(1);
    EXPECT_EQ(grid.pick_person(0, 0, rng), -1);
    EXPECT_EQ(grid.pick_person(3, 0, rng), -1);
    EXPECT_GE(grid.pick_person(0, 1, rng), 0);
}

TEST(HumanState, ConservationAcrossTheCycleWithBites) {
    HumanCompartmentGrid grid;
    grid.init(2, 2, {500.0f, 1000.0f, 250.0f, 0.0f}, 8, 14, 60, true, 0.20);

    Prng rng(777);
    for (int day = 1; day <= 90; ++day) {
        grid.advance_day();
        for (int k = 0; k < 40; ++k) {
            grid.expose(grid.pick_person(static_cast<int32_t>(k % 2), static_cast<int32_t>(k % 2), rng));
        }
        ASSERT_TRUE(grid.validate_invariants()) << "Failed on day " << day;
    }
}

}  // namespace
}  // namespace mal_abm_fast
