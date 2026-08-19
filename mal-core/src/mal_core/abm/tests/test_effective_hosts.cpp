// SPDX-License-Identifier: MIT
// test_effective_hosts.cpp — EffectiveHostLandscape tests (M7.8).
// Implemented by ag-mov: identity, conservation, reproducibility, beta.
#include <gtest/gtest.h>

#include <array>
#include <utility>
#include <vector>

#include "mal_abm_fast/effective_host_landscape.hpp"

namespace mal_abm_fast {
namespace {

// Build a row-stochastic SparseOD from a list of rows, each row being a list
// of (dest, prob) pairs. n_cols is derived from the max dest index. Mirrors
// the raw-CSR pattern in test_mobility.cpp.
SparseOD make_od(const std::vector<std::vector<std::pair<int32_t, float>>>& rows) {
    const int32_t n = static_cast<int32_t>(rows.size());
    int32_t max_col = -1;
    std::vector<int32_t> rp;
    rp.reserve(static_cast<size_t>(n) + 1);
    rp.push_back(0);
    int32_t nnz = 0;
    std::vector<int32_t> ci;
    std::vector<float> vl;
    for (const auto& row : rows) {
        nnz += static_cast<int32_t>(row.size());
        rp.push_back(nnz);
        for (const auto& [c, p] : row) {
            ci.push_back(c);
            vl.push_back(p);
            if (c > max_col) max_col = c;
        }
    }
    const int32_t n_cols = max_col + 1;
    return SparseOD(std::move(rp), std::move(ci), std::move(vl), n, n_cols);
}

float grid_sum(const EffectiveGrid& g) {
    float s = 0.0f;
    for (float v : g) s += v;
    return s;
}

}  // namespace

TEST(EffectiveHosts, ConfigureSizes) {
    EffectiveHostLandscape el;
    el.configure({1.0f}, {2.0f}, 1);
    EXPECT_EQ(el.n_cells(), 1);
    EXPECT_FALSE(el.has_schedule());
}

TEST(EffectiveHosts, IdentityScheduleReturnsResidential) {
    MobilitySchedule ms;
    const int32_t n = 4;
    ms.set_human_od(SparseOD::identity(n), SparseOD::identity(n));
    EffectiveHostLandscape el;
    el.configure({10.0f, 20.0f, 30.0f, 40.0f}, std::vector<float>(n, 0.0f), n);
    el.set_schedule(&ms);

    const EffectiveGrid res = {10.0f, 20.0f, 30.0f, 40.0f};
    Prng rng(42);
    const EffectiveGrid sampled =
        el.sample_effective_hosts(0, TimePhase::DAY, /*is_livestock=*/false, rng);
    for (size_t j = 0; j < n; ++j) {
        EXPECT_FLOAT_EQ(sampled[j], res[j]) << "cell " << j;
    }
}

TEST(EffectiveHosts, NoScheduleFallsBackToResidential) {
    EffectiveHostLandscape el;
    el.configure({7.0f, 3.0f}, {0.0f, 0.0f}, 2);
    Prng rng(7);
    const EffectiveGrid sampled =
        el.sample_effective_hosts(1, TimePhase::NIGHT, /*is_livestock=*/false, rng);
    EXPECT_FLOAT_EQ(sampled[0], 7.0f);
    EXPECT_FLOAT_EQ(sampled[1], 3.0f);
}

TEST(EffectiveHosts, ConservationGlobalAndPerOrigin) {
    MobilitySchedule ms;
    // Row 0 -> {0:0.6, 1:0.4}, row 1 -> {1:0.8, 2:0.2}, row 2 -> {2:1.0}
    const std::vector<std::vector<std::pair<int32_t, float>>> rows = {
        {{0, 0.6f}, {1, 0.4f}},
        {{1, 0.8f}, {2, 0.2f}},
        {{2, 1.0f}},
    };
    ms.set_human_od(make_od(rows), SparseOD::identity(3));

    EffectiveHostLandscape el;
    el.configure({100.0f, 200.0f, 50.0f}, {0.0f, 0.0f, 0.0f}, 3);
    el.set_schedule(&ms);

    Prng rng(1);
    const EffectiveGrid sampled =
        el.sample_effective_hosts(3, TimePhase::EVENING, /*is_livestock=*/false, rng);

    // Global mass conserved: Σ H_eff == Σ residential = 350.
    EXPECT_NEAR(grid_sum(sampled), 350.0f, 1e-3f);
    // Expected (deterministic) global mass also conserved.
    const EffectiveGrid expected = el.expected_effective_hosts(TimePhase::EVENING, false);
    EXPECT_NEAR(grid_sum(expected), 350.0f, 1e-2f);

    // Per-origin conservation: with identity night, each origin stays intact.
    Prng rng2(2);
    const EffectiveGrid night =
        el.sample_effective_hosts(3, TimePhase::NIGHT, /*is_livestock=*/false, rng2);
    EXPECT_NEAR(night[0], 100.0f, 1e-3f);
    EXPECT_NEAR(night[1], 200.0f, 1e-3f);
    EXPECT_NEAR(night[2], 50.0f, 1e-3f);
}

TEST(EffectiveHosts, ConservationLivestock) {
    MobilitySchedule ms;
    ms.set_livestock_od(SparseOD::identity(3));
    EffectiveHostLandscape el;
    el.configure({0.0f, 0.0f, 0.0f}, {5.0f, 6.0f, 7.0f}, 3);
    el.set_schedule(&ms);
    Prng rng(9);
    const EffectiveGrid sampled =
        el.sample_effective_hosts(0, TimePhase::DAY, /*is_livestock=*/true, rng);
    EXPECT_NEAR(grid_sum(sampled), 18.0f, 1e-3f);
    EXPECT_NEAR(sampled[0], 5.0f, 1e-3f);
    EXPECT_NEAR(sampled[1], 6.0f, 1e-3f);
    EXPECT_NEAR(sampled[2], 7.0f, 1e-3f);
}

TEST(EffectiveHosts, ReproducibleSameSeed) {
    MobilitySchedule ms;
    const std::vector<std::vector<std::pair<int32_t, float>>> rows = {
        {{0, 0.4f}, {1, 0.6f}},
        {{0, 0.3f}, {1, 0.7f}},
    };
    ms.set_human_od(make_od(rows), SparseOD::identity(2));
    EffectiveHostLandscape el;
    el.configure({100.0f, 100.0f}, {0.0f, 0.0f}, 2);
    el.set_schedule(&ms);

    Prng rng_a(123);
    Prng rng_b(123);  // separate object, same seed
    const EffectiveGrid a = el.sample_effective_hosts(5, TimePhase::DAY, false, rng_a);
    const EffectiveGrid b = el.sample_effective_hosts(5, TimePhase::DAY, false, rng_b);
    EXPECT_EQ(a, b);  // byte-equal

    Prng rng_c(124);
    const EffectiveGrid c = el.sample_effective_hosts(5, TimePhase::DAY, false, rng_c);
    bool any_diff = false;
    for (size_t j = 0; j < a.size(); ++j) {
        if (a[j] != c[j]) { any_diff = true; break; }
    }
    EXPECT_TRUE(any_diff);  // different seed -> different realization
}

TEST(EffectiveHosts, PhaseContrastDayVsNight) {
    MobilitySchedule ms;
    // Day redistributes from cell 0 to cell 1, night identity.
    const std::vector<std::vector<std::pair<int32_t, float>>> rows = {
        {{0, 0.5f}, {1, 0.5f}},
        {{1, 1.0f}},
    };
    ms.set_human_od(make_od(rows), SparseOD::identity(2));
    EffectiveHostLandscape el;
    el.configure({100.0f, 0.0f}, {0.0f, 0.0f}, 2);
    el.set_schedule(&ms);

    Prng rng_day(50);
    const EffectiveGrid day =
        el.sample_effective_hosts(1, TimePhase::DAY, false, rng_day);
    Prng rng_night(50);
    const EffectiveGrid night =
        el.sample_effective_hosts(1, TimePhase::NIGHT, false, rng_night);

    // Night keeps everyone home; day spreads a substantial part to cell 1.
    EXPECT_NEAR(night[1], 0.0f, 1e-3f);
    EXPECT_GT(day[1], 20.0f);
    EXPECT_NE(day[1], night[1]);
}

TEST(EffectiveHosts, BetaSensitivitySteeperMatrixRedistributesLess) {
    // Same residential mass in cell 0; a steeper (higher-friction) day matrix
    // keeps more mass at the origin, so less lands in cell 1.
    std::vector<float> res = {100.0f, 0.0f};

    MobilitySchedule mild;
    // Mild friction: 40% leaves.
    const std::vector<std::vector<std::pair<int32_t, float>>> mild_rows = {
        {{0, 0.6f}, {1, 0.4f}},
        {{1, 1.0f}},
    };
    mild.set_human_od(make_od(mild_rows), SparseOD::identity(2));

    MobilitySchedule steep;
    // Steep friction: only 10% leaves.
    const std::vector<std::vector<std::pair<int32_t, float>>> steep_rows = {
        {{0, 0.9f}, {1, 0.1f}},
        {{1, 1.0f}},
    };
    steep.set_human_od(make_od(steep_rows), SparseOD::identity(2));

    EffectiveHostLandscape el_mild;
    el_mild.configure(res, {0.0f, 0.0f}, 2);
    el_mild.set_schedule(&mild);
    EffectiveHostLandscape el_steep;
    el_steep.configure(res, {0.0f, 0.0f}, 2);
    el_steep.set_schedule(&steep);

    // Deterministic expectation: monotone — steeper matrix sends less to cell 1.
    const EffectiveGrid mild_exp = el_mild.expected_effective_hosts(TimePhase::DAY, false);
    const EffectiveGrid steep_exp = el_steep.expected_effective_hosts(TimePhase::DAY, false);
    EXPECT_GT(mild_exp[1], steep_exp[1]);

    // Sampled (fixed seed): steeper still redistributes strictly less.
    Prng rng_m(11);
    Prng rng_s(11);
    const EffectiveGrid mild_s = el_mild.sample_effective_hosts(0, TimePhase::DAY, false, rng_m);
    const EffectiveGrid steep_s = el_steep.sample_effective_hosts(0, TimePhase::DAY, false, rng_s);
    EXPECT_GT(mild_s[1], steep_s[1]);
}

TEST(EffectiveHosts, StochasticRoundingExpectedMass) {
    // Fractional stock: repeated sampling should approach E[H_eff(ident)] = res.
    MobilitySchedule ms;
    ms.set_human_od(SparseOD::identity(2), SparseOD::identity(2));
    EffectiveHostLandscape el;
    el.configure({2.5f, 0.0f}, {0.0f, 0.0f}, 2);
    el.set_schedule(&ms);

    const int trials = 2000;
    double sum_h0 = 0.0;
    for (int t = 0; t < trials; ++t) {
        Prng rng(static_cast<uint64_t>(t));
        const EffectiveGrid g = el.sample_effective_hosts(0, TimePhase::DAY, false, rng);
        sum_h0 += g[0];
    }
    // E[H_eff[0]] ≈ res[0] = 2.5 across many independent realizations.
    const double mean = sum_h0 / trials;
    EXPECT_NEAR(mean, 2.5, 0.1);
}

TEST(EffectiveHosts, WeightedDailyExpectationSinglePhase) {
    MobilitySchedule ms;
    const std::vector<std::vector<std::pair<int32_t, float>>> rows = {
        {{0, 0.5f}, {1, 0.5f}},
        {{1, 1.0f}},
    };
    ms.set_human_od(make_od(rows), SparseOD::identity(2));
    EffectiveHostLandscape el;
    el.configure({100.0f, 0.0f}, {0.0f, 0.0f}, 2);
    el.set_schedule(&ms);

    // weight=1 on DAY -> reproduces the DAY expectation.
    std::array<float, PHASE_WEIGHT_COUNT> w = {1.0f, 0.0f, 0.0f, 0.0f};
    const EffectiveGrid daily = el.weighted_daily_expectation(w);
    const EffectiveGrid day = el.expected_effective_hosts(TimePhase::DAY, false);
    EXPECT_NEAR(daily[0], day[0], 1e-4f);
    EXPECT_NEAR(daily[1], day[1], 1e-4f);

    // Weights sum to 1 and global mass of the aggregate equals residential mass.
    std::array<float, PHASE_WEIGHT_COUNT> w2 = {0.25f, 0.25f, 0.25f, 0.25f};
    const EffectiveGrid daily2 = el.weighted_daily_expectation(w2);
    EXPECT_NEAR(grid_sum(daily2), 100.0f, 1e-2f);
}

}  // namespace mal_abm_fast
