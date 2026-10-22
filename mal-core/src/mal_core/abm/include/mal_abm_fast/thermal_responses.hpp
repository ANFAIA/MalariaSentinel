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
//
// All parameters (T_L, T_H, a) live in model_constants.yaml under
// `thermal:`; this header only implements the formulas.
#pragma once

#include <algorithm>
#include <cmath>

#include "config.hpp"

namespace mal_abm_fast {

// ---------------------------------------------------------------------------
// Egg development — Brière-1 thermal response
//   rate(T) = a * T * (T - T_L) * sqrt(T_H - T)  if T_L < T < T_H
//   rate(T) = 0                                    otherwise
// ---------------------------------------------------------------------------
inline float egg_development_rate(float temp_c) {
    static const ThermalCfg& cfg = load_config().thermal;
    const double T = static_cast<double>(temp_c);
    const double tl = cfg.egg_development_tmin_c;
    const double th = cfg.egg_development_tmax_c;
    if (T <= tl || T >= th) return 0.0f;
    const double rate = cfg.egg_development_scale * T * (T - tl) * std::sqrt(th - T);
    return static_cast<float>(std::max(0.0, std::min(rate, 1.0)));
}

// ---------------------------------------------------------------------------
// Larva development — quadratic thermal response
//   rate(T) = a * (T - T_L) * (T_H - T)  if T_L < T < T_H
//   rate(T) = 0                           otherwise
//
// Calibrated against Bayoh & Lindsay (2003) experimental data and
// validated against Agyekum et al. (2022, Ghana) and Ouédraogo et al.
// (2024, Burkina Faso).
//
// Sources:
//   - Bayoh & Lindsay 2003 (doi:10.1079/BER2003259): 13–16 days L1→adult at 25°C
//   - Agyekum et al. 2022 (doi:10.1111/tmi.13732): 20.17 ± 0.75 days at 25°C (Ghana)
//   - Ouédraogo et al. 2024 (doi:10.1186/s13071-024-06260-2): 11.87 days at 24.5–28.5°C
//   - Depinay et al. 2004 (doi:10.1186/1475-2875-3-29): fitted to Bayoh data
// ---------------------------------------------------------------------------
inline float larva_development_rate(float temp_c) {
    static const ThermalCfg& cfg = load_config().thermal;
    const double T = static_cast<double>(temp_c);
    const double tl = cfg.larva_development_tmin_c;
    const double th = cfg.larva_development_tmax_c;
    if (T <= tl || T >= th) return 0.0f;
    const double rate = cfg.larva_development_scale * (T - tl) * (th - T);
    return static_cast<float>(std::max(0.0, std::min(rate, 1.0)));
}

// ---------------------------------------------------------------------------
// Pupa development — Brière-1 thermal response
//   rate(T) = a * T * (T - T_L) * sqrt(T_H - T)  if T_L < T < T_H
//   rate(T) = 0                                    otherwise
//
// Parameters (Couper et al. 2021 Table 2, An. gambiae): the pupal lower
// threshold is higher than the egg one (pupae are more sensitive to cold).
// ---------------------------------------------------------------------------
inline float pupa_development_rate(float temp_c) {
    static const ThermalCfg& cfg = load_config().thermal;
    const double T = static_cast<double>(temp_c);
    const double tl = cfg.pupa_development_tmin_c;
    const double th = cfg.pupa_development_tmax_c;
    if (T <= tl || T >= th) return 0.0f;
    const double rate = cfg.pupa_development_scale * T * (T - tl) * std::sqrt(th - T);
    return static_cast<float>(std::max(0.0, std::min(rate, 1.0)));
}

// ---------------------------------------------------------------------------
// Gonotrophic development rate — placeholder for M7.2 (test-only today; no
// production caller). Parameters from Mordecai 2013 (gonotrophic cycle).
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
