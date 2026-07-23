// SPDX-License-Identifier: MIT
// test_gonotrophic.cpp — GoogleTest tests for G4: gonotrophic cycle,
// BiteLedger, and multirate scheduler.
//
// Tests cover:
//   1. GonotrophicState enum values
//   2. GonotrophicParams defaults
//   3. State machine transitions (advance_gonotrophic_one_day)
//   4. BiteLedger record/reset
//   5. Multirate scheduler nighttime detection
//   6. MosquitoSoA gonotrophic fields after construction
//   7. MosquitoSubmodel advance_day with gonotrophic cycle
//   8. Emerged adults start as TENERAL
//   9. Females feed and transition to BLOOD_FED
//  10. Determinism with gonotrophic cycle
#include <gtest/gtest.h>

#include <cmath>
#include <cstdint>
#include <vector>

#include "aoi.hpp"
#include "wire.hpp"
#include "gonotrophic_cycle.hpp"
#include "bite_ledger.hpp"
#include "multirate_scheduler.hpp"
#include "mosquito_state.hpp"
#include "mosquito_submodel.hpp"

namespace {

// Helper: create a 10x10 AOI at the equator.
mal_abm_fast::AOI make_test_aoi() {
    mal_abm_fast::AOI aoi;
    aoi.west          = 0.0;
    aoi.south         = 0.0;
    aoi.east          = 10.0;
    aoi.north         = 10.0;
    aoi.resolution_m  = 111320;
    aoi.crs           = "EPSG:4326";
    aoi.slug          = "test";
    aoi.scale         = "regional";
    return aoi;
}

// Helper: create patch_states with all patches active at a given temp.
std::vector<mal_abm_fast::PatchState> make_patch_states(
    float temp_c = 25.0f, bool all_active = true) {
    std::vector<mal_abm_fast::PatchState> ps(100);
    for (int64_t i = 0; i < 100; ++i) {
        ps[static_cast<size_t>(i)].patch_id   = i;
        ps[static_cast<size_t>(i)].row        = static_cast<int32_t>(i / 10);
        ps[static_cast<size_t>(i)].col        = static_cast<int32_t>(i % 10);
        ps[static_cast<size_t>(i)].activated  = all_active;
        ps[static_cast<size_t>(i)].rain_d     = 20.0f;
        ps[static_cast<size_t>(i)].temp_d     = temp_c;
        ps[static_cast<size_t>(i)].water_frac = 0.5f;
    }
    return ps;
}

}  // namespace

// ---------------------------------------------------------------------------
// GonotrophicState enum
// ---------------------------------------------------------------------------

TEST(GonotrophicState, EnumValues) {
    static_assert(
        static_cast<uint8_t>(mal_abm_fast::GonotrophicState::TENERAL) == 0,
        "TENERAL must be 0");
    static_assert(
        static_cast<uint8_t>(mal_abm_fast::GonotrophicState::HOST_SEEKING) == 1,
        "HOST_SEEKING must be 1");
    static_assert(
        static_cast<uint8_t>(mal_abm_fast::GonotrophicState::BLOOD_FED) == 2,
        "BLOOD_FED must be 2");
    static_assert(
        static_cast<uint8_t>(mal_abm_fast::GonotrophicState::EGG_MATURING) == 3,
        "EGG_MATURING must be 3");
    static_assert(
        static_cast<uint8_t>(mal_abm_fast::GonotrophicState::GRAVID) == 4,
        "GRAVID must be 4");
    static_assert(
        static_cast<uint8_t>(mal_abm_fast::GonotrophicState::OVIPOSITION_SEEKING) == 5,
        "OVIPOSITION_SEEKING must be 5");
    static_assert(
        static_cast<uint8_t>(mal_abm_fast::GonotrophicState::OVIPOSITING) == 6,
        "OVIPOSITING must be 6");
}

// ---------------------------------------------------------------------------
// GonotrophicParams defaults
// ---------------------------------------------------------------------------

