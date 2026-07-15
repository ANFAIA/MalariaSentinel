// SPDX-License-Identifier: MIT
// eip.cpp — extrinsic incubation period (stub; F1.c implements)
#include "eip.hpp"

namespace mal_abm_fast {

double accumulate_eip(double eip_progress, double daily_mean_temp_c) {
    if (daily_mean_temp_c != daily_mean_temp_c) return eip_progress;  // NaN-safe
    double gd = (daily_mean_temp_c > EIP_BASE_C) ? (daily_mean_temp_c - EIP_BASE_C) : 0.0;
    return eip_progress + gd;
}

}  // namespace mal_abm_fast
