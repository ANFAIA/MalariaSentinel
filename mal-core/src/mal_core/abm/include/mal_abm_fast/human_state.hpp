// SPDX-License-Identifier: MIT
// human_state.hpp — Individual human population (SoA) with SEIR timers.
//
// Plan individualization-and-movement, Paso 2a (§2, §15.0). The per-cell
// compartment grid of M7.4 is replaced by a population of *individual*
// people in Structure-of-Arrays form, in the same module and behind the same
// API boundary (`HumanCompartmentGrid` keeps its name and its seeding calls):
//
//   * every person has a stable `human_id`, a fixed position inside its cell
//     (metres from the south-west corner of the AOI, drawn uniformly from the
//     seed) and a SEIR state with a discrete timer (non-Markovian dwell, as
//     the old cohort queues did, but per individual);
//   * the number of people in a cell is the real one (rounded `human_total`
//     of the grid): there is no SLOTS_PER_CELL and there are no empty slots;
//   * S/E/I/R per cell (`s_at`, `i_at`, `prev_at`, ...) are DERIVED
//     statistics kept in step with the individuals;
//   * `advance_day()` advances timers only. Infection vector→human happens
//     only at a bite, on one concrete person (`expose`); the per-cell force
//     of infection lambda_H no longer exists.
#pragma once

#include <cstddef>
#include <cstdint>
#include <string>
#include <tuple>
#include <utility>
#include <vector>

#include "prng.hpp"

namespace mal_abm_fast {

enum class HumanState : uint8_t {
    SUSCEPTIBLE = 0,
    EXPOSED     = 1,
    INFECTIOUS  = 2,
    RECOVERED   = 3,
};

/// Parse "SUSCEPTIBLE" | "EXPOSED" | "INFECTIOUS" | "RECOVERED" (scenario
/// JSON spelling). Throws std::invalid_argument on anything else.
HumanState parse_human_state(const std::string& s);

/// Individual people, Structure-of-Arrays. Persons are stored contiguously
/// by cell (row-major cell order), so the people of cell `c` are the index
/// range [cell_begin(c), cell_begin(c + 1)).
struct HumanSoA {
    std::vector<int64_t>  human_id;     // (cell_id << 32) | slot: unique, stable
    std::vector<int32_t>  cell_id;      // home cell, row * W + col
    std::vector<float>    home_x;       // m from the SW corner of the AOI
    std::vector<float>    home_y;
    std::vector<float>    cur_x;        // = home in this version (no mobility yet)
    std::vector<float>    cur_y;
    std::vector<uint8_t>  state;        // HumanState
    std::vector<int32_t>  timer;        // days left in `state` (E, I, R)
    std::vector<uint8_t>  susceptible;  // individual flag: 1 = can be infected

    size_t size() const { return human_id.size(); }
    void clear();
    void reserve(size_t n);
};

/// One declared individual (scenario `humans[]`): position in metres, state
/// and, for E/I/R, the days left in it (<= 0 means "the full duration").
struct HumanSeed {
    double     x = 0.0;
    double     y = 0.0;
    HumanState state = HumanState::SUSCEPTIBLE;
    double     timer_days = 0.0;
};

struct HumanCompartmentStats {
    double total_susceptible = 0.0;
    double total_exposed     = 0.0;
    double total_infectious  = 0.0;
    double total_recovered   = 0.0;
    double total_population  = 0.0;
    double total_incidence   = 0.0;  // new E_H today across grid
    double mean_prevalence   = 0.0;  // total_infectious / total_population
};

class HumanCompartmentGrid {
public:
    HumanCompartmentGrid() = default;

    /// Build the population. `human_density` is persons per cell (row-major,
    /// size h*w); each cell gets round(density) people placed uniformly in
    /// the cell from `seed`. `cell_m` is the cell side in metres
    /// (`aoi.resolution_m`). If initial_prevalence > 0, that fraction of
    /// each cell's people starts infectious, with timers spread evenly over
    /// the infectious period.
    void init(int32_t h, int32_t w,
              const std::vector<float>& human_density,
              int32_t incubation_days = 12,
              int32_t infectious_days = 20,
              int32_t immunity_days = 180,
              bool immunity_enabled = false,
              double initial_prevalence = 0.0,
              double cell_m = 1000.0,
              uint64_t seed = 0);