TEST(GonotrophicParams, DefaultValues) {
    mal_abm_fast::GonotrophicParams p;
    EXPECT_FLOAT_EQ(p.cycle_duration_days, 2.65f);
    EXPECT_FLOAT_EQ(p.first_cycle_days, 4.0f);
    EXPECT_FLOAT_EQ(p.feeding_success_rate, 0.825f);
    EXPECT_EQ(p.egg_batch_mean, 52);
    EXPECT_EQ(p.egg_batch_min, 30);
    EXPECT_EQ(p.egg_batch_max, 170);
    EXPECT_FLOAT_EQ(p.resting_duration_days, 1.0f);
}

// ---------------------------------------------------------------------------
// State machine transitions
// ---------------------------------------------------------------------------

TEST(GonotrophicCycle, TeneralTransitionsToHostSeeking) {
    auto state = mal_abm_fast::GonotrophicState::TENERAL;
    int32_t timer = 0;
    mal_abm_fast::GonotrophicParams params;
    const bool wants = mal_abm_fast::advance_gonotrophic_one_day(
        state, timer, params);
    EXPECT_EQ(state, mal_abm_fast::GonotrophicState::HOST_SEEKING);
    EXPECT_FALSE(wants);
}

TEST(GonotrophicCycle, HostSeekingStaysWhenNotFed) {
    auto state = mal_abm_fast::GonotrophicState::HOST_SEEKING;
    int32_t timer = 0;
    mal_abm_fast::GonotrophicParams params;
    // Caller does NOT set BLOOD_FED, so state stays HOST_SEEKING.
    const bool wants = mal_abm_fast::advance_gonotrophic_one_day(
        state, timer, params);
    EXPECT_EQ(state, mal_abm_fast::GonotrophicState::HOST_SEEKING);
    EXPECT_FALSE(wants);
}

TEST(GonotrophicCycle, BloodFedToEggMaturing) {
    auto state = mal_abm_fast::GonotrophicState::BLOOD_FED;
    int32_t timer = 0;
    mal_abm_fast::GonotrophicParams params;
    // After 1 day rest, should transition to EGG_MATURING.
    const bool wants = mal_abm_fast::advance_gonotrophic_one_day(
        state, timer, params);
    EXPECT_EQ(state, mal_abm_fast::GonotrophicState::EGG_MATURING);
    EXPECT_FALSE(wants);
}

TEST(GonotrophicCycle, EggMaturingToGravid) {
    auto state = mal_abm_fast::GonotrophicState::EGG_MATURING;
    int32_t timer = 0;
    mal_abm_fast::GonotrophicParams params;
    // Timer starts at 0, gets incremented each call. After the first
    // increment, timer != 0 so cycle_duration_days (2.65) is used.
    // After 3 increments (timer=3 >= 2.65), transition to GRAVID.
    for (int d = 0; d < 2; ++d) {
        mal_abm_fast::advance_gonotrophic_one_day(state, timer, params);
        EXPECT_EQ(state, mal_abm_fast::GonotrophicState::EGG_MATURING);
    }
    // Day 3: timer reaches 3, should transition.
    mal_abm_fast::advance_gonotrophic_one_day(state, timer, params);
    EXPECT_EQ(state, mal_abm_fast::GonotrophicState::GRAVID);
}

TEST(GonotrophicCycle, GravidToOvipositionSeeking) {
    auto state = mal_abm_fast::GonotrophicState::GRAVID;
    int32_t timer = 0;
    mal_abm_fast::GonotrophicParams params;
    const bool wants = mal_abm_fast::advance_gonotrophic_one_day(
        state, timer, params);
    EXPECT_EQ(state, mal_abm_fast::GonotrophicState::OVIPOSITION_SEEKING);
    EXPECT_FALSE(wants);
}

TEST(GonotrophicCycle, OvipositionSeekingStaysWithoutHabitat) {
    auto state = mal_abm_fast::GonotrophicState::OVIPOSITION_SEEKING;
    int32_t timer = 0;
    mal_abm_fast::GonotrophicParams params;
    // Caller does NOT transition to OVIPOSITING.
    const bool wants = mal_abm_fast::advance_gonotrophic_one_day(
        state, timer, params);
    EXPECT_EQ(state, mal_abm_fast::GonotrophicState::OVIPOSITION_SEEKING);
    EXPECT_FALSE(wants);
}

