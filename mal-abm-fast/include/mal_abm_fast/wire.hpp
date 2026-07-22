// SPDX-License-Identifier: MIT
// wire.hpp — single shared header for the C++ ABM engine (M-perf / mal-abm-fast).
//
// This is the canonical "data contract" header. Every module in
// mal-abm-fast includes wire.hpp to pick up:
//   * the F1.5 default constants (EIP thresholds, dispersal kernel, birth rate,
//     PLUVIAL_POOL rule thresholds, the no-data sentinel, the state-band
//     names, the contract / generator version strings)
//   * the shared value types (AOI, HabitatPatch, PatchState, DensityGrid,
//     SuitabilityGrid)
//
// The constants must match `mal_ghana_sim.abm` defaults exactly — the C++
// engine's per-day outputs must be bit-for-bit compatible with the Python
// Mesa-Geo engine for the same (env, habitat, seed, days) inputs.
//
// The wire.hpp header is header-only. The AOI::cells_per_side() method is
// defined in aoi.hpp (separately compiled into the library, although
// header-only is also viable).
#pragma once

#include <array>
#include <cmath>
#include <cstdint>
#include <string>
#include <vector>

namespace mal_abm_fast {

// ---------------------------------------------------------------------------
// Constants — match mal_ghana_sim.abm defaults exactly (M1.5 thin slice).
// ---------------------------------------------------------------------------

// Per-patch carrying capacity.
inline constexpr int    K_MAX                       = 1000;
// Default initialisation: round(n_patches * k_per_patch * init_frac) larvae.
inline constexpr int    K_PER_PATCH_DEFAULT        = 1000;
// 30% of K is seeded as larvae on construction.
inline constexpr float  INIT_FRAC                   = 0.30f;

// EIP (extrinsic incubation period) growing-degree-day model.
//   daily_gd       = max(0, T - EIP_BASE_C)
//   infective when eip_progress >= EIP_THRESHOLD_GD
// Tuned for An. gambiae s.s. in the M1.5 thin slice.
inline constexpr float  EIP_BASE_C                  = 16.0f;
inline constexpr float  EIP_THRESHOLD_GD            = 110.0f;

// Adult dispersal kernel: isotropic Gaussian in metres, clipped at 2000 m.
// 10% of adults move per day (An. gambiae rural dispersal).
// Sigma=450m: midpoint of Costantini et al. 1996 (350-650 m/day, Burkina
//   Faso MRR) and Thomas et al. 2013 (median 386m, The Gambia).
// Cap=2000m: Thomas et al. 2013 95th percentile (1.7-2.8 km); captures
//   rare long-distance colonization events.
inline constexpr float  ADULT_DISPERSE_PROB         = 0.05f;
inline constexpr float  ADULT_DISPERSE_SIGMA_M      = 450.0f;
inline constexpr float  ADULT_DISPERSE_MAX_M        = 2000.0f;

// Per-adult per-day fecundity: binomial(n_adults/2, BIRTH_FECUNDITY) new larvae.
// Tuned so the population stays near the initial seeded count on the
// 30k-patch, 30-day M1.5 perf budget. The M1.5 perf baseline; raising
// this would only mask the structural 150-adult point-source collapse
// (see docs/calibration-test-framework.md §6 and the p_7b70cbc1 proposal
// summary for the resolution path discussion).
inline constexpr float  BIRTH_FECUNDITY              = 0.25f;

// Larva density-dependent mortality (Beverton-Holt, docs/abm-status.md:79).
inline constexpr float  LARVA_BH_S0    = 0.95f;   // baseline daily survival
inline constexpr float  LARVA_BH_ALPHA = 0.05f;   // competition coefficient

// Adult daily mortality — Lardeux thermo-dependent with basal cap.
//   p_d = ADULT_DAILY_MORT_BASAL * exp(-((T - ADULT_OPT_C)^2) / (2 * ADULT_SIGMA^2))
//   clipped to [ADULT_MORT_FLOOR, ADULT_MORT_CAP]
// ADULT_DAILY_MORT_BASAL (default 0.95) is the maximum daily survival at
// the optimal temperature. It accounts for non-thermal mortality sources
// (senescence, predation, accidents) that the Lardeux Gaussian does not
// model. At Ghana June median T=27.5°C: p_d=0.892, mean life 9.3 days,
// matching Saarman 2019 (0.87) and Midega 2007 (0.83-0.95). Previous
// value 0.90 was at the low end of the field MRR range and produced an
// immediate 5-day collapse of the 150-adult point-source; 0.95 delays
// collapse to ~day 30-45 but does not prevent it (the F=0.10 reproduction
// rate cannot sustain 150 adults at p_d=0.892 — see proposal p_7b70cbc1
// and docs/calibration-test-framework.md §6 for the resolution path).
//   - Costantini 1996: 0.80-0.88 (Burkina Faso savanna)
//   - Saarman 2019:    0.87 (West Africa, self-marking)
//   - North 2018:      0.875 (model param)
//   - Midega 2007:     0.83-0.95 (Kenya coast)
// ADULT_OPT_C = 25°C: matches Mordecai 2013 + Lunde 2013 (Bayoh-Mordecai).
// ADULT_SIGMA = 7: broader curve, matches Martens 1997 (West Africa MRR
// at 30-35°C remains survivable).
// ADULT_MORT_CAP = 0.95: empirical upper bound from Midega 2007.
// ADULT_MORT_FLOOR = 0.60: emergency floor for extreme temps.
inline constexpr float  ADULT_DAILY_MORT_BASAL  = 0.93f;
inline constexpr float  ADULT_OPT_C             = 25.0f;
// ADULT_SIGMA = 15: broader curve, matches Martens 1997 (West Africa MRR
// at 30-35°C remains survivable). With sigma=7, survival at 32°C was only
// 57.7% (mean life 2.5 days) — too low for field observations. Sigma=15
// gives p_d=0.852 at 32°C (mean life 6.8 days), matching the "survivable"
// range from Martens 1997 and Costantini 1996.
inline constexpr float  ADULT_SIGMA             = 15.0f;
inline constexpr float  ADULT_MORT_CAP          = 0.93f;
inline constexpr float  ADULT_MORT_FLOOR        = 0.60f;
// Backward-compat alias for existing code that reads ADULT_DAILY_MORT_BASE.
inline constexpr float  ADULT_DAILY_MORT_BASE   = ADULT_DAILY_MORT_BASAL;

// Fallback temperature (deg C) when the env COG returns NaN at a
// cell (e.g. out-of-coverage pixels near the AOI edges, or
// land/water mask that rasterized to NaN). 25 deg C gives a Lardeux
// p_d = exp(-((25-26)^2) / (2*49)) ≈ 0.9898 — a strong survival
// value well above the 0.60 mortality floor, and well above the
// 0.90 fallback that the previous behaviour produced (which crashed
// the population). EIP accumulation also resumes (T > EIP_BASE_C
// so the daily GD is non-zero and larvae mature).
inline constexpr float  ADULT_TEMP_FALLBACK_C  = 25.0f;

// Larva desiccation mortality (Depinay 2004 §3.1).
inline constexpr int    LARVA_DESICCATION_GRACE_DAYS = 5;
inline constexpr float  LARVA_DESICCATION_DAILY_RATE = 0.10f;

// PLUVIAL_POOL dynamic-patch rule (M2 combined, C2):
//   cell (r, c) is a habitat patch today iff
//       TWI(r, c) >  PLUVIAL_POOL_TWI_THRESHOLD
//       water_frac(r, c) > PLUVIAL_POOL_WATER_FRAC_MIN  (strictly > 0)
//       rain_d(r, c) >  PLUVIAL_POOL_RAIN_THRESHOLD_MM
//
// Rationale for 15mm (was 50mm): Ghana's rainy season averages 5-15mm/day,
// so 50mm was almost never reached and the rule rarely activated. 15mm is
// the biological threshold for ephemeral pool formation. Also, daily rain
// >40mm correlates NEGATIVELY with larval density (heavy rain washes larvae
// out of pools), so 50mm was biologically counterproductive as well.
inline constexpr float  PLUVIAL_POOL_RAIN_THRESHOLD_MM = 15.0f;
inline constexpr float  PLUVIAL_POOL_TWI_THRESHOLD  = 8.0f;
inline constexpr float  PLUVIAL_POOL_WATER_FRAC_MIN = 0.0f;  // strictly > 0

// Habitat-engine build-time filter: a gpkg patch is loaded only if
// its TWI exceeds this threshold. TWI is a static terrain signal
// (Topographic Wetness Index, derived from the SRTM DEM) and should
// NOT be a daily dynamic rule. Daily dynamics use water_frac + rain
// (see PLUVIAL_POOL_RAIN_THRESHOLD_MM above).
// Threshold 8.0: standard cut-off for terrain-driven Anopheles
// habitat identification (Aduvukha 2026, Kleinschmidt 2000).
inline constexpr float  HABITAT_MIN_TWI             = 8.0f;

// No-data sentinel for the 2-band state COG.
inline constexpr float  NODATA_SENTINEL             = -9999.0f;

// State COG band identifiers. The 2 bands are (in order):
//   band 1 (STATE_BAND_DENSITY)     — normalised density (count / K_MAX)
//   band 2 (STATE_BAND_SUITABILITY) — per-cell adult density (post-dispersal)
inline constexpr int    STATE_BAND_DENSITY          = 1;
inline constexpr int    STATE_BAND_SUITABILITY      = 2;
inline constexpr const char* STATE_BAND_NAMES[2]     = {"density", "suitability"};

// Contract and generator version strings — written into the sidecar JSON
// and used by the Python parity test (F1.e) to verify engine equivalence.
//
// CONTRACT_VERSION bumped to "1.1" in F1.c with the addition of
// `n_rollouts` and `rollout_index` to the sidecar JSON (see
// output_contract.hpp). F1.e's parity test will need to special-case
// the new keys (it compares everything except the F1.c additions).
inline constexpr const char* CONTRACT_VERSION        = "1.1";
inline constexpr const char* GENERATOR_VERSION       = "m1.5-mesa-frames+polars";

// ---------------------------------------------------------------------------
// Value types — shared across all modules.
// ---------------------------------------------------------------------------

// Area of Interest. Mirrors `mal_commonlib.aoi.AOI` (M1.2a) but in C++:
// the bbox (W, S, E, N) in EPSG:4326 degrees, the CRS string, the slug
// (used in file naming), the ground resolution in metres, and the scale
// level (matches the Python `Scale` enum: "regional" / "national" /
// "continental").
//
// `cells_per_side()` returns the number of cells along the east-west axis
// (the WIDTH of the AOI in cells). The height can be derived
// symmetrically: H = round((north - south) * 111320 / resolution_m).
// The full inline implementation lives in aoi.hpp; the declaration is
// here so wire.hpp remains self-contained for the data types.
struct AOI {
    double  west          = 0.0;
    double  south         = 0.0;
    double  east          = 0.0;
    double  north         = 0.0;
    std::string crs       = "EPSG:4326";
    std::string slug      = "custom";
    int32_t  resolution_m = 1000;
    std::string scale    = "regional";  // matches Scale.REGIONAL.value

