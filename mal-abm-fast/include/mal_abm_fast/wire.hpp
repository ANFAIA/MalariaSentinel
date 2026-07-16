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

// Adult dispersal kernel: isotropic Gaussian in metres, clipped at 2 km.
// 20% of adults move per day (An. gambiae rural dispersal).
inline constexpr float  ADULT_DISPERSE_PROB         = 0.20f;
inline constexpr float  ADULT_DISPERSE_SIGMA_M      = 1000.0f;
inline constexpr float  ADULT_DISPERSE_MAX_M        = 2000.0f;

// Per-patch per-day birth rate (binomial(K, BIRTH_RATE) new larvae).
// Tuned so the population stays near the initial seeded count on the
// 30k-patch, 30-day M1.5 perf budget.
inline constexpr float  BIRTH_RATE                  = 0.005f;

// Larva density-dependent mortality (Beverton-Holt, docs/abm-status.md:79).
inline constexpr float  LARVA_BH_S0    = 0.95f;   // baseline daily survival
inline constexpr float  LARVA_BH_ALPHA = 0.05f;   // competition coefficient

// Adult daily mortality — Lardeux thermo-dependent (Lardeux 2009).
// p_d = exp(-((T - OPT_C)^2) / (2 * SIGMA^2))
inline constexpr float  ADULT_DAILY_MORT_BASE = 0.90f;  // fallback if T unavailable
inline constexpr float  ADULT_OPT_C           = 26.0f;  // optimal temperature
inline constexpr float  ADULT_SIGMA           = 7.0f;   // width of thermal response

// Larva desiccation mortality (Depinay 2004 §3.1).
inline constexpr int    LARVA_DESICCATION_GRACE_DAYS = 2;
inline constexpr float  LARVA_DESICCATION_DAILY_RATE = 0.30f;

// PLUVIAL_POOL dynamic-patch rule (M2 combined, C2):
//   cell (r, c) is a habitat patch today iff
//       TWI(r, c) >  PLUVIAL_POOL_TWI_THRESHOLD
//       water_frac(r, c) > PLUVIAL_POOL_WATER_FRAC_MIN  (strictly > 0)
//       rain_d(r, c) >  PLUVIAL_POOL_RAIN_THRESHOLD_MM
inline constexpr float  PLUVIAL_POOL_RAIN_THRESHOLD_MM = 15.0f;
inline constexpr float  PLUVIAL_POOL_TWI_THRESHOLD  = 8.0f;
inline constexpr float  PLUVIAL_POOL_WATER_FRAC_MIN = 0.0f;  // strictly > 0

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
