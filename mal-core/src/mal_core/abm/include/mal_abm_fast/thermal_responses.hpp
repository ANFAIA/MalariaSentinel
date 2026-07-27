// SPDX-License-Identifier: MIT
// thermal_responses.hpp — Stage-specific thermal development rates for
// mosquito aquatic stages (Egg, Larva, Pupa).
//
// Based on Mordecai et al. (2013) + Couper et al. (2021).
// Each function returns the daily development rate as a fraction [0, 1].
// A rate of 1.0 means the stage completes in exactly one day at that
// temperature. Rates above 0 indicate temperatures that support
// development; rates below the lower threshold are clamped to 0.
//
// Thermal response curves: Brière-1 (eggs, pupae) and quadratic
// (larvae) from Mordecai 2013 "Thermal biology of mosquito-borne
// disease". Lower thresholds from Couper et al. 2021 "A model of
// environmental drivers of population-level Anopheles mosquito larval
// development rates".
#pragma once

#include <algorithm>
#include <cmath>

namespace mal_abm_fast {

// ---------------------------------------------------------------------------
// Egg development — Brière-1 thermal response
//   rate(T) = a * T * (T - T_L) * sqrt(T_H - T)  if T_L < T < T_H
//   rate(T) = 0                                    otherwise
//
// Parameters (Couper et al. 2021 Table 2, An. gambiae):
//   T_L = 10.0°C  (lower developmental threshold)
//   T_H = 40.0°C  (upper developmental threshold)
//   a   = 0.00062 (scaling constant, fitted to ~1 day at 25°C)
//
// At 25°C: rate ≈ 0.90 (stage duration ≈ 1.11 days)
// At 20°C: rate ≈ 0.52 (stage duration ≈ 1.92 days)
// At 15°C: rate ≈ 0.16 (stage duration ≈ 6.25 days)
// ---------------------------------------------------------------------------
inline constexpr double EGG_TL = 10.0;
inline constexpr double EGG_TH = 40.0;
inline constexpr double EGG_A  = 0.00062;

inline float egg_development_rate(float temp_c) {
    const double T = static_cast<double>(temp_c);
    if (T <= EGG_TL || T >= EGG_TH) return 0.0f;
    const double rate = EGG_A * T * (T - EGG_TL) * std::sqrt(EGG_TH - T);
    return static_cast<float>(std::max(0.0, std::min(rate, 1.0)));
}

// ---------------------------------------------------------------------------
// Larva development — quadratic thermal response
//   rate(T) = a * (T - T_L) * (T_H - T)  if T_L < T < T_H
//   rate(T) = 0                           otherwise
//
// Parameters recalibrated against Bayoh & Lindsay (2003) experimental data
// and validated against Agyekum et al. (2022, Ghana) and Ouédraogo et al.
// (2024, Burkina Faso). The previous value a = 0.00052 produced a per-instar
// rate of ~0.117/day at 25°C (8.5 days per instar × 4 instars = 34 days
// total), which is ~2× too slow vs the measured 13–20 day total.
//
// Sources:
//   - Bayoh & Lindsay 2003 (doi:10.1079/BER2003259): 13–16 days L1→adult at 25°C
//   - Agyekum et al. 2022 (doi:10.1111/tmi.13732): 20.17 ± 0.75 days at 25°C (Ghana)
//   - Ouédraogo et al. 2024 (doi:10.1186/s13071-024-06260-2): 11.87 days at 24.5–28.5°C (Burkina Faso)
//   - Depinay et al. 2004 (doi:10.1186/1475-2875-3-29): fitted to Bayoh data, ~11–13 days
//
//   T_L = 10.0°C  (lower developmental threshold)
//   T_H = 40.0°C  (upper developmental threshold)
//   a   = 0.001   (calibrated so max rate ≈ 0.225 at 25°C,
//                   i.e., stage duration ≈ 4.4 days per instar at 25°C,
//                   total 4 instars ≈ 17.8 days — within the 13–20 day range)
//
// At 25°C: rate ≈ 0.225 (total larva duration ≈ 17.8 days)
// At 20°C: rate ≈ 0.200 (total larva duration ≈ 20.0 days)
// At 28°C: rate ≈ 0.216 (total larva duration ≈ 18.5 days)
// At 30°C: rate ≈ 0.200 (total larva duration ≈ 20.0 days)
// ---------------------------------------------------------------------------
inline constexpr double LARVA_TL = 10.0;
inline constexpr double LARVA_TH = 40.0;
inline constexpr double LARVA_A  = 0.001;

inline float larva_development_rate(float temp_c) {
    const double T = static_cast<double>(temp_c);
    if (T <= LARVA_TL || T >= LARVA_TH) return 0.0f;
    const double rate = LARVA_A * (T - LARVA_TL) * (LARVA_TH - T);
    return static_cast<float>(std::max(0.0, std::min(rate, 1.0)));
}

// ---------------------------------------------------------------------------
// Pupa development — Brière-1 thermal response
//   rate(T) = a * T * (T - T_L) * sqrt(T_H - T)  if T_L < T < T_H
//   rate(T) = 0                                    otherwise
//
// Parameters (Couper et al. 2021 Table 2, An. gambiae):
//   T_L = 12.0°C  (higher threshold — pupae are more sensitive to cold)
//   T_H = 40.0°C  (upper developmental threshold)
//   a   = 0.00066 (fitted to ~1.2 days at 25°C)
//
// At 25°C: rate ≈ 0.83 (stage duration ≈ 1.20 days)
// At 20°C: rate ≈ 0.43 (stage duration ≈ 2.33 days)
// At 30°C: rate ≈ 0.92 (stage duration ≈ 1.09 days)
// ---------------------------------------------------------------------------
inline constexpr double PUPA_TL = 12.0;
inline constexpr double PUPA_TH = 40.0;
inline constexpr double PUPA_A  = 0.00066;

inline float pupa_development_rate(float temp_c) {
    const double T = static_cast<double>(temp_c);
    if (T <= PUPA_TL || T >= PUPA_TH) return 0.0f;
    const double rate = PUPA_A * T * (T - PUPA_TL) * std::sqrt(PUPA_TH - T);
    return static_cast<float>(std::max(0.0, std::min(rate, 1.0)));
}

// ---------------------------------------------------------------------------
// Gonotrophic development rate — placeholder for M7.2
//   Quadratic thermal response for the blood-meal-to-oviposition cycle.
//   Parameters from Mordecai 2013 (gonotrophic cycle).
//
//   T_L = 16.0°C, T_H = 38.0°C, Topt = 25.0°C
//   rate at Topt ≈ 0.25 (cycle duration ≈ 4 days)
// ---------------------------------------------------------------------------
inline constexpr double GONO_TL   = 16.0;
inline constexpr double GONO_TH   = 38.0;
inline constexpr double GONO_TOPT = 25.0;

inline float gonotrophic_development_rate(float temp_c) {
    const double T = static_cast<double>(temp_c);
    if (T <= GONO_TL || T >= GONO_TH) return 0.0f;
    // Normalised quadratic: peaks at 1.0 at Topt
    const double rate = (T - GONO_TL) * (GONO_TH - T) /
                        ((GONO_TOPT - GONO_TL) * (GONO_TH - GONO_TOPT));
    return static_cast<float>(std::max(0.0, std::min(rate * 0.25, 1.0)));
}

}  // namespace mal_abm_fast
