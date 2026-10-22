// SPDX-License-Identifier: MIT
// species_params.cpp — SpeciesParams registry (M7.8).
//
// Plan-v2 paso 12: the WHOLE registry body is a lookup of the
// model_constants.yaml species.<name> rows (activity_weights [DAY,
// EVENING, NIGHT, DAWN], pref per HostType BY NAME, salinity opt/hi_tol/
// slope per species). NO in-code species phase remains; the struct
// defaults are NOT a source (see species_params.hpp).
// gonotrophic_days stays OUT of the YAML (verdict plan v2 §0-3: the
// SpeciesParams field has NO runtime consumer; the real cycle uses
// GonotrophicParams::cycle_duration_days).
#include <cmath>
#include <stdexcept>
#include <string>

#include "mal_abm_fast/config.hpp"
#include "mal_abm_fast/species_params.hpp"

namespace mal_abm_fast {
namespace {

std::string yaml_name(MosquitoSpeciesId id) {
    switch (id) {
        case MosquitoSpeciesId::ANOPHELES_COLUZZII:    return "coluzzii";
        case MosquitoSpeciesId::ANOPHELES_GAMBIAE_SS:  return "gambiae_ss";
        case MosquitoSpeciesId::ANOPHELES_FUNESTUS_SS: return "funestus";
        case MosquitoSpeciesId::ANOPHELES_ARABIENSIS:  return "arabiensis";
        case MosquitoSpeciesId::ANOPHELES_MELAS:       return "melas";
        case MosquitoSpeciesId::ANOPHELES_STEPHENSI:   return "stephensi";
    }
    throw std::invalid_argument("unknown MosquitoSpeciesId");
}

}  // namespace

SpeciesParams species_params_for(MosquitoSpeciesId id) {
    SpeciesParams sp;
    sp.id = id;
    sp.canonical_name = species_name(id);

    // Whole-body lookup from the YAML (validation/normalization is the
    // loader's job; a missing/unknown row already raised ConfigError).
    const auto& rows = load_config().species.rows;
    const std::string name = yaml_name(id);
    const auto it = rows.find(name);
    if (it == rows.end()) {
        throw std::invalid_argument(
            "species_params_for: no species row '" + name +
            "' in model_constants.yaml");
    }
    const SpeciesRow& row = it->second;
    for (size_t i = 0; i < 4; ++i) {
        sp.activity_weights[i] = static_cast<float>(row.activity_weights[i]);
    }
    sp.pref_human    = static_cast<float>(row.pref[0]);
    sp.pref_cattle   = static_cast<float>(row.pref[1]);
    sp.pref_goat     = static_cast<float>(row.pref[2]);
    sp.pref_sheep    = static_cast<float>(row.pref[3]);
    sp.pref_wildlife = static_cast<float>(row.pref[4]);
    sp.host_seeking_scale_m =
        static_cast<float>(row.host_seeking_scale_m);
    sp.host_seeking_radius_m =
        static_cast<float>(row.host_seeking_radius_m);
    sp.salinity_opt_ppt    = static_cast<float>(row.salinity_opt_ppt);
    sp.salinity_hi_tol_ppt = static_cast<float>(row.salinity_hi_tol_ppt);
    sp.salinity_slope      = static_cast<float>(row.salinity_slope);
    // gonotrophic_days: dead knob (no runtime consumer) — the struct
    // default 2.0f remains for tests only; NOT a YAML key.
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
