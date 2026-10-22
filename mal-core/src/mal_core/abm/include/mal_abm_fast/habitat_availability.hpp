// SPDX-License-Identifier: MIT
// habitat_availability.hpp — the single number (0..1) that determines
// whether mosquitoes CAN breed in a cell right now. Contract v3.0.
//
//   habitat_potential : static per-cell amplitude, six habitat types
//   update_z_step     : one-day pluvial recursion (rain-driven)
//   species_accuracy  : daily accuracy, affinity × potential × availability
//   k_habitat         : absolute per-cell capacity in individual-equivalents
//
// Legacy foreword (plan 01 §7): what was removed is what didn't belong —
// the pool water balance in mm and its constants, the TWI gate, the
// urban mm floor, and the urban capacity clamp K_eff. Rain only enters the
// pluvial reservoir as a forcing; total water is not reconstructed.
//
// The urban persistent supply premise (user-fixed): leaks, seepage,
// drainage and human water storage support small dry-season breeding
// supply, represented by urban.beta_urban × lc_built (a proxy, not
// a measurement, not a forced depth).
#pragma once

#include "mal_abm_fast/config.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>

namespace mal_abm_fast {

// -- constants ----------------------------------------------------------------
//
// Single source: mal-core/config/model_constants.yaml (plan constants-yaml
// §4). All inline accessors below go through the load_config() singleton;
// there are NO compiled defaults left in this header.


/// Static bundle of features read from the env contract (v3.0 planes).
struct HabitatFeatures {
    float jrc_persistent = 0.0f;
    float lc_built = 0.0f;
    float lc_wetland = 0.0f;
    float lc_open_plus_water = 0.0f;
    float lc_crop = 0.0f;

