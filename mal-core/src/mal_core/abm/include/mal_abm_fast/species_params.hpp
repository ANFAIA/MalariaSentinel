// SPDX-License-Identifier: MIT
// species_params.hpp — Per-species behavioural parameters (M7.8).
//
// SpeciesParams separates identity (species.hpp enum) from quantitative
// parameters: host preference, phase activity, salinity response, etc.
// Defaults are versioned here; the registry function `species_params_for`
// is the single source for a species' parameters.
#pragma once

#include <array>
#include <cstdint>
#include <string>

#include "species.hpp"

namespace mal_abm_fast {

// Daily phase activity weights, in TimePhase order:
//   [DAY, EVENING, NIGHT, DAWN]
// Default for An. coluzzii / gambiae s.l. (Ghana + West Africa HLC):
//   Akuoko et al. 2024 (Parasit Vectors 17:16): LE 22-04h 66.6%, EM 04-06h 20.1%,
//   EE 18-22h 13.3% mapped onto the 4 phase windows.
inline constexpr int PHASE_WEIGHT_COUNT = 4;

struct SpeciesParams {
    MosquitoSpeciesId id = MosquitoSpeciesId::ANOPHELES_COLUZZII;
    std::string canonical_name = "Anopheles coluzzii";

    // Phase activity weights, TimePhase order [DAY, EVENING, NIGHT, DAWN], sum=1.
    std::array<float, PHASE_WEIGHT_COUNT> activity_weights =
        {0.02f, 0.10f, 0.80f, 0.08f};

    // Model attraction weights (pref_k), per host type. NOT the same as
    // observed HBI — see plan §5.3. Order matches HostType.
    float pref_human    = 0.99f;
    float pref_cattle   = 0.005f;
    float pref_goat     = 0.003f;
    float pref_sheep    = 0.001f;
    float pref_wildlife = 0.001f;

    // Host-seeking kernel scale/radius (metres).
    float host_seeking_scale_m  = 100.0f;
    float host_seeking_radius_m = 300.0f;

    // Salinity response (psu). salinity_suitability() below maps a psu
    // value to a habitat-fitness multiplier in [0,1].
    float salinity_opt_ppt   = 0.0f;   // freshwater peak
    float salinity_hi_tol_ppt = 30.0f; // high-tolerance psu (coluzzii > gambiae s.s.)
    float salinity_slope     = 0.08f;  // per-psu decay beyond opt

    // Gonotrophic cycle length (days) — M7.2 default for gambiae s.l.
    float gonotrophic_days = 2.0f;
};

/// Registry: returns the canonical parameter set for a species id.
/// MVP instantiates only ANOPHELES_COLUZZII.
SpeciesParams species_params_for(MosquitoSpeciesId id);

/// Salinity habitat-suitability multiplier in [0,1].
///   = 1.0 at and below opt; decays as (1 - frac) * exp(-slope * above)
///   past opt (frac = (psu - opt) / (hi_tol - opt)), reaching exactly 0
///   at hi_tol; psu >= hi_tol => 0.0 (hard cap — the species cannot
///   breed above its high tolerance). coluzzii (gentler slope + higher
///   hi_tol) tolerates > gambiae s.s. at equal psu.
float salinity_suitability(const SpeciesParams& sp, float salinity_ppt);

}  // namespace mal_abm_fast
