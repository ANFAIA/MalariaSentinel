// SPDX-License-Identifier: MIT
// wire.hpp — single shared header for the C++ ABM engine (M-perf / mal-abm-fast).
//
// This is the canonical "data contract" header. Every module in
// mal-abm-fast includes wire.hpp to pick up:
//   * the model-constant accessors (EIP thresholds, dispersal kernel,
//     birth rate, the no-data sentinel — all read from
//     model_constants.yaml), the state-band names and the contract /
//     generator version strings
//   * the shared value types (AOI, HabitatPatch, PatchState, DensityGrid,
//     SuitabilityGrid)
//
// Historical note: bit-for-bit parity with the retired Python Mesa-Geo
// engine was the constraining invariant until proxy_habitat_v1 removed
// the Python engine (plan docs/plans/in-process/redesign/01-retirada-*.md
// §9). Parity tests compare against the historical baseline outputs.
//
// The wire.hpp header is header-only. The AOI::cells_per_side() method is
// defined in aoi.hpp (separately compiled into the library, although
// header-only is also viable).
#pragma once

#include <array>
#include <cmath>
#include <cstdint>

#include "mal_abm_fast/config.hpp"
#include <string>
#include <vector>

namespace mal_abm_fast {
// Values live in mal-core/config/model_constants.yaml; accessors read the
// load_config() singleton (plan constants-yaml §4 — no compiled defaults).
inline double EIP_BASE_C() { return static_cast<double>(load_config().eip.base_c); }
inline double EIP_THRESHOLD_GD() { return static_cast<double>(load_config().eip.threshold_gd); }
inline double ADULT_DISPERSE_PROB() { return static_cast<double>(load_config().dispersal.adult_prob_day); }
inline double ADULT_DISPERSE_SIGMA_M() { return static_cast<double>(load_config().dispersal.adult_sigma_m); }
inline double ADULT_DISPERSE_MAX_M() { return static_cast<double>(load_config().dispersal.adult_max_m); }
inline double WIND_MIGRATION_PROB() { return static_cast<double>(load_config().dispersal.wind_migration_prob); }
inline double WIND_FLIGHT_HOURS() { return static_cast<double>(load_config().dispersal.wind_flight_hours); }
inline double WIND_SURVIVAL() { return static_cast<double>(load_config().dispersal.wind_survival); }
inline double WIND_FLIGHT_SPEED_MS() { return static_cast<double>(load_config().dispersal.wind_self_speed_ms); }
inline int HOST_SEEKING_STARVATION_DAYS() { return static_cast<int>(load_config().host_seeking.starvation_days); }
inline double OVIPOSITION_SCALE_M() { return static_cast<double>(load_config().oviposition.scale_m); }
inline double OVIPOSITION_SEEKING_TIMEOUT_DAYS() { return static_cast<double>(load_config().oviposition.timeout_days); }
inline double LARVA_BH_S0() { return static_cast<double>(load_config().aquatic_stages.larva_bh_s0); }
inline double LARVA_BH_ALPHA() { return static_cast<double>(load_config().aquatic_stages.larva_bh_alpha); }
inline double ADULT_DAILY_MORT_BASAL() { return static_cast<double>(load_config().adults.daily_mort_basal); }
inline double ADULT_OPT_C() { return static_cast<double>(load_config().adults.opt_c); }
inline double ADULT_SIGMA() { return static_cast<double>(load_config().adults.sigma_c); }
inline double ADULT_MORT_CAP() { return static_cast<double>(load_config().adults.mort_cap); }
inline double ADULT_MORT_FLOOR() { return static_cast<double>(load_config().adults.mort_floor); }
inline double NODATA_SENTINEL() { return static_cast<double>(load_config().ingest.nodata_sentinel); }
inline double kEarthRadiusM() { return static_cast<double>(load_config().geodesy.earth_radius_m); }
inline double kMetresPerDegLat() { return static_cast<double>(load_config().geodesy.metres_per_deg_lat); }
inline std::string CONTRACT_VERSION() { return load_config().contracts.cogs_state; }


// ---------------------------------------------------------------------------
// Constants — match mal_ghana_sim.abm defaults exactly (M1.5 thin slice).
// ---------------------------------------------------------------------------

// K_MAX retired (plan 03-retirada-k-max): the larval capacity is the
// absolute per-cell K_ref × area_km2 × S computed by the coordinator
// (habitat_availability.hpp k_habitat); initial populations are
// explicit adult/immature counts (SeedingConfig), and the state COG
// carries raw per-cell adult counts. No global adult-capacity
// constant exists anymore.

// EIP (extrinsic incubation period) growing-degree-day model.
//   daily_gd       = max(0, T - EIP_BASE_C)
//   infective when eip_progress >= EIP_THRESHOLD_GD

// Adult dispersal kernel: isotropic Gaussian in metres, clipped at
// dispersal.adult_max_m (probabilities and widths come from dispersal.*).

// Windborne long-range migration (M7.6 Phase 1). Parameters come from
// dispersal.wind_* in model_constants.yaml.

// Egg batch size is temperature-scaled at oviposition time via the EFD
// thermal modifier (birth_rate.hpp): the binomial draw of
// GonotrophicParams::egg_batch_n trials uses
// p = (egg_batch_mean / egg_batch_n) × birth_rate_modifier(T),
// with T the same per-patch temp_d that drives adult survival.

// Larva density-dependent mortality (Beverton-Holt, docs/abm-status.md:79).

// Runtime-configurable overrides for dispersal and larval parameters.
// Used by CLI to override wire.hpp defaults for invasion simulations.
struct RuntimeOverrides {
    float disperse_prob    = static_cast<float>(load_config().dispersal.adult_prob_day);
    float disperse_sigma_m = static_cast<float>(load_config().dispersal.adult_sigma_m);
    float disperse_max_m   = static_cast<float>(load_config().dispersal.adult_max_m);
    float larva_bh_alpha   = static_cast<float>(load_config().aquatic_stages.larva_bh_alpha);
};

// Adult daily mortality: thermo-dependent survival with a basal cap
// (values in adults.*; formula in mosquito_submodel.cpp).

// Temperature NaN policy (2026-10-13): the legacy per-lookup temperature
// fallback constant was removed. Out-of-coverage / sea-mask NaN pixels
// in the env NC water_temp_c channel are imputed at load time by
// neighbor-mean wavefront fill (climate.cpp impute_temp_nans) — each
// imputed cell inherits the same day's spatial temperature field, so it
// tracks the seasonal cycle instead of pinning a fixed value year-round
// (the fixed fallback put out-of-place values on coastal/edge cells in
// hot and cold seasons). temp_at() clamps off-grid (row, col) to the
// border cell; the only remaining fallback is a documented
// degenerate-engine guard for an all-NaN slice or an unloaded engine.

// Larva desiccation: grace + daily rate live in aquatic_stress.*
// (see aquatic_stress.hpp).

// proxy_habitat_v1: habitat availability is the static H[i, g] over the
// six habitat types; the biological stress bits (rain wash, desiccation)
// live in aquatic_stress.hpp.

// No-data sentinel for the 2-band state COG.

// State COG band identifiers. Contract 4.0: both bands are RAW
// per-cell adult counts (individuals), NOT normalized by any
// capacity constant (K_MAX retired). In order:
//   band 1 (STATE_BAND_DENSITY)     — adults associated with each cell
//                                     via their patch (post-dispersal)
//   band 2 (STATE_BAND_SUITABILITY) — adults counted at their current
//                                     position (lon/lat snap)
inline constexpr int    STATE_BAND_DENSITY          = 1;
inline constexpr int    STATE_BAND_SUITABILITY      = 2;
inline constexpr const char* STATE_BAND_NAMES[2]     = {"adult_patch_count", "adult_cell_count"};

// Contract and generator version strings — written into the sidecar JSON
// and used by the Python parity test (F1.e) to verify engine equivalence.
//
// CONTRACT_VERSION bumped to "1.1" in F1.c, to "2.0" in M7.1+M7.2,
// to "3.0" with proxy_habitat_v1 (contract docs/plans/in-process/
// redesign/02-oferta-criaderos-proxies-download-ingest-abm.md §5: the
// ingested env NC planes and the habitat gpkg schema changed), and to
// "4.0" with the K_MAX retirement (plan 03-retirada-k-max): the state
// COG bands are raw per-cell adult counts, the sidecar no longer
// carries `k_max`, and the band names changed. Consumers must
// version-gate on the sidecar string.
inline constexpr const char* GENERATOR_VERSION       = "proxy_habitat_v1";

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
// symmetrically: H = round((north - south) * geodesy met/deg / resolution_m).
// The full inline implementation lives in aoi.hpp; the declaration is
// here so wire.hpp remains self-contained for the data types.
struct AOI {
    double  west          = 0.0;
    double  south         = 0.0;
    double  east          = 0.0;
    double  north         = 0.0;
    std::string crs       = "EPSG:4326";
    std::string slug      = "custom";
    int32_t  resolution_m = static_cast<int32_t>(
        load_config().ingest.cell_size_hint_m);
    std::string scale    = "regional";  // matches Scale.REGIONAL.value