    static HabitatFeatures from_bands(float jrc, float built, float wetland,
                                      float open_plus, float crop) {
        return HabitatFeatures{std::max(0.0f, jrc), std::max(0.0f, built),
                               std::max(0.0f, wetland), std::max(0.0f, open_plus),
                               std::max(0.0f, crop)};
    }
};

/// Assemble H[i, g] (the static potential in [0,1] per habitat type) from
/// the feature bundle. One explicit rule per habitat type.
inline std::array<float, kNumZoneId> habitat_potential(
    const HabitatFeatures& f) {
    std::array<float, kNumZoneId> h{};
    h[static_cast<size_t>(ZoneId::JRC_PERSISTENT)] =
        std::clamp(f.jrc_persistent, 0.0f, 1.0f);
    // Urban persistent supply — extends the lease.
    h[static_cast<size_t>(ZoneId::URBAN_PERSISTENT)] =
        std::clamp(static_cast<float>(
                       load_config().urban.beta_urban) *
                       f.lc_built,
                   0.0f, 1.0f);
    h[static_cast<size_t>(ZoneId::WETLAND)] =
        std::clamp(f.lc_wetland, 0.0f, 1.0f);
    // Open pluvial: open/low-veg + water + rain pools on the built surface…
    // (documented rule; does NOT double-count man-made supply: pools go
    // under a distinct habitat type and a distinct temporal dynamic.)
    h[static_cast<size_t>(ZoneId::OPEN_PLUVIAL)] =
        std::clamp(f.lc_open_plus_water +
                       static_cast<float>(load_config()
                                              .urban.rain_pools_built_damage) *
                           f.lc_built,
                   0.0f, 1.0f);
    h[static_cast<size_t>(ZoneId::CROP)] =
        std::clamp(f.lc_crop, 0.0f, 1.0f);
    h[static_cast<size_t>(ZoneId::FOREST)] = 0.0f;
    return h;
}

/// Total static amplitude of the cell: sum_g H[i, g] capped on 1. Used by
/// the candidate floor (the urban_capacity_factor consumer retired with
/// contract 4.0).
inline float habitat_total_potential(const std::array<float, kNumZoneId>& h) {
    float total = 0.0f;
    for (const float v : h) total += v;
    return std::min(total, 1.0f);
}

/// One-day pluvial recursion (rain-driven; contract v3.0 floors of the
/// two-forcing design). Called per-step and during warm-up.
///
///   z_dry = z * exp(-delta_days / pluvial.dry_memory_days)
///   z     = z_dry + (1 - z_dry) * (1 - exp(-rain_mm / pluvial.rain_scale_mm))
inline float update_z_step(float z, float rain_mm, float delta_days) {
    const auto& pluvial = load_config().pluvial;
    const float z_dry =
        z * std::exp(-delta_days / static_cast<float>(pluvial.dry_memory_days));
    const float fill =
        1.0f - std::exp(-std::max(0.0f, rain_mm) /
                        static_cast<float>(pluvial.rain_scale_mm));
    return std::clamp(z_dry + (1.0f - z_dry) * fill, 0.0f, 1.0f);
}

// -- species affinities -------------------------------------------------------

/// Species affinity w[s, g]; each row sums to 1. Anchored on 1.0 × the
/// plant list (order, habitat-preference context; plan 02 §8).
enum class SpeciesId : std::size_t {
    FUNESTUS = 0,
    GAMBIAE_SS,
    COLUZZII,
    ARABIENSIS,
};

inline const char* species_name(SpeciesId id) {
    switch (id) {
        case SpeciesId::FUNESTUS:   return "funestus";
        case SpeciesId::GAMBIAE_SS: return "gambiae_ss";
        case SpeciesId::COLUZZII:   return "coluzzii";
        case SpeciesId::ARABIENSIS: return "arabiensis";
    }
    return "unknown";
}

/// One vector per species; each row sums to 1.0 (plan 02 §8 calibration).
/// Loaded BY NAME from model_constants.yaml (species.<name>.weights),
/// pre-transformed at load time to ZoneId order.
inline std::array<float, kNumZoneId> default_species_weights(SpeciesId s) {
    const auto& rows = load_config().species.rows;
    const auto it = rows.find(species_name(s));
    if (it != rows.end()) {
        std::array<float, kNumZoneId> out{};
        for (size_t g = 0; g < kNumZoneId; ++g)
            out[g] = static_cast<float>(it->second.weights[g]);
        return out;
    }
    return {};
}

/// Species-neutral default (single-engine runs): the neutral row loaded
/// from model_constants.yaml (species.neutral.weights).
inline std::array<float, kNumZoneId> default_species_weights() {
    std::array<float, kNumZoneId> out{};
    const auto& w = load_config().species.neutral_weights;
    for (size_t g = 0; g < kNumZoneId; ++g) out[g] = static_cast<float>(w[g]);
    return out;
}

// -- the day formula ----------------------------------------------------------

/// Static sum_k w[g] * H[*, g] * A[*, k] accuracy: persistent habitats ride
/// at capacity.persistent_availability (A = that constant whenever their
/// potential > 0); pluvial habitats use the rain-driven z. No path takes
/// S above 1.
inline float species_accuracy(const std::array<float, kNumZoneId>& h,
                              const std::array<float, kNumZoneId>& w,
                              float z_pluvial) {
    // Persistent/pluvial split comes from habitat_types.dynamics (names),
    // precomputed as a ZoneId bitset at load time (no positional rule).
    const auto& persistent_zone = load_config().habitat_types.persistent_zone;
    float s = 0.0f;
    for (size_t g = 0; g < kNumZoneId; ++g) {
        if (w[g] <= 0.0f || h[g] <= 0.0f) continue;
        const float availability =
            persistent_zone[g]
                ? static_cast<float>(
                      load_config().capacity.persistent_availability)
                : std::clamp(z_pluvial, 0.0f, 1.0f);
        s += w[g] * h[g] * availability;
    }
    return std::clamp(s, 0.0f, 1.0f);
}

/// Absolute capacity (individual-equivalent units; plan §5.4):
///   K[i, s, t] = K_ref[s] * cell_area_km2 * S[i, s, t]
/// `cell_area_km2` handles cut AOI edge cells; the return is a plain
/// multiplier the cohort bank uses as-is (ABSOLUTE K — not K_MAX × f, the
/// removed urban clamp).
inline double k_habitat(double s, double cell_area_km2) {
    return load_config().species.k_ref * cell_area_km2 * std::max(0.0, s);
}

/// Approximate cell area (km²) at a given latitude and edge cell size (m).
inline double cell_area_km2(double lat_deg, double cell_size_m) {
    // Equirectangular approximation, adequate at the scale of a single cell:
    // area = dx * dy where dx ≈ cell_size * cos(lat).
    constexpr double kDegToRad = 3.14159265358979323846 / 180.0;
    const double dx_m = cell_size_m * std::cos(lat_deg * kDegToRad);
    return (dx_m * cell_size_m) / 1.0e6;
}

}  // namespace mal_abm_fast
