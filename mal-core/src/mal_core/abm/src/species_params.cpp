// SPDX-License-Identifier: MIT
// species_params.cpp — SpeciesParams registry (M7.8).
// Implementation by ag-spp. MVP: ANOPHELES_COLUZZII active; all other
// species are seeded with literature-based dormancy defaults so the
// registry is total over the 6-id enum without activating them.
#include <cmath>

#include "mal_abm_fast/species_params.hpp"

namespace mal_abm_fast {

SpeciesParams species_params_for(MosquitoSpeciesId id) {
    SpeciesParams sp;
    sp.id = id;
    sp.canonical_name = species_name(id);
    switch (id) {
        // MVP: An. coluzzii is the only active population (plan §5.1).
        // Anthropophilic, phase activity from Ghana HLC (Akuoko et al.
        // 2024, Parasit Vectors 17:16), moderate brackish tolerance
        // (more than gambiae s.s., far less than melas).
        case MosquitoSpeciesId::ANOPHELES_COLUZZII:
            sp.activity_weights   = {0.02f, 0.10f, 0.80f, 0.08f};
            sp.pref_human         = 0.99f;
            sp.pref_cattle        = 0.005f;
            sp.pref_goat          = 0.003f;
            sp.pref_sheep         = 0.001f;
            sp.pref_wildlife      = 0.001f;
            sp.host_seeking_scale_m  = 100.0f;
            sp.host_seeking_radius_m = 300.0f;
            sp.salinity_opt_ppt   = 0.0f;
            sp.salinity_hi_tol_ppt = 30.0f;
            sp.salinity_slope     = 0.08f;
            sp.gonotrophic_days   = 2.0f;
            break;
        // An. gambiae s.s. — inland/forest, fresh-water pools, lower
        // brackish tolerance than coluzzii: lower hi_tol AND steeper slope.
        case MosquitoSpeciesId::ANOPHELES_GAMBIAE_SS:
            sp.activity_weights   = {0.02f, 0.10f, 0.80f, 0.08f};
            sp.pref_human         = 0.99f;
            sp.pref_cattle        = 0.005f;
            sp.pref_goat          = 0.003f;
            sp.pref_sheep         = 0.001f;
            sp.pref_wildlife      = 0.001f;
            sp.host_seeking_scale_m  = 100.0f;
            sp.host_seeking_radius_m = 300.0f;
            sp.salinity_opt_ppt   = 0.0f;
            sp.salinity_hi_tol_ppt = 20.0f;
            sp.salinity_slope     = 0.12f;
            sp.gonotrophic_days   = 2.0f;
            break;
        // An. funestus s.s. — permanent vegetation water, highly
        // anthropophagus in southern Ghana; essentially freshwater.
        case MosquitoSpeciesId::ANOPHELES_FUNESTUS_SS:
            sp.activity_weights   = {0.02f, 0.10f, 0.80f, 0.08f};
            sp.pref_human         = 0.99f;
            sp.pref_cattle        = 0.005f;
            sp.pref_goat          = 0.003f;
            sp.pref_sheep         = 0.001f;
            sp.pref_wildlife      = 0.001f;
            sp.host_seeking_scale_m  = 100.0f;
            sp.host_seeking_radius_m = 300.0f;
            sp.salinity_opt_ppt   = 0.0f;
            sp.salinity_hi_tol_ppt = 15.0f;
            sp.salinity_slope     = 0.15f;
            sp.gonotrophic_days   = 2.0f;
            break;
        // An. arabiensis — dry savanna, more zoophilic/exophilic,
        // largely freshwater breeding.
        case MosquitoSpeciesId::ANOPHELES_ARABIENSIS:
            sp.activity_weights   = {0.02f, 0.10f, 0.80f, 0.08f};
            sp.pref_human         = 0.50f;
            sp.pref_cattle        = 0.20f;
            sp.pref_goat          = 0.15f;
            sp.pref_sheep         = 0.10f;
            sp.pref_wildlife      = 0.05f;
            sp.host_seeking_scale_m  = 120.0f;
            sp.host_seeking_radius_m = 300.0f;
            sp.salinity_opt_ppt   = 0.0f;
            sp.salinity_hi_tol_ppt = 15.0f;
            sp.salinity_slope     = 0.15f;
            sp.gonotrophic_days   = 2.0f;
            break;
        // An. melas — mangrove/brackish coastal, marine-tolerant. Known
        // dormant (requires coastal data); hi_tol above seawater so the
        // future species could invert the freshwater-default profile.
        case MosquitoSpeciesId::ANOPHELES_MELAS:
            sp.activity_weights   = {0.02f, 0.10f, 0.80f, 0.08f};
            sp.pref_human         = 0.99f;
            sp.pref_cattle        = 0.005f;
            sp.pref_goat          = 0.003f;
            sp.pref_sheep         = 0.001f;
            sp.pref_wildlife      = 0.001f;
            sp.host_seeking_scale_m  = 100.0f;
            sp.host_seeking_radius_m = 300.0f;
            sp.salinity_opt_ppt   = 0.0f;
            sp.salinity_hi_tol_ppt = 38.0f;
            sp.salinity_slope     = 0.02f;
            sp.gonotrophic_days   = 2.0f;
            break;
        // An. stephensi — urban invader, uncharacterised locally (M8+).
        case MosquitoSpeciesId::ANOPHELES_STEPHENSI:
            sp.activity_weights   = {0.02f, 0.10f, 0.80f, 0.08f};
            sp.pref_human         = 0.70f;
            sp.pref_cattle        = 0.15f;
            sp.pref_goat          = 0.05f;
            sp.pref_sheep         = 0.05f;
            sp.pref_wildlife      = 0.05f;
            sp.host_seeking_scale_m  = 100.0f;
            sp.host_seeking_radius_m = 300.0f;
            sp.salinity_opt_ppt   = 0.0f;
            sp.salinity_hi_tol_ppt = 20.0f;
            sp.salinity_slope     = 0.15f;
            sp.gonotrophic_days   = 2.0f;
            break;
    }
    return sp;
}

// Salinity habitat-suitability multiplier in [0,1].
//
//   above = psu - opt
//   if above <= 0:            s = 1.0
//   else:                     s = (1 - frac) * exp(-slope * above)
//                             frac = above / (hi_tol - opt)
//   if psu >= hi_tol:         s = 0.0          (hard cap: cannot breed)
//
// Properties:
//   - s = 1.0 for psu <= opt (freshwater peak).
//   - Monotonic decreasing for psu > opt; maximum at opt.
//   - Smooth exponential decay in (opt, hi_tol): the (1 - frac) factor
//     tapers the tail so s reaches exactly 0 at psu == hi_tol. At mid
//     psu the slope still discriminates species (coluzzii with its
//     gentler slope out-tolerates gambiae s.s. with the steeper slope).
//   - Hard cap: psu >= hi_tol => s = 0.0. The species cannot breed in
//     brackish water above its high tolerance; coastal cells deactivate
//     for fresh-water-limited species.
// Deterministic and continuous on (opt, hi_tol); the hard cap makes
// hi_tol the breeding cut-off (previously an unused registry value).
float salinity_suitability(const SpeciesParams& sp, float salinity_ppt) {
    if (salinity_ppt >= sp.salinity_hi_tol_ppt) return 0.0f;
    const float above = salinity_ppt - sp.salinity_opt_ppt;
    if (above <= 0.0f) return 1.0f;
    const float range = sp.salinity_hi_tol_ppt - sp.salinity_opt_ppt;
    if (range <= 0.0f) return 0.0f;
    const float frac = above / range;
    const float s = (1.0f - frac) * std::exp(-sp.salinity_slope * above);
    if (s < 0.0f) return 0.0f;
    if (s > 1.0f) return 1.0f;
    return s;
}

}  // namespace mal_abm_fast