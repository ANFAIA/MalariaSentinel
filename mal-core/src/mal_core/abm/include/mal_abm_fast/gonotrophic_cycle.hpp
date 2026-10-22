// SPDX-License-Identifier: MIT
// gonotrophic_cycle.hpp — Gonotrophic state machine for female mosquitoes.
//
// The gonotrophic cycle is the repeating sequence:
//   HOST_SEEKING → BLOOD_FED → EGG_MATURING → GRAVID → OVIPOSITION → HOST_SEEKING
//
// Newly emerged females start as TENERAL and must complete their first
// blood meal before entering the regular cycle. The cycle drives
// oviposition events (which feed the AquaticCohortBank) and feeding
// events (which feed the BiteLedger).
#pragma once

#include <cmath>
#include <cstdint>
#include <vector>

#include "config.hpp"

namespace mal_abm_fast {

/// Gonotrophic state for adult female mosquitoes.
/// Males and aquatic stages ignore this field (kept at TENERAL=0).
///
/// Full state machine (An. gambiae s.s.):
///   TENERAL → MATE_SEEKING → HOST_SEEKING → HOST_APPROACH → PROBING
///   → BLOOD_FED → RESTING → EGG_MATURING → GRAVID
///   → OVIPOSITION_SEEKING → OVIPOSITING → HOST_SEEKING (cycle restarts)
enum class GonotrophicState : uint8_t {
    TENERAL = 0,          // newly emerged, needs first blood meal
    MATE_SEEKING,         // seeking mating (pre-host-seeking)
    HOST_SEEKING,         // searching for host (18:00–06:00 active)
    HOST_APPROACH,        // approaching detected host (close range)
    PROBING,              // probing / attempting to feed
    BLOOD_FED,            // post-feeding, abdomen distended
    RESTING,              // post-feed rest (endophilic / exophilic)
    EGG_MATURING,         // developing eggs (2–4 days)
    GRAVID,               // ready to oviposit
    OVIPOSITION_SEEKING,  // searching for oviposition site
    OVIPOSITING,          // laying eggs
};

/// Host type for bite events (BiteLedger aggregation).
enum class HostType : uint8_t {
    HUMAN  = 0,
    CATTLE = 1,
    GOAT   = 2,
    SHEEP  = 3,
    OTHER  = 4,
};

/// Gonotrophic cycle parameters. Values come from ``gonotrophic:`` in
/// model_constants.yaml (single source, R1); the default constructor reads
/// the validated config so no compiled default exists.
struct GonotrophicParams {
    float cycle_duration_days;    // post-first-cycle egg maturation
    float first_cycle_days;       // first-cycle egg maturation
    float feeding_success_rate;   // PROBING -> BLOOD_FED
    int32_t egg_batch_mean;       // binomial(n, p) mean, p = mean/n
    int32_t egg_batch_n;          // trials for the egg-batch draw
    int32_t egg_batch_min;
    int32_t egg_batch_max;
    float resting_duration_days;  // post-feed rest (BLOOD_FED -> RESTING)

    GonotrophicParams();
};

inline GonotrophicParams::GonotrophicParams() {
    const GonotrophicCfg& cfg = load_config().gonotrophic;
    cycle_duration_days = static_cast<float>(cfg.cycle_duration_days);
    first_cycle_days = static_cast<float>(cfg.first_cycle_days);
    feeding_success_rate = static_cast<float>(cfg.feeding_success_rate);
    egg_batch_mean = cfg.egg_batch_mean;
    egg_batch_n = cfg.egg_batch_n;
    egg_batch_min = cfg.egg_batch_min;
    egg_batch_max = cfg.egg_batch_max;
    resting_duration_days = static_cast<float>(cfg.resting_duration_days);
}

/// Advance one female's gonotrophic state by one day.
///
/// This function handles deterministic state transitions only.
/// The caller is responsible for:
///   - Checking host availability for HOST_SEEKING → HOST_APPROACH
///   - Computing feeding success for PROBING → BLOOD_FED
///   - Computing egg batch size via binomial draw (Prng) when
///     transitioning OVIPOSITING → HOST_SEEKING
///   - Recording feeding events in the BiteLedger
///
/// `cycles_completed` counts gonotrophic cycles this female has already
/// completed (0 before the first oviposition). It distinguishes the
/// first, slower egg-maturation phase (first_cycle_days) from
/// subsequent cycles (cycle_duration_days). Durations are rounded to
/// whole days because the model advances in one-day steps.
///
/// Returns true if the female is in OVIPOSITING state after the
/// transition (caller should deposit eggs).
inline bool advance_gonotrophic_one_day(
    GonotrophicState& state,
    int32_t& timer,
    int32_t& cycles_completed,
    const GonotrophicParams& params)
{
    switch (state) {
    case GonotrophicState::TENERAL:
        // Teneral females first seek a mate, then seek a host.
        state = GonotrophicState::MATE_SEEKING;
        break;

    case GonotrophicState::MATE_SEEKING:
        // Mating is assumed instantaneous for An. gambiae (swarm mating).
        // Proceed directly to host-seeking.
        state = GonotrophicState::HOST_SEEKING;
        break;

    case GonotrophicState::HOST_SEEKING:
        // Caller checks host availability in the landscape.
        // If host detected: state → HOST_APPROACH.
        // If not: stay HOST_SEEKING (retry next hourly step).
        break;

    case GonotrophicState::HOST_APPROACH:
        // Caller computes approach vector toward host.
        // Once close enough (within probing range): state → PROBING.
        // If host escapes: state → HOST_SEEKING.
        break;

    case GonotrophicState::PROBING:
        // Caller computes feeding success (0.75–0.90).
        // If success: state → BLOOD_FED, record in BiteLedger.
        // If fail (host defense, ITN): state → HOST_SEEKING.
        break;

    case GonotrophicState::BLOOD_FED:
        // Rest for resting_duration_days, then begin egg maturation.
        timer++;
        if (timer >= static_cast<int32_t>(params.resting_duration_days)) {
            timer = 0;
            state = GonotrophicState::RESTING;
        }
        break;

    case GonotrophicState::RESTING:
        // Post-feed rest complete. Begin egg development.
        state = GonotrophicState::EGG_MATURING;
        break;

    case GonotrophicState::EGG_MATURING: {
        // First cycle matures eggs more slowly than subsequent cycles.
        const float required = (cycles_completed == 0) ? params.first_cycle_days
                                                       : params.cycle_duration_days;
        // Durations are configured as fractional days but the model
        // advances in one-day steps; round up so the phase lasts at
        // least the configured duration.
        const int32_t required_days = static_cast<int32_t>(
            std::ceil(required));
        timer++;
        if (timer >= required_days) {
            state = GonotrophicState::GRAVID;
            timer = 0;
            ++cycles_completed;
        }
        break;
    }

    case GonotrophicState::GRAVID:
        // Transition to seeking an oviposition site.
        state = GonotrophicState::OVIPOSITION_SEEKING;
        break;

    case GonotrophicState::OVIPOSITION_SEEKING:
        // Caller checks habitat. If found: state → OVIPOSITING.
        // If not: retain eggs (skip-oviposition, try next day).
        break;

    case GonotrophicState::OVIPOSITING:
        // Caller computes egg batch, deposits eggs, then sets
        // state → HOST_SEEKING.
        break;
    }

    return state == GonotrophicState::OVIPOSITING;
}

}  // namespace mal_abm_fast
