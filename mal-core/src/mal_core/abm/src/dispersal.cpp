// SPDX-License-Identifier: MIT
// dispersal.cpp — F1.c real implementation of the adult mosquito
// dispersal kernel.
//
// The kernel matches the Python reference in
// `mal_ghana_sim.abm.mosquito_submodel._lon_lat_offset_m`:
//
//     dx = N(0, sigma_m)
//     dy = N(0, sigma_m)
//     dist = sqrt(dx^2 + dy^2)
//     if dist > max_m:  dx *= max_m / dist;  dy *= max_m / dist   (clip)
//     dlon = dx / (geodesy.metres_per_deg_lat * cos(lat_rad))
//     dlat = dy / geodesy.metres_per_deg_lat
//
// The longitude divisor is shrunk by `cos(lat)` so the *ground* distance
// is correct at the patch's latitude. We guard against
// `cos(lat_rad) <= 0` (the poles) with a small floor to keep the
// division finite — the Ghana AOI sits at lat ≈ 8° so this branch is
// effectively dead in the M1.5 thin slice.
#include "dispersal.hpp"

#include <cmath>

#include "mal_abm_fast/config.hpp"

namespace mal_abm_fast {

namespace {

constexpr double kCosLatFloor  = 1e-6;  // avoid div-by-near-zero at the poles.

}  // namespace

DispOffset offset_m(Prng& prng, double lon, double lat,
                    double sigma_m, double max_m) {
    (void)lon;  // The kernel is isotropic in metres; lon only affects
                // the cos(lat) correction for the dlon conversion. It
                // is kept in the signature for parity with the Python
                // reference and for future non-isotropic extensions.

    const double dx = prng.normal(0.0, sigma_m);
    const double dy = prng.normal(0.0, sigma_m);
    const double dist = std::sqrt(dx * dx + dy * dy);

    // Clip to the dispersal cap. The `dist > 0` guard avoids
    // 0/0 = NaN when the Gaussian draw lands exactly on the origin
    // (probability zero in theory, but the normal approximation can
    // produce a 0.0 double).
    double clip_dx = dx;
    double clip_dy = dy;
    if (dist > max_m && dist > 0.0) {
        const double scale = max_m / dist;
        clip_dx *= scale;
        clip_dy *= scale;
    }

    const double lat_rad  = lat * M_PI / 180.0;
    const double cos_lat  = std::cos(lat_rad);
    const double safe_cos = (cos_lat > kCosLatFloor) ? cos_lat : kCosLatFloor;

    const double m_per_deg = load_config().geodesy.metres_per_deg_lat;
    DispOffset out;
    out.dlon = clip_dx / (m_per_deg * safe_cos);
    out.dlat = clip_dy / m_per_deg;
    return out;
}

}  // namespace mal_abm_fast
