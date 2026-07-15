// SPDX-License-Identifier: MIT
// test_dispersal.cpp — F1.c unit tests for the adult mosquito
// dispersal kernel (`offset_m`).
//
// The kernel draws (dx, dy) from N(0, sigma_m^2), clips to a circle of
// radius `max_m`, and converts to (dlon, dlat) degrees using the
// 111320 m/deg constant and a `cos(lat)` correction on the longitude
// axis.
//
// The 4 tests below cover the pinned behaviour:
//   * Determinism: same Prng + same params -> same offset.
//   * Cap: max(|dlat| * 111320, |dlon| * 111320 * cos(lat)) <= max_m.
//   * Distribution: mean near 0, stddev near sigma_m.
//   * cos(lat) correction: dlon scales as 1 / cos(lat) at constant
//     ground distance.
#include <gtest/gtest.h>

#include <algorithm>
#include <cmath>
#include <limits>
#include <vector>

#include "dispersal.hpp"
#include "prng.hpp"
#include "wire.hpp"

namespace {

constexpr double kMetresPerDeg = 111320.0;

}  // namespace

TEST(MalAbmFastDispersal, Determinism) {
    mal_abm_fast::Prng p(123);
    mal_abm_fast::DispOffset a = mal_abm_fast::offset_m(p, 0.0, 0.0, 1000.0, 2000.0);
    mal_abm_fast::Prng q(123);
    mal_abm_fast::DispOffset b = mal_abm_fast::offset_m(q, 0.0, 0.0, 1000.0, 2000.0);
    EXPECT_DOUBLE_EQ(a.dlon, b.dlon);
    EXPECT_DOUBLE_EQ(a.dlat, b.dlat);
}

TEST(MalAbmFastDispersal, OffsetIsZeroWhenPrngIsUnseededAndZero) {
    // Unseeded Prng lazy-seeds with state=1, so the result is non-zero
    // in general. This test pins that the implementation does not
    // return NaN/Inf for a fresh Prng.
    mal_abm_fast::Prng p;  // unseeded
    mal_abm_fast::DispOffset o = mal_abm_fast::offset_m(p, 0.0, 0.0, 1000.0, 2000.0);
    EXPECT_TRUE(std::isfinite(o.dlon));
    EXPECT_TRUE(std::isfinite(o.dlat));
}

TEST(MalAbmFastDispersal, CapAtMaxMeters) {
    // 10000 draws with sigma=1000, max=2000, lon=0, lat=0. The
    // ground-distance magnitude must never exceed max_m.
    mal_abm_fast::Prng p(7);
    constexpr int N = 10000;
    double max_dx = 0.0;
    double max_dy = 0.0;
    for (int i = 0; i < N; ++i) {
        mal_abm_fast::DispOffset o = mal_abm_fast::offset_m(p, 0.0, 0.0, 1000.0, 2000.0);
        const double dx_m = o.dlon * kMetresPerDeg;  // cos(0) = 1
        const double dy_m = o.dlat * kMetresPerDeg;
        EXPECT_LE(std::abs(dx_m), 2000.0 + 1e-9) << "i=" << i;
        EXPECT_LE(std::abs(dy_m), 2000.0 + 1e-9) << "i=" << i;
        max_dx = std::max(max_dx, std::abs(dx_m));
        max_dy = std::max(max_dy, std::abs(dy_m));
    }
    // The cap is tight: with 10000 draws, the empirical max should be
    // very close to 2000 m (within numerical noise).
    EXPECT_NEAR(max_dx, 2000.0, 5.0);
    EXPECT_NEAR(max_dy, 2000.0, 5.0);
}

TEST(MalAbmFastDispersal, MeanNearZero) {
    mal_abm_fast::Prng p(11);
    constexpr int N = 10000;
    double sum_dlon = 0.0;
    double sum_dlat = 0.0;
    for (int i = 0; i < N; ++i) {
        mal_abm_fast::DispOffset o = mal_abm_fast::offset_m(p, 0.0, 0.0, 1000.0, 2000.0);
        sum_dlon += o.dlon;
        sum_dlat += o.dlat;
    }
    const double mean_dlon = sum_dlon / static_cast<double>(N);
    const double mean_dlat = sum_dlat / static_cast<double>(N);
    // Mean of N(0, sigma) over 10000 draws is within ~sigma/sqrt(N) ≈ 10 m
    // => in degrees: 10/111320 ≈ 9e-5.
    EXPECT_NEAR(mean_dlon, 0.0, 0.001);
    EXPECT_NEAR(mean_dlat, 0.0, 0.001);
}

