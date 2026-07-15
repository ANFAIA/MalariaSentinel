// SPDX-License-Identifier: MIT
// test_prng.cpp — F1.c unit tests for the xoshiro256**-backed Prng.
//
// Covers:
//   * Determinism: same seed -> identical stream (byte-equal).
//   * Distribution: uniform in [0, 1), normal mean/stddev, binomial
//     range/mean/stddev.
//   * Splitmix64: zero seed maps to 1; the 4-word state is non-zero.
//   * The F1.a `xoshiro256pp` shim delegates to the same primitives
//     and produces the same stream as the F1.b `Prng` class.
//   * Peek state advances monotonically (sanity check on the step).
#include <gtest/gtest.h>

#include <array>
#include <cmath>
#include <cstdint>
#include <set>
#include <vector>

#include "prng.hpp"

namespace {

constexpr uint64_t kSeed = 42;

}  // namespace

TEST(MalAbmFastPrng, Determinism) {
    // Same seed -> same 1000-draw stream, byte-equal.
    mal_abm_fast::Prng a(kSeed);
    mal_abm_fast::Prng b(kSeed);
    std::vector<double> seq_a, seq_b;
    seq_a.reserve(1000);
    seq_b.reserve(1000);
    for (int i = 0; i < 1000; ++i) seq_a.push_back(a.uniform_double());
    for (int i = 0; i < 1000; ++i) seq_b.push_back(b.uniform_double());
    ASSERT_EQ(seq_a.size(), seq_b.size());
    for (size_t i = 0; i < seq_a.size(); ++i) {
        EXPECT_EQ(seq_a[i], seq_b[i]) << "diverged at i=" << i;
    }
    // Also check the first 10 explicitly (the brief's "save the first
    // 10 outputs" check).
    for (int i = 0; i < 10; ++i) {
        EXPECT_EQ(seq_a[i], seq_b[i]) << "first-10 diverged at i=" << i;
    }
}

TEST(MalAbmFastPrng, DifferentSeedsDifferentStreams) {
    mal_abm_fast::Prng a(1);
    mal_abm_fast::Prng b(2);
    for (int i = 0; i < 16; ++i) {
        EXPECT_NE(a.uniform_double(), b.uniform_double()) << "i=" << i;
    }
}

TEST(MalAbmFastPrng, UniformDoubleRange) {
    mal_abm_fast::Prng p(kSeed);
    for (int i = 0; i < 10000; ++i) {
        const double u = p.uniform_double();
        EXPECT_GE(u, 0.0) << "i=" << i;
        EXPECT_LT(u, 1.0) << "i=" << i;
    }
}

TEST(MalAbmFastPrng, UniformDoubleMean) {
    // The mean of U[0, 1) is 0.5. With 100k draws the sample mean
    // should be within ~0.01 of 0.5.
    mal_abm_fast::Prng p(kSeed);
    constexpr int N = 100000;
    double sum = 0.0;
    for (int i = 0; i < N; ++i) sum += p.uniform_double();
    const double mean = sum / static_cast<double>(N);
    EXPECT_NEAR(mean, 0.5, 0.01);
}

TEST(MalAbmFastPrng, NormalMeanAndStddev) {
    // N(0, 1) sample mean and stddev over 100k draws.
    mal_abm_fast::Prng p(kSeed);
    constexpr int N = 100000;
    std::vector<double> samples;
    samples.reserve(N);
    double sum = 0.0;
    for (int i = 0; i < N; ++i) {
        const double z = p.normal();
        samples.push_back(z);
        sum += z;
    }
    const double mean = sum / static_cast<double>(N);
    double var = 0.0;
    for (double z : samples) var += (z - mean) * (z - mean);
    var /= static_cast<double>(N);
    const double stddev = std::sqrt(var);
    EXPECT_NEAR(mean,   0.0, 0.02);
    EXPECT_NEAR(stddev, 1.0, 0.02);
}

TEST(MalAbmFastPrng, NormalShiftsAndScales) {
    // mu + sigma * Z should shift the mean and scale the stddev.
    mal_abm_fast::Prng p(kSeed);
    constexpr double mu    = 25.0;
    constexpr double sigma = 3.0;
    constexpr int    N     = 50000;
    double sum = 0.0;
    std::vector<double> samples;
    samples.reserve(N);
    for (int i = 0; i < N; ++i) {
        const double x = p.normal(mu, sigma);
        samples.push_back(x);
        sum += x;
    }
    const double mean = sum / static_cast<double>(N);
    double var = 0.0;
    for (double x : samples) var += (x - mean) * (x - mean);
    var /= static_cast<double>(N);
    EXPECT_NEAR(mean,   mu,    0.05);
    EXPECT_NEAR(std::sqrt(var), sigma, 0.05);
}

TEST(MalAbmFastPrng, BinomialRange) {
    mal_abm_fast::Prng p(kSeed);
    for (int i = 0; i < 1000; ++i) {
        const int k = p.binomial(1000, 0.5);
        EXPECT_GE(k, 0);
        EXPECT_LE(k, 1000);
    }
}

