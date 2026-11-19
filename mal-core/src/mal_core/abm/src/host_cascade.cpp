// SPDX-License-Identifier: MIT
// host_cascade.cpp — Perception cascade and emergent movement (Paso 5).
// See host_cascade.hpp for the design.
#include "mal_abm_fast/host_cascade.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <utility>

#include "mal_abm_fast/config.hpp"
#include "mal_abm_fast/species_params.hpp"

namespace mal_abm_fast {

namespace {

constexpr double kPi = 3.14159265358979323846;
constexpr double kWindMin = 0.1;   // m/s: below it there is no usable wind (plan §4)

inline double deg2rad(double d) { return d * kPi / 180.0; }

inline void raise_stage(FlightState& fs, CascadeStage s) {
    if (static_cast<uint8_t>(s) > static_cast<uint8_t>(fs.stage)) fs.stage = s;
}

// Everything one phase needs, bundled so the helpers stay short.
struct Flight {
    const CascadeParams& P;
    const HumanCompartmentGrid& humans;
    FlightState& fs;
    const WindSample& wind;
    double width_m, height_m;
    Prng& rng;
    double t_left;
    PhaseOutcome out;

    double wind_speed() const { return std::hypot(wind.u, wind.v); }
    bool has_wind() const { return wind_speed() >= kWindMin; }
    // Direction the wind blows FROM (the way "upwind" points), rad.
    double upwind_angle() const { return std::atan2(-wind.v, -wind.u); }

    // The advance is blocked when the headwind component along the direction
    // of travel reaches the blocking threshold (plan §4: the female does not
    // advance faster than the wind pushes her back).
    bool blocked(double dx, double dy) const {
        if (!has_wind()) return false;
        const double headwind = -(wind.u * dx + wind.v * dy);
        return headwind >= P.wind_block_threshold_ms;
    }

    double uniform(double lo, double hi) { return lo + (hi - lo) * rng.uniform_double(); }

    void spend(double len_m) {
        const double dt = len_m / P.flight_speed_ms;
        t_left -= dt;
        fs.flight_used_s += dt;
    }

    // Move along (dx, dy) (unit vector) by len; the AOI border stops the walk.
    void move(double dx, double dy, double len_m) {
        const double nx = std::clamp(fs.x + dx * len_m, 0.0, std::nextafter(width_m, 0.0));
        const double ny = std::clamp(fs.y + dy * len_m, 0.0, std::nextafter(height_m, 0.0));
        const double flown = std::hypot(nx - fs.x, ny - fs.y);
        fs.x = nx;
        fs.y = ny;
        fs.path_used_m += len_m;   // path length counts the intended flight, even at the border
        (void)flown;
        spend(len_m);
        fs.heading = std::atan2(dy, dx);
        fs.has_heading = true;
    }

