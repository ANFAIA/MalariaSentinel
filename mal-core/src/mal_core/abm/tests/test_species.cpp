// SPDX-License-Identifier: MIT
// test_species.cpp — Species identity + SpeciesParams registry + salinity
// response tests (M7.8). Implemented by ag-spp.
#include <gtest/gtest.h>

#include "mal_abm_fast/species.hpp"
#include "mal_abm_fast/species_params.hpp"

namespace mal_abm_fast {
namespace {

TEST(Species, DefaultRegistryReturnsColuzzii) {
    const auto sp = species_params_for(MosquitoSpeciesId::ANOPHELES_COLUZZII);
    EXPECT_EQ(sp.id, MosquitoSpeciesId::ANOPHELES_COLUZZII);
    EXPECT_EQ(sp.canonical_name, "Anopheles coluzzii");
}

TEST(Species, RegistryMapsEveryIdToCanonicalName) {
    for (int i = 0; i < MOSQUITO_SPECIES_COUNT; ++i) {
        const auto id = static_cast<MosquitoSpeciesId>(i);
        const auto sp = species_params_for(id);
        EXPECT_EQ(sp.id, id);
        EXPECT_EQ(sp.canonical_name, std::string(species_name(id)));
    }
}

TEST(Species, ActivityWeightsSumToOneForAllSpecies) {
    for (int i = 0; i < MOSQUITO_SPECIES_COUNT; ++i) {
        const auto sp =
            species_params_for(static_cast<MosquitoSpeciesId>(i));
        float sum = 0.0f;
        for (const float w : sp.activity_weights) sum += w;
        EXPECT_NEAR(sum, 1.0f, 1e-4f)
            << "activity weights must sum to 1.0 for " << sp.canonical_name;
    }
}

TEST(Species, ColuzziiDefaultsAreAnthropophilic) {
    const auto sp = species_params_for(MosquitoSpeciesId::ANOPHELES_COLUZZII);
    EXPECT_GT(sp.pref_human, 0.9f);
    EXPECT_EQ(sp.host_seeking_scale_m, 100.0f);
    EXPECT_EQ(sp.host_seeking_radius_m, 300.0f);
    EXPECT_EQ(sp.gonotrophic_days, 2.0f);
}

TEST(Salinity, MaxAtFreshwaterOptimum) {
    const auto sp = species_params_for(MosquitoSpeciesId::ANOPHELES_COLUZZII);
    // Opt is 0 psu; suitability at 0 and below is exactly 1.0.
    EXPECT_FLOAT_EQ(salinity_suitability(sp, 0.0f), 1.0f);
    EXPECT_FLOAT_EQ(salinity_suitability(sp, -2.0f), 1.0f);
    EXPECT_GE(salinity_suitability(sp, 0.0f),
              salinity_suitability(sp, 5.0f));
}

TEST(Salinity, MonotonicDecreasingAboveOptimum) {
    const auto sp = species_params_for(MosquitoSpeciesId::ANOPHELES_COLUZZII);
    float prev = salinity_suitability(sp, 0.0f);
    for (float psu = 1.0f; psu <= 45.0f; psu += 1.0f) {
        const float s = salinity_suitability(sp, psu);
        EXPECT_LE(s, prev + 1e-6f) << "must not increase at psu=" << psu;
        prev = s;
    }
}

TEST(Salinity, HardCapAtHiTolZeroesBreeding) {
    const auto col =
        species_params_for(MosquitoSpeciesId::ANOPHELES_COLUZZII);
    const auto gam =
        species_params_for(MosquitoSpeciesId::ANOPHELES_GAMBIAE_SS);
    // psu >= hi_tol => s == 0 exactly (hard cap, no breeding).
    EXPECT_FLOAT_EQ(salinity_suitability(col, col.salinity_hi_tol_ppt), 0.0f);
    EXPECT_FLOAT_EQ(salinity_suitability(col, col.salinity_hi_tol_ppt + 5.0f), 0.0f);
    EXPECT_FLOAT_EQ(salinity_suitability(gam, gam.salinity_hi_tol_ppt), 0.0f);
    EXPECT_FLOAT_EQ(salinity_suitability(gam, 35.0f), 0.0f);
    // Just below hi_tol the survival is small-but-positive.
    EXPECT_GT(salinity_suitability(col, col.salinity_hi_tol_ppt - 0.5f), 0.0f);
}

TEST(Salinity, ColuzziiToleratesMoreThanGambiaeSS) {
    const auto col =
        species_params_for(MosquitoSpeciesId::ANOPHELES_COLUZZII);
    const auto gam =
        species_params_for(MosquitoSpeciesId::ANOPHELES_GAMBIAE_SS);
    // Mid psu (below gambiae s.s. hi_tol): both strictly positive, and
    // coluzzii strictly higher than gambiae s.s. at equal psu > opt.
    for (float psu = 5.0f; psu <= 15.0f; psu += 5.0f) {
        const float s_col = salinity_suitability(col, psu);
        const float s_gam = salinity_suitability(gam, psu);
        EXPECT_GT(s_col, s_gam)
            << "coluzzii must out-tolerate gambiae s.s. at psu=" << psu;
        EXPECT_GT(s_col, 0.0f) << "coluzzii survival must be >0 at psu=" << psu;
        EXPECT_GT(s_gam, 0.0f) << "gambiae s.s. survival must be >0 at psu=" << psu;
    }
    // Between gambiae s.s. hi_tol and coluzzii hi_tol, coluzzii still
    // breeds (small positive) while gambiae s.s. is hard-zero.
    EXPECT_GT(salinity_suitability(col, 25.0f), 0.0f);
    EXPECT_FLOAT_EQ(salinity_suitability(gam, 25.0f), 0.0f);
    // Seawater (35 psu) exceeds both hi_tols: both hard-zero.
    EXPECT_FLOAT_EQ(salinity_suitability(col, 35.0f), 0.0f);
    EXPECT_FLOAT_EQ(salinity_suitability(gam, 35.0f), 0.0f);
}

TEST(Salinity, GamiaeSSNegligibleAtSeawater) {
    const auto gam =
        species_params_for(MosquitoSpeciesId::ANOPHELES_GAMBIAE_SS);
    // Freshwater species: hard-zero at 35 psu (hi_tol = 20).
    EXPECT_FLOAT_EQ(salinity_suitability(gam, 35.0f), 0.0f);
}

TEST(Salinity, MelasToleratesSeawater) {
    const auto mel =
        species_params_for(MosquitoSpeciesId::ANOPHELES_MELAS);
    // melas hi_tol (38) > seawater (35): still breeds, small but positive.
    EXPECT_GT(mel.salinity_hi_tol_ppt, 35.0f);
    EXPECT_GT(salinity_suitability(mel, 35.0f), 0.0f);
    EXPECT_FLOAT_EQ(salinity_suitability(mel, 38.0f), 0.0f);
    EXPECT_FLOAT_EQ(salinity_suitability(mel, 40.0f), 0.0f);
}

TEST(SpeciesParams, PodCopiesRoundTrip) {
    auto sp = species_params_for(MosquitoSpeciesId::ANOPHELES_COLUZZII);
    sp.activity_weights = {0.1f, 0.2f, 0.5f, 0.2f};
    sp.pref_human = 0.5f;
    sp.salinity_hi_tol_ppt = 12.5f;
    sp.gonotrophic_days = 3.0f;

    // Struct is trivially copyable (POD-like): a byte copy round-trips.
    SpeciesParams copy = sp;
    EXPECT_EQ(copy.id, sp.id);
    EXPECT_EQ(copy.canonical_name, sp.canonical_name);
    EXPECT_EQ(copy.activity_weights, sp.activity_weights);
    EXPECT_EQ(copy.pref_human, sp.pref_human);
    EXPECT_EQ(copy.salinity_hi_tol_ppt, sp.salinity_hi_tol_ppt);
    EXPECT_EQ(copy.gonotrophic_days, sp.gonotrophic_days);
}

}  // namespace
}  // namespace mal_abm_fast