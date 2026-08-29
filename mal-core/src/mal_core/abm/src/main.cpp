// SPDX-License-Identifier: MIT
// main.cpp — mal_abm_fast CLI (M-perf / F1.b / F1.c / F1.d thin-slice ABM).
//
// Mirrors `python -m mal_ghana_sim.abm.run`. The CLI takes an AOI (or
// custom bbox), loads the 4-band env COG and the habitat patches gpkg,
// runs the Engine for `--days` days, and writes the 2-band state COG
// and sidecar JSON via `Engine::snapshot()`.
//
// F1.c: with `--n-rollouts N`, the engine is rebuilt N times in this
// process, each with a fresh `Prng` instance seeded at
// `seed_rollout = --seed + i`. Each rollout writes its own
// `state_seed{NNNN}.tif` + `.json` sidecar (the N is the number of
// rollouts, NNNN is the 0-indexed rollout id zero-padded to 4
// digits). The legacy single-rollout invocation (no `--n-rollouts`
// flag) is unchanged: it produces `state.tif` + `state.json` (the
// file name is taken verbatim from `--output`).
//
// Usage:
//   mal_abm_fast run \
//     --aoi ghana --year 2024 --month 6 --seed 1 --days 30 \
//     --env    data/runs/ghana/ghana_regional_2024_06_env.tif \
//     --habitat data/runs/ghana/ghana_regional_2024_06_habitat_patches.gpkg \
//     --output data/runs/ghana/ghana_regional_2024_06_seed0001.tif
//
// F1.c multi-rollout:
//   mal_abm_fast run --n-rollouts 3 \
//     --aoi ghana --year 2024 --month 6 --seed 1 --days 30 \
//     --env    data/runs/ghana/ghana_regional_2024_06_env.tif \
//     --habitat data/runs/ghana/ghana_regional_2024_06_habitat_patches.gpkg \
//     --output /tmp/rollout/state.tif
//   -> /tmp/rollout/state_seed0000.tif
//      /tmp/rollout/state_seed0001.tif
//      /tmp/rollout/state_seed0002.tif
//      (plus the .json sidecars)
#include <cstdio>
#include <cstdlib>
#include <exception>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>

#include <CLI/CLI.hpp>
#include <omp.h>

#include "engine.hpp"
#include "prng.hpp"
#include "seeding.hpp"
#include "wire.hpp"
#include "transmission.hpp"
#include "transmission_output.hpp"

