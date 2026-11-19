// SPDX-License-Identifier: MIT
// host_cascade.hpp — Perception cascade and emergent movement of the female
// (plan individualization-and-movement, §4 and §5, Paso 5).
//
// Replaces the per-cell attraction field of the previous version. The female has
// a continuous metric position and senses the NEAREST PERSON through bands of
// distance taken from `species.<row>`:
//
//   EXPLORATION  no stimulus: correlated random walk (+ casting across the
//                wind), steps inside the exploration disk
//   ACTIVATION   a person within co2_activation_radius_m: CO2 activates her,
//                she orients upwind (no direction without wind)
//   PLUME        within olfactory_radius_m: optomotor anemotaxis towards the
//                source with intermittent casting; micro-step dt_olfactory_s
//   VISUAL       within visual_radius_m: fine micro-step dt_terminal_s
//   CONTACT      within terminal_radius_m, then the landing gate
//                (v < landing_speed_mm_s held landing_speed_hold_s)
//
// Entering a band is decided on d_min, the minimum distance of the SWEPT
// SEGMENT to the person, never on the end point of the step, and a step never
// exceeds the radius of the next band (the step is truncated where the band
// is entered). The day is bounded by a flight-time budget (consumable per
// day, not per phase) and by the daily path length daily_move_capacity_m.
#pragma once

#include <array>
#include <cstdint>
#include <string>

#include "human_state.hpp"
#include "prng.hpp"
#include "species.hpp"

namespace mal_abm_fast {

enum class CascadeStage : uint8_t {
    NONE        = 0,
    EXPLORATION = 1,
    ACTIVATION  = 2,
    PLUME       = 3,
    VISUAL      = 4,
    CONTACT     = 5,
    LANDED      = 6,
};

const char* cascade_stage_name(CascadeStage s);

/// Everything the cascade reads from model_constants.yaml, resolved for one
/// species (`species.<row>` + `integration:`).
struct CascadeParams {
    double co2_activation_radius_m = 0.0;
    double olfactory_radius_m = 0.0;
    double visual_radius_m = 0.0;
    double terminal_radius_m = 0.0;
    double flight_speed_ms = 0.0;
    double exploration_range_m = 0.0;
    double exploration_step_m = 0.0;
    double exploration_step_correlation = 0.0;
    double casting_probability = 0.0;
    double casting_angle_deg = 0.0;
    double plume_memory_s = 0.0;
    double anemotaxis_deviation_deg = 0.0;
    double wind_block_threshold_ms = 0.0;
    double daily_move_capacity_m = 0.0;
    double directed_flight_budget_h = 0.0;
    double dt_terminal_s = 0.0;
    double dt_olfactory_s = 0.0;
    double landing_speed_mm_s = 0.0;
    double landing_speed_hold_s = 0.0;
    std::array<double, 4> phase_duration_hours{};   // [DAY, EVENING, NIGHT, DAWN]
    std::array<double, 4> activity_weights{};       // [DAY, EVENING, NIGHT, DAWN]

    /// Resolve the row of `id`. The species row wins over `integration:` for
    /// plume_memory_s and directed_flight_budget_h (plan §12 duplication rule).
    static CascadeParams for_species(MosquitoSpeciesId id);

    /// Scenario overrides (plan 13.2): set the cascade key `name` to `value`.
    /// Returns false for a name that is not an overridable cascade key.
    /// Throws std::invalid_argument when the result breaks an invariant
    /// (radii must nest: terminal < visual < olfactory <= co2_activation; equal radii mean an empty ACTIVATION band).
    bool apply_override(const std::string& name, double value);
    static bool is_overridable(const std::string& name);

    /// Seconds of directed flight a phase may use: its share of the daily
    /// budget by activity weight, never more than the phase itself lasts.
    double phase_flight_seconds(int phase) const;
};

/// Horizontal wind at the mosquito (m/s); (0, 0) = no wind field.
struct WindSample {
    double u = 0.0;   // east
    double v = 0.0;   // north
};

/// State of one female's flight during one day.
struct FlightState {
    double x = 0.0;
    double y = 0.0;
    double heading = 0.0;          // rad, 0 = east, counter-clockwise
    bool   has_heading = false;
    double path_used_m = 0.0;      // path length flown today
    double flight_used_s = 0.0;    // flight time used today
    int64_t locked_person = -1;    // person being tracked inside the olfactory band
    CascadeStage stage = CascadeStage::NONE;   // highest stage reached
};

struct PhaseOutcome {
    bool     landed = false;
    int64_t  person = -1;          // the person she landed on
    int64_t  micro_ticks = 0;      // olfactory + terminal ticks spent (cost accounting)
};

/// Fly ONE phase: at most `params.phase_flight_seconds(phase)` of flight and
/// the path left of the day. Moves `fs`; returns whether she landed on a
/// person. `width_m`/`height_m` bound the AOI (the walk reflects nowhere: it
/// stops at the border). Deterministic given `rng`.
PhaseOutcome fly_phase(const CascadeParams& params,
                       const HumanCompartmentGrid& humans,
                       FlightState& fs, int phase,
                       const WindSample& wind,
                       double width_m, double height_m, Prng& rng);

}  // namespace mal_abm_fast