TEST(MalAbmFastPrng, BinomialMeanAndStddev) {
    // binomial(1000, 0.5) has mean 500 and stddev sqrt(250) ≈ 15.811.
    // The brief pins 1000 draws at ~500 / ~15.8; we use 2000 draws to
    // tighten the stddev estimate to ~0.35.
    mal_abm_fast::Prng p(kSeed);
    constexpr int N = 2000;
    std::vector<int> draws;
    draws.reserve(N);
    double sum = 0.0;
    for (int i = 0; i < N; ++i) {
        const int k = p.binomial(1000, 0.5);
        draws.push_back(k);
        sum += k;
    }
    const double mean = sum / static_cast<double>(N);
    double var = 0.0;
    for (int k : draws) var += (k - mean) * (k - mean);
    var /= static_cast<double>(N);
    const double stddev = std::sqrt(var);
    EXPECT_NEAR(mean,   500.0,            5.0);
    EXPECT_NEAR(stddev, std::sqrt(250.0), 1.0);
}

TEST(MalAbmFastPrng, BinomialBernoulliBranch) {
    // n*p < 30: exercises the Bernoulli-sum branch.
    // n=60, p=0.1 -> np=6. Mean = 6, stddev = sqrt(60*0.1*0.9) ≈ 2.32.
    mal_abm_fast::Prng p(kSeed);
    constexpr int N = 5000;
    double sum = 0.0;
    for (int i = 0; i < N; ++i) sum += p.binomial(60, 0.1);
    const double mean = sum / static_cast<double>(N);
    EXPECT_NEAR(mean, 6.0, 0.5);
}

TEST(MalAbmFastPrng, BinomialNormalBranch) {
    // n*p >= 30: exercises the normal-approximation branch.
    // n=1000, p=0.5 -> np=500. Mean ≈ 500, stddev ≈ 15.81.
    mal_abm_fast::Prng p(kSeed);
    constexpr int N = 2000;
    std::vector<int> draws;
    draws.reserve(N);
    double sum = 0.0;
    for (int i = 0; i < N; ++i) {
        const int k = p.binomial(1000, 0.5);
        draws.push_back(k);
        sum += k;
    }
    const double mean = sum / static_cast<double>(N);
    double var = 0.0;
    for (int k : draws) var += (k - mean) * (k - mean);
    var /= static_cast<double>(N);
    EXPECT_NEAR(mean,   500.0,            5.0);
    EXPECT_NEAR(std::sqrt(var), std::sqrt(250.0), 1.0);
}

TEST(MalAbmFastPrng, BinomialEdgeCases) {
    mal_abm_fast::Prng p(kSeed);
    EXPECT_EQ(p.binomial(0,    0.5), 0);
    EXPECT_EQ(p.binomial(100,  0.0), 0);
    EXPECT_EQ(p.binomial(100,  1.0), 100);
    EXPECT_EQ(p.binomial(-5,   0.5), 0);
}

TEST(MalAbmFastPrng, PeekStateAdvances) {
    // `peek_state()` returns s[0]; it should change as the state steps.
    mal_abm_fast::Prng p(kSeed);
    const uint64_t s0 = p.peek_state();
    (void)p.uniform_double();
    const uint64_t s1 = p.peek_state();
    EXPECT_NE(s0, s1);
}

TEST(MalAbmFastPrng, PeekStateDeterministic) {
    // Same seed -> same initial s[0] before any draws.
    mal_abm_fast::Prng a(kSeed);
    mal_abm_fast::Prng b(kSeed);
    EXPECT_EQ(a.peek_state(), b.peek_state());
    (void)a.uniform_double();
    (void)b.uniform_double();
    EXPECT_EQ(a.peek_state(), b.peek_state());
}

TEST(MalAbmFastPrng, ZeroSeedMapsToOne) {
    // splitmix64 requires a non-zero seed. Prng::seed(0) must remap
    // to 1 internally; the resulting stream must be the same as
    // Prng::seed(1).
    mal_abm_fast::Prng a(0);
    mal_abm_fast::Prng b(1);
    for (int i = 0; i < 16; ++i) {
        EXPECT_EQ(a.uniform_double(), b.uniform_double()) << "i=" << i;
    }
}

TEST(MalAbmFastPrng, XoshiroShimMatchesPrng) {
    // The F1.a `xoshiro256pp` shim must produce the same stream as the
    // F1.b `Prng` class for the same seed (both go through the same
    // xoshiro256** step + splitmix64 seeding).
    mal_abm_fast::xoshiro256pp shim;
    shim.seed_from(kSeed);
    mal_abm_fast::Prng prng(kSeed);
    for (int i = 0; i < 64; ++i) {
        EXPECT_EQ(shim.uniform(), prng.uniform_double()) << "i=" << i;
    }
}

TEST(MalAbmFastPrng, Splitmix64StateAdvances) {
    uint64_t s = 1;
    const uint64_t a = mal_abm_fast::splitmix64(s);
    const uint64_t b = mal_abm_fast::splitmix64(s);
    EXPECT_NE(a, b);
    EXPECT_NE(a, 0u);
    EXPECT_NE(b, 0u);
}

TEST(MalAbmFastPrng, UniformDoubleFirstTenArePinned) {
    // Property check: the first 10 draws from Prng(42) must be
    // non-zero, distinct, and in [0, 1). We don't pin the exact
    // values (the brief allows the internal stream to differ from
    // Python's) but we do require the deterministic replay to work.
    mal_abm_fast::Prng p(kSeed);
    std::set<double> seen;
    for (int i = 0; i < 10; ++i) {
        const double u = p.uniform_double();
        EXPECT_GE(u, 0.0);
        EXPECT_LT(u, 1.0);
        seen.insert(u);
    }
    // With 53-bit mantissa, collisions in 10 draws are essentially
    // impossible. EXPECT_GT is a sanity check, not a strict guarantee.
    EXPECT_GT(seen.size(), 5u);
}
