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

#include <cstdint>
#include <vector>

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

/// Gonotrophic cycle parameters. Defaults are calibrated for
/// An. gambiae s.s. in West Africa (Ghana).
struct GonotrophicParams {
    float cycle_duration_days   = 2.65f;   // post-first-cycle duration
    float first_cycle_days      = 4.0f;    // pre-gravid (teneral → first oviposition)
    float feeding_success_rate  = 0.825f;  // [0.75, 0.90]
    int32_t egg_batch_mean      = 52;      // binomial(105, 0.5)
    int32_t egg_batch_min       = 30;
    int32_t egg_batch_max       = 170;
    float resting_duration_days = 1.0f;    // post-feed rest
};

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
/// Returns true if the female is in OVIPOSITING state after the
/// transition (caller should deposit eggs).
inline bool advance_gonotrophic_one_day(
    GonotrophicState& state,
    int32_t& timer,
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
        // First cycle uses first_cycle_days; subsequent cycles use
        // cycle_duration_days.
        const float required = (timer == 0) ? params.first_cycle_days
                                             : params.cycle_duration_days;
        timer++;
        if (static_cast<float>(timer) >= required) {
            state = GonotrophicState::GRAVID;
            timer = 0;
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
