// SPDX-License-Identifier: MIT
// dispersal.hpp — adult mosquito dispersal kernel.
//
// The 2D Gaussian kernel is isotropic in metres, clipped at max_m
// (the rural An. gambiae s.s. 2 km cap). The longitude offset is
// divided by cos(lat) so the ground distance is correct at the
// patch's latitude.
//
//   dx = N(0, sigma_m)
//   dy = N(0, sigma_m)
//   dist = sqrt(dx^2 + dy^2)
//   if dist > max_m: scale (dx, dy) by max_m / dist   (clip to circle)
//   dlon = dx / (111320 * cos(lat_rad))
//   dlat = dy / 111320
//
// The math subagent (F1.c) implements the kernel. The `dispersal` and
// `mosquito_submodel` modules share the same `Prng` stream so the
// deterministic per-adult draw order is reproducible across runs.
#pragma once

#include "prng.hpp"

namespace mal_abm_fast {

// (dlon, dlat) offset in degrees. The caller adds these to the
// agent's current (lon, lat) to get the post-dispersal cell.
struct DispOffset {
    double dlon = 0.0;
    double dlat = 0.0;
};

// Sample a single adult's (dlon, dlat) offset. The math subagent
// implements this as: draw (dx, dy) from N(0, sigma_m^2), clip to a
// circle of radius `max_m`, convert to degrees with the cos(lat)
// correction. The same `prng` is used across the whole submodel so
// the per-adult draw order is stable.
DispOffset offset_m(Prng& prng, double lon, double lat,
                    double sigma_m, double max_m);

}  // namespace mal_abm_fast
