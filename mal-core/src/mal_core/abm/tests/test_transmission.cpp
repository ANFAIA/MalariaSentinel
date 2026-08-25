// SPDX-License-Identifier: MIT
// test_transmission.cpp — Unit tests for TransmissionModel (SEIR-SEI).
#include <gtest/gtest.h>
#include <vector>
#include <cmath>

#include "mal_abm_fast/transmission.hpp"
#include "mal_abm_fast/climate.hpp"

namespace mal_abm_fast {
namespace {

TEST(TransmissionModel, Initialization) {
    TransmissionModel tm;
    TransmissionParams params;
    params.enabled = true;
    params.beta_hv = 0.45f;
    params.beta_vh = 0.55f;
    params.human_seeding_mode = "uniform-legacy";
    params.initial_human_prevalence = 0.05;

    std::vector<float> human_pop = {100.0f, 200.0f};
    tm.init(1, 2, human_pop, params, 42);

    EXPECT_TRUE(tm.is_enabled());
    EXPECT_FLOAT_EQ(tm.params().beta_hv, 0.45f);
    EXPECT_FLOAT_EQ(tm.params().beta_vh, 0.55f);
    EXPECT_EQ(tm.human_grid().h(), 1);
    EXPECT_EQ(tm.human_grid().w(), 2);
    EXPECT_NEAR(tm.human_grid().prev_at(0, 0), 0.05, 1e-4);
}

TEST(TransmissionModel, ForceOfInfectionHazardFormula) {
    TransmissionModel tm;
    TransmissionParams params;
    params.enabled = true;
    params.beta_vh = 0.50f;
    params.initial_human_prevalence = 0.0;

    std::vector<float> human_pop = {100.0f, 0.0f};
    tm.init(1, 2, human_pop, params, 100);

    BiteLedger bites;
    // Record 10 infectious bites at (0, 0) and 5 at (0, 1) (where H=0)
    for (int i = 0; i < 10; ++i) {
        bites.record_infectious_success(0, 0, HostType::HUMAN);
    }
    for (int i = 0; i < 5; ++i) {
        bites.record_infectious_success(0, 1, HostType::HUMAN);
    }

    AOI aoi;
    tm.advance_human_transmission(bites, aoi);

    const auto& lambda = tm.last_force_of_infection();
    // At (0, 0): lambda = 1 - exp(- 0.50 * 10 / 100) = 1 - exp(-0.05) ≈ 0.04877
    const double expected_lambda_0 = 1.0 - std::exp(-0.50 * 10.0 / 100.0);
    EXPECT_NEAR(lambda[0], expected_lambda_0, 1e-5);

    // At (0, 1): H=0 -> lambda must be strictly 0.0
    EXPECT_DOUBLE_EQ(lambda[1], 0.0);
}

TEST(TransmissionModel, VectorEipProgressionAtConstantTemp) {
    TransmissionModel tm;
    TransmissionParams params;
    params.enabled = true;
    params.eip_base_temp = 16.0f;
    params.eip_threshold_gd = 110.0f;

    std::vector<float> human_pop = {100.0f};
    tm.init(1, 1, human_pop, params, 1);

    MosquitoSoA soa;
    soa.n_alive = 1;
    soa.uid.push_back(1);
    soa.patch_id.push_back(0);
    soa.row.push_back(0);
    soa.col.push_back(0);
    soa.stage.push_back(1);  // adult
    soa.sex.push_back(1);    // female
    soa.lon.push_back(0.0f);
    soa.lat.push_back(0.0f);
    soa.development_progress.push_back(0.0f);
    soa.parasite_eip_progress.push_back(0.0f);
    soa.aquatic_stage.push_back(0);
    soa.larval_instar.push_back(0);
    soa.stage_age.push_back(0);
    soa.days_since_active.push_back(0);
    soa.gonotrophic_state.push_back(0);
    soa.gonotrophic_timer.push_back(0);
    soa.gonotrophic_cycles.push_back(0);
    soa.feeding_success.push_back(0.0f);
    soa.species_id.push_back(0);
    soa.vector_state.push_back(static_cast<uint8_t>(VectorTransmissionState::EXPOSED));
    soa.last_patch_update_row.push_back(0);
    soa.last_patch_update_col.push_back(0);

    ClimateEngine climate;
    // We can test with dummy patch_states where temp_d is 25 deg C (daily GD = 25 - 16 = 9)
    std::vector<PatchState> patch_states;
    AOI aoi;

    // At 25°C: 12 days * 9 = 108 GD (< 110 threshold) -> still EXPOSED
    for (int day = 1; day <= 12; ++day) {
        tm.advance_vector_eip(soa, climate, patch_states, aoi);
        EXPECT_EQ(soa.vector_state[0], static_cast<uint8_t>(VectorTransmissionState::EXPOSED))
            << "Day " << day;
    }
    EXPECT_NEAR(soa.parasite_eip_progress[0], 108.0f, 1e-4f);

    // Day 13: 108 + 9 = 117 GD (>= 110 threshold) -> transitions to INFECTIOUS
    tm.advance_vector_eip(soa, climate, patch_states, aoi);
    EXPECT_EQ(soa.vector_state[0], static_cast<uint8_t>(VectorTransmissionState::INFECTIOUS));
    EXPECT_NEAR(soa.parasite_eip_progress[0], 117.0f, 1e-4f);
}

TEST(TransmissionModel, SeedVectorInfections) {
    TransmissionModel tm;
    TransmissionParams params;
    params.enabled = true;
    params.eip_threshold_gd = 110.0f;

    std::vector<float> human_pop = {100.0f};
    tm.init(1, 1, human_pop, params, 77);

    MosquitoSoA soa;
    const int N = 100;
    soa.n_alive = N;
    for (int i = 0; i < N; ++i) {
        soa.uid.push_back(i);
        soa.patch_id.push_back(0);
        soa.row.push_back(0);
        soa.col.push_back(0);
        soa.stage.push_back(1);
        soa.sex.push_back(1);  // females
        soa.lon.push_back(0.0f);
        soa.lat.push_back(0.0f);
        soa.development_progress.push_back(0.0f);
        soa.parasite_eip_progress.push_back(0.0f);
        soa.aquatic_stage.push_back(0);
        soa.larval_instar.push_back(0);
        soa.stage_age.push_back(0);
        soa.days_since_active.push_back(0);
        soa.gonotrophic_state.push_back(0);
        soa.gonotrophic_timer.push_back(0);
        soa.gonotrophic_cycles.push_back(0);
        soa.feeding_success.push_back(0.0f);
        soa.species_id.push_back(0);
        soa.vector_state.push_back(static_cast<uint8_t>(VectorTransmissionState::SUSCEPTIBLE));
        soa.last_patch_update_row.push_back(0);
        soa.last_patch_update_col.push_back(0);
    }

    tm.seed_vector_infections(soa, 0.20);

    int count_inf = 0;
    for (int i = 0; i < N; ++i) {
        if (soa.vector_state[i] == static_cast<uint8_t>(VectorTransmissionState::INFECTIOUS)) {
            count_inf++;
            EXPECT_GE(soa.parasite_eip_progress[i], 110.0f);
        }
    }
    EXPECT_GT(count_inf, 5);
    EXPECT_LT(count_inf, 40);
}

TEST(TransmissionModel, FemaleOnlyVectorInfectionInvariant) {
    TransmissionModel tm;
    TransmissionParams params;
    params.enabled = true;

    std::vector<float> human_pop = {100.0f};
    tm.init(1, 1, human_pop, params, 99);

    MosquitoSoA soa;
    soa.n_alive = 2;

    // Mosquito 0: Adult Male (sex=0)
    soa.uid.push_back(1); soa.patch_id.push_back(0); soa.row.push_back(0); soa.col.push_back(0);
    soa.stage.push_back(1); soa.sex.push_back(0); soa.lon.push_back(0.0f); soa.lat.push_back(0.0f);
    soa.development_progress.push_back(0.0f); soa.parasite_eip_progress.push_back(0.0f);
    soa.aquatic_stage.push_back(0); soa.larval_instar.push_back(0); soa.stage_age.push_back(0);
    soa.days_since_active.push_back(0); soa.gonotrophic_state.push_back(0); soa.gonotrophic_timer.push_back(0);
    soa.gonotrophic_cycles.push_back(0); soa.feeding_success.push_back(0.0f); soa.species_id.push_back(0);
    soa.vector_state.push_back(static_cast<uint8_t>(VectorTransmissionState::SUSCEPTIBLE));
    soa.last_patch_update_row.push_back(0); soa.last_patch_update_col.push_back(0);

    // Mosquito 1: Adult Female (sex=1)
    soa.uid.push_back(2); soa.patch_id.push_back(0); soa.row.push_back(0); soa.col.push_back(0);
    soa.stage.push_back(1); soa.sex.push_back(1); soa.lon.push_back(0.0f); soa.lat.push_back(0.0f);
    soa.development_progress.push_back(0.0f); soa.parasite_eip_progress.push_back(0.0f);
    soa.aquatic_stage.push_back(0); soa.larval_instar.push_back(0); soa.stage_age.push_back(0);
    soa.days_since_active.push_back(0); soa.gonotrophic_state.push_back(0); soa.gonotrophic_timer.push_back(0);
    soa.gonotrophic_cycles.push_back(0); soa.feeding_success.push_back(0.0f); soa.species_id.push_back(0);
    soa.vector_state.push_back(static_cast<uint8_t>(VectorTransmissionState::SUSCEPTIBLE));
    soa.last_patch_update_row.push_back(0); soa.last_patch_update_col.push_back(0);

    // Seed 100% infection
    tm.seed_vector_infections(soa, 1.0);

    // Male MUST remain SUSCEPTIBLE
    EXPECT_EQ(soa.vector_state[0], static_cast<uint8_t>(VectorTransmissionState::SUSCEPTIBLE));
    // Female MUST become INFECTIOUS
    EXPECT_EQ(soa.vector_state[1], static_cast<uint8_t>(VectorTransmissionState::INFECTIOUS));
}

TEST(TransmissionModel, RandomViableHumanFocalSeeding) {
    TransmissionModel tm;
    TransmissionParams params;
    params.enabled = true;
    params.human_seeding_mode = "random-viable";
    params.human_outbreak_day = 0;
    params.human_outbreak_foci = 2;
    params.human_outbreak_cases = 30.0;
    params.human_min_cell_pop = 50.0;

    // Grid 2x2: (0,0)=100 humans, (0,1)=200 humans, (1,0)=10 humans (<50), (1,1)=0 humans
    std::vector<float> human_pop = {100.0f, 200.0f, 10.0f, 0.0f};
    std::vector<float> mosq_dens = {0.1f, 0.2f, 0.0f, 0.0f};

    tm.init(2, 2, human_pop, params, 123);
    tm.check_and_trigger_outbreak(0, mosq_dens);

    const auto stats = tm.human_grid().compute_stats();
    // 2 foci seeded with 30 cases each = 60 infectious humans
    EXPECT_DOUBLE_EQ(stats.total_infectious, 60.0);
    // (1,0) had 10 pop < 50, so must have 0 infected
    EXPECT_DOUBLE_EQ(tm.human_grid().i_at(1, 0), 0.0);
    // (1,1) had 0 pop, so 0 infected
    EXPECT_DOUBLE_EQ(tm.human_grid().i_at(1, 1), 0.0);
    // Total pop is 310
    EXPECT_DOUBLE_EQ(stats.total_population, 310.0);
    EXPECT_TRUE(tm.human_grid().validate_invariants());
}

TEST(TransmissionModel, DelayedHumanOutbreakTrigger) {
    TransmissionModel tm;
    TransmissionParams params;
    params.enabled = true;
    params.human_seeding_mode = "random-viable";
    params.human_outbreak_day = 60; // Brote en dia 60 (2 meses warm-up)
    params.human_outbreak_foci = 1;
    params.human_outbreak_cases = 40.0;
    params.human_min_cell_pop = 50.0;

    std::vector<float> human_pop = {500.0f};
    tm.init(1, 1, human_pop, params, 42);

    // At day 0..59: 0 infected
    tm.check_and_trigger_outbreak(0, {});
    EXPECT_DOUBLE_EQ(tm.human_grid().i_at(0, 0), 0.0);
    EXPECT_FALSE(tm.outbreak_triggered());

    tm.check_and_trigger_outbreak(30, {});
    EXPECT_DOUBLE_EQ(tm.human_grid().i_at(0, 0), 0.0);
    EXPECT_FALSE(tm.outbreak_triggered());

    // At day 60: Outbreak triggers!
    tm.check_and_trigger_outbreak(60, {1.0f});
    EXPECT_TRUE(tm.outbreak_triggered());
    EXPECT_DOUBLE_EQ(tm.human_grid().i_at(0, 0), 40.0);
    EXPECT_DOUBLE_EQ(tm.human_grid().s_at(0, 0), 460.0);
}

TEST(TransmissionModel, ExplicitFociSeeding) {
    TransmissionModel tm;
    TransmissionParams params;
    params.enabled = true;
    params.human_seeding_mode = "explicit";
    params.human_outbreak_day = 0;
    params.human_foci_coords = "0,1:25.0;1,0:15.0";

    std::vector<float> human_pop = {100.0f, 100.0f, 100.0f, 100.0f};
    tm.init(2, 2, human_pop, params, 11);

    EXPECT_DOUBLE_EQ(tm.human_grid().i_at(0, 0), 0.0);
    EXPECT_DOUBLE_EQ(tm.human_grid().i_at(0, 1), 25.0);
    EXPECT_DOUBLE_EQ(tm.human_grid().i_at(1, 0), 15.0);
    EXPECT_DOUBLE_EQ(tm.human_grid().i_at(1, 1), 0.0);
    EXPECT_TRUE(tm.human_grid().validate_invariants());
}

}  // namespace
}  // namespace mal_abm_fast