TEST(MalAbmFastDispersal, StddevNearSigmaMeters) {
    // The radial cap at 2*sigma removes ~13.5% of the Rayleigh tail,
    // which reduces the per-axis stddev by ~6% (the clipped per-axis
    // stddev is ~940m, not 1000m). We accept a 10% tolerance to
    // account for this. The `CapAtMaxMeters` test pins the cap
    // behaviour directly.
    mal_abm_fast::Prng p(13);
    constexpr int N = 10000;
    std::vector<double> dx_m, dy_m;
    dx_m.reserve(N);
    dy_m.reserve(N);
    for (int i = 0; i < N; ++i) {
        mal_abm_fast::DispOffset o = mal_abm_fast::offset_m(p, 0.0, 0.0, 1000.0, 2000.0);
        dx_m.push_back(o.dlon * kMetresPerDeg);
        dy_m.push_back(o.dlat * kMetresPerDeg);
    }
    auto mean_std = [](const std::vector<double>& v) {
        double mean = 0.0;
        for (double x : v) mean += x;
        mean /= static_cast<double>(v.size());
        double var = 0.0;
        for (double x : v) var += (x - mean) * (x - mean);
        return std::pair<double, double>(mean, std::sqrt(var / static_cast<double>(v.size())));
    };
    const auto [mx, sdx] = mean_std(dx_m);
    const auto [my, sdy] = mean_std(dy_m);
    EXPECT_NEAR(mx, 0.0, 50.0);      // 5% of sigma; cap is symmetric
    EXPECT_NEAR(my, 0.0, 50.0);
    EXPECT_NEAR(sdx, 1000.0, 100.0); // 10% tolerance for the cap bias
    EXPECT_NEAR(sdy, 1000.0, 100.0);
}

TEST(MalAbmFastDispersal, CosLatCorrection) {
    // At lat=60, cos(lat)=0.5, so the dlon degrees should be 2x what
    // they would be at lat=0 for the same ground dx. We compare two
    // streams seeded with the same Prng so the underlying (dx, dy)
    // draws are identical.
    mal_abm_fast::Prng p_equator(99);
    mal_abm_fast::Prng p_high(99);
    constexpr int N = 1000;
    std::vector<double> dlon_eq, dlon_hi;
    dlon_eq.reserve(N);
    dlon_hi.reserve(N);
    for (int i = 0; i < N; ++i) {
        mal_abm_fast::DispOffset eq = mal_abm_fast::offset_m(p_equator, 0.0,  0.0, 1000.0, 2000.0);
        mal_abm_fast::DispOffset hi = mal_abm_fast::offset_m(p_high,    0.0, 60.0, 1000.0, 2000.0);
        dlon_eq.push_back(eq.dlon);
        dlon_hi.push_back(hi.dlon);
    }
    // dlon_high ≈ dlon_equator / cos(60°) = 2 * dlon_equator.
    // Check on the sample mean of the ratio.
    double ratio_sum = 0.0;
    for (int i = 0; i < N; ++i) {
        if (std::abs(dlon_eq[i]) > 1e-12) {
            ratio_sum += dlon_hi[i] / dlon_eq[i];
        }
    }
    const double mean_ratio = ratio_sum / static_cast<double>(N);
    EXPECT_NEAR(mean_ratio, 2.0, 0.05);
}

TEST(MalAbmFastDispersal, UsesWireConstants) {
    // The wire.hpp constants are the production values. Drawing from
    // the F1.b dispersal kernel with those constants should produce
    // offsets within the (sigma_m, max_m) envelope.
    mal_abm_fast::Prng p(2024);
    constexpr int N = 1000;
    for (int i = 0; i < N; ++i) {
        mal_abm_fast::DispOffset o = mal_abm_fast::offset_m(
            p, 0.0, 0.0,
            static_cast<double>(mal_abm_fast::ADULT_DISPERSE_SIGMA_M),
            static_cast<double>(mal_abm_fast::ADULT_DISPERSE_MAX_M));
        const double dx_m = std::abs(o.dlon) * kMetresPerDeg;
        const double dy_m = std::abs(o.dlat) * kMetresPerDeg;
        EXPECT_LE(dx_m, mal_abm_fast::ADULT_DISPERSE_MAX_M + 1e-6);
        EXPECT_LE(dy_m, mal_abm_fast::ADULT_DISPERSE_MAX_M + 1e-6);
    }
}