namespace {

// Minimal in-repo slug registry (mirrors scripts/build_env.py and
// `mal_ghana_sim.abm.run._DEFAULT_REGISTRY`). Only "ghana" is
// registered; custom bboxes use --bbox "W,S,E,N".
mal_abm_fast::AOI resolve_aoi(const std::string& aoi_slug,
                              const std::string& bbox_str,
                              const std::string& crs,
                              int resolution_m,
                              const std::string& scale) {
    mal_abm_fast::AOI aoi;
    if (!bbox_str.empty()) {
        // Parse "W,S,E,N" — sscanf handles the float conversion.
        const int n = std::sscanf(
            bbox_str.c_str(), "%lf,%lf,%lf,%lf",
            &aoi.west, &aoi.south, &aoi.east, &aoi.north);
        if (n != 4) {
            throw CLI::ValidationError(
                "--bbox must be 4 floats 'W,S,E,N'");
        }
        aoi.slug = aoi_slug.empty() ? "custom" : aoi_slug;
    } else if (aoi_slug == "ghana") {
        aoi = mal_abm_fast::AOI{-3.5, 4.5, 1.5, 11.5, "EPSG:4326", "ghana", 1000, "regional"};
    } else if (!aoi_slug.empty()) {
        throw CLI::ValidationError(
            "unknown --aoi slug '" + aoi_slug +
            "'; use --bbox for a custom region");
    } else {
        throw CLI::ValidationError(
            "either --aoi or --bbox is required");
    }
    aoi.crs          = crs;
    aoi.resolution_m = resolution_m;
    aoi.scale        = scale;
    return aoi;
}

// F1.c: build the per-rollout output path. The base `output_path`
// is the user-supplied `--output` value (e.g. `state.tif` or
// `/tmp/rollout/state.tif`). The rollout's filename replaces the
// leaf with `state_seed{NNNN}.tif` where NNNN is the 0-indexed
// rollout id zero-padded to 4 digits.
//
// If `rollout_index == 0 && n_rollouts == 1` (the legacy single
// rollout case), the file name is returned verbatim. This keeps
// the F1.b CLI output identical: a single-rollout invocation with
// `--output state.tif` writes `state.tif`, not
// `state_seed0000.tif`. The v1.1 sidecar will still carry
// `n_rollouts=1` and `rollout_index=0` so downstream consumers
// can detect the new fields.
//
// Path safety: this function rejects (a) empty paths, (b) paths
// with a trailing separator (the user probably meant a directory
// not a file), and (c) paths whose parent contains `..` traversal
// segments. It does NOT enforce that the path is within the
// current working directory (callers are allowed to write to
// absolute paths like /tmp/foo.tif). The point is to catch
// obvious footguns, not to be a general sandbox.
std::string rollout_output_path(const std::string& output_path,
                                int rollout_index,
                                int n_rollouts) {
    if (output_path.empty()) {
        throw std::runtime_error(
            "rollout_output_path: --output is empty");
    }
    const std::filesystem::path p(output_path);
    if (p.has_parent_path()) {
        for (const auto& seg : p.parent_path()) {
            if (seg == "..") {
                throw std::runtime_error(
                    "rollout_output_path: --output contains '..' "
                    "traversal segment: " + output_path);
            }
        }
    }
    if (n_rollouts == 1 && rollout_index == 0) {
        return output_path;
    }
    const std::filesystem::path parent = p.has_parent_path()
        ? p.parent_path() : std::filesystem::path{};
    const std::string stem = p.stem().string();
    const std::string ext  = p.has_extension() ? p.extension().string() : ".tif";
    std::ostringstream name;
    name << stem << "_seed" << std::setw(4) << std::setfill('0')
         << rollout_index << ext;
    return (parent / name.str()).string();
}

// Build the per-day intermediate snapshot path.
// Given output_path = "/tmp/rollout/state.tif" and day=5,
// returns "/tmp/rollout/state_day005.tif"
//
// If the output path doesn't end in .tif, append ".tif".
std::string rollout_day_path(const std::string& output_path, int day) {
    if (output_path.empty()) {
        throw std::runtime_error("rollout_day_path: output path is empty");
    }
    const std::filesystem::path p(output_path);
    const std::filesystem::path parent = p.has_parent_path()
        ? p.parent_path() : std::filesystem::path{};
    std::string stem = p.stem().string();
    std::string ext = p.has_extension() ? p.extension().string() : ".tif";
    std::ostringstream name;
    name << stem << "_day" << std::setw(3) << std::setfill('0') << day << ext;
    return (parent / name.str()).string();
}

// Build the per-rollout transmission output path.
std::string rollout_transmission_output_path(const std::string& output_path,
                                            int rollout_index,
                                            int n_rollouts) {
    if (output_path.empty()) {
        throw std::runtime_error("rollout_transmission_output_path: output path is empty");
    }
    const std::filesystem::path p(output_path);
    const std::filesystem::path parent = p.has_parent_path()
        ? p.parent_path() : std::filesystem::path{};
    std::string stem = p.stem().string();
    const std::string ext = p.has_extension() ? p.extension().string() : ".tif";

    const size_t state_pos = stem.find("state");
    if (state_pos != std::string::npos) {
        stem.replace(state_pos, 5, "transmission");
    } else {
        stem += "_transmission";
    }

    std::ostringstream name;
    if (n_rollouts == 1 && rollout_index == 0) {
        name << stem << ext;
    } else {
        name << stem << "_seed" << std::setw(4) << std::setfill('0')
             << rollout_index << ext;
    }
    return (parent / name.str()).string();
}

// Build the per-day intermediate transmission snapshot path.
std::string rollout_transmission_day_path(const std::string& rollout_trans_path, int day) {
    if (rollout_trans_path.empty()) {
        throw std::runtime_error("rollout_transmission_day_path: path is empty");
    }
    const std::filesystem::path p(rollout_trans_path);
    const std::filesystem::path parent = p.has_parent_path()
        ? p.parent_path() : std::filesystem::path{};
    std::string stem = p.stem().string();
    const std::string ext = p.has_extension() ? p.extension().string() : ".tif";
    std::ostringstream name;
    name << stem << "_day" << std::setw(3) << std::setfill('0') << day << ext;
    return (parent / name.str()).string();
}

// Parse a "lat1,lon1;lat2,lon2;..." string into a list of
// DetectionPoint. The default per-point adult / larva counts are
// taken from the supplied SeedingConfig so the user can override
// them on a per-point basis in a future version (today the
// per-point fields are ignored — see the implementation).
std::vector<mal_abm_fast::DetectionPoint> parse_detection_points(
    const std::string& csv_str) {
    std::vector<mal_abm_fast::DetectionPoint> out;
    if (csv_str.empty()) return out;
    std::stringstream ss(csv_str);
    std::string pair_str;
    while (std::getline(ss, pair_str, ';')) {
        if (pair_str.empty()) continue;
        // Allow either "lat,lon" or "lon,lat" via the
        // --detection-points-fmt flag (default: "lat,lon").
        // For now we only support the documented "lat,lon" form.
        double lat = 0.0, lon = 0.0;
        const int n = std::sscanf(pair_str.c_str(), "%lf,%lf", &lat, &lon);
        if (n != 2) {
            throw CLI::ValidationError(
                "--detection-points: each point must be 'lat,lon' "
                "(got '" + pair_str + "')");
        }
        mal_abm_fast::DetectionPoint dp;
        dp.lat = lat;
        dp.lon = lon;
        dp.n_adults = 50;  // overwritten by SeedingConfig defaults below
        dp.n_larvae = 30;
        out.push_back(dp);
    }
    return out;
}

}  // namespace

