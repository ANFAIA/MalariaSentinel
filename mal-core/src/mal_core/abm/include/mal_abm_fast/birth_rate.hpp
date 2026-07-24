// SPDX-License-Identifier: MIT
// birth_rate.hpp — Temperature-dependent egg production rate (EFD).
//
// Based on Mordecai et al. (2013) thermal response curves for Anopheles gambiae.
// The EFD function is a quadratic thermal response:
//   EFD(T) = afd * (T - T0) * (T - Tm) / (T - Tm - 2*Topt)
// where:
//   afd = maximum egg production rate at optimal temperature
//   T0 = minimum temperature for reproduction (16°C)
//   Tm = maximum temperature for reproduction (34°C)
//   Topt = optimal temperature (25°C)
//
// This replaces the constant BIRTH_FECUNDITY with a temperature-dependent
// value that varies across the AOI grid cells.
#pragma once

#include <cmath>
#include <algorithm>

namespace mal_abm_fast {

// Mordecai 2013 thermal parameters for An. gambiae egg production
inline constexpr double EFD_AFD    = 0.5;    // max eggs per female per day at Topt
inline constexpr double EFD_T0     = 16.0;   // min temp for reproduction (°C)
inline constexpr double EFD_TM     = 34.0;   // max temp for reproduction (°C)
inline constexpr double EFD_TOPT   = 25.0;   // optimal temp (°C)

// Temperature-dependent egg production rate (eggs per female per day).
// Returns 0 outside [T0, Tm] range. Quadratic thermal response from
// Mordecai et al. (2013) "Thermal biology of mosquito-borne disease".
// At 25°C: returns 0.5 (maximum). At 20°C: ~0.21. At 30°C: ~0.21.
inline double egg_production_rate(double temp_c) {
    if (temp_c < EFD_T0 || temp_c > EFD_TM) return 0.0;
    const double T = temp_c;
    const double T0 = EFD_T0;
    const double Tm = EFD_TM;
    const double Topt = EFD_TOPT;
    // Quadratic thermal response (Mordecai 2013 eq. 1)
    const double numer = (T - T0) * (Tm - T);
    const double denom = (Tm - T0) * (Tm - T0) / 4.0;  // normalization
    if (denom <= 0.0) return 0.0;
    return EFD_AFD * numer / denom;
}

// Normalized birth rate modifier (0-1 scale) for use in ABM.
// At optimal temp (25°C): returns 1.0
// At boundaries (16°C, 34°C): returns 0.0
inline double birth_rate_modifier(double temp_c) {
    const double efd = egg_production_rate(temp_c);
    const double efd_opt = egg_production_rate(EFD_TOPT);
    if (efd_opt <= 0.0) return 0.0;
    return std::clamp(efd / efd_opt, 0.0, 1.0);
}

}  // namespace mal_abm_fast