    double path_left() const { return P.daily_move_capacity_m - fs.path_used_m; }
};

// One exploration / activation step. `band_radius` is the radius of the NEXT
// band the female can enter (CO2 radius when nothing is sensed, olfactory
// radius when activated); the step never exceeds it and is cut where the
// swept segment enters it.
void explore_step(Flight& f, bool sensed) {
    const CascadeParams& P = f.P;
    FlightState& fs = f.fs;
    const double band = sensed ? P.olfactory_radius_m : P.co2_activation_radius_m;
    double L = std::min({P.exploration_step_m, band, P.flight_speed_ms * f.t_left, f.path_left()});
    if (L <= 0.0) { f.t_left = 0.0; return; }

    double heading;
    if (sensed && f.has_wind()) {
        // ACTIVATION: orient upwind (optomotor), +-deviation.
        const double dev = deg2rad(P.anemotaxis_deviation_deg);
        heading = f.upwind_angle() + f.uniform(-dev, dev);
    } else if (f.has_wind() && f.rng.uniform_double() < P.casting_probability) {
        // Casting across the wind.
        const double dev = deg2rad(P.anemotaxis_deviation_deg);
        const double side = (f.rng.uniform_double() < 0.5) ? -1.0 : 1.0;
        heading = f.upwind_angle() + side * (deg2rad(P.casting_angle_deg) + f.uniform(-dev, dev));
    } else {
        // Correlated random walk: blend the previous heading with a fresh one.
        const double fresh = f.uniform(-kPi, kPi);
        if (fs.has_heading) {
            const double c = P.exploration_step_correlation;
            heading = std::atan2(c * std::sin(fs.heading) + (1.0 - c) * std::sin(fresh),
                                 c * std::cos(fs.heading) + (1.0 - c) * std::cos(fresh));
        } else {
            heading = fresh;
        }
    }
    const double dx = std::cos(heading), dy = std::sin(heading);
    if (f.blocked(dx, dy)) {          // the wind stops the advance: time passes, no progress
        f.spend(L);
        fs.heading = heading;
        fs.has_heading = true;
        return;
    }

    // Swept-segment detection: where the segment first comes within `band`
    // of a person, the female ENTERS that band and the step ends there.
    HumanCompartmentGrid::SegmentHit hit;
    double len = L;
    const double x1 = fs.x + dx * L, y1 = fs.y + dy * L;
    const bool entered = f.humans.nearest_to_segment(fs.x, fs.y, x1, y1, band, hit);
    if (entered) {
        // Step just PAST the entry point (1 mm) so rounding cannot leave her
        // on the wrong side of the band edge and re-trigger the same entry.
        len = std::min(L, std::max(1e-3, hit.t_entry * L + 1e-3));
        if (sensed) {
            fs.locked_person = hit.person;      // inside the olfactory band: track it
            raise_stage(fs, CascadeStage::PLUME);
        } else {
            raise_stage(fs, CascadeStage::ACTIVATION);
        }
    } else {
        raise_stage(fs, sensed ? CascadeStage::ACTIVATION : CascadeStage::EXPLORATION);
    }
    f.move(dx, dy, len);
}

// One micro-step towards the locked person. Returns true when she lands.
bool track_step(Flight& f) {
    const CascadeParams& P = f.P;
    FlightState& fs = f.fs;
    const HumanSoA& pp = f.humans.people();
    const size_t k = static_cast<size_t>(fs.locked_person);
    const double tx = static_cast<double>(pp.cur_x[k]), ty = static_cast<double>(pp.cur_y[k]);
    const double ddx = tx - fs.x, ddy = ty - fs.y;
    const double d = std::hypot(ddx, ddy);

    if (d <= P.terminal_radius_m) {
        // CONTACT (by distance); LANDING needs the speed gate held for
        // landing_speed_hold_s, sampled at dt_terminal_s (75 samples at 25 Hz).
        raise_stage(fs, CascadeStage::CONTACT);
        const double hold = P.landing_speed_hold_s;
        if (f.t_left + 1e-12 < hold) { f.t_left = 0.0; return false; }   // not enough time left today
        f.t_left -= hold;
        fs.flight_used_s += hold;
        f.out.micro_ticks += static_cast<int64_t>(std::llround(hold / P.dt_terminal_s));
        raise_stage(fs, CascadeStage::LANDED);
        f.out.landed = true;
        f.out.person = fs.locked_person;
        return true;
    }
    if (d > P.olfactory_radius_m) {       // lost the plume entirely: back to activation
        fs.locked_person = -1;
        return false;
    }

    const double bearing = std::atan2(ddy, ddx);
    double dt, len, heading;
    if (d <= P.visual_radius_m) {
        raise_stage(fs, CascadeStage::VISUAL);
        dt = P.dt_terminal_s;
        heading = bearing;                       // vector towards the silhouette
        len = std::min(P.flight_speed_ms * dt, d);
    } else {
        raise_stage(fs, CascadeStage::PLUME);
        dt = P.dt_olfactory_s;
        if (f.rng.uniform_double() < P.casting_probability) {
            // Plume lost: cast across the line to the source for the plume memory.
            const double dev = deg2rad(P.anemotaxis_deviation_deg);
            const double side = (f.rng.uniform_double() < 0.5) ? -1.0 : 1.0;
            heading = bearing + side * (deg2rad(P.casting_angle_deg) + f.uniform(-dev, dev));
            dt = P.plume_memory_s;
        } else {
            const double dev = deg2rad(P.anemotaxis_deviation_deg);
            heading = bearing + f.uniform(-dev, dev);
        }
        len = P.flight_speed_ms * dt;
    }
    len = std::min({len, P.flight_speed_ms * f.t_left, f.path_left()});
    if (len <= 0.0) { f.t_left = 0.0; return false; }
    f.out.micro_ticks += std::max<int64_t>(1, static_cast<int64_t>(std::llround(
        (len / P.flight_speed_ms) / ((d <= P.visual_radius_m) ? P.dt_terminal_s : P.dt_olfactory_s))));
    const double dx = std::cos(heading), dy = std::sin(heading);
    if (f.blocked(dx, dy)) {
        f.spend(len);
        return false;
    }
    f.move(dx, dy, len);
    return false;
}

}  // namespace

const char* cascade_stage_name(CascadeStage s) {
    switch (s) {
        case CascadeStage::NONE:        return "NONE";
        case CascadeStage::EXPLORATION: return "EXPLORATION";
        case CascadeStage::ACTIVATION:  return "ACTIVATION";
        case CascadeStage::PLUME:       return "PLUME";
        case CascadeStage::VISUAL:      return "VISUAL";
        case CascadeStage::CONTACT:     return "CONTACT";
        case CascadeStage::LANDED:      return "LANDED";
    }
    return "NONE";
}

CascadeParams CascadeParams::for_species(MosquitoSpeciesId id) {
    const ModelConfig& cfg = load_config();
    const SpeciesRow& r = cfg.species.rows.at(species_row_name(id));
    CascadeParams p;
    p.co2_activation_radius_m = r.co2_activation_radius_m;
    p.olfactory_radius_m = r.olfactory_radius_m;
    p.visual_radius_m = r.visual_radius_m;
    p.terminal_radius_m = r.terminal_radius_m;
    p.flight_speed_ms = r.flight_speed_ms;
    p.exploration_range_m = r.exploration_range_m;
    p.exploration_step_m = r.exploration_step_m;
    p.exploration_step_correlation = r.exploration_step_correlation;
    p.casting_probability = r.casting_probability;
    p.casting_angle_deg = r.casting_angle_deg;
    p.plume_memory_s = r.plume_memory_s;                 // the species row wins
    p.anemotaxis_deviation_deg = r.anemotaxis_deviation_deg;
    p.wind_block_threshold_ms = r.wind_block_threshold_ms;
    p.daily_move_capacity_m = r.daily_move_capacity_m;
    p.directed_flight_budget_h = r.directed_flight_budget_h;   // the species row wins
    p.dt_terminal_s = cfg.integration.dt_terminal_s;
    p.dt_olfactory_s = cfg.integration.dt_olfactory_s;
    p.landing_speed_mm_s = cfg.integration.landing_speed_mm_s;
    p.landing_speed_hold_s = cfg.integration.landing_speed_hold_s;
    p.phase_duration_hours = cfg.integration.phase_duration_hours;
    p.activity_weights = r.activity_weights;
    return p;
}

namespace {
// Name -> member of the cascade keys a scenario may override.
using Member = double CascadeParams::*;
const std::pair<const char*, Member> kOverridable[] = {
    {"co2_activation_radius_m", &CascadeParams::co2_activation_radius_m},
    {"olfactory_radius_m", &CascadeParams::olfactory_radius_m},
    {"visual_radius_m", &CascadeParams::visual_radius_m},
    {"terminal_radius_m", &CascadeParams::terminal_radius_m},
    {"flight_speed_ms", &CascadeParams::flight_speed_ms},
    {"exploration_range_m", &CascadeParams::exploration_range_m},
    {"exploration_step_m", &CascadeParams::exploration_step_m},
    {"exploration_step_correlation", &CascadeParams::exploration_step_correlation},
    {"casting_probability", &CascadeParams::casting_probability},
    {"casting_angle_deg", &CascadeParams::casting_angle_deg},
    {"plume_memory_s", &CascadeParams::plume_memory_s},
    {"anemotaxis_deviation_deg", &CascadeParams::anemotaxis_deviation_deg},
    {"wind_block_threshold_ms", &CascadeParams::wind_block_threshold_ms},
    {"daily_move_capacity_m", &CascadeParams::daily_move_capacity_m},
    {"directed_flight_budget_h", &CascadeParams::directed_flight_budget_h},
};
}  // namespace

bool CascadeParams::is_overridable(const std::string& name) {
    for (const auto& [k, m] : kOverridable) { (void)m; if (name == k) return true; }
    return false;
}

bool CascadeParams::apply_override(const std::string& name, double value) {
    for (const auto& [k, m] : kOverridable) {
        if (name != k) continue;
        CascadeParams trial = *this;
        trial.*m = value;
        if (!(trial.terminal_radius_m < trial.visual_radius_m &&
              trial.visual_radius_m < trial.olfactory_radius_m &&
              trial.olfactory_radius_m <= trial.co2_activation_radius_m)) {
            throw std::invalid_argument("override " + name + " = " + std::to_string(value) +
                                        " breaks terminal < visual < olfactory < co2_activation");
        }
        *this = trial;
        return true;
    }
    return false;
}

double CascadeParams::phase_flight_seconds(int phase) const {
    const size_t p = static_cast<size_t>(phase);
    if (p >= 4 || activity_weights[p] <= 0.0) return 0.0;
    const double budget_s = directed_flight_budget_h * 3600.0;
    return std::min(phase_duration_hours[p] * 3600.0, activity_weights[p] * budget_s);
}

PhaseOutcome fly_phase(const CascadeParams& params,
                       const HumanCompartmentGrid& humans,
                       FlightState& fs, int phase,
                       const WindSample& wind,
                       double width_m, double height_m, Prng& rng)
{
    const double budget_s = params.directed_flight_budget_h * 3600.0;
    Flight f{params, humans, fs, wind, width_m, height_m, rng,
             std::min(params.phase_flight_seconds(phase), budget_s - fs.flight_used_s), {}};

    for (int64_t guard = 0; guard < 2'000'000 && f.t_left > 1e-9 && f.path_left() > 1e-9; ++guard) {
        if (fs.locked_person >= 0) {
            if (track_step(f)) break;
            continue;
        }
        HumanCompartmentGrid::SegmentHit here;
        const bool sensed = humans.nearest_to_segment(
            fs.x, fs.y, fs.x, fs.y, params.co2_activation_radius_m, here);
        if (sensed && here.d_min <= params.olfactory_radius_m) {
            fs.locked_person = here.person;          // already inside the olfactory band
            raise_stage(fs, CascadeStage::PLUME);
            continue;
        }
        explore_step(f, sensed);
    }
    return f.out;
}

}  // namespace mal_abm_fast
