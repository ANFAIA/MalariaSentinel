// SPDX-License-Identifier: MIT
// main.cpp — mal_abm_fast CLI (stub; F1.b/d implement the real subcommands)
#include <cstdlib>
#include <iostream>

#include <CLI/CLI.hpp>

#include "prng.hpp"

int main(int argc, char** argv) {
    CLI::App app{"mal_abm_fast — fast C++ ABM engine for MalariaSentinel Centinela (M-perf)"};
    // CLI11 2.x: set_version_flag installs --version (and its short form -V) and
    // handles the print+exit internally. Do NOT re-register via add_flag — that
    // throws OptionAlreadyAdded.
    app.set_version_flag("--version", "0.1.0");

    CLI11_PARSE(app, argc, argv);

    // If we reach here, the user did NOT pass --version.
    // (set_version_flag exits on its own when --version is hit.)

    // F1.a: no subcommands yet. Print a friendly message.
    std::cout << "mal_abm_fast 0.1.0 (M-perf F1.a scaffold)\n"
              << "F1.a scaffold — no subcommands yet. See docs/perf-cpp-abm-plan.md.\n"
              << "F1.b (climate + habitat readers), F1.c (SoA + PRNG + day loop), "
              << "F1.d (output contract writer) ship next.\n";

    // Smoke test: instantiate the PRNG stub and emit one uniform draw so a
    // manual `./mal_abm_fast --version && ./mal_abm_fast` round-trip is exercised.
    mal_abm_fast::xoshiro256pp rng;
    rng.seed_from(42);
    std::cout << "PRNG smoke: xoshiro256** seeded with 42; first uniform = "
              << rng.uniform() << "\n";

    return EXIT_SUCCESS;
}
