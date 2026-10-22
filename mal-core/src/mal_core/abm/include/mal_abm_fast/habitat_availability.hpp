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
// supply, represented by URBAN_PERSISTENT_BETA × lc_built (a proxy, not
// a measurement, not a forced depth).
#pragma once

#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>

namespace mal_abm_fast {

// -- constants (all proxy_habitat v1; see plan 02 §7) -------------------------

/// Effective scale K_ref[s]: daily capacity multiplier in the 0..1 model
/// state vector (verify final capacity once calibrated with occupancies!)
constexpr float K_REF_GHANA = 50.0f;   // [individual per cell km²] (0.921 km² average)

/// Built-surface persistent warmth index: urban coefficient.
/// Engineering prior in (0, 1]: proxy of supply via built-up surface; the
/// Z-pull is blued towards humans. NOT a measured flow. Calibrate in WM.
constexpr float URBAN_PERSISTENT_BETA = 0.75f;

/// DAMAGED-RAIN fraction of the built surface that acts as additional
/// open-pluvial surface for rain-pool formation (subject to the clip).
constexpr float RAIN_POOLS_BUIT_DAMAGE = 0.3f;   // [dimensionless]

/// Candidate-cell floor. Cells with total.static potential below this are
/// handled without a patch — they disappear from the patch union (no
/// TWI/water/urban floors involved).
constexpr float kHabitatCandidateMin = 0.01f;

/// Pluvial daily demand: the precipitation scale (mm) that saturates the
/// z-update for a wet day in the Gulf of Guinea. Calibration in WM.
constexpr float RAIN_SCALE_MM = 2.5f;  // [mm/d**]

/// Pluvial daily memory: effective exponential drying (days). Calibrate
/// with Accra seasonal reservoirs (KLK / WM3).
constexpr float DRY_MEMORY_DAYS = 5.0f;   // [days]

/// Species/species-neutral daily accuracy S threshold below which a cell
/// is "dry" for the aquatic-stress functions (preserved from the pool
/// module contract; cohort parsing depends on the S<dynamic typedef).
constexpr float kActivationMin = 0.01f;

// -- habitat types ------------------------------------------------------------

/// Six static habitat types (g). The first three are always persistent
/// (k(g) = 0); the rest are pluvial (k(g) = 1). The list is a DESIGN
/// CHOICE to match the WorldCover/JRC bands; extend with care.
enum class ZoneId : std::size_t {
    JRC_PERSISTENT = 0,   // JRC GSW persistent surface water fraction
    URBAN_PERSISTENT,     // built-surface persistent supply (human)
    WETLAND,              // wetland + mangrove (ESA WorldCover)
    OPEN_PLUVIAL,         // open/low-veg + bare + water (+ rain pools)
    CROP,                 // cropland (irrigation/backyard agriculture)
    FOREST,               // forest fraction (currently unused; 0 throughout)
};
constexpr size_t kNumZoneId = 6;

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
    // URBAN persistent supply — extends the lease.
    h[static_cast<size_t>(ZoneId::URBAN_PERSISTENT)] =
        std::clamp(URBAN_PERSISTENT_BETA * f.lc_built, 0.0f, 1.0f);
    h[static_cast<size_t>(ZoneId::WETLAND)] =
        std::clamp(f.lc_wetland, 0.0f, 1.0f);
    // Open pluvial: open/low-veg + water + rain pools on the built surface…
    // (documented rule; does NOT double-count man-made supply: pools go
    // under a distinct habitat type and a distinct temporal dynamic.)
    h[static_cast<size_t>(ZoneId::OPEN_PLUVIAL)] =
        std::clamp(f.lc_open_plus_water +
                       RAIN_POOLS_BUIT_DAMAGE * f.lc_built, 0.0f, 1.0f);
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
///   z_dry = z * exp(-delta_days / DRY_MEMORY_DAYS)
///   z     = z_dry + (1 - z_dry) * (1 - exp(-rain_mm / RAIN_SCALE_MM))
inline float update_z_step(float z, float rain_mm, float delta_days) {
    const float z_dry = z * std::exp(-delta_days / DRY_MEMORY_DAYS);
    const float fill = 1.0f - std::exp(-std::max(0.0f, rain_mm) / RAIN_SCALE_MM);
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
constexpr size_t kSentinelSpecies = 4;   // index boundary (not a real species)

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
inline std::array<float, kNumZoneId> default_species_weights(SpeciesId s) {
    switch (s) {
        case SpeciesId::FUNESTUS: {
            return {0.45f /* jrc */,  0.10f /* urban */, 0.30f /* wetland */,
                    0.10f /* open */, 0.05f /* crop */,  0.00f /* forest */};
        }
        case SpeciesId::GAMBIAE_SS: {
            return {0.05f, 0.15f, 0.05f, 0.65f, 0.10f, 0.00f};
        }
        case SpeciesId::COLUZZII: {
            return {0.40f, 0.20f, 0.10f, 0.25f, 0.05f, 0.00f};
        }
        case SpeciesId::ARABIENSIS: {
            return {0.10f, 0.15f, 0.10f, 0.55f, 0.10f, 0.00f};
        }
    }
    return {};
}

/// Species-neutral default (single-engine runs): the coluzzii-weighted mix
/// of the canonical vector (mid-complex; fuelled by both persistent and
/// seasonal supply). Preserved for external engine parity against
/// my static-coluzzii-foreasted default (below). Deterministic.
inline std::array<float, kNumZoneId> default_species_weights() {
    return {0.25f, 0.15f, 0.15f, 0.40f, 0.05f, 0.00f};
}

// -- the day formula ----------------------------------------------------------

/// Static sum_k w[g] * H[*, g] * A[*, k] accuracy: persistent habitats ride
/// at availability 1 in the MVP (A = 1 whenever their potential > 0);
/// pluvial habitats use the rain-driven z. No path takes S above 1.
inline float species_accuracy(const std::array<float, kNumZoneId>& h,
                              const std::array<float, kNumZoneId>& w,
                              float z_pluvial) {
    static constexpr size_t kNumPersistent = 3;  // [jrc, urban, wetland]
    float s = 0.0f;
    for (size_t g = 0; g < kNumZoneId; ++g) {
        if (w[g] <= 0.0f || h[g] <= 0.0f) continue;
        const float availability =
            (g < kNumPersistent) ? 1.0f : std::clamp(z_pluvial, 0.0f, 1.0f);
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
    return K_REF_GHANA * cell_area_km2 * std::max(0.0, s);
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