    /// Replace the whole population by the declared individuals (synthetic
    /// scenarios): only these people exist. Requires a prior `init`. Throws
    /// std::runtime_error on a position outside the grid.
    void set_individuals(const std::vector<HumanSeed>& people);

    /// Seed explicit infectious humans at a specific cell (row, col): the
    /// first `round(count)` susceptible people of the cell (capped at the
    /// susceptibles available) become INFECTIOUS at age zero.
    void seed_infections(int32_t row, int32_t col, double count);

    /// Seed random viable foci: picks up to n_foci cells with population >= min_pop.
    /// Requires cells with mosquito_density > 0 when density is provided.
    /// Injects up to cases_per_focus into each selected cell as infectious humans (I_H).
    /// Returns vector of selected (row, col) coordinates.
    std::vector<std::pair<int32_t, int32_t>> seed_random_viable_foci(
        int32_t n_foci,
        double cases_per_focus,
        double min_pop,
        const std::vector<float>& mosquito_density,
        Prng& rng);

    /// Seed explicit foci list: vector of (row, col, cases).
    void seed_explicit_foci(
        const std::vector<std::tuple<int32_t, int32_t, double>>& foci);

    /// Seed ONE spatially concentrated outbreak cluster (M7.4.1):
    /// `total_cases` split ∝ cell population across the core cell and
    /// satellites within `radius_cells` (Chebyshev window, candidates
    /// require population >= min_pop; when mosquito density is provided
    /// the core must have density > 0 so the cluster lands where the
    /// chain can actually start). Returns the seeded (row, col) cells
    /// (core first). Deterministic given (rng, population layout).
    std::vector<std::pair<int32_t, int32_t>> seed_outbreak_cluster(
        int32_t core_row,
        int32_t core_col,
        double total_cases,
        int32_t radius_cells,
        double min_pop,
        const std::vector<float>& mosquito_density,
        Prng& rng);

    /// Advance ONE day of timers only: resets the daily incidence, then
    /// E -> I, I -> R (or S without immunity) and R -> S when a timer
    /// reaches zero. It applies no infection probability: exposure happens
    /// at a bite, through `expose`.
    void advance_day();

    /// Index of a uniformly random person of cell (row, col), or -1 when the
    /// cell is empty. Stand-in for "the person the bite landed on" until the
    /// movement cascade (Paso 5) identifies the person.
    int64_t pick_person(int32_t row, int32_t col, Prng& rng) const;

    /// S -> E for the person at `index` (timer = incubation period). Returns
    /// false, and changes nothing, unless the person is susceptible. Counts
    /// towards today's incidence of the person's cell.
    bool expose(int64_t index);

    /// Closest person to a segment, as found by `nearest_to_segment`.
    struct SegmentHit {
        int64_t person = -1;      // index into the HumanSoA
        double  d_min  = 0.0;     // minimum distance from the segment to the person (m)
        double  t_entry = 0.0;    // first fraction of the segment at which d <= radius
    };

    /// Build the spatial index (a uniform bin grid over the AOI, finer than
    /// the 1 km cell) used by the perception cascade. `target_bin_m` is the
    /// preferred bin side; it is enlarged on very large AOIs to cap the
    /// number of bins. People do not move in this version, so the index is
    /// built once, after the population is final (init / set_individuals
    /// invalidate it).
    void build_spatial_index(double target_bin_m);
    bool has_spatial_index() const { return !bin_begin_.empty(); }

    /// The person closest to the segment (x0,y0)->(x1,y1) among those within
    /// `radius` of it (x0==x1, y0==y1 gives a point query). Distances are
    /// to the segment, not to its end point (plan §4: "d_min of the swept
    /// segment"). Returns false when nobody is within `radius`.
    bool nearest_to_segment(double x0, double y0, double x1, double y1,
                            double radius, SegmentHit& hit) const;