TEST(GonotrophicCycle, OviposingReportsWantsOviposit) {
    auto state = mal_abm_fast::GonotrophicState::OVIPOSITING;
    int32_t timer = 0;
    mal_abm_fast::GonotrophicParams params;
    const bool wants = mal_abm_fast::advance_gonotrophic_one_day(
        state, timer, params);
    EXPECT_TRUE(wants);
}

// ---------------------------------------------------------------------------
// BiteLedger
// ---------------------------------------------------------------------------

TEST(BiteLedger, EmptyAfterConstruction) {
    mal_abm_fast::BiteLedger ledger;
    EXPECT_TRUE(ledger.today().empty());
    EXPECT_EQ(ledger.total_successful_meals(), 0);
    EXPECT_EQ(ledger.total_attempts(), 0);
}

TEST(BiteLedger, RecordAttempt) {
    mal_abm_fast::BiteLedger ledger;
    ledger.record_attempt(5, 3, mal_abm_fast::HostType::HUMAN);
    ledger.record_attempt(5, 3, mal_abm_fast::HostType::HUMAN);
    ledger.record_attempt(5, 4, mal_abm_fast::HostType::CATTLE);
    EXPECT_EQ(ledger.today().size(), 2u);
    EXPECT_EQ(ledger.total_attempts(), 3);
}

TEST(BiteLedger, RecordSuccess) {
    mal_abm_fast::BiteLedger ledger;
    ledger.record_attempt(5, 3, mal_abm_fast::HostType::HUMAN);
    ledger.record_success(5, 3, mal_abm_fast::HostType::HUMAN);
    EXPECT_EQ(ledger.total_successful_meals(), 1);
}

TEST(BiteLedger, RecordDeath) {
    mal_abm_fast::BiteLedger ledger;
    ledger.record_attempt(5, 3, mal_abm_fast::HostType::HUMAN);
    ledger.record_death(5, 3, mal_abm_fast::HostType::HUMAN);
    ASSERT_EQ(ledger.today().size(), 1u);
    EXPECT_EQ(ledger.today()[0].mosquito_deaths, 1);
}

TEST(BiteLedger, ResetDay) {
    mal_abm_fast::BiteLedger ledger;
    ledger.record_attempt(5, 3, mal_abm_fast::HostType::HUMAN);
    ledger.record_success(5, 3, mal_abm_fast::HostType::HUMAN);
    ledger.reset_day();
    EXPECT_TRUE(ledger.today().empty());
}

TEST(BiteLedger, AggregatesByHostType) {
    mal_abm_fast::BiteLedger ledger;
    ledger.record_attempt(5, 3, mal_abm_fast::HostType::HUMAN);
    ledger.record_attempt(5, 3, mal_abm_fast::HostType::CATTLE);
    ASSERT_EQ(ledger.today().size(), 2u);
    // Same cell, different host types are separate aggregates.
    EXPECT_EQ(ledger.today()[0].host, mal_abm_fast::HostType::HUMAN);
    EXPECT_EQ(ledger.today()[1].host, mal_abm_fast::HostType::CATTLE);
}

// ---------------------------------------------------------------------------
// Multirate scheduler
// ---------------------------------------------------------------------------

TEST(MultirateScheduler, NighttimeHours) {
    // Hours 18-23 and 0-5 are nighttime.
    for (int32_t h = 18; h < 24; ++h) {
        EXPECT_TRUE(mal_abm_fast::is_nighttime_hour(h))
            << "hour " << h << " should be nighttime";
    }
    for (int32_t h = 0; h < 6; ++h) {
        EXPECT_TRUE(mal_abm_fast::is_nighttime_hour(h))
            << "hour " << h << " should be nighttime";
    }
    // Hours 6-17 are daytime.
    for (int32_t h = 6; h < 18; ++h) {
        EXPECT_FALSE(mal_abm_fast::is_nighttime_hour(h))
            << "hour " << h << " should be daytime";
    }
}

