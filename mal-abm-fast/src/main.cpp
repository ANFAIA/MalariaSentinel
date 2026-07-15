// SPDX-License-Identifier: MIT
// main.cpp — mal_abm_fast CLI (M-perf / F1.b / F1.d thin-slice ABM).
//
// Mirrors `python -m mal_ghana_sim.abm.run`. The CLI takes an AOI (or
// custom bbox), loads the 4-band env COG and the habitat patches gpkg,
// runs the Engine for `--days` days, and writes the 2-band state COG
// and sidecar JSON via `Engine::snapshot()`.
//
// Usage:
//   mal_abm_fast run \
//     --aoi ghana --year 2024 --month 6 --seed 1 --days 30 \
//     --env    data/runs/ghana/ghana_regional_2024_06_env.tif \
//     --habitat data/runs/ghana/ghana_regional_2024_06_habitat_patches.gpkg \
//     --output data/runs/ghana/ghana_regional_2024_06_seed0001.tif
#include <cstdio>
#include <cstdlib>
#include <exception>
#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <string>

#include <CLI/CLI.hpp>

#include "engine.hpp"
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
                    "Path to write the state COG (.tif).")
        ->required();
    run->add_option("--days", days, "Days to run (1..366).")
        ->default_val(30)
        ->check(CLI::Range(1, 366));

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

    // -- Build the engine + run -----------------------------------------
    std::unique_ptr<mal_abm_fast::Engine> engine_ptr;
    try {
        engine_ptr = std::make_unique<mal_abm_fast::Engine>(
            aoi, env_path, habitat_path,
            static_cast<uint64_t>(seed), start_date);
    } catch (const std::exception& e) {
        std::cerr << "abm_run: failed to build engine: " << e.what() << "\n";
        return EXIT_FAILURE;
    }
    auto& engine = *engine_ptr;

    try {
        for (int d = 0; d < days; ++d) {
            engine.step();
        }
    } catch (const std::exception& e) {
        std::cerr << "abm_run: step() failed on day " << days << ": "
                  << e.what() << "\n";
        return EXIT_FAILURE;
    }

    // -- Snapshot -------------------------------------------------------
    try {
        // Ensure the output parent directory exists.
        const std::filesystem::path out_path(output_path);
        if (out_path.has_parent_path()) {
            std::error_code ec;
            std::filesystem::create_directories(out_path.parent_path(), ec);
            // Ignore ec: if the dir already exists, create_directories
            // returns false; if it cannot be created, snapshot() will
            // surface the IO error.
        }
        engine.snapshot(output_path, year, month, seed);
    } catch (const std::exception& e) {
        std::cerr << "abm_run: snapshot failed: " << e.what() << "\n";
        return EXIT_FAILURE;
    }

    std::cout << "abm_run: AOI=" << aoi.slug
              << " year=" << year
              << " month=" << month
              << " seed=" << seed
              << " days=" << days
              << " -> " << output_path << std::endl;
    return EXIT_SUCCESS;
}