    int32_t cells_per_side() const noexcept;

    // Bbox as (W, S, E, N) for GDAL/rasterio interop.
    std::array<double, 4> bbox() const noexcept { return {west, south, east, north}; }
};

// Patch (row, col) state for one day. This is the per-patch record the
// coordinator hands to the MosquitoSubmodel. Mirrors the Polars
// patch_state.PATCH_STATE_SCHEMA in the Python engine.
struct PatchState {
    int64_t patch_id      = 0;
    int32_t row           = 0;
    int32_t col           = 0;
    bool    activated     = false;
    float   rain_d        = 0.0f;     // mm, today's daily rainfall at the cell
    float   temp_d        = 25.0f;    // deg C, post thermal inverse (EIP uses T)
    // proxy_habitat_v1: species-neutral overall availability of the patch
    // today, S(i, t) in [0, 1] (weights + H total + z combined). Replaces
    // the retired water_frac / pool_water_mm signalling.
    float   habitat_avail = 0.0f;
    int     habitat_dry_days = 0;     // consecutive days below habitat.activation_min_engine
    float   k_habitat     = 0.0f;     // daily Beverton-Holt capacity (absolute count)
    float   salinity_ppt  = 0.0f;     // env water salinity (psu); 0 = freshwater
};

// A single habitat patch loaded from the gpkg. Carries the cell (row, col),
// the static potential amplitude (H total in [0, 1]) and the dominant
// habitat type's dynamics label. proxy_habitat_v1 contract (env.py):
//   * patch_id    — row-major WM index for the (row, col); runtime assigned
//   * potential   — H_total = sum_g H[i,g] (attraction amplitude)
//   * hab_col_    — the six per-type H features are carried at the
//                   coordinator level (habitat_features struct), not here.
struct HabitatPatch {
    int64_t patch_id  = 0;
    int32_t row       = 0;
    int32_t col       = 0;
    float   potential = 0.0f;         // H_total in [0, 1]
    double  lon       = 0.0;   // EPSG:4326 deg
    double  lat       = 0.0;   // EPSG:4326 deg
    int     dynamics  = 0;      // 0 = persistent offer, 1 = pluvial offer
                               // (dominant type; diagnostic only)
};

// Two-band adult count grid (raw per-cell adult counts, contract 4.0).
// Row-major float32 layout matching GDAL/rasterio conventions.
struct DensityGrid {
    std::vector<float> data;
    int32_t h = 0;
    int32_t w = 0;
};

// Two-band suitability grid (raw per-cell adult counts at their
// current position, contract 4.0).
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
//   m_per_deg_lat  = π · R / 180 from geodesy.* (WGS84 mean Earth radius)
//   width_m        = (east - west) * m_per_deg_lat * cos(centroid_lat_rad)
//   cells_per_side = ceil(width_m / resolution_m)  (NOT lround — see parity note)
//
// F1.b parity note: Python's `mal_commonlib.aoi.AOI.cells_per_side` uses
// `math.ceil` (not `round`); we use `std::ceil` to match. For the Ghana
// regional AOI both formulas agree; for AOIs near a cell boundary the
// rounding mode diverges.
inline constexpr double kPi              = 3.14159265358979323846;

inline int32_t AOI::cells_per_side() const noexcept {
    const double centroid_lat_rad = ((north + south) * 0.5) * (kPi / 180.0);
    const double width_m = (east - west) * load_config().geodesy.metres_per_deg_lat * std::cos(centroid_lat_rad);
    const double cells_d = width_m / static_cast<double>(resolution_m);
    int32_t cells = static_cast<int32_t>(std::ceil(cells_d));
    if (cells < 1) cells = 1;
    return cells;
}

}  // namespace mal_abm_fast