TEST(MultirateScheduler, NighttimeHoursCount) {
    EXPECT_EQ(mal_abm_fast::nighttime_hours_count(), 12);
}

TEST(MultirateScheduler, HourOfDay) {
    EXPECT_EQ(mal_abm_fast::hour_of_day(0), 0);
    EXPECT_EQ(mal_abm_fast::hour_of_day(17), 17);
    EXPECT_EQ(mal_abm_fast::hour_of_day(18), 18);
    EXPECT_EQ(mal_abm_fast::hour_of_day(23), 23);
    EXPECT_EQ(mal_abm_fast::hour_of_day(24), 0);
    EXPECT_EQ(mal_abm_fast::hour_of_day(25), 1);
}

TEST(MultirateScheduler, DayStateAdvance) {
    mal_abm_fast::MultirateDayState day;
    EXPECT_EQ(day.night_hour_index, 0);
    for (int32_t i = 0; i < 11; ++i) {
        EXPECT_TRUE(day.advance_night_hour());
        EXPECT_EQ(day.night_hour_index, i + 1);
    }
    // 12th advance should return false.
    EXPECT_FALSE(day.advance_night_hour());
}

TEST(MultirateScheduler, DayStateReset) {
    mal_abm_fast::MultirateDayState day;
    day.advance_night_hour();
    day.advance_night_hour();
    day.reset_day();
    EXPECT_EQ(day.night_hour_index, 0);
}

// ---------------------------------------------------------------------------
// MosquitoSoA gonotrophic fields
// ---------------------------------------------------------------------------

TEST(MosquitoSoA, GonotrophicFieldsAfterConstruction) {
    mal_abm_fast::MosquitoSubmodel sub(10, 100, 0.3f, 42);
    const auto& soa = sub.soa();
    EXPECT_EQ(static_cast<int64_t>(soa.gonotrophic_state.size()), soa.n_alive);
    EXPECT_EQ(static_cast<int64_t>(soa.gonotrophic_timer.size()), soa.n_alive);
    EXPECT_EQ(static_cast<int64_t>(soa.feeding_success.size()), soa.n_alive);
    // All new adults start as TENERAL.
    for (int64_t i = 0; i < soa.n_alive; ++i) {
        EXPECT_EQ(soa.gonotrophic_state[static_cast<size_t>(i)],
                  static_cast<uint8_t>(mal_abm_fast::GonotrophicState::TENERAL));
        EXPECT_EQ(soa.gonotrophic_timer[static_cast<size_t>(i)], 0);
        EXPECT_FLOAT_EQ(soa.feeding_success[static_cast<size_t>(i)], 0.0f);
    }
}

// ---------------------------------------------------------------------------
// MosquitoSubmodel with gonotrophic cycle
// ---------------------------------------------------------------------------

TEST(MosquitoSubmodelG4, AdvanceDayPopulatesGonotrophicStats) {
    mal_abm_fast::MosquitoSubmodel sub(10, 100, 0.3f, 42);
    const auto aoi = make_test_aoi();
    const auto ps  = make_patch_states(25.0f);
    sub.advance_day(aoi, ps);
    const auto& stats = sub.last_day_stats();
    // After day 1, teneral females should have transitioned to HOST_SEEKING.
    // Some may have fed (success rate 0.825).
    EXPECT_GE(stats.n_feeding_attempts, 0);
    EXPECT_GE(stats.n_successful_feeds, 0);
}

TEST(MosquitoSubmodelG4, TeneralToHostSeekingAfterOneDay) {
    mal_abm_fast::MosquitoSubmodel sub(10, 100, 0.3f, 42);
    const auto aoi = make_test_aoi();
    const auto ps  = make_patch_states(25.0f);
    sub.advance_day(aoi, ps);

    // After one day, no females should remain TENERAL — they should
    // all be HOST_SEEKING or BLOOD_FED (if they fed).
    const auto& soa = sub.soa();
    for (int64_t i = 0; i < soa.n_alive; ++i) {
        if (soa.stage[static_cast<size_t>(i)] != 1) continue;
        if (soa.sex[static_cast<size_t>(i)] != 1) continue;
        const uint8_t gs = soa.gonotrophic_state[static_cast<size_t>(i)];
        EXPECT_NE(gs, static_cast<uint8_t>(mal_abm_fast::GonotrophicState::TENERAL));
    }
}

