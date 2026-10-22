// SPDX-License-Identifier: MIT
// birth_rate.hpp — Temperature-dependent egg production rate (EFD).
//
// Based on Mordecai et al. (2013) thermal response curves for Anopheles gambiae.
// The EFD function is a quadratic thermal response:
//   EFD(T) = afd * (T - T0) * (Tm - T) / ((Tm - T0)^2 / 4)
// where afd / T0 / Tm / Topt live in model_constants.yaml (thermal.efd_*).
//
// This temperature-dependent modifier is wired (2026-10-13) into the
// OVIPOSITING egg-batch draw in mosquito_submodel.cpp, replacing the
// legacy constant BIRTH_FECUNDITY (removed — dead code).
#pragma once

#include <cmath>
#include <algorithm>

#include "config.hpp"

namespace mal_abm_fast {

// Temperature-dependent egg production rate (eggs per female per day).
// Returns 0 outside [efd_tmin_c, efd_tmax_c]. Quadratic thermal response
// from Mordecai et al. (2013) "Thermal biology of mosquito-borne disease".
inline double egg_production_rate(double temp_c) {
    static const ThermalCfg& cfg = load_config().thermal;
    if (temp_c < cfg.efd_tmin_c || temp_c > cfg.efd_tmax_c) return 0.0;
    const double T = temp_c;
    const double T0 = cfg.efd_tmin_c;
    const double Tm = cfg.efd_tmax_c;
    const double numer = (T - T0) * (Tm - T);
    const double denom = (Tm - T0) * (Tm - T0) / 4.0;  // normalization
    if (denom <= 0.0) return 0.0;
    return cfg.efd_max_eggs_per_day * numer / denom;
}

// Normalized birth rate modifier (0-1 scale) for use in ABM:
// 1.0 at thermal.efd_topt_c, 0.0 at the thresholds.
inline double birth_rate_modifier(double temp_c) {
    const double efd = egg_production_rate(temp_c);
    const double efd_opt = egg_production_rate(load_config().thermal.efd_topt_c);
    if (efd_opt <= 0.0) return 0.0;
    return std::clamp(efd / efd_opt, 0.0, 1.0);
}

}  // namespace mal_abm_fast
