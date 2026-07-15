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
#include <iomanip>
#include <iostream>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>

#include <CLI/CLI.hpp>

#include "engine.hpp"
#include "prng.hpp"
#include "wire.hpp"

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

}  // namespace

int main(int argc, char** argv) {
    CLI::App app{
        "mal_abm_fast: M1.5 thin-slice ABM (C++ port of mal_ghana_sim.abm)"
    };
    app.set_version_flag("--version", "0.1.0");

    // --run subcommand: thin-slice ABM run.
    auto* run = app.add_subcommand("run", "Run the ABM for an AOI + month");

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
    std::string env_path;
    std::string habitat_path;
    std::string output_path;

    run->add_option("--aoi", aoi_slug,
                    "AOI slug (default 'ghana'). Use --bbox for custom.");
    run->add_option("--bbox", bbox_str,
                    "Custom bbox 'W,S,E,N' in degrees (overrides --aoi).");
    run->add_option("--crs", crs,
                    "CRS for the AOI (default 'EPSG:4326').");
    run->add_option("--resolution-m", resolution_m,
                    "Ground resolution in metres (default 1000).");
    run->add_option("--scale", scale_str,
                    "AOI scale: 'regional', 'national', or 'continental' "
                    "(default 'regional').");
    run->add_option("--year", year, "Year (1st day of the run).")
        ->required();
    run->add_option("--month", month, "Month (1..12).")
        ->required()
        ->check(CLI::Range(1, 12));
    run->add_option("--seed", seed, "RNG seed (default 1).")
        ->default_val(1);
    run->add_option("--env", env_path,
                    "Path to the 4-band env COG (build_env output).")
        ->required()
        ->check(CLI::ExistingFile);
    run->add_option("--habitat", habitat_path,
                    "Path to the habitat patches gpkg.")
        ->required()
        ->check(CLI::ExistingFile);
    run->add_option("--output", output_path,
                    "Path to write the state COG (.tif). When --n-rollouts "
                    "> 1, the leaf file name is rewritten to "
                    "<stem>_seed{NNNN}.tif where NNNN is the 0-indexed "
                    "rollout id zero-padded to 4 digits.")
        ->required();
    run->add_option("--days", days, "Days to run (1..366).")
        ->default_val(30)
        ->check(CLI::Range(1, 366));
    run->add_option("--n-rollouts", n_rollouts,
                    "Number of rollouts to run in this process (1+). "
                    "Default 1. Each rollout gets a fresh `Prng` instance "
                    "seeded at `seed + i`; outputs are written to "
                    "<output>_seed{NNNN}.tif alongside the sidecar JSON.")
        ->default_val(1)
        ->check(CLI::PositiveNumber);

    CLI11_PARSE(app, argc, argv);

    // If no subcommand was given, print help and exit.
    if (!run->parsed()) {
        std::cout << app.help();
        return EXIT_SUCCESS;
    }

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

    // -- Rollouts loop (F1.c) -------------------------------------------
    // Each rollout gets a fresh `Prng` instance seeded at
    // `seed_rollout = seed + i`. A new `Engine` is built per rollout
    // (the Engine derives its own sub-stream seeds from the master
    // Prng, then discards it). The Engine and the master Prng go
    // out of scope at the end of each iteration, so no Prng state
    // leaks across rollouts.
    for (int i = 0; i < n_rollouts; ++i) {
        const uint64_t seed_rollout =
            static_cast<uint64_t>(seed) + static_cast<uint64_t>(i);
        mal_abm_fast::Prng rng(seed_rollout);

        // -- Build the engine -----------------------------------------
        std::unique_ptr<mal_abm_fast::Engine> engine_ptr;
        try {
            engine_ptr = std::make_unique<mal_abm_fast::Engine>(
                aoi, env_path, habitat_path, rng, start_date);
        } catch (const std::exception& e) {
            std::cerr << "abm_run: rollout " << i
                      << " failed to build engine: " << e.what() << "\n";
            return EXIT_FAILURE;
        }
        auto& engine = *engine_ptr;

        // -- Step ----------------------------------------------------
        try {
            for (int d = 0; d < days; ++d) {
                engine.step();
            }
        } catch (const std::exception& e) {
            std::cerr << "abm_run: rollout " << i
                      << " step() failed on day " << days << ": "
                      << e.what() << "\n";
            return EXIT_FAILURE;
        }

        // -- Snapshot ------------------------------------------------
        const std::string rollout_path =
            rollout_output_path(output_path, i, n_rollouts);
        try {
            // Ensure the output parent directory exists.
            const std::filesystem::path out_path(rollout_path);
            if (out_path.has_parent_path()) {
                std::error_code ec;
                std::filesystem::create_directories(
                    out_path.parent_path(), ec);
                // Ignore ec: if the dir already exists,
                // create_directories returns false; if it cannot be
                // created, snapshot() will surface the IO error.
            }
            engine.snapshot(rollout_path, year, month,
                            static_cast<int32_t>(seed_rollout),
                            n_rollouts, i);
        } catch (const std::exception& e) {
            std::cerr << "abm_run: rollout " << i
                      << " snapshot failed: " << e.what() << "\n";
            return EXIT_FAILURE;
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
