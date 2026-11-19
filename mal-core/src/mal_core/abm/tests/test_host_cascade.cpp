// SPDX-License-Identifier: MIT
// test_host_cascade.cpp — Perception cascade (plan Paso 5): bands by distance,
// d_min of the swept segment, wind blocking, flight budget, determinism.
#include <gtest/gtest.h>

#include <cmath>
#include <vector>

#include "mal_abm_fast/host_cascade.hpp"
#include "mal_abm_fast/human_state.hpp"

namespace mal_abm_fast {
namespace {

// A 10 x 10 km world (10 x 10 cells of 1 km) with only the declared people.
HumanCompartmentGrid world(const std::vector<std::pair<double, double>>& people) {
    HumanCompartmentGrid g;
    g.init(10, 10, std::vector<float>(100, 0.0f), 5, 10, 30, false, 0.0, 1000.0, 1);
    std::vector<HumanSeed> seeds;
    for (const auto& [x, y] : people) {
        HumanSeed s; s.x = x; s.y = y; seeds.push_back(s);
    }
    g.set_individuals(seeds);
    g.build_spatial_index(25.0);
    return g;
}

CascadeParams params() { return CascadeParams::for_species(MosquitoSpeciesId::ANOPHELES_COLUZZII); }

FlightState at(double x, double y) { FlightState f; f.x = x; f.y = y; return f; }

TEST(CascadeParams, ComeFromTheYamlAndTheBudgetIsDerived) {
    const auto p = params();
    EXPECT_DOUBLE_EQ(p.co2_activation_radius_m, 100.0);
    EXPECT_NEAR(p.directed_flight_budget_h, p.daily_move_capacity_m / p.flight_speed_ms / 3600.0, 1e-3);
    // The daily budget is split by activity weight over the active phases.
    double total = 0.0;
    for (int ph = 0; ph < 4; ++ph) total += p.phase_flight_seconds(ph);
    EXPECT_NEAR(total, p.directed_flight_budget_h * 3600.0, 1e-6);
    EXPECT_DOUBLE_EQ(p.phase_flight_seconds(0), 0.0);       // DAY: weight 0
    EXPECT_GT(p.phase_flight_seconds(2), p.phase_flight_seconds(1));   // NIGHT > EVENING
}

TEST(CascadeParams, OverridesChangeOneKeyAndKeepTheRadiiNested) {
    auto p = params();
    EXPECT_TRUE(CascadeParams::is_overridable("olfactory_radius_m"));
    EXPECT_FALSE(CascadeParams::is_overridable("not_a_key"));
    EXPECT_TRUE(p.apply_override("olfactory_radius_m", 30.0));
    EXPECT_DOUBLE_EQ(p.olfactory_radius_m, 30.0);
    EXPECT_FALSE(p.apply_override("not_a_key", 1.0));
    // 150 m olfactory would exceed the 100 m CO2 radius: refused, params intact.
    EXPECT_THROW(p.apply_override("olfactory_radius_m", 150.0), std::invalid_argument);
    EXPECT_DOUBLE_EQ(p.olfactory_radius_m, 30.0);
}

TEST(SpatialIndex, NearestToSegmentUsesDistanceToTheSegmentNotTheEndPoint) {
    auto g = world({{5200.0, 5240.0}});
    HumanCompartmentGrid::SegmentHit hit;
    // A 300 m step along y = 5200 passes 40 m from the person at x = 5200...
    ASSERT_TRUE(g.nearest_to_segment(5000, 5200, 5300, 5200, 50.0, hit));
    EXPECT_NEAR(hit.d_min, 40.0, 1e-6);
    // ...even though its end point is 100.4 m away from them.
    EXPECT_GT(std::hypot(5300 - 5200, 5200 - 5240), 100.0);
    // Entry fraction: the segment first comes within 50 m of the person at
    // x = 5200 - sqrt(50^2 - 40^2) = 5170 -> t = 170/300.
    EXPECT_NEAR(hit.t_entry, 170.0 / 300.0, 1e-9);
    // Nobody within 30 m of the segment.
    EXPECT_FALSE(g.nearest_to_segment(5000, 5200, 5300, 5200, 30.0, hit));
}

TEST(Cascade, FarFemaleOnlyExploresAndKeepsTheDailyPathBudget) {
    auto g = world({{9000.0, 9000.0}});
    const auto p = params();
    FlightState fs = at(1000, 1000);
    Prng rng(5);
    for (int ph = 0; ph < 4; ++ph) fly_phase(p, g, fs, ph, WindSample{}, 10000, 10000, rng);
    EXPECT_EQ(fs.stage, CascadeStage::EXPLORATION);
    EXPECT_LE(fs.path_used_m, p.daily_move_capacity_m + 1e-9);          // 590 m of path per day
    EXPECT_NEAR(fs.path_used_m, p.daily_move_capacity_m, 1e-6);         // and the day is used up
    EXPECT_LE(fs.flight_used_s, p.directed_flight_budget_h * 3600.0 + 1e-6);
    // Net displacement is an OUTPUT, far below the path length.
    EXPECT_LT(std::hypot(fs.x - 1000, fs.y - 1000), p.daily_move_capacity_m);
}

TEST(Cascade, ActivationHappensOnlyInsideTheCo2Radius) {
    // Person at 250 m: even exploring the whole day, the female reaches the
    // 100 m band only if the walk gets there; far from it she stays EXPLORATION.
    auto g = world({{9500.0, 5000.0}});                // 9 km away
    const auto p = params();
    FlightState fs = at(500, 5000);
    Prng rng(11);
    for (int ph = 0; ph < 4; ++ph) fly_phase(p, g, fs, ph, WindSample{}, 10000, 10000, rng);
    EXPECT_EQ(fs.stage, CascadeStage::EXPLORATION);
}

TEST(Cascade, StepsAreCutWhereTheBandIsEntered) {
    // Person 90 m away: already inside the CO2 band, outside the olfactory one.
    auto g = world({{5090.0, 5000.0}});
    const auto p = params();
    FlightState fs = at(5000, 5000);
    Prng rng(3);
    fly_phase(p, g, fs, 2, WindSample{}, 10000, 10000, rng);
    EXPECT_GE(static_cast<int>(fs.stage), static_cast<int>(CascadeStage::ACTIVATION));
}

TEST(Cascade, ClosePersonIsReachedAndLanded) {
    // 40 m: inside the olfactory band -> plume tracking -> visual -> contact.
    auto g = world({{5040.0, 5000.0}});
    const auto p = params();
    FlightState fs = at(5000, 5000);
    Prng rng(9);
    PhaseOutcome out;
    for (int ph = 0; ph < 4 && !out.landed; ++ph) out = fly_phase(p, g, fs, ph, WindSample{}, 10000, 10000, rng);
    ASSERT_TRUE(out.landed);
    EXPECT_EQ(out.person, 0);
    EXPECT_EQ(fs.stage, CascadeStage::LANDED);
    EXPECT_GT(out.micro_ticks, 75);   // at least the 3 s landing gate at 25 Hz
    EXPECT_LE(fs.path_used_m, p.daily_move_capacity_m);
}

TEST(Cascade, LandingNeedsTheSpeedGateTime) {
    // Female already at the terminal radius with less than 3 s of flight left.
    auto g = world({{5000.05, 5000.0}});
    auto p = params();
    p.directed_flight_budget_h = 2.0 / 3600.0;           // 2 s of budget
    p.activity_weights = {0.0, 0.0, 1.0, 0.0};
    FlightState fs = at(5000, 5000);
    Prng rng(1);
    const auto out = fly_phase(p, g, fs, 2, WindSample{}, 10000, 10000, rng);
    EXPECT_FALSE(out.landed);                            // v < 50 mm/s for 3 s does not fit in 2 s
    EXPECT_EQ(fs.stage, CascadeStage::CONTACT);
}

TEST(Cascade, StrongHeadwindBlocksTheAdvanceButABreezeDoesNot) {
    // Person 60 m east. Wind blowing FROM the east at 5.1 m/s (night case of
    // the plan) opposes any eastward advance: blocked. From the west: free.
    auto g = world({{5060.0, 5000.0}});
    const auto p = params();
    {
        FlightState fs = at(5000, 5000);
        Prng rng(2);
        WindSample from_east; from_east.u = -5.1;        // u < 0: blowing towards the west
        const auto out = fly_phase(p, g, fs, 2, from_east, 10000, 10000, rng);
        EXPECT_FALSE(out.landed);
        EXPECT_NEAR(fs.x, 5000.0, 1.0);                  // no net progress towards the east
    }
    {
        // A breeze below the blocking threshold (flight speed 0.3375 m/s) does
        // not stop the advance against it.
        FlightState fs = at(5000, 5000);
        Prng rng(2);
        WindSample breeze; breeze.u = -0.2;
        PhaseOutcome out;
        for (int ph = 0; ph < 4 && !out.landed; ++ph)
            out = fly_phase(p, g, fs, ph, breeze, 10000, 10000, rng);
        EXPECT_TRUE(out.landed);
    }
}

TEST(Cascade, SweepsStepPastTheBandEdgeSoTheSameEntryIsNotRetriggered) {
    // E10 shapes: tiny olfactory radius, wide activation radius. A step that
    // stopped exactly ON the band edge used to re-trigger the same entry with
    // 1 mm steps for the rest of the day.
    auto g = world({{5150.0, 5000.0}});
    auto p = params();
    ASSERT_TRUE(p.apply_override("co2_activation_radius_m", 200.0));
    ASSERT_TRUE(p.apply_override("olfactory_radius_m", 10.0));
    for (uint64_t seed = 1; seed <= 20; ++seed) {
        FlightState fs = at(5000, 5000);
        Prng rng(seed);
        for (int ph = 0; ph < 4; ++ph) fly_phase(p, g, fs, ph, WindSample{}, 10000, 10000, rng);
        EXPECT_LE(fs.path_used_m, p.daily_move_capacity_m + 1e-6);
    }
}

TEST(Cascade, IsDeterministicGivenTheStream) {
    auto g = world({{5300.0, 5100.0}, {4800.0, 5200.0}});
    const auto p = params();
    auto run = [&]() {
        FlightState fs = at(5000, 5000);
        Prng rng(77);
        for (int ph = 0; ph < 4; ++ph) fly_phase(p, g, fs, ph, WindSample{}, 10000, 10000, rng);
        return fs;
    };
    const FlightState a = run(), b = run();
    EXPECT_DOUBLE_EQ(a.x, b.x);
    EXPECT_DOUBLE_EQ(a.y, b.y);
    EXPECT_EQ(a.stage, b.stage);
}

TEST(Cascade, StaysInsideTheAoi) {
    auto g = world({{9000.0, 9000.0}});
    const auto p = params();
    FlightState fs = at(5.0, 5.0);
    Prng rng(21);
    for (int ph = 0; ph < 4; ++ph) fly_phase(p, g, fs, ph, WindSample{}, 10000, 10000, rng);
    EXPECT_GE(fs.x, 0.0); EXPECT_LT(fs.x, 10000.0);
    EXPECT_GE(fs.y, 0.0); EXPECT_LT(fs.y, 10000.0);
}

}  // namespace
}  // namespace mal_abm_fast
