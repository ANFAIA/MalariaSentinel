// SPDX-License-Identifier: MIT
// seeding.cpp — detection-based initial seeding implementation.
//
// Three modes:
//
//   * UNIFORM: emit zero instructions. The submodel uses init_frac
//              for every patch (backward compatible legacy path).
//   * RANDOM_VIABLE: pick N random patch_ids from `viable_patch_ids`,
//              where each chosen patch receives
//              `n_adults_per_detection` adults (ready to disperse)
//              and `n_larvae_per_detection` larvae (need EIP).
//   * EXPLICIT: for each user-supplied DetectionPoint, find the
//              nearest viable patch within `detection_radius_km`
//              (Euclidean metric on lon/lat — a proper geodesic
//              metric is a future improvement). If no patch is
//              within radius, the point is silently dropped.
//
// Distance is computed in degrees (Euclidean on the (lon, lat)
// grid). The Ghana regional AOI spans ~5 deg lon, ~7 deg lat, so
// 1 deg ~ 111 km. A `detection_radius_km = 5.0` translates to
// ~0.045 deg, which is far above the Ghana cell resolution of
// 0.011 deg (1 km / 111 km/deg). This is a coarse approximation
// but adequate for "snap a village to the nearest patch".
#include "mal_abm_fast/seeding.hpp"

#include <array>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <vector>