    int32_t cells_per_side() const noexcept;

    // Bbox as (W, S, E, N) for GDAL/rasterio interop.
    std::array<double, 4> bbox() const noexcept { return {west, south, east, north}; }
};

// Patch (row, col) state for one day. This is the per-patch record the
// coordinator hands to the MosquitoSubmodel. Mirrors the Polars
// patch_state.PATCH_STATE_SCHEMA in the Python engine.
struct PatchState {
    int64_t patch_id  = 0;
    int32_t row       = 0;
    int32_t col       = 0;
    bool    activated = false;
    float   rain_d    = 0.0f;     // mm, today's daily rainfall at the cell
    float   temp_d    = 25.0f;    // deg C, post Mordecai inverse (EIP uses T)
    float   water_frac = 0.0f;    // [0, 1], open-water fraction in the cell
};

// A single habitat patch loaded from the gpkg. Carries the cell (row, col),
// the carrying capacity K, the (static) TWI value, and a flag for the
// patch subtype. M1 only honours hab_type == "pluvial_pool".
//
// Note: this struct is forward-declared in habitat_engine.hpp; the
// canonical definition lives in wire.hpp to keep all shared data types
// in one place. The .hpp file then reopens the namespace with extra
// members (e.g. lon, lat) and free functions.
struct HabitatPatch {
    int64_t patch_id  = 0;
    int32_t row       = 0;
    int32_t col       = 0;
    int32_t K         = K_MAX;
    float   twi_value = 0.0f;
    double  lon       = 0.0;   // EPSG:4326 deg
    double  lat       = 0.0;   // EPSG:4326 deg
    bool    hab_pluvial_pool = true;
};

// Two-band density grid (mosquitoes / K_MAX, clipped to [0, 1]).
// Row-major float32 layout matching GDAL/rasterio conventions.
struct DensityGrid {
    std::vector<float> data;
    int32_t h = 0;
    int32_t w = 0;
};

// Two-band suitability grid (per-cell adult density / K_MAX, clipped to [0, 1]).
// Row-major float32 layout matching GDAL/rasterio conventions.
struct SuitabilityGrid {
    std::vector<float> data;
    int32_t h = 0;
    int32_t w = 0;
};

// ---------------------------------------------------------------------------
// Inline method definitions
// ---------------------------------------------------------------------------

// AOI::cells_per_side — number of cells along the east-west axis (WIDTH).
// The full derivation lives here (rather than in aoi.hpp) so that every
// translation unit pulling in wire.hpp sees the inline definition and the
// linker does not have to find a separate .cpp definition. aoi.hpp
// contains the related free function `cells_per_side_h` (H dimension).
//
// Parity with the Python reference (mal_commonlib.aoi.AOI.cells_per_side):
//   m_per_deg_lat  = (pi * 6371008.8) / 180.0  (WGS84 mean Earth radius)
//   width_m        = (east - west) * m_per_deg_lat * cos(centroid_lat_rad)
//   cells_per_side = ceil(width_m / resolution_m)  (NOT lround — see parity note)
//
// F1.b parity note: Python's `mal_commonlib.aoi.AOI.cells_per_side` uses
// `math.ceil` (not `round`); we use `std::ceil` to match. For the Ghana
// regional AOI both formulas give 551/779; for AOIs near a cell
// boundary the rounding mode diverges (e.g. width_m = 999.5 m at
// resolution_m = 1000: Python gives 1, lround gives 1, floor gives 0).
inline constexpr double kEarthRadiusM = 6371008.8;  // WGS84 mean
inline constexpr double kMetresPerDegLat = (3.14159265358979323846 * kEarthRadiusM) / 180.0;
inline constexpr double kPi              = 3.14159265358979323846;

inline int32_t AOI::cells_per_side() const noexcept {
    const double centroid_lat_rad = ((north + south) * 0.5) * (kPi / 180.0);
    const double width_m = (east - west) * kMetresPerDegLat * std::cos(centroid_lat_rad);
    const double cells_d = width_m / static_cast<double>(resolution_m);
    int32_t cells = static_cast<int32_t>(std::ceil(cells_d));
    if (cells < 1) cells = 1;
    return cells;
}

}  // namespace mal_abm_fast