    // Grid properties
    int32_t h() const { return h_; }
    int32_t w() const { return w_; }
    int64_t total_cells() const { return static_cast<int64_t>(h_) * static_cast<int64_t>(w_); }
    double  cell_m() const { return cell_m_; }

    // Individuals
    const HumanSoA& people() const { return soa_; }
    int64_t n_people() const { return static_cast<int64_t>(soa_.size()); }
    /// First person index of cell `cell` (valid for cell in [0, total_cells()]).
    int64_t cell_begin(int64_t cell) const { return cell_begin_[static_cast<size_t>(cell)]; }

    // Derived per-cell statistics (row-major, size h*w)
    const std::vector<double>& susceptible() const { return susceptible_; }
    const std::vector<double>& exposed()     const { return exposed_; }
    const std::vector<double>& infectious()  const { return infectious_; }
    const std::vector<double>& recovered()   const { return recovered_; }
    const std::vector<double>& population()  const { return population_; }
    const std::vector<double>& incidence()   const { return daily_incidence_; }
    const std::vector<double>& prevalence()  const { return daily_prevalence_; }

    // Single cell accessors
    double s_at(int32_t r, int32_t c) const { return susceptible_[r * w_ + c]; }
    double e_at(int32_t r, int32_t c) const { return exposed_[r * w_ + c]; }
    double i_at(int32_t r, int32_t c) const { return infectious_[r * w_ + c]; }
    double r_at(int32_t r, int32_t c) const { return recovered_[r * w_ + c]; }
    double pop_at(int32_t r, int32_t c) const { return population_[r * w_ + c]; }
    double prev_at(int32_t r, int32_t c) const { return daily_prevalence_[r * w_ + c]; }
    double inc_at(int32_t r, int32_t c) const { return daily_incidence_[r * w_ + c]; }

    // Grid-wide summary statistics (derived from the per-cell statistics)
    HumanCompartmentStats compute_stats() const;

    // Parameters
    int32_t incubation_days() const { return incubation_days_; }
    int32_t infectious_days() const { return infectious_days_; }
    int32_t immunity_days()   const { return immunity_days_; }
    bool    immunity_enabled() const { return immunity_enabled_; }

    /// Recount S/E/I/R per cell from the individuals and compare them with
    /// the derived statistics; also checks ids, positions and timers. Returns
    /// true if valid, throws if strict=true.
    bool validate_invariants(bool strict = true) const;

private:
    // Build the cell index (cell_begin_) and the per-cell statistics from soa_.
    void rebuild_cell_index_();
    // Move person `i` to `to`, keeping the per-cell statistics in step.
    void set_state_(size_t i, HumanState to, int32_t timer);
    void refresh_prevalence_(size_t cell);
    // First `n` susceptible people of `cell` become INFECTIOUS (age zero).
    int64_t infect_first_susceptibles_(size_t cell, int64_t n);

    int32_t h_ = 0;
    int32_t w_ = 0;
    double  cell_m_ = 1000.0;

    int32_t incubation_days_ = 12;
    int32_t infectious_days_ = 20;
    int32_t immunity_days_   = 180;
    bool    immunity_enabled_ = false;

    HumanSoA soa_;
    std::vector<int64_t> cell_begin_;   // size h*w + 1

    // Spatial index (see build_spatial_index): bins sorted CSR-style.
    double bin_m_ = 0.0;
    int32_t nbx_ = 0, nby_ = 0;
    std::vector<int64_t> bin_begin_;    // nbx*nby + 1
    std::vector<uint32_t> bin_people_;  // person indices grouped by bin

    // Derived per-cell statistics
    std::vector<double> susceptible_;
    std::vector<double> exposed_;
    std::vector<double> infectious_;
    std::vector<double> recovered_;
    std::vector<double> population_;
    std::vector<double> daily_incidence_;   // count of new E_H today
    std::vector<double> daily_prevalence_;  // I_H / population
};

}  // namespace mal_abm_fast
