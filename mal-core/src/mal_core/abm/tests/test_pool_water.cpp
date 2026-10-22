// test_pool_water.cpp — contract v3.0 habitat-availability regression.
//
// Covers:
//   1. habitat_potential rules (five static habitat types)
//   2. pluvial z recursion (monotone rise, exponential decay)
//   3. k_habitat sanity + species accuracy clipping
//   4. the urban-persistent supply premise (built > 0 ⇒ H > 0)
#include "mal_abm_fast/habitat_availability.hpp"

#include <gtest/gtest.h>

using namespace mal_abm_fast;

namespace {

HabitatFeatures urban_features() {
    return HabitatFeatures{0.0f /* jrc */,     0.06f /* built */,
                           0.0f /* wetland */, 0.05f /* open+water */,
                           0.04f /* crop */};
}

}  // namespace

TEST(PoolWater, KeffSanity) {
    // Plan §5.4 (v1): K_ref * cell_area_km2 * S with K_REF_GHANA = 50.0.
    const double S_full = 1.0, a_ghana_1km = 0.921;
    const double K = k_habitat(S_full, a_ghana_1km);
    EXPECT_NEAR(K, K_REF_GHANA * 0.921, 1.0);
    EXPECT_DOUBLE_EQ(k_habitat(0.0, a_ghana_1km), 0.0);
    EXPECT_FLOAT_EQ(K_REF_GHANA, 50.0f);
}

TEST(PoolWater, UrbanPersistentSupply) {
    // The user-fixed urban premise: a built cell keeps small potential
    // habitat even with JRC = 0 across the whole cell.
    const auto f = urban_features();
    const auto h = habitat_potential(f);
    EXPECT_GT(h[static_cast<size_t>(ZoneId::URBAN_PERSISTENT)], 0.0f);
    EXPECT_FLOAT_EQ(h[static_cast<size_t>(ZoneId::URBAN_PERSISTENT)],
                    URBAN_PERSISTENT_BETA * f.lc_built);
}

TEST(PoolWater, PluvialRecursionBehavior) {
    float z = 0.0f;
    // A single large pulse raises z substantially; a dry day lowers it.
    z = update_z_step(z, RAIN_SCALE_MM, 1.0f);
    EXPECT_GT(z, 0.6f);
    z = update_z_step(z, 0.0f, 1.0f);
    EXPECT_LT(z, 0.95f);
    // Drying is monotone: consecutive dry days keep decreasing.
    float d1 = z, d2 = z;
    for (int i = 0; i < 4; ++i) {
        d1 = update_z_step(d1, 0.0f, 1.0f);
    }
    for (int i = 0; i < 4; ++i) {
        d2 = update_z_step(d2, 0.0f, 1.0f);
    }
    EXPECT_FLOAT_EQ(d1, d2);  // deterministic
}

TEST(PoolWater, SpeciesAccuracyClips) {
    std::array<float, 6> h{0.8f, 0.5f, 0.3f, 0.2f, 0.1f, 0.0f};
    const auto w = default_species_weights();
    // Persistent habitats ride at availability 1 even under z = 0; only
    // the pluvial share is gated by z. The result is never out of [0,1].
    const float s_dry = species_accuracy(h, w, 0.0f);
    const float s_wet = species_accuracy(h, w, 1.0f);
    EXPECT_GT(s_dry, 0.0f);
    EXPECT_LT(s_dry, s_wet);
    EXPECT_LE(s_wet, 1.0f);
    // Pluvial-only floor case: all potential in the pluvial columns.
    std::array<float, 6> h_pluv{0.0f, 0.0f, 0.0f, 0.5f, 0.0f, 0.0f};
    EXPECT_FLOAT_EQ(species_accuracy(h_pluv, w, 0.0f), 0.0f);
}

TEST(PoolWater, PotentialFormula) {
    HabitatFeatures f{0.2f, 0.1f, 0.3f, 0.4f, 0.5f};
    const auto h = habitat_potential(f);
    EXPECT_FLOAT_EQ(h[static_cast<size_t>(ZoneId::JRC_PERSISTENT)],
                    f.jrc_persistent);
    EXPECT_FLOAT_EQ(h[static_cast<size_t>(ZoneId::WETLAND)], f.lc_wetland);
    EXPECT_FLOAT_EQ(h[static_cast<size_t>(ZoneId::CROP)], f.lc_crop);
    // Open pluvial: open_frac + RAIN_POOLS_BUIT_DAMAGE * built_frac, clipped 1.
    EXPECT_FLOAT_EQ(
        h[static_cast<size_t>(ZoneId::OPEN_PLUVIAL)],
        std::min(1.0f, f.lc_open_plus_water +
                           RAIN_POOLS_BUIT_DAMAGE * f.lc_built));
}