int main(int argc, char** argv) {
    CLI::App app;
    app.description(R"mal(
mal_abm_fast — Mosquito ABM for malaria transmission modelling

An agent-based model (ABM) simulating Anopheles gambiae population dynamics,
dispersal, and transmission potential. The engine is written in C++20 with
OpenMP parallelism for multi-rollout execution.

ARCHITECTURE
  Engine
    ├── ClimateEngine      — daily temperature, rainfall, water_frac grids
    ├── HabitatEngine      — static habitat patches (gpkg) with K, TWI
    ├── HostLandscape       — human/livestock density grids (optional)
    ├── MobilitySchedule   — OD matrices for human/livestock movement
    ├── CoordinatorModel   — patch activation, state aggregation
    └── MosquitoSubmodel   — population lifecycle
          ├── AquaticCohortBank  — egg → larva → pupa development
          ├── GonotrophicCycle   — female biting/oviposition state machine
          ├── HostSeekingModel   — spatial host attraction (optional)
          └── MosquitoSoA       — 17 parallel vectors (SoA layout)

DAILY SIMULATION LOOP (Engine::step)
  1. coord_->set_climate_day(day)      — select today's climate slice
  2. coord_->activate_patches()        — enable patches by rain/temp thresholds
  3. coord_->to_dataframe()            — build PatchState vector (pre-existing
                                        + dynamic pluvial pool cells)
  4. sub_->advance_day()               — the 5-step mosquito lifecycle:
       a. AquaticCohortBank::advance_day()
          — thermal development (Briere-1 / Quadratic per stage)
          — Beverton-Holt density-dependent larval mortality
          — desiccation on inactive patches (grace + daily rate)
          — stage promotion: EGG→L1→L2→L3→L4→Pupa
       b. collect_emergence()          — pupa → new adults (TENERAL)
       c. Gonotrophic cycle (females)
          — TENERAL → HOST_SEEKING → BLOOD_FEED → GRAVID → OVIPOSITING
          — host-seeking via HostSeekingModel (if --hosts provided)
       d. adult_dispersal()            — clipped Gaussian kernel
       e. adult_mortality()            — Lardeux thermo-dependent model
  5. divergence check                  — population bounds
  6. advance date by 1 day

OUTPUT
  State COG (.tif): 2 bands
    Band 1 — adult_occupancy (post-dispersal density / K_MAX)
    Band 2 — host_seeking_pressure (female biting pressure / K_MAX)
  Sidecar JSON: metadata, rollout info, contract version
)mal");
    app.set_version_flag("--version", "0.1.0");

    // --run subcommand
    auto* run = app.add_subcommand("run", "Run the ABM simulation");

    std::string aoi_slug;
    std::string bbox_str;
    std::string crs         = "EPSG:4326";
    int         resolution_m = 1000;
    std::string scale_str   = "regional";
    int         year        = 2024;
    int         month       = 6;
    int         seed        = 1;
    int         days        = 30;
    int         n_rollouts  = 1;
    int         snapshot_every = 0;
    int64_t     max_population = 0;
    int         threads = 0;
    std::string env_path;
    std::string habitat_path;
    std::string output_path;

    std::string seeding_mode = "random-viable";
    double      detection_radius_km = 5.0;
    int         n_detections = 3;
    int         n_adults_per_detection = 50;
    int         n_larvae_per_detection = 30;
    std::string detection_points_str;
    float       init_frac = 0.30f;               // UNIFORM mode
    double      host_seeding_radius_km = 5.0;    // HOST_WEIGHTED mode

    // Host data (optional; if not provided, no host-seeking).
    std::string hosts_path;
    std::string human_mobility_day_path;
    std::string human_mobility_night_path;
    std::string livestock_mobility_path;

    // Wind field (optional; M7.6 windborne migration).
    std::string wind_field_path;

    // Runtime overrides for dispersal and larval parameters.
    float disperse_prob    = mal_abm_fast::ADULT_DISPERSE_PROB;
    float disperse_sigma_m = mal_abm_fast::ADULT_DISPERSE_SIGMA_M;
    float disperse_max_m   = mal_abm_fast::ADULT_DISPERSE_MAX_M;
    float larva_bh_alpha   = mal_abm_fast::LARVA_BH_ALPHA;
    float birth_fecundity  = mal_abm_fast::BIRTH_FECUNDITY;

    bool debug_population = false;
    std::string cohort_log_path;

    // Transmission (M7.4/M7.4.1 SEIR-SEI).
    bool   enable_transmission          = false;
    float  beta_hv                      = 0.40f;
    float  beta_vh                      = 0.50f;
    int    human_incubation_days        = 12;
    int    human_infectious_days        = 20;
    int    immunity_duration_days       = 180;
    bool   enable_immunity              = false;
    double initial_human_prevalence     = 0.05;
    double initial_vector_infected_frac = 0.0;
    std::string human_seeding_mode      = "random-viable";
    int    human_outbreak_day           = 0;
    int    human_outbreak_foci          = 3;
    double human_outbreak_cases         = 50.0;
    double human_min_cell_pop           = 50.0;
    std::string human_foci_coords       = "";
    float  transmission_focus_threshold = 0.01f;
    int    transmission_snapshot_every  = 0;
    std::string transmission_log_path;

    // ─── Spatial & Temporal ──────────────────────────────────────────────
    run->add_option("--aoi", aoi_slug,
                    "Area of Interest slug. Built-in: 'ghana'. "
                    "Use --bbox for custom regions.")
        ->group("Spatial & Temporal");
    run->add_option("--bbox", bbox_str,
                    "Custom bounding box 'W,S,E,N' in EPSG:4326 degrees. "
                    "Overrides --aoi. Example: '-3.5,4.5,1.5,11.5'")
        ->group("Spatial & Temporal");
    run->add_option("--crs", crs,
                    "Coordinate Reference System (default 'EPSG:4326').")
        ->group("Spatial & Temporal");
    run->add_option("--resolution-m", resolution_m,
                    "Ground cell resolution in metres (default 1000). "
                    "Controls patch density: smaller = more patches.")
        ->group("Spatial & Temporal");
    run->add_option("--scale", scale_str,
                    "AOI scale: 'regional' | 'national' | 'continental'.")
        ->group("Spatial & Temporal");
    run->add_option("--year", year, "Start year (1st day of run).")
        ->required()
        ->group("Spatial & Temporal");
    run->add_option("--month", month, "Start month (1..12).")
        ->required()
        ->check(CLI::Range(1, 12))
        ->group("Spatial & Temporal");
    run->add_option("--seed", seed, "RNG seed (default 1). "
                    "Each rollout gets seed+i.")
        ->default_val(1)
        ->group("Spatial & Temporal");
    run->add_option("--days", days, "One continuous simulation (1..731 days; 2024+2025 = 731).")
        ->default_val(30)
        ->check(CLI::Range(1, 731))
        ->group("Spatial & Temporal");
    run->add_option("--n-rollouts", n_rollouts,
                    "Parallel rollouts (1+). Each gets fresh PRNG seeded "
                    "at seed+i; outputs: <stem>_seed{NNNN}.tif.")
        ->default_val(1)
        ->check(CLI::PositiveNumber)
        ->group("Spatial & Temporal");
    run->add_option("--threads", threads,
                    "OpenMP threads for parallel rollouts (0=auto).")
        ->default_val(0)
        ->check(CLI::NonNegativeNumber)
        ->group("Spatial & Temporal");

    // ─── Input Data ──────────────────────────────────────────────────────
    run->add_option("--env", env_path,
                    "Climate raster: GeoTIFF (.tif) or NetCDF (.nc). "
                    "4-band: temperature, rainfall, water_frac, ndvi/twi.")
        ->required()
        ->group("Input Data");
    run->add_option("--habitat", habitat_path,
                    "Habitat patches GeoPackage (.gpkg). Each feature: "
                    "row, col, K (carrying capacity), TWI.")
        ->required()
        ->check(CLI::ExistingFile)
        ->group("Input Data");
    run->add_option("--output", output_path,
                    "Output state COG path (.tif). When --n-rollouts > 1, "
                    "leaf is rewritten to <stem>_seed{NNNN}.tif.")
        ->required()
        ->group("Input Data");
    run->add_option("--hosts", hosts_path,
                    "Host density grid (.nc). Enables host-seeking model "
                    "with human/cattle/goat/sheep/wildlife density per cell.")
        ->group("Input Data");
    run->add_option("--human-mobility-day", human_mobility_day_path,
                    "Human mobility OD matrix — daytime (.csr). "
                    "Sparse OD: P(origin→dest) × host_density.")
        ->group("Input Data");
    run->add_option("--human-mobility-night", human_mobility_night_path,
                    "Human mobility OD matrix — nighttime (.csr).")
        ->group("Input Data");
    run->add_option("--livestock-mobility", livestock_mobility_path,
                    "Livestock mobility OD matrix — seasonal (.csr).")
        ->group("Input Data");
    run->add_option("--wind-field", wind_field_path,
                    "ERA5 6-hourly wind field NetCDF (u100, v100). Enables "
                    "windborne long-range migration with night-only flight "
                    "(18-06h) during monsoon/Harmattan season (M7.6).")
        ->group("Input Data");

    // ─── Seeding ─────────────────────────────────────────────────────────
    run->add_option("--seeding-mode", seeding_mode,
                    "Population initialisation mode:\n"
                    "  random-viable (default) — N random viable patches, "
                    "each seeded with adults + larvae\n"
                    "  uniform — init_frac of K in every patch\n"
                    "  explicit — user lat/lon points snapped to nearest "
                    "habitat patch\n"
                    "  host-weighted — N viable patches sampled in "
                    "proportion to nearby host abundance weighted by the "
                    "species' host preferences (requires --hosts)")
        ->default_val("random-viable")
        ->group("Seeding");
    run->add_option("--init-frac", init_frac,
                    "UNIFORM mode: fraction of K seeded in every patch "
                    "(legacy constant was 0.30). Higher values shorten the "
                    "vector population warm-up but do not change the "
                    "carrying-capacity equilibrium.")
        ->default_val(0.30f)
        ->check(CLI::Bound(0.0f, 1.0f))
        ->group("Seeding");
    run->add_option("--host-seeding-radius-km", host_seeding_radius_km,
                    "HOST_WEIGHTED mode: search radius (km) around each "
                    "viable patch for host cells when computing its seed "
                    "weight.")
        ->default_val(5.0)
        ->check(CLI::PositiveNumber)
        ->group("Seeding");
    run->add_option("--detection-radius-km", detection_radius_km,
                    "Max snap distance (km) from explicit point to "
                    "nearest patch. EXPLICIT mode only.")
        ->default_val(5.0)
        ->check(CLI::PositiveNumber)
        ->group("Seeding");
    run->add_option("--n-detections", n_detections,
                    "Number of random viable patches to seed. "
                    "RANDOM_VIABLE mode only.")
        ->default_val(3)
        ->check(CLI::NonNegativeNumber)
        ->group("Seeding");
    run->add_option("--n-adults-per-detection", n_adults_per_detection,
                    "Adult mosquitoes per detection point. "
                    "RANDOM_VIABLE / EXPLICIT modes.")
        ->default_val(50)
        ->check(CLI::NonNegativeNumber)
        ->group("Seeding");
    run->add_option("--n-larvae-per-detection", n_larvae_per_detection,
                    "Larvae per detection point. "
                    "RANDOM_VIABLE / EXPLICIT modes.")
        ->default_val(30)
        ->check(CLI::NonNegativeNumber)
        ->group("Seeding");
    run->add_option("--detection-points", detection_points_str,
                    "Explicit detection points: 'lat,lon;lat,lon;...'. "
                    "Example: '5.6,-0.2;9.4,-0.8'. EXPLICIT mode only.")
        ->group("Seeding");

    // ─── Population Dynamics ─────────────────────────────────────────────
    run->add_option("--disperse-prob", disperse_prob,
                    "Adult dispersal probability per day (default 0.05). "
                    "Fraction of adults that attempt to move each day.")
        ->default_val(mal_abm_fast::ADULT_DISPERSE_PROB)
        ->group("Population Dynamics");
    run->add_option("--disperse-sigma-m", disperse_sigma_m,
                    "Dispersal kernel sigma in metres (default 450). "
                    "Gaussian width; controls neighbourhood movement.")
        ->default_val(mal_abm_fast::ADULT_DISPERSE_SIGMA_M)
        ->group("Population Dynamics");
    run->add_option("--disperse-max-m", disperse_max_m,
                    "Max dispersal distance in metres (default 2000). "
                    "Hard cap on kernel; rare long-distance colonisation.")
        ->default_val(mal_abm_fast::ADULT_DISPERSE_MAX_M)
        ->group("Population Dynamics");
    run->add_option("--birth-fecundity", birth_fecundity,
                    "Per-adult per-day fecundity (default 0.25). "
                    "n_eggs = binomial(n_females, fecundity). "
                    "Lower = slower population growth.")
        ->default_val(mal_abm_fast::BIRTH_FECUNDITY)
        ->group("Population Dynamics");
    run->add_option("--larva-bh-alpha", larva_bh_alpha,
                    "Beverton-Holt competition coefficient (default 0.05). "
                    "Controls density-dependent larval mortality: "
                    "survival = S0 / (1 + alpha * N_larvae / K). "
                    "Higher = stronger competition at high density.")
        ->default_val(mal_abm_fast::LARVA_BH_ALPHA)
        ->group("Population Dynamics");

    // ─── Output & Debug ──────────────────────────────────────────────────
    run->add_option("--snapshot-every", snapshot_every,
                    "Intermediate snapshot interval in days (0 = final "
                    "only). Intermediate files: <stem>_dayNNN.tif.")
        ->default_val(0)
        ->check(CLI::NonNegativeNumber)
        ->group("Output & Debug");
    run->add_option("--max-population", max_population,
                    "Population divergence threshold (0 = auto: "
                    "n_patches × K_MAX × 10). Aborts if exceeded.")
        ->default_val(0)
        ->check(CLI::NonNegativeNumber)
        ->group("Output & Debug");
    run->add_flag("--debug-population", debug_population,
                  "Stderr diagnostics: daily n_alive, n_adults, n_larvae, "
                  "Lardeux p_d, births/deaths/maturation. "
                  "Rate-limited: daily for first 10 days, then every 5.")
        ->group("Output & Debug");
    run->add_option("--emit-cohort-log", cohort_log_path,
                    "Path for daily cohort log JSON. Fields: day, n_alive, "
                    "n_adults, n_larvae, n_births, n_deaths, n_maturation, "
                    "eip_frac.")
        ->default_val("")
        ->group("Output & Debug");

    // ─── Transmission (SEIR-SEI) ─────────────────────────────────────────
    run->add_flag("--enable-transmission", enable_transmission,
                  "Enable spatial SEIR-SEI malaria transmission model.")
        ->group("Transmission (SEIR-SEI)");
    run->add_option("--beta-hv", beta_hv,
                    "Human-to-vector transmission probability per bite (default 0.40).")
        ->default_val(0.40f)
        ->group("Transmission (SEIR-SEI)");
    run->add_option("--beta-vh", beta_vh,
                    "Vector-to-human transmission probability per bite (default 0.50).")
        ->default_val(0.50f)
        ->group("Transmission (SEIR-SEI)");
    run->add_option("--human-incubation-days", human_incubation_days,
                    "Human intrinsic incubation period E_H -> I_H in days (default 12).")
        ->default_val(12)
        ->check(CLI::PositiveNumber)
        ->group("Transmission (SEIR-SEI)");
    run->add_option("--human-infectious-days", human_infectious_days,
                    "Human infectious duration I_H in days (default 20).")
        ->default_val(20)
        ->check(CLI::PositiveNumber)
        ->group("Transmission (SEIR-SEI)");
    run->add_option("--immunity-duration-days", immunity_duration_days,
                    "Duration of temporary human immunity R_H in days (default 180).")
        ->default_val(180)
        ->check(CLI::PositiveNumber)
        ->group("Transmission (SEIR-SEI)");
    run->add_flag("--enable-immunity", enable_immunity,
                  "Enable temporary human immunity (R_H -> S_H waning). Default false (SIS-like).")
        ->group("Transmission (SEIR-SEI)");
    run->add_option("--initial-human-prevalence", initial_human_prevalence,
                    "Initial infectious fraction of human population (default 0.05).")
        ->default_val(0.05)
        ->group("Transmission (SEIR-SEI)");
    run->add_option("--human-seeding-mode", human_seeding_mode,
                    "Human infection seeding mode: 'random-viable' | 'explicit' | 'uniform-legacy' | 'none' (default 'random-viable').")
        ->default_val("random-viable")
        ->group("Transmission (SEIR-SEI)");
    run->add_option("--human-outbreak-day", human_outbreak_day,
                    "Day of simulation to trigger human outbreak (default 0).")
        ->default_val(0)
        ->group("Transmission (SEIR-SEI)");
    run->add_option("--human-outbreak-foci", human_outbreak_foci,
                    "Number of random foci for human outbreak (default 3).")
        ->default_val(3)
        ->group("Transmission (SEIR-SEI)");
    run->add_option("--human-outbreak-cases", human_outbreak_cases,
                    "Infectious human cases seeded per focus (default 50.0).")
        ->default_val(50.0)
        ->group("Transmission (SEIR-SEI)");
    run->add_option("--human-min-cell-pop", human_min_cell_pop,
                    "Minimum cell population to qualify as candidate focus (default 50.0).")
        ->default_val(50.0)
        ->group("Transmission (SEIR-SEI)");
    run->add_option("--human-foci-coords", human_foci_coords,
                    "Explicit foci coordinates 'r1,c1:N1;r2,c2:N2' for explicit mode.")
        ->default_val("")
        ->group("Transmission (SEIR-SEI)");
    run->add_option("--initial-vector-infected-frac", initial_vector_infected_frac,
                    "Initial infectious fraction of adult female mosquitoes (default 0.0).")
        ->default_val(0.0)
        ->group("Transmission (SEIR-SEI)");
    run->add_option("--transmission-focus-threshold", transmission_focus_threshold,
                    "Prevalence threshold for active transmission focus band (default 0.01).")
        ->default_val(0.01f)
        ->group("Transmission (SEIR-SEI)");
    run->add_option("--transmission-snapshot-every", transmission_snapshot_every,
                    "Intermediate transmission snapshot interval in days (0 = matches --snapshot-every).")
        ->default_val(0)
        ->group("Transmission (SEIR-SEI)");
    run->add_option("--emit-transmission-log", transmission_log_path,
                    "Path for daily transmission log JSON.")
        ->default_val("")
        ->group("Transmission (SEIR-SEI)");

    CLI11_PARSE(app, argc, argv);

    // If no subcommand was given, print help and exit.
    if (!run->parsed()) {
        std::cout << app.help();
        return EXIT_SUCCESS;
    }

    // -- Seeding config: parse --seeding-mode into a SeedingConfig ---
    mal_abm_fast::SeedingConfig seeding_config;
    if (seeding_mode == "uniform") {
        seeding_config.mode = mal_abm_fast::SeedingMode::UNIFORM;
    } else if (seeding_mode == "random-viable") {
        seeding_config.mode = mal_abm_fast::SeedingMode::RANDOM_VIABLE;
    } else if (seeding_mode == "explicit") {
        seeding_config.mode = mal_abm_fast::SeedingMode::EXPLICIT;
        try {
            seeding_config.detections =
                parse_detection_points(detection_points_str);
        } catch (const CLI::ValidationError& e) {
            std::cerr << "abm_run: " << e.what() << "\n";
            return EXIT_FAILURE;
        }
        if (seeding_config.detections.empty()) {
            std::cerr << "abm_run: --seeding-mode=explicit requires "
                         "at least one point in --detection-points\n";
            return EXIT_FAILURE;
        }
    } else if (seeding_mode == "host-weighted") {
        seeding_config.mode = mal_abm_fast::SeedingMode::HOST_WEIGHTED;
    } else {
        std::cerr << "abm_run: unknown --seeding-mode '" << seeding_mode
                  << "' (expected 'random-viable', 'uniform', "
                      "'explicit', or 'host-weighted')\n";
        return EXIT_FAILURE;
    }
    seeding_config.detection_radius_km  = detection_radius_km;
    seeding_config.n_detections         = n_detections;
    seeding_config.n_adults_per_detection = n_adults_per_detection;
    seeding_config.n_larvae_per_detection = n_larvae_per_detection;
    seeding_config.init_frac            = init_frac;
    seeding_config.host_weight_radius_km = host_seeding_radius_km;

    // -- Runtime overrides for dispersal / larval parameters -----------
    mal_abm_fast::RuntimeOverrides overrides;
    overrides.disperse_prob    = disperse_prob;
    overrides.disperse_sigma_m = disperse_sigma_m;
    overrides.disperse_max_m   = disperse_max_m;
    overrides.larva_bh_alpha   = larva_bh_alpha;
    overrides.birth_fecundity  = birth_fecundity;

    // -- AOI resolution ------------------------------------------------
    mal_abm_fast::AOI aoi;
    try {
        aoi = resolve_aoi(aoi_slug, bbox_str, crs, resolution_m, scale_str);
    } catch (const CLI::ValidationError& e) {
        std::cerr << "abm_run: " << e.what() << "\n";
        return EXIT_FAILURE;
    }

    // -- start_date: 1st of (year, month) ------------------------------
    // std::chrono::year/month/day are C++20. If a non-valid date is
    // given (e.g. month=13 from the caller side-stepping CLI11's
    // check), the sys_days construction throws.
    std::chrono::sys_days start_date;
    try {
        start_date = std::chrono::sys_days{
            std::chrono::year{year} /
            std::chrono::month{static_cast<unsigned>(month)} /
            std::chrono::day{1}
        };
    } catch (const std::exception& e) {
        std::cerr << "abm_run: invalid year/month: " << e.what() << "\n";
        return EXIT_FAILURE;
    }

    // -- Shared ClimateEngine (memory optimization) ----------------------
    // Load climate data once and share across all rollouts.
    // This reduces memory from O(n_rollouts * n_days * grid_size) to O(n_days * grid_size).
    auto shared_climate = std::make_shared<mal_abm_fast::ClimateEngine>();
    try {
        const bool is_nc = env_path.size() >= 3
            && env_path.substr(env_path.size() - 3) == ".nc";
        if (is_nc) {
            shared_climate->load_from_env_nc(env_path, aoi, days);
            if (days > 0 && shared_climate->n_days() < days) {
                throw std::runtime_error(
                    "env NC file has " + std::to_string(shared_climate->n_days())
                    + " days but simulation requests " + std::to_string(days) + " days");
            }
        } else {
            shared_climate->load_from_env_tif(env_path, aoi);
        }
        std::cout << "abm_run: loaded climate data (" << shared_climate->n_days() 
                  << " days, " << shared_climate->h() << "x" << shared_climate->w() 
                  << " grid)\n";
    } catch (const std::exception& e) {
        std::cerr << "abm_run: ClimateEngine load failed: " << e.what() << "\n";
        return EXIT_FAILURE;
    }

    // -- Transmission config (M7.4/M7.4.1) ---------------------------
    mal_abm_fast::TransmissionParams transmission_params;
    transmission_params.enabled = enable_transmission;
    transmission_params.beta_hv = beta_hv;
    transmission_params.beta_vh = beta_vh;
    transmission_params.human_incubation_days = human_incubation_days;
    transmission_params.human_infectious_days = human_infectious_days;
    transmission_params.immunity_duration_days = immunity_duration_days;
    transmission_params.immunity_enabled = enable_immunity;
    if (!enable_immunity) {
        std::cerr << "abm_run: NOTE --enable-immunity not set: humans "
                     "recover I_H -> S_H directly (SIS); R_H stays 0 and "
                     "--immunity-duration-days is ignored.\n";
    }
    transmission_params.initial_human_prevalence = initial_human_prevalence;
    transmission_params.initial_vector_infected_frac = initial_vector_infected_frac;
    transmission_params.human_seeding_mode = human_seeding_mode;
    transmission_params.human_outbreak_day = human_outbreak_day;
    transmission_params.human_outbreak_foci = human_outbreak_foci;
    transmission_params.human_outbreak_cases = human_outbreak_cases;
    transmission_params.human_min_cell_pop = human_min_cell_pop;
    transmission_params.human_foci_coords = human_foci_coords;
    transmission_params.focus_threshold = transmission_focus_threshold;

    // -- Rollouts loop (F1.c) -------------------------------------------
    // Each rollout gets a fresh `Prng` instance seeded at
    // `seed_rollout = seed + i`. A new `Engine` is built per rollout
    // (the Engine derives its own sub-stream seeds from the master
    // Prng, then discards it). The Engine and the master Prng go
    // out of scope at the end of each iteration, so no Prng state
    // leaks across rollouts.
    if (threads > 0) {
        omp_set_num_threads(threads);
    }
#pragma omp parallel for schedule(dynamic, 1)
    for (int i = 0; i < n_rollouts; ++i) {
        const uint64_t seed_rollout =
            static_cast<uint64_t>(seed) + static_cast<uint64_t>(i);
        mal_abm_fast::Prng rng(seed_rollout);

        // Clone the shared climate engine for this thread (shares multi-day
        // buffers but has independent single-day accessor arrays)
        auto thread_climate = shared_climate->clone_for_thread();

        // -- Build the engine -----------------------------------------
        // Derive mobility directory from the individual file paths (if any).
        std::string mobility_dir;
        if (!human_mobility_day_path.empty()) {
            mobility_dir = std::filesystem::path(human_mobility_day_path)
                .parent_path().string();
        } else if (!human_mobility_night_path.empty()) {
            mobility_dir = std::filesystem::path(human_mobility_night_path)
                .parent_path().string();
        } else if (!livestock_mobility_path.empty()) {
            mobility_dir = std::filesystem::path(livestock_mobility_path)
                .parent_path().string();
        }
        std::unique_ptr<mal_abm_fast::Engine> engine_ptr;
        try {
            engine_ptr = std::make_unique<mal_abm_fast::Engine>(
                aoi, thread_climate, habitat_path, rng, start_date,
                seeding_config, overrides, hosts_path, mobility_dir,
                wind_field_path, transmission_params);
        } catch (const std::exception& e) {
            std::cerr << "abm_run: rollout " << i
                      << " failed to build engine: " << e.what() << "\n";
            std::exit(EXIT_FAILURE);
        }
        auto& engine = *engine_ptr;
        engine.set_max_population(max_population);

        // -- debug instrumentation (M7.0 population-crash investigation)
        // When the user passes --debug-population, the submodel emits
        // one stderr line per day with the population counts, the
        // Lardeux p_d at the seeding patch, and the per-day
        // births/deaths/maturation counts. Rate-limited: every day
        // for the first 10 days, then every 5 days.
        if (debug_population) {
            engine.set_debug_population(true);
            const auto sp = engine.seeding_patch();
            if (sp.patch_id >= 0) {
                engine.set_debug_seeding_patch(sp.patch_id, sp.row, sp.col);
            }
        }

        // -- Rollout output path --------------------------------------
        const std::string rollout_path =
            rollout_output_path(output_path, i, n_rollouts);

        // -- Foci audit log sidecar (plan §5.2) ------------------------
        if (enable_transmission && !rollout_path.empty()) {
            std::string foci_path = rollout_path;
            const std::string suffix = ".tif";
            if (foci_path.size() > suffix.size() &&
                foci_path.compare(foci_path.size() - suffix.size(),
                                  suffix.size(), suffix) == 0) {
                foci_path.replace(foci_path.size() - suffix.size(),
                                  suffix.size(), "_foci.json");
            } else {
                foci_path += "_foci.json";
            }
            engine.set_foci_log_path(foci_path);
        }

        // -- Cohort log collection -----------------------------------
        std::vector<mal_abm_fast::DailyStats> cohort_log;
        if (!cohort_log_path.empty()) {
            cohort_log.reserve(static_cast<size_t>(days));
        }

        // -- Step ----------------------------------------------------
        try {
            for (int d = 0; d < days; ++d) {
                try {
                    engine.step();
                } catch (const std::exception& e) {
                    std::cerr << "abm_run: rollout " << i
                              << " diverged on day " << (d + 1)
                              << ": " << e.what() << "\n";
                    std::exit(EXIT_FAILURE);
                }

                if (!cohort_log_path.empty()) {
                    cohort_log.push_back(engine.last_day_stats());
                }

                // Intermediate snapshot every N days
                if (snapshot_every > 0 && (d + 1) % snapshot_every == 0) {
                    const std::string day_path = rollout_day_path(rollout_path, d + 1);
                    // Ensure parent directory exists
                    const std::filesystem::path day_out(day_path);
                    if (day_out.has_parent_path()) {
                        std::error_code ec;
                        std::filesystem::create_directories(day_out.parent_path(), ec);
                    }
                    engine.snapshot(day_path, year, month,
                                    static_cast<int32_t>(seed_rollout),
                                    n_rollouts, i);
                    std::cout << "abm_run: rollout " << i << "/" << n_rollouts
                              << " day=" << (d + 1) << "/" << days
                              << " -> " << day_path << std::endl;
                }

                // Intermediate transmission snapshot (M7.4)
                const int effective_trans_snapshot = (transmission_snapshot_every > 0)
                    ? transmission_snapshot_every : snapshot_every;
                if (enable_transmission && effective_trans_snapshot > 0 &&
                    (d + 1) % effective_trans_snapshot == 0) {
                    const std::string trans_base =
                        rollout_transmission_output_path(output_path, i, n_rollouts);
                    const std::string trans_day_path =
                        rollout_transmission_day_path(trans_base, d + 1);
                    const std::filesystem::path trans_day_out(trans_day_path);
                    if (trans_day_out.has_parent_path()) {
                        std::error_code ec;
                        std::filesystem::create_directories(trans_day_out.parent_path(), ec);
                    }
                    engine.snapshot_transmission(trans_day_path, year, month, d + 1,
                                                 static_cast<int32_t>(seed_rollout),
                                                 n_rollouts, i);
                    std::cout << "abm_run: rollout " << i << "/" << n_rollouts
                              << " transmission day=" << (d + 1) << "/" << days
                              << " -> " << trans_day_path << std::endl;
                }
            }
        } catch (const std::exception& e) {
            std::cerr << "abm_run: rollout " << i
                      << " snapshot failed during stepping: "
                      << e.what() << "\n";
            std::exit(EXIT_FAILURE);
        }

        // -- Write cohort log JSON ----------------------------------
        if (!cohort_log_path.empty() && !cohort_log.empty()) {
            std::string rollout_cohort_path;
            if (n_rollouts == 1) {
                rollout_cohort_path = cohort_log_path;
            } else {
                const std::filesystem::path cp(cohort_log_path);
                const std::filesystem::path cparent = cp.has_parent_path()
                    ? cp.parent_path() : std::filesystem::path{};
                const std::string cstem = cp.stem().string();
                const std::string cext  = cp.has_extension()
                    ? cp.extension().string() : ".json";
                std::ostringstream cname;
                cname << "cohort_seed"
                      << std::setw(4) << std::setfill('0') << i << cext;
                rollout_cohort_path = (cparent / cname.str()).string();
            }
            // Ensure parent directory exists
            {
                const std::filesystem::path cop(rollout_cohort_path);
                if (cop.has_parent_path()) {
                    std::error_code ec;
                    std::filesystem::create_directories(cop.parent_path(), ec);
                }
            }
            std::ofstream ofs(rollout_cohort_path);
            ofs << "{\n  \"n_days\": " << days << ",\n  \"daily\": [\n";
            for (size_t di = 0; di < cohort_log.size(); ++di) {
                const auto& s = cohort_log[di];
                ofs << "    {\"day\": " << s.day
                    << ", \"n_alive\": " << s.n_alive
                    << ", \"n_adults\": " << s.n_adults
                    << ", \"n_larvae\": " << s.n_larvae
                    << ", \"n_eggs\": " << s.n_eggs
                    << ", \"n_pupae\": " << s.n_pupae
                    << ", \"n_emerged\": " << s.n_emerged
                    << ", \"n_births\": " << s.n_births
                    << ", \"n_deaths\": " << s.n_deaths
                    << ", \"n_maturation\": " << s.n_maturation
                    << ", \"eip_frac\": " << std::fixed << std::setprecision(4) << s.eip_frac
                    << "}";
                if (di + 1 < cohort_log.size()) ofs << ",";
                ofs << "\n";
            }
            ofs << "  ]\n}\n";
            ofs.close();
            std::cout << "abm_run: rollout " << i << "/" << n_rollouts
                      << " cohort log -> " << rollout_cohort_path << std::endl;
        }

        // -- Write transmission log JSON (M7.4) ----------------------
        if (!transmission_log_path.empty() && engine.transmission()) {
            std::string rollout_trans_log;
            if (n_rollouts == 1) {
                rollout_trans_log = transmission_log_path;
            } else {
                const std::filesystem::path tp(transmission_log_path);
                const std::filesystem::path tparent = tp.has_parent_path()
                    ? tp.parent_path() : std::filesystem::path{};
                const std::string tstem = tp.stem().string();
                const std::string text  = tp.has_extension()
                    ? tp.extension().string() : ".json";
                std::ostringstream tname;
                tname << "transmission_seed"
                      << std::setw(4) << std::setfill('0') << i << text;
                rollout_trans_log = (tparent / tname.str()).string();
            }
            mal_abm_fast::write_transmission_log(
                rollout_trans_log, engine.transmission()->history(), days);
            std::cout << "abm_run: rollout " << i << "/" << n_rollouts
                      << " transmission log -> " << rollout_trans_log << std::endl;
        }

        // -- Snapshot ------------------------------------------------
        try {
            // Ensure the output parent directory exists.
            const std::filesystem::path out_path(rollout_path);
            if (out_path.has_parent_path()) {
                std::error_code ec;
                std::filesystem::create_directories(
                    out_path.parent_path(), ec);
            }
            engine.snapshot(rollout_path, year, month,
                            static_cast<int32_t>(seed_rollout),
                            n_rollouts, i);

            // Final transmission snapshot (M7.4)
            if (enable_transmission) {
                const std::string trans_path =
                    rollout_transmission_output_path(output_path, i, n_rollouts);
                const std::filesystem::path tout_path(trans_path);
                if (tout_path.has_parent_path()) {
                    std::error_code ec;
                    std::filesystem::create_directories(tout_path.parent_path(), ec);
                }
                engine.snapshot_transmission(trans_path, year, month, days,
                                             static_cast<int32_t>(seed_rollout),
                                             n_rollouts, i);
                std::cout << "abm_run: rollout " << i << "/" << n_rollouts
                          << " transmission -> " << trans_path << std::endl;
            }
        } catch (const std::exception& e) {
            std::cerr << "abm_run: rollout " << i
                      << " snapshot failed: " << e.what() << "\n";
            std::exit(EXIT_FAILURE);
        }

        std::cout << "abm_run: rollout " << i << "/" << n_rollouts
                  << " AOI=" << aoi.slug
                  << " year=" << year
                  << " month=" << month
                  << " seed=" << seed_rollout
                  << " days=" << days
                  << " -> " << rollout_path << std::endl;
    }

    return EXIT_SUCCESS;
}