namespace mal_abm_fast {

namespace {

// 1 degree of latitude is ~111.32 km everywhere. 1 degree of
// longitude varies with latitude (cos(lat)). We use a single
// combined factor — `km_per_deg_lon` and `km_per_deg_lat` — so
// the squared-distance formula is isotropic in the AOI's local
// tangent plane.
constexpr double kKmPerDegLat = 111.32;

inline double km_per_deg_lon(double lat_deg) {
    return kKmPerDegLat * std::cos(lat_deg * (3.14159265358979323846 / 180.0));
}

// Approximate distance in km between two (lon, lat) points using
// a simple equirectangular projection. Good enough for snapping
// a user detection to the nearest habitat patch on a regional
// AOI; not suitable for continental or polar scales.
inline double haversine_km(double lon1, double lat1,
                           double lon2, double lat2) {
    // Use the equirectangular approximation since the radius is
    // small (a few km). Convert to km: dlon * km_per_deg_lon at
    // the midpoint latitude, dlat * km_per_deg_lat.
    const double mid_lat = 0.5 * (lat1 + lat2);
    const double dlon_km = (lon1 - lon2) * km_per_deg_lon(mid_lat);
    const double dlat_km = (lat1 - lat2) * kKmPerDegLat;
    return std::sqrt(dlon_km * dlon_km + dlat_km * dlat_km);
}

// Find the index (into `viable_patch_ids`) of the nearest patch
// to (lon, lat) within `radius_km`. Returns -1 if no patch is
// within radius. Operates on the parallel arrays directly to
// avoid a hashmap allocation.
inline int32_t find_nearest_patch(
    double lon, double lat, double radius_km,
    const std::vector<int32_t>& viable_patch_ids,
    const std::vector<std::array<double, 2>>& patch_lonlat) {
    int32_t best_idx = -1;
    double  best_dist = radius_km;
    for (size_t i = 0; i < viable_patch_ids.size(); ++i) {
        const double plon = patch_lonlat[i][0];
        const double plat = patch_lonlat[i][1];
        const double d = haversine_km(lon, lat, plon, plat);
        if (d <= best_dist) {
            best_dist = d;
            best_idx = static_cast<int32_t>(i);
        }
    }
    return best_idx;
}

}  // namespace

std::vector<SeedInstruction> build_seed_instructions_host_weighted(
    const SeedingConfig& config,
    const std::vector<int32_t>& viable_patch_ids,
    const std::vector<std::array<double, 2>>& patch_lonlat,
    const std::vector<std::array<int32_t, 2>>& patch_rowcol,
    const std::vector<float>& cell_host_score,
    int32_t grid_h,
    int32_t grid_w,
    float cell_size_m,
    Prng& rng) {
    std::vector<SeedInstruction> out;
    const size_t n_patches = viable_patch_ids.size();
    if (n_patches == 0 || cell_host_score.empty() ||
        grid_h <= 0 || grid_w <= 0 || !(cell_size_m > 0.0f)) {
        return out;
    }
    if (cell_host_score.size() !=
        static_cast<size_t>(grid_h) * static_cast<size_t>(grid_w)) {
        throw std::runtime_error(
            "build_seed_instructions_host_weighted: cell_host_score size "
            "does not match grid dimensions");
    }

    // -- 1. Per-patch weight: Σ nearby host score with Gaussian decay ---
    // Mirrors HostSeekingModel::cell_attraction's distance kernel
    // (exp(-dist/scale)) but sums host density rather than a single
    // target cell: patches surrounded by preferred hosts weigh most.
    const double scale_m = (config.host_seeking_scale_m > 0.0f)
        ? static_cast<double>(config.host_seeking_scale_m) : 100.0;
    const double radius_km = std::max(0.05, config.host_weight_radius_km);
    const int32_t search_cells = static_cast<int32_t>(
        std::ceil(radius_km * 1000.0 / static_cast<double>(cell_size_m)));
    const double radius_m = radius_km * 1000.0;

    std::vector<double> weights(n_patches, 0.0);
    for (size_t i = 0; i < n_patches; ++i) {
        const int32_t pr = patch_rowcol[i][0];
        const int32_t pc = patch_rowcol[i][1];
        if (pr < 0 || pr >= grid_h || pc < 0 || pc >= grid_w) continue;
        const int32_t r_min = std::max(0, pr - search_cells);
        const int32_t r_max = std::min(grid_h - 1, pr + search_cells);
        const int32_t c_min = std::max(0, pc - search_cells);
        const int32_t c_max = std::min(grid_w - 1, pc + search_cells);
        double w = 0.0;
        for (int32_t r = r_min; r <= r_max; ++r) {
            const double dy = (static_cast<double>(r) - static_cast<double>(pr))
                * static_cast<double>(cell_size_m);
            for (int32_t c = c_min; c <= c_max; ++c) {
                const double dx = (static_cast<double>(c) - static_cast<double>(pc))
                    * static_cast<double>(cell_size_m);
                const double dist_m = std::sqrt(dx * dx + dy * dy);
                if (dist_m > radius_m) continue;
                const float score = cell_host_score[static_cast<size_t>(r) *
                    static_cast<size_t>(grid_w) + static_cast<size_t>(c)];
                if (score <= 0.0f) continue;
                w += static_cast<double>(score) * std::exp(-dist_m / scale_m);
            }
        }
        weights[i] = w;
    }

    double total = 0.0;
    for (const double w : weights) total += w;
    if (total <= 0.0) {
        std::cerr << "seeding: host-weighted mode found no hosts within "
                  << radius_km << " km of any viable patch; nothing seeded\n";
        return out;
    }

    // -- 2. Weighted sampling without replacement (roulette w/ removal) --
    std::vector<double> remaining = weights;
    const int32_t n = std::min<int32_t>(
        config.n_detections, static_cast<int32_t>(n_patches));
    out.reserve(static_cast<size_t>(n));
    for (int32_t k = 0; k < n; ++k) {
        double tot = 0.0;
        for (const double w : remaining) tot += w;
        if (tot <= 0.0) break;
        const double draw = rng.uniform_double() * tot;
        size_t chosen = n_patches;
        double cum = 0.0;
        for (size_t i = 0; i < n_patches; ++i) {
            cum += remaining[i];
            if (cum >= draw) { chosen = i; break; }
        }
        if (chosen == n_patches) {
            // Floating-point edge: fall back to the last non-zero patch.
            for (size_t i = n_patches; i-- > 0;) {
                if (remaining[i] > 0.0) { chosen = i; break; }
            }
            if (chosen == n_patches) break;
        }
        SeedInstruction inst;
        inst.patch_id = viable_patch_ids[chosen];
        inst.row      = patch_rowcol[chosen][0];
        inst.col      = patch_rowcol[chosen][1];
        inst.lon      = patch_lonlat[chosen][0];
        inst.lat      = patch_lonlat[chosen][1];
        inst.n_adults = config.n_adults_per_detection;
        inst.n_larvae = config.n_larvae_per_detection;
        out.push_back(inst);
        remaining[chosen] = 0.0;  // removal: spread across distinct patches
    }
    return out;
}

std::vector<SeedInstruction> build_seed_instructions_for_patches(
    const SeedingConfig& config,
    const std::vector<int32_t>& viable_patch_ids,
    const std::vector<std::array<double, 2>>& patch_lonlat,
    const std::vector<std::array<int32_t, 2>>& patch_rowcol,
    Prng& rng) {
    std::vector<SeedInstruction> out;

    switch (config.mode) {
        case SeedingMode::UNIFORM:
            // Legacy path: the submodel seeds `init_frac` of K in
            // every patch. No instructions are needed.
            return out;

        case SeedingMode::RANDOM_VIABLE: {
            if (viable_patch_ids.empty()) return out;
            if (patch_lonlat.size() != viable_patch_ids.size() ||
                patch_rowcol.size() != viable_patch_ids.size()) {
                throw std::runtime_error(
                    "build_seed_instructions: viable_patch_ids / patch_lonlat / "
                    "patch_rowcol size mismatch");
            }
            const int32_t n = std::min<int32_t>(
                config.n_detections,
                static_cast<int32_t>(viable_patch_ids.size()));
            if (n <= 0) return out;

            // Sample without replacement using a Fisher-Yates
            // partial shuffle on the first `n` slots. The Prng
            // stream is consumed in `n + (n_patches - n)` draws so
            // two calls with the same seed produce the same
            // selection.
            const int32_t nv = static_cast<int32_t>(viable_patch_ids.size());
            std::vector<int32_t> idx(static_cast<size_t>(nv));
            for (int32_t i = 0; i < nv; ++i) idx[static_cast<size_t>(i)] = i;
            for (int32_t i = 0; i < n; ++i) {
                const int32_t j = i + static_cast<int32_t>(
                    rng.uniform_double() * static_cast<double>(nv - i));
                if (j != i) {
                    std::swap(idx[static_cast<size_t>(i)],
                              idx[static_cast<size_t>(j)]);
                }
            }

            out.reserve(static_cast<size_t>(n));
            for (int32_t k = 0; k < n; ++k) {
                const int32_t i = idx[static_cast<size_t>(k)];
                SeedInstruction inst;
                inst.patch_id = viable_patch_ids[static_cast<size_t>(i)];
                inst.row      = patch_rowcol[static_cast<size_t>(i)][0];
                inst.col      = patch_rowcol[static_cast<size_t>(i)][1];
                inst.lon      = patch_lonlat[static_cast<size_t>(i)][0];
                inst.lat      = patch_lonlat[static_cast<size_t>(i)][1];
                inst.n_adults = config.n_adults_per_detection;
                inst.n_larvae = config.n_larvae_per_detection;
                out.push_back(inst);
            }
            return out;
        }

        case SeedingMode::EXPLICIT: {
            if (config.detections.empty()) return out;
            if (viable_patch_ids.empty()) return out;
            if (patch_lonlat.size() != viable_patch_ids.size() ||
                patch_rowcol.size() != viable_patch_ids.size()) {
                throw std::runtime_error(
                    "build_seed_instructions: viable_patch_ids / patch_lonlat / "
                    "patch_rowcol size mismatch");
            }
            out.reserve(config.detections.size());
            for (const auto& det : config.detections) {
                const int32_t idx = find_nearest_patch(
                    det.lon, det.lat, config.detection_radius_km,
                    viable_patch_ids, patch_lonlat);
                if (idx < 0) continue;  // no patch within radius
                SeedInstruction inst;
                inst.patch_id = viable_patch_ids[static_cast<size_t>(idx)];
                inst.row      = patch_rowcol[static_cast<size_t>(idx)][0];
                inst.col      = patch_rowcol[static_cast<size_t>(idx)][1];
                inst.lon      = patch_lonlat[static_cast<size_t>(idx)][0];
                inst.lat      = patch_lonlat[static_cast<size_t>(idx)][1];
                inst.n_adults = det.n_adults > 0
                    ? det.n_adults
                    : config.n_adults_per_detection;
                inst.n_larvae = det.n_larvae > 0
                    ? det.n_larvae
                    : config.n_larvae_per_detection;
                out.push_back(inst);
            }
            return out;
        }
    }
    return out;
}

}  // namespace mal_abm_fast