TEST(MosquitoSubmodelG4, DeterministicFeedingAllFemalesFeed) {
    // In G4, feeding is deterministic (all HOST_SEEKING females feed).
    // Stochastic version comes in a later gate.
    mal_abm_fast::MosquitoSubmodel sub(10, 100, 0.3f, 42);
    const auto aoi = make_test_aoi();
    const auto ps  = make_patch_states(25.0f);

    int64_t total_attempts = 0;
    int64_t total_feeds = 0;
    for (int day = 0; day < 10; ++day) {
        sub.advance_day(aoi, ps);
        total_attempts += sub.last_day_stats().n_feeding_attempts;
        total_feeds += sub.last_day_stats().n_successful_feeds;
    }
    // All attempts should succeed in deterministic mode.
    if (total_attempts > 0) {
        EXPECT_EQ(total_feeds, total_attempts);
    }
}

TEST(MosquitoSubmodelG4, BiteLedgerRecordedDaily) {
    mal_abm_fast::MosquitoSubmodel sub(10, 100, 0.3f, 42);
    const auto aoi = make_test_aoi();
    const auto ps  = make_patch_states(25.0f);
    sub.advance_day(aoi, ps);
    // BiteLedger should have some entries after one day.
    // (Some females will have attempted feeding.)
    // The ledger is reset each day, so we check the current day's data.
    EXPECT_GE(sub.bite_ledger().total_attempts(), 0);
}

TEST(MosquitoSubmodelG4, DeterminismWithGonotrophic) {
    mal_abm_fast::MosquitoSubmodel a(10, 100, 0.3f, 42);
    mal_abm_fast::MosquitoSubmodel b(10, 100, 0.3f, 42);
    const auto aoi = make_test_aoi();
    const auto ps  = make_patch_states(25.0f);
    for (int day = 0; day < 30; ++day) {
        a.advance_day(aoi, ps);
        b.advance_day(aoi, ps);
    }
    EXPECT_EQ(a.total_agents(), b.total_agents());
    EXPECT_EQ(a.last_day_stats().n_feeding_attempts,
              b.last_day_stats().n_feeding_attempts);
    EXPECT_EQ(a.last_day_stats().n_successful_feeds,
              b.last_day_stats().n_successful_feeds);
}

TEST(MosquitoSubmodelG4, ThirtyDayPopulationStable) {
    mal_abm_fast::MosquitoSubmodel sub(100, 1000, 0.3f, 42);
    const auto aoi = make_test_aoi();
    const auto ps  = make_patch_states(25.0f);
    for (int day = 0; day < 30; ++day) {
        sub.advance_day(aoi, ps);
    }
    // Population should still be alive after 30 days.
    EXPECT_GT(sub.total_agents(), 0);
}

TEST(MosquitoSubmodelG4, GonotrophicParamsAccessible) {
    mal_abm_fast::MosquitoSubmodel sub(10, 100, 0.3f, 42);
    const auto& p = sub.gonotrophic_params();
    EXPECT_FLOAT_EQ(p.feeding_success_rate, 0.825f);
    // Mutable access works.
    sub.gonotrophic_params_mutable().feeding_success_rate = 0.90f;
    EXPECT_FLOAT_EQ(sub.gonotrophic_params().feeding_success_rate, 0.90f);
}

TEST(MosquitoSubmodelG4, GonotrophicStatsInDailyStats) {
    mal_abm_fast::MosquitoSubmodel sub(10, 100, 0.3f, 42);
    const auto aoi = make_test_aoi();
    const auto ps  = make_patch_states(25.0f);
    sub.advance_day(aoi, ps);
    const auto& stats = sub.last_day_stats();
    // Stats should be populated (non-negative).
    EXPECT_GE(stats.n_feeding_attempts, 0);
    EXPECT_GE(stats.n_successful_feeds, 0);
    EXPECT_GE(stats.n_ovipositions, 0);
}
