// SPDX-License-Identifier: MIT
// dispersal.hpp — adult mosquito dispersal kernel (stub; F1.c implements)
#pragma once

#include <cstdint>

namespace mal_abm_fast {

struct DispersalParams {
    double sigma_m   = 1000.0;   // stddev of the Gaussian kernel (m)
    double max_m     = 2000.0;   // hard cap (m)
    double prob      = 0.2;      // per-day dispersal probability
};

}  // namespace mal_abm_fast
