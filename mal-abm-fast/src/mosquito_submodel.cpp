// SPDX-License-Identifier: MIT
// mosquito_submodel.cpp — F1.b: Polars-style vectorised mosquito half
// of the ABM, ported to a C++20 SoA.
//
// Per-day order (mirrors `mal_ghana_sim.abm.mosquito_submodel.
// MosquitoSubmodel.advance_day` exactly):
//   1. larva_mortality_inactive(patch_states)
//   2.5. larva_mortality_density(patch_states)
//   2. larva_growth(patch_states)
//   3. larva_to_adult()
//   4. adult_dispersal()
//   6. adult_mortality(patch_states)
//   5. birth(aoi, patch_states)
//
// Determinism: every stochastic draw goes through `rng_` (the
// per-submodel `Prng`). The draw order — one `uniform_double()` per
// adult in `adult_dispersal`, then two `normal()` draws per
// dispersing adult via `dispersal::offset_m`, and one `binomial()`
// per active patch in `birth` — matches the Python reference's
// `np.random.default_rng` sequence so F1.e can byte-compare the
// per-day outputs.
#include "mal_abm_fast/mosquito_submodel.hpp"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <limits>
#include <unordered_map>
#include <utility>
#include <vector>

#include "mal_abm_fast/aoi.hpp"
#include "mal_abm_fast/birth_rate.hpp"
#include "mal_abm_fast/dispersal.hpp"
#include "mal_abm_fast/eip.hpp"
#include "mal_abm_fast/seeding.hpp"

namespace mal_abm_fast {

namespace {

// Swap agent `i` with agent `n-1` in every SoA vector. Caller must
// ensure 0 <= i < n. No-op when i == n-1 (degenerate case: the agent
// at the end of the live range just needs `n_alive` decremented).
inline void swap_with_last(MosquitoSoA& soa, int64_t i, int64_t n) {
    if (i == n - 1) return;
    std::swap(soa.uid[i],          soa.uid[n - 1]);
    std::swap(soa.patch_id[i],     soa.patch_id[n - 1]);
    std::swap(soa.row[i],          soa.row[n - 1]);
    std::swap(soa.col[i],          soa.col[n - 1]);
    std::swap(soa.stage[i],        soa.stage[n - 1]);
    std::swap(soa.lon[i],          soa.lon[n - 1]);
    std::swap(soa.lat[i],          soa.lat[n - 1]);
    std::swap(soa.eip_progress[i], soa.eip_progress[n - 1]);
    std::swap(soa.stage_age[i],    soa.stage_age[n - 1]);
    std::swap(soa.days_since_active[i], soa.days_since_active[n - 1]);
}

// Trim every SoA vector to `new_size` (the new live range after a
// compaction op). No-op when new_size == current size.
inline void trim_soa(MosquitoSoA& soa, size_t new_size) {
    if (new_size >= soa.uid.size()) return;
    soa.uid.resize(new_size);
    soa.patch_id.resize(new_size);
    soa.row.resize(new_size);
    soa.col.resize(new_size);
    soa.stage.resize(new_size);
    soa.lon.resize(new_size);
    soa.lat.resize(new_size);
    soa.eip_progress.resize(new_size);
    soa.stage_age.resize(new_size);
    soa.days_since_active.resize(new_size);
}

}  // namespace

// ---------------------------------------------------------------------------
// Cell-centre helpers
// ---------------------------------------------------------------------------

static inline std::pair<int32_t, int32_t> LonLatToCell(
    double lon, double lat, const AOI& aoi) {
    const int32_t w = aoi.cells_per_side();
    const int32_t h = cells_per_side_h(aoi);
    const double cellW = (aoi.east - aoi.west) / static_cast<double>(w);
    const double cellH = (aoi.north - aoi.south) / static_cast<double>(h);
    int32_t col = static_cast<int32_t>((lon - aoi.west) / cellW);
    int32_t row = static_cast<int32_t>((aoi.north - lat) / cellH);
    if (col < 0) col = 0; if (col >= w) col = w - 1;
    if (row < 0) row = 0; if (row >= h) row = h - 1;
    return {row, col};
}

// ---------------------------------------------------------------------------
// Construction
// ---------------------------------------------------------------------------

MosquitoSubmodel::MosquitoSubmodel(int32_t n_patches, int32_t k_per_patch,
                                   float init_frac, uint64_t seed,
                                   RuntimeOverrides overrides)
    : rng_(seed), k_per_patch_(k_per_patch), overrides_(overrides) {
    if (n_patches <= 0 || k_per_patch <= 0 || !(init_frac > 0.0f)) {
        soa_.n_alive  = 0;
        soa_.next_uid = 0;
        return;
    }
    const int64_t np = static_cast<int64_t>(n_patches);
    const int64_t n  = static_cast<int64_t>(std::llround(
        static_cast<double>(n_patches) *
        static_cast<double>(k_per_patch)  *
        static_cast<double>(init_frac)));
    if (n <= 0) {
        soa_.n_alive  = 0;
        soa_.next_uid = 0;
        return;
    }

    // Round-robin: each patch gets floor(n / n_patches) agents; the
    // first (n % n_patches) patches get one more.
    const int64_t base = n / np;
    const int64_t rem  = n % np;
    std::vector<int64_t> per_patch(static_cast<size_t>(np), base);
    for (int64_t i = 0; i < rem; ++i) per_patch[static_cast<size_t>(i)] += 1;

    const size_t cap = static_cast<size_t>(n);
    soa_.uid.reserve(cap);
    soa_.patch_id.reserve(cap);
    soa_.row.reserve(cap);
    soa_.col.reserve(cap);
    soa_.stage.reserve(cap);
    soa_.lon.reserve(cap);
    soa_.lat.reserve(cap);
    soa_.eip_progress.reserve(cap);
    soa_.stage_age.reserve(cap);
    soa_.days_since_active.reserve(cap);

    // Stable age distribution at seeding time: 10% pre-mature (EIP
    // already complete) and 90% fresh larvae (eip_progress=0, will
    // mature over the next ~10 days). At p_d=0.95 mean adult life is
    // ~13 days, so 10% is a reasonable steady-state adult fraction
    // for the suitability band (which counts adults) to be non-zero
    // from day 1 with this distribution.
    //
    // The pre-mature agents are seeded as stage=0 LARVAE with
    // eip_progress = EIP_THRESHOLD_GD (NOT stage=1 adults). The
    // first `larva_to_adult` pass on day 1 promotes them and
    // snaps lon/lat to the cell centre of their birth patch (via
    // the existing larva_to_adult snap). If we seeded them as
    // stage=1, they would keep the (lon=0, lat=0) constructor
    // sentinel and get bucketed into the SW corner of the AOI by
    // adult_density_by_cell — exactly the bug the larva_to_adult
    // snap was designed to prevent. The first advance_day then
    // promotes and disperses them, so the day-1 state COG already
    // shows them as spread adults with proper lon/lat.
    constexpr float UNIFORM_ADULT_FRAC = 0.10f;
    constexpr float EIP_COMPLETE = static_cast<float>(EIP_THRESHOLD_GD);
    for (int64_t p = 0; p < np; ++p) {
        const int64_t k = per_patch[static_cast<size_t>(p)];
        const int64_t n_premature = static_cast<int64_t>(std::llround(
            static_cast<double>(k) * UNIFORM_ADULT_FRAC));
        const int64_t n_larvae = k - n_premature;
        // Pre-mature: larva with EIP complete. The first
        // larva_to_adult pass promotes them and snaps lon/lat.
        for (int64_t j = 0; j < n_premature; ++j) {
            soa_.uid.push_back(static_cast<int64_t>(soa_.uid.size()));
            soa_.patch_id.push_back(p);
            soa_.row.push_back(0);
            soa_.col.push_back(0);
            soa_.stage.push_back(0);
            soa_.lon.push_back(0.0f);
            soa_.lat.push_back(0.0f);
            soa_.eip_progress.push_back(EIP_COMPLETE);
            soa_.stage_age.push_back(0);
            soa_.days_since_active.push_back(0);
        }
        // Larvae: fresh eggs, will accumulate EIP
        for (int64_t j = 0; j < n_larvae; ++j) {
            soa_.uid.push_back(static_cast<int64_t>(soa_.uid.size()));
            soa_.patch_id.push_back(p);
            soa_.row.push_back(0);
            soa_.col.push_back(0);
            soa_.stage.push_back(0);
            soa_.lon.push_back(0.0f);
            soa_.lat.push_back(0.0f);
            soa_.eip_progress.push_back(0.0f);
            soa_.stage_age.push_back(0);
            soa_.days_since_active.push_back(0);
        }
    }
    soa_.n_alive  = n;
    soa_.next_uid = n;
}

// ---------------------------------------------------------------------------
// Detection-based constructor
// ---------------------------------------------------------------------------
//
// For each `SeedInstruction`:
//   * `n_adults` agents are added with `stage = 1` (adult) and
//     `eip_progress = EIP_THRESHOLD_GD` so the first `larva_to_adult`
//     pass does NOT re-promote them — they are already adult, ready
//     to disperse on day 1.
//   * `n_larvae` agents are added with `stage = 0` (larva) and
//     `eip_progress = 0`. They must accumulate growing-degree-days
//     before promotion (matches the legacy "seed K*init_frac larvae"
//     path).
// Adults get the instruction's lon/lat (the cell centre) so the
// first `adult_dispersal` pass has a valid origin; larvae are placed
// at the same (lon, lat) so subsequent cell snapping is consistent.
MosquitoSubmodel::MosquitoSubmodel(int32_t n_patches, int32_t k_per_patch,
                                   const std::vector<SeedInstruction>& instructions,
                                   uint64_t seed,
                                   RuntimeOverrides overrides)
    : rng_(seed), k_per_patch_(k_per_patch), overrides_(overrides) {
    (void)n_patches;  // not needed; instructions are explicit
    if (instructions.empty()) {
        soa_.n_alive  = 0;
        soa_.next_uid = 0;
        return;
    }

    int64_t total = 0;
    for (const auto& inst : instructions) {
        if (inst.n_adults < 0 || inst.n_larvae < 0) continue;
        total += static_cast<int64_t>(inst.n_adults);
        total += static_cast<int64_t>(inst.n_larvae);
    }
    if (total <= 0) {
        soa_.n_alive  = 0;
        soa_.next_uid = 0;
        return;
    }

    const size_t cap = static_cast<size_t>(total);
    soa_.uid.reserve(cap);
    soa_.patch_id.reserve(cap);
    soa_.row.reserve(cap);
    soa_.col.reserve(cap);
    soa_.stage.reserve(cap);
    soa_.lon.reserve(cap);
    soa_.lat.reserve(cap);
    soa_.eip_progress.reserve(cap);
    soa_.stage_age.reserve(cap);
    soa_.days_since_active.reserve(cap);

    for (const auto& inst : instructions) {
        // Adults: ready to disperse immediately. eip_progress is
        // irrelevant for adults but we write EIP_THRESHOLD_GD so a
        // later code path that reads it sees a sensible value.
        for (int32_t j = 0; j < inst.n_adults; ++j) {
            soa_.uid.push_back(static_cast<int64_t>(soa_.uid.size()));
            soa_.patch_id.push_back(inst.patch_id);
            soa_.row.push_back(inst.row);
            soa_.col.push_back(inst.col);
            soa_.stage.push_back(1);  // adult
            soa_.lon.push_back(static_cast<float>(inst.lon));
            soa_.lat.push_back(static_cast<float>(inst.lat));
            soa_.eip_progress.push_back(EIP_THRESHOLD_GD);
            soa_.stage_age.push_back(0);
            soa_.days_since_active.push_back(0);
        }
        // Larvae: need to complete EIP before becoming adults.
        for (int32_t j = 0; j < inst.n_larvae; ++j) {
            soa_.uid.push_back(static_cast<int64_t>(soa_.uid.size()));
            soa_.patch_id.push_back(inst.patch_id);
            soa_.row.push_back(inst.row);
            soa_.col.push_back(inst.col);
            soa_.stage.push_back(0);  // larva
            soa_.lon.push_back(static_cast<float>(inst.lon));
            soa_.lat.push_back(static_cast<float>(inst.lat));
            soa_.eip_progress.push_back(0.0f);
            soa_.stage_age.push_back(0);
            soa_.days_since_active.push_back(0);
        }
    }
    soa_.n_alive  = total;
    soa_.next_uid = total;
}

// ---------------------------------------------------------------------------
// Per-day orchestrator
// ---------------------------------------------------------------------------

namespace {

// Count the number of agents in stage `stage` (0=larva, 1=adult).
// Used by the debug instrumentation to log per-day breakdowns
// without re-walking the SoA twice in the hot path.
inline int64_t count_stage(const MosquitoSoA& soa, uint8_t stage) {
    int64_t n = 0;
    for (int64_t i = 0; i < soa.n_alive; ++i) {
        if (soa.stage[static_cast<size_t>(i)] == stage) ++n;
    }
    return n;
}

// Look up today's temperature at the seeding patch via
// PatchState.temp_d (the canonical per-day temperature after the
// NaN fallback in climate.cpp::temp_at). Returns NaN if the
// seeding patch is not in today's patch_states (e.g. it was never
// activated — should not happen post-fix, but we handle it
// gracefully).
inline float seeding_temp_d(const std::vector<PatchState>& ps,
                            int32_t row, int32_t col) {
    for (const auto& s : ps) {
        if (s.row == row && s.col == col) return s.temp_d;
    }
    return std::numeric_limits<float>::quiet_NaN();
}

// Lardeux daily survival probability at temperature T. Mirrors the
// formula in adult_mortality() so the debug log shows the same
// value the mortality step uses.
inline float lardeux_p_d(float T) {
    if (!std::isfinite(static_cast<double>(T))) {
        return static_cast<float>(ADULT_DAILY_MORT_BASAL);
    }
    const double opt_c   = static_cast<double>(ADULT_OPT_C);
    const double sigma   = static_cast<double>(ADULT_SIGMA);
    const double basal   = static_cast<double>(ADULT_DAILY_MORT_BASAL);
    const double two_ss  = 2.0 * sigma * sigma;
    const double Td      = static_cast<double>(T);
    double p = basal * std::exp(-((Td - opt_c) * (Td - opt_c)) / two_ss);
    if (p < static_cast<double>(ADULT_MORT_FLOOR)) p = static_cast<double>(ADULT_MORT_FLOOR);
    if (p > static_cast<double>(ADULT_MORT_CAP))   p = static_cast<double>(ADULT_MORT_CAP);
    return static_cast<float>(p);
}

}  // namespace

void MosquitoSubmodel::advance_day(const AOI& aoi,
                                   const std::vector<PatchState>& patch_states) {
    // -- debug snapshot: pre-day counts (used to derive
    // n_births/n_deaths/n_maturation at the end of the orchestrator
    // without touching the SoA twice in the hot path). Skipped
    // entirely when debug_population_ is off.
    const int64_t day_idx = day_counter_++;
    int64_t pre_n_alive  = 0;
    int64_t pre_n_adults = 0;
    int64_t pre_n_larvae = 0;
    bool    want_log    = false;
    if (debug_population_) {
        pre_n_alive  = soa_.n_alive;
        pre_n_adults = count_stage(soa_, 1);
        pre_n_larvae = count_stage(soa_, 0);
        // Rate-limited: every day for the first 10 days, then every
        // 5 days. The first day (day_idx == 0) is always logged.
        want_log = (day_idx < 10) || (day_idx % 5 == 0);
    }

    larva_mortality_inactive(patch_states);   // Op 1
    larva_mortality_density(patch_states);    // Op 2.5 (Beverton-Holt)
    larva_growth(patch_states);               // Op 2
    // -- snapshot: pre-maturation (just before larva_to_adult).
    // n_maturation = post_mat_n_adults - pre_mat_n_adults.
    const int64_t pre_mat_n_alive  = soa_.n_alive;
    const int64_t pre_mat_n_adults = count_stage(soa_, 1);
    larva_to_adult(aoi, patch_states);        // Op 3
    // -- snapshot: post-maturation (just after larva_to_adult,
    // before dispersal which only moves lon/lat not stage).
    const int64_t post_mat_n_alive  = soa_.n_alive;
    const int64_t post_mat_n_adults = count_stage(soa_, 1);
    adult_dispersal(aoi);                     // Op 4
    const int64_t pre_mort_n_alive = soa_.n_alive;
    adult_mortality(patch_states);            // Op 6 (Lardeux)
    const int64_t post_mort_n_alive = soa_.n_alive;
    birth(aoi, patch_states);                 // Op 5
    const int64_t post_birth_n_alive = soa_.n_alive;

    // Always compute last_day_stats_ (used by --emit-cohort-log).
    const int64_t post_n_adults = count_stage(soa_, 1);
    const int64_t post_n_larvae = count_stage(soa_, 0);
    const int64_t n_maturation  = post_mat_n_adults - pre_mat_n_adults;
    const int64_t n_deaths      = pre_mort_n_alive - post_mort_n_alive;
    const int64_t n_births      = post_birth_n_alive - post_mort_n_alive;

    last_day_stats_.day          = day_idx;
    last_day_stats_.n_alive      = post_birth_n_alive;
    last_day_stats_.n_adults     = post_n_adults;
    last_day_stats_.n_larvae     = post_n_larvae;
    last_day_stats_.n_births     = n_births;
    last_day_stats_.n_deaths     = n_deaths;
    last_day_stats_.n_maturation = n_maturation;
    // Compute eip_completion_frac: fraction of total population that are
    // adults (i.e., have completed EIP). In the 2-stage model, all adults
    // completed EIP by definition (larva_to_adult promotes when
    // eip_progress >= EIP_THRESHOLD_GD). The adult fraction is a proxy
    // for EIP completion rate: higher adult fraction = more larvae
    // successfully completing EIP and becoming infective adults.
    // Target range for D3_eip scorer: 0.20-0.50 (20-50% adults).
    last_day_stats_.eip_frac = (post_birth_n_alive > 0)
        ? static_cast<float>(post_n_adults) / static_cast<float>(post_birth_n_alive)
        : 0.0f;

    if (debug_population_ && want_log) {
        const float   temp_d        = seeding_temp_d(
            patch_states, debug_seeding_row_, debug_seeding_col_);
        const float   p_d           = lardeux_p_d(temp_d);
        const bool    in_states     = !std::isnan(static_cast<double>(temp_d));
        std::fprintf(stderr,
            "abm_debug: day=%lld n_alive=%lld n_adults=%lld "
            "n_larvae=%lld seeding_in_states=%s seeding_temp_d=%.2f "
            "p_d=%.4f n_births=%lld n_deaths=%lld n_maturation=%lld\n",
            static_cast<long long>(day_idx),
            static_cast<long long>(post_birth_n_alive),
            static_cast<long long>(post_n_adults),
            static_cast<long long>(post_n_larvae),
            in_states ? "yes" : "no",
            static_cast<double>(temp_d),
            static_cast<double>(p_d),
            static_cast<long long>(n_births),
            static_cast<long long>(n_deaths),
            static_cast<long long>(n_maturation));
    }
}

// ---------------------------------------------------------------------------
// Op 1: larva mortality at inactive patches (desiccation, Depinay 2004)
// ---------------------------------------------------------------------------

void MosquitoSubmodel::larva_mortality_inactive(
    const std::vector<PatchState>& patch_states) {
    if (soa_.n_alive <= 0) return;

    // Build active set from patch_states.
    int64_t max_pid = -1;
    for (const auto& ps : patch_states) {
        if (ps.patch_id > max_pid) max_pid = ps.patch_id;
    }
    for (int64_t i = 0; i < soa_.n_alive; ++i) {
        const int64_t pid = soa_.patch_id[static_cast<size_t>(i)];
        if (pid > max_pid) max_pid = pid;
    }
    if (max_pid < 0) return;

    std::vector<uint8_t> active_by_id(static_cast<size_t>(max_pid) + 1, 0);
    for (const auto& ps : patch_states) {
        if (ps.activated) {
            active_by_id[static_cast<size_t>(ps.patch_id)] = 1;
        }
    }

    // Phase 1: for each larva, update days_since_active.
    //   - Active patch: reset counter to 0.
    //   - Inactive patch: increment counter. If > grace period, kill
    //     with probability LARVA_DESICCATION_DAILY_RATE.
    // Use reverse swap-with-last for compaction.
    int64_t i = soa_.n_alive - 1;
    while (i >= 0) {
        const size_t si = static_cast<size_t>(i);
        if (soa_.stage[si] == 0) {  // larvae only
            const int64_t pid = soa_.patch_id[si];
            if (active_by_id[pid]) {
                soa_.days_since_active[si] = 0;
            } else {
                ++soa_.days_since_active[si];
                if (soa_.days_since_active[si] > LARVA_DESICCATION_GRACE_DAYS) {
                    if (rng_.uniform_double() < LARVA_DESICCATION_DAILY_RATE) {
                        swap_with_last(soa_, i, soa_.n_alive);
                        --soa_.n_alive;
                    }
                }
            }
        }
        --i;
    }

    trim_soa(soa_, static_cast<size_t>(soa_.n_alive));
}

// ---------------------------------------------------------------------------
// Op 2.5: density-dependent larva mortality (Beverton-Holt)
// ---------------------------------------------------------------------------

void MosquitoSubmodel::larva_mortality_density(
    const std::vector<PatchState>& patch_states) {
    if (soa_.n_alive <= 0) return;

    // Build active set and larva count per patch.
    int64_t max_pid = -1;
    for (const auto& ps : patch_states) {
        if (ps.patch_id > max_pid) max_pid = ps.patch_id;
    }
    for (int64_t i = 0; i < soa_.n_alive; ++i) {
        const int64_t pid = soa_.patch_id[static_cast<size_t>(i)];
        if (pid > max_pid) max_pid = pid;
    }
    if (max_pid < 0) return;

    std::vector<uint8_t> active_by_id(static_cast<size_t>(max_pid) + 1, 0);
    for (const auto& ps : patch_states) {
        if (ps.activated) {
            active_by_id[static_cast<size_t>(ps.patch_id)] = 1;
        }
    }

    // Count larvae per active patch.
    std::vector<int64_t> larva_count(static_cast<size_t>(max_pid) + 1, 0);
    for (int64_t i = 0; i < soa_.n_alive; ++i) {
        const size_t si = static_cast<size_t>(i);
        if (soa_.stage[si] == 0 && active_by_id[soa_.patch_id[si]]) {
            ++larva_count[soa_.patch_id[si]];
        }
    }

    // Beverton-Holt survival: p = S0 * K / (K + alpha * N_larvae).
    const double K = static_cast<double>(K_MAX);
    int64_t i = soa_.n_alive - 1;
    while (i >= 0) {
        const size_t si = static_cast<size_t>(i);
        if (soa_.stage[si] == 0 && active_by_id[soa_.patch_id[si]]) {
            const int64_t N = larva_count[soa_.patch_id[si]];
            const double p = static_cast<double>(LARVA_BH_S0) * K /
                (K + static_cast<double>(overrides_.larva_bh_alpha) * static_cast<double>(N));
            if (rng_.uniform_double() >= p) {
                swap_with_last(soa_, i, soa_.n_alive);
                --soa_.n_alive;
            }
        }
        --i;
    }

    trim_soa(soa_, static_cast<size_t>(soa_.n_alive));
}

// ---------------------------------------------------------------------------
// Op 2: larva growth (age + EIP accumulation at active patches)
// ---------------------------------------------------------------------------

void MosquitoSubmodel::larva_growth(const std::vector<PatchState>& patch_states) {
    if (soa_.n_alive <= 0) return;

    // F1.c perf: replace std::unordered_map<int64_t, float> with a
    // flat std::vector<float> indexed by patch_id. We keep a parallel
    // std::vector<uint8_t> `active_by_id` to distinguish "inactive
    // patch (skip EIP update)" from "active patch with T == 0"
    // (accumulate_eip would add 0 to eip_progress, so the EIP is
    // unchanged in that case — but stage_age MUST still increment
    // only for active patches, matching the original
    // `active_temp.find() == end` skip). Sized by max_pid across
    // both patch_states and the SoA (see op 1 for the rationale).
    int64_t max_pid = -1;
    for (const auto& ps : patch_states) {
        if (ps.patch_id > max_pid) max_pid = ps.patch_id;
    }
    for (int64_t i = 0; i < soa_.n_alive; ++i) {
        const int64_t pid = soa_.patch_id[static_cast<size_t>(i)];
        if (pid > max_pid) max_pid = pid;
    }
    if (max_pid < 0) return;

    std::vector<uint8_t> active_by_id(static_cast<size_t>(max_pid) + 1, 0);
    std::vector<float>  temp_by_id (static_cast<size_t>(max_pid) + 1, 0.0f);
    bool any_active = false;
    for (const auto& ps : patch_states) {
        if (ps.activated) {
            active_by_id[static_cast<size_t>(ps.patch_id)] = 1;
            temp_by_id [static_cast<size_t>(ps.patch_id)] = ps.temp_d;
            any_active = true;
        }
    }
    if (!any_active) return;

    for (int64_t i = 0; i < soa_.n_alive; ++i) {
        const size_t si = static_cast<size_t>(i);
        if (soa_.stage[si] != 0) continue;
        const int64_t pid = soa_.patch_id[si];
        if (!active_by_id[pid]) continue;
        ++soa_.stage_age[si];
        soa_.eip_progress[si] = accumulate_eip(soa_.eip_progress[si],
                                                temp_by_id[pid]);
    }
}

// ---------------------------------------------------------------------------
// Op 3: EIP completion (larva -> adult)
// ---------------------------------------------------------------------------

void MosquitoSubmodel::larva_to_adult(const AOI& aoi,
                                       const std::vector<PatchState>& patch_states) {
    // Parity with the Python reference: promoted agents' lon/lat are
    // written to the patch cell centre (via aoi + transform.xy) so the
    // next dispersal step has a valid origin. Without this fix the
    // initial 80% of adults that do not disperse (u >= 0.2) would
    // retain (lon=0, lat=0) from the constructor and get bucketed into
    // the wrong cell by adult_density_by_cell (inflating suitability
    // at the (col=0, row=H-1) corner). Mirrors Python's
    // _larva_to_adult + birth() cell-centre placement.
    //
    // F1.c perf: replace std::unordered_map<int64_t, pair<int32_t,int32_t>>
    // with two flat vectors indexed by patch_id. The presence flag
    // preserves the original `it == end() → skip lon/lat update`
    // behaviour for agents whose birth-patch is not in today's
    // patch_states (e.g. a now-inactive dynamic patch from a
    // previous day). Sized by max_pid across both patch_states and
    // the SoA.
    int64_t max_pid = -1;
    for (const auto& ps : patch_states) {
        if (ps.patch_id > max_pid) max_pid = ps.patch_id;
    }
    for (int64_t i = 0; i < soa_.n_alive; ++i) {
        const int64_t pid = soa_.patch_id[static_cast<size_t>(i)];
        if (pid > max_pid) max_pid = pid;
    }
    if (max_pid < 0) return;

    std::vector<uint8_t> cell_present_by_id(static_cast<size_t>(max_pid) + 1, 0);
    std::vector<std::pair<int32_t, int32_t>> cell_by_id(
        static_cast<size_t>(max_pid) + 1, {0, 0});
    for (const auto& ps : patch_states) {
        cell_by_id[static_cast<size_t>(ps.patch_id)] = {ps.row, ps.col};
        cell_present_by_id[static_cast<size_t>(ps.patch_id)] = 1;
    }

    // Cell-centre math (matches from_bounds(*aoi.bbox, w, h) inverse).
    const int32_t W = (aoi.east > aoi.west)
        ? static_cast<int32_t>(aoi.cells_per_side()) : 1;
    const int32_t H = (aoi.north > aoi.south)
        ? static_cast<int32_t>(cells_per_side_h(aoi)) : 1;
    const double cell_w = (aoi.east - aoi.west) / static_cast<double>(W);
    const double cell_h = (aoi.north - aoi.south) / static_cast<double>(H);

    for (int64_t i = 0; i < soa_.n_alive; ++i) {
        const size_t si = static_cast<size_t>(i);
        if (soa_.stage[si] == 0 && soa_.eip_progress[si] >= EIP_THRESHOLD_GD) {
            soa_.stage[si] = 1;
            // The C++ implementation zeros eip_progress on promotion;
            // the Python reference does not. The state COG output is
            // identical (eip_progress is only read for larvae), but
            // document the divergence for the F1.e parity test.
            soa_.eip_progress[si] = 0.0f;
            // Write lon/lat to the patch cell centre. The patch_id
            // comes from the agent's own column; the (row, col) comes
            // from the per-day patch state cache. The presence flag
            // preserves the original skip-if-not-found behaviour for
            // agents whose birth-patch dropped out of patch_states.
            const int64_t pid = soa_.patch_id[si];
            if (cell_present_by_id[pid]) {
                const auto& rc = cell_by_id[pid];
                const int32_t r = rc.first;
                const int32_t c = rc.second;
                soa_.lon[si] = static_cast<float>(
                    aoi.west + (static_cast<double>(c) + 0.5) * cell_w);
                soa_.lat[si] = static_cast<float>(
                    aoi.north - (static_cast<double>(r) + 0.5) * cell_h);
            } else {
                // Patch inactive today — snap existing lon/lat to enclosing cell.
                auto [r, c] = LonLatToCell(
                    static_cast<double>(soa_.lon[si]),
                    static_cast<double>(soa_.lat[si]), aoi);
                soa_.lon[si] = static_cast<float>(
                    aoi.west + (static_cast<double>(c) + 0.5) * cell_w);
                soa_.lat[si] = static_cast<float>(
                    aoi.north - (static_cast<double>(r) + 0.5) * cell_h);
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Op 4: adult dispersal
// ---------------------------------------------------------------------------

void MosquitoSubmodel::adult_dispersal(const AOI& aoi) {
    for (int64_t i = 0; i < soa_.n_alive; ++i) {
        const size_t si = static_cast<size_t>(i);
        if (soa_.stage[si] != 1) continue;
        const double u = rng_.uniform_double();
        if (u < static_cast<double>(overrides_.disperse_prob)) {
            const DispOffset off = offset_m(
                rng_,
                static_cast<double>(soa_.lon[si]),
                static_cast<double>(soa_.lat[si]),
                static_cast<double>(overrides_.disperse_sigma_m),
                static_cast<double>(overrides_.disperse_max_m));
            soa_.lon[si] = static_cast<float>(static_cast<double>(soa_.lon[si]) + off.dlon);
            soa_.lat[si] = static_cast<float>(static_cast<double>(soa_.lat[si]) + off.dlat);
        }
        auto [r, c] = LonLatToCell(static_cast<double>(soa_.lon[si]),
                                    static_cast<double>(soa_.lat[si]), aoi);
        soa_.row[si] = r;
        soa_.col[si] = c;
    }
}

// ---------------------------------------------------------------------------
// Op 6: adult mortality (Lardeux thermo-dependent daily survival)
// ---------------------------------------------------------------------------

void MosquitoSubmodel::adult_mortality(
    const std::vector<PatchState>& patch_states) {
    if (soa_.n_alive <= 0) return;

    int32_t max_row = 0;
    int32_t max_col = 0;
    for (const auto& ps : patch_states) {
        if (ps.row > max_row) max_row = ps.row;
        if (ps.col > max_col) max_col = ps.col;
    }
    for (int64_t i = 0; i < soa_.n_alive; ++i) {
        const size_t si = static_cast<size_t>(i);
        if (soa_.stage[si] != 1) continue;
        if (soa_.row[si] > max_row) max_row = soa_.row[si];
        if (soa_.col[si] > max_col) max_col = soa_.col[si];
    }

    const int32_t grid_w = max_col + 1;
    const int32_t grid_h = max_row + 1;
    const size_t grid_size = static_cast<size_t>(grid_h) * static_cast<size_t>(grid_w);

    std::vector<uint8_t> has_temp(grid_size, 0);
    std::vector<float>   temp_grid(grid_size, 0.0f);
    for (const auto& ps : patch_states) {
        const size_t idx = static_cast<size_t>(ps.row) * static_cast<size_t>(grid_w)
                         + static_cast<size_t>(ps.col);
        has_temp[idx] = 1;
        temp_grid[idx] = ps.temp_d;
    }

    const double opt_c       = static_cast<double>(ADULT_OPT_C);
    const double sigma       = static_cast<double>(ADULT_SIGMA);
    const double two_sigma_sq = 2.0 * sigma * sigma;
    const double basal       = static_cast<double>(ADULT_DAILY_MORT_BASAL);

    int64_t i = soa_.n_alive - 1;
    while (i >= 0) {
        const size_t si = static_cast<size_t>(i);
        if (soa_.stage[si] == 1) {
            const int32_t r = soa_.row[si];
            const int32_t c = soa_.col[si];
            const size_t idx = static_cast<size_t>(r) * static_cast<size_t>(grid_w)
                             + static_cast<size_t>(c);
            double p_d;
            if (idx < grid_size && has_temp[idx]) {
                const double T = static_cast<double>(temp_grid[idx]);
                p_d = basal * std::exp(-((T - opt_c) * (T - opt_c)) / two_sigma_sq);
            } else {
                p_d = static_cast<double>(ADULT_DAILY_MORT_BASAL);
            }
            if (p_d < ADULT_MORT_FLOOR) p_d = ADULT_MORT_FLOOR;
            if (p_d > ADULT_MORT_CAP)   p_d = ADULT_MORT_CAP;
            if (rng_.uniform_double() >= p_d) {
                swap_with_last(soa_, i, soa_.n_alive);
                --soa_.n_alive;
            }
        }
        --i;
    }

    trim_soa(soa_, static_cast<size_t>(soa_.n_alive));
}

// ---------------------------------------------------------------------------
// Op 5: birth (binomial draw per active patch, cell-centre placement)
// ---------------------------------------------------------------------------

void MosquitoSubmodel::birth(const AOI& aoi,
                             const std::vector<PatchState>& patch_states) {
    if (patch_states.empty() || k_per_patch_ <= 0) return;
    const int32_t w = aoi.cells_per_side();
    const int32_t h = cells_per_side_h(aoi);
    if (w <= 0 || h <= 0) return;

    // Local hash for (row, col) keys. Defined here (instead of
    // including coordinator.hpp) to avoid a circular include.
    struct PairHash {
        std::size_t operator()(const std::pair<int32_t, int32_t>& p) const noexcept {
            const std::uint64_t packed =
                (static_cast<std::uint64_t>(static_cast<std::uint32_t>(p.first)) << 32) |
                 static_cast<std::uint32_t>(p.second);
            return std::hash<std::uint64_t>{}(packed);
        }
    };

    // Build (row, col) -> PatchState index map for fast lookup.
    // Adults lay eggs at their CURRENT (row, col) -- the cell they
    // dispersed to. The PatchState for that cell becomes the parent
    // of the new larvae; the cell's patch_id is inherited. This
    // replaces the old per-patch_id indexing, which meant adults
    // that dispersed 500m to a new cell still contributed births
    // to their old birth patch (dispersal was decorative).
    std::unordered_map<std::pair<int32_t, int32_t>, int32_t, PairHash>
        cell_to_state_idx;
    cell_to_state_idx.reserve(patch_states.size());
    for (size_t i = 0; i < patch_states.size(); ++i) {
        cell_to_state_idx[{patch_states[i].row, patch_states[i].col}] =
            static_cast<int32_t>(i);
    }

    // Count adults per CELL (not per patch_id). Adults at the same
    // (row, col) as an active PatchState contribute to births there.
    std::unordered_map<std::pair<int32_t, int32_t>, int32_t, PairHash>
        adult_count_by_cell;
    adult_count_by_cell.reserve(soa_.n_alive);
    for (int64_t i = 0; i < soa_.n_alive; ++i) {
        const size_t si = static_cast<size_t>(i);
        if (soa_.stage[si] != 1) continue;  // adults only
        const auto key = std::make_pair(soa_.row[si], soa_.col[si]);
        auto it = cell_to_state_idx.find(key);
        if (it == cell_to_state_idx.end()) continue;  // cell not a patch today
        if (!patch_states[static_cast<size_t>(it->second)].activated) continue;
        ++adult_count_by_cell[key];
    }

    struct PatchDraw {
        int64_t patch_id;
        int32_t row;
        int32_t col;
        int64_t n_birth;
    };
    std::vector<PatchDraw> draws;
    draws.reserve(adult_count_by_cell.size());

    int64_t total_birth = 0;
    for (const auto& kv : adult_count_by_cell) {
        const int64_t n_females = static_cast<int64_t>(kv.second) / 2;
        if (n_females <= 0) continue;
        const auto& ps = patch_states[static_cast<size_t>(cell_to_state_idx.at(kv.first))];
        // Temperature-dependent birth rate (Mordecai 2013)
        const double temp_c = static_cast<double>(ps.temp_d);
        const double rate_mod = birth_rate_modifier(temp_c);
        const double effective_fecundity = static_cast<double>(overrides_.birth_fecundity) * rate_mod;
        const int n = rng_.binomial(static_cast<int>(n_females),
                                    effective_fecundity);
        const int64_t nb = static_cast<int64_t>(n);
        if (nb <= 0) continue;
        draws.push_back({ps.patch_id, ps.row, ps.col, nb});
        total_birth += nb;
    }
    if (total_birth <= 0) return;

    const double cellW = (aoi.east - aoi.west) / static_cast<double>(w);
    const double cellH = (aoi.north - aoi.south) / static_cast<double>(h);

    const size_t old_cap = soa_.uid.size();
    const size_t new_cap = old_cap + static_cast<size_t>(total_birth);
    soa_.uid.reserve(new_cap);
    soa_.patch_id.reserve(new_cap);
    soa_.row.reserve(new_cap);
    soa_.col.reserve(new_cap);
    soa_.stage.reserve(new_cap);
    soa_.lon.reserve(new_cap);
    soa_.lat.reserve(new_cap);
    soa_.eip_progress.reserve(new_cap);
    soa_.stage_age.reserve(new_cap);
    soa_.days_since_active.reserve(new_cap);

    int64_t uid_counter = soa_.next_uid;
    for (const auto& d : draws) {
        const double lon = aoi.west  + (static_cast<double>(d.col) + 0.5) * cellW;
        const double lat = aoi.north - (static_cast<double>(d.row) + 0.5) * cellH;
        for (int64_t k = 0; k < d.n_birth; ++k) {
            soa_.uid.push_back(uid_counter++);
            soa_.patch_id.push_back(d.patch_id);
            soa_.row.push_back(d.row);
            soa_.col.push_back(d.col);
            soa_.stage.push_back(0);
            soa_.lon.push_back(static_cast<float>(lon));
            soa_.lat.push_back(static_cast<float>(lat));
            soa_.eip_progress.push_back(0.0f);
            soa_.stage_age.push_back(0);
            soa_.days_since_active.push_back(0);
        }
    }
    soa_.n_alive  += total_birth;
    soa_.next_uid  = uid_counter;
}

// ---------------------------------------------------------------------------
// Queries used by the coordinator
// ---------------------------------------------------------------------------

std::vector<std::pair<int64_t, int64_t>>
MosquitoSubmodel::density_by_patch() const {
    // F1.c perf: replace std::unordered_map<int64_t, int64_t> with a
    // flat std::vector<int64_t> indexed by patch_id. The single
    // pass over the SoA is now a tight ++counts[pid] (cache-
    // friendly). The result is collected by scanning the vector
    // for non-zero entries; for sparse pids (which is the common
    // case) this is cheaper than iterating a hash table. Sized
    // by the max pid in the SoA (an agent's birth-patch may be a
    // now-inactive dynamic patch).
    if (soa_.n_alive <= 0) return {};
    int64_t max_pid = -1;
    for (int64_t i = 0; i < soa_.n_alive; ++i) {
        const int64_t pid = soa_.patch_id[static_cast<size_t>(i)];
        if (pid > max_pid) max_pid = pid;
    }
    if (max_pid < 0) return {};

    std::vector<int64_t> counts(static_cast<size_t>(max_pid) + 1, 0);
    for (int64_t i = 0; i < soa_.n_alive; ++i) {
        const size_t si = static_cast<size_t>(i);
        ++counts[soa_.patch_id[si]];
    }
    std::vector<std::pair<int64_t, int64_t>> result;
    result.reserve(static_cast<size_t>(max_pid) + 1);
    for (int64_t pid = 0; pid <= max_pid; ++pid) {
        const int64_t c = counts[static_cast<size_t>(pid)];
        if (c > 0) result.emplace_back(pid, c);
    }
    // result is already in ascending pid order (we iterated pid 0..max_pid).
    return result;
}

std::vector<std::tuple<int32_t, int32_t, int64_t>>
MosquitoSubmodel::adult_density_by_cell(const AOI& aoi) const {
    const int32_t w = aoi.cells_per_side();
    const int32_t h = cells_per_side_h(aoi);
    if (w <= 0 || h <= 0) return {};

    const double cellW = (aoi.east - aoi.west) / static_cast<double>(w);
    const double cellH = (aoi.north - aoi.south) / static_cast<double>(h);

    // F1.c perf: replace std::unordered_map<int64_t, int64_t> (with
    // packed (row, col) composite key) with a flat
    // std::vector<int64_t> indexed by `row * w + col`. The SoA
    // inner loop is now a tight ++counts[idx] (cache-friendly).
    // The result is collected by scanning the vector in (row, col)
    // order — no final sort needed since we iterate in the same
    // order we want to emit.
    const size_t n_cells = static_cast<size_t>(w) * static_cast<size_t>(h);
    std::vector<int64_t> counts(n_cells, 0);

    for (int64_t i = 0; i < soa_.n_alive; ++i) {
        const size_t si = static_cast<size_t>(i);
        if (soa_.stage[si] != 1) continue;
        int32_t col = static_cast<int32_t>(
            (static_cast<double>(soa_.lon[si]) - aoi.west) / cellW);
        int32_t row = static_cast<int32_t>(
            (aoi.north - static_cast<double>(soa_.lat[si])) / cellH);
        if (col < 0)      col = 0;
        if (col >= w)     col = w - 1;
        if (row < 0)      row = 0;
        if (row >= h)     row = h - 1;
        const size_t idx = static_cast<size_t>(row) *
                               static_cast<size_t>(w) +
                           static_cast<size_t>(col);
        ++counts[idx];
    }

    std::vector<std::tuple<int32_t, int32_t, int64_t>> result;
    result.reserve(n_cells);
    for (int32_t row = 0; row < h; ++row) {
        for (int32_t col = 0; col < w; ++col) {
            const size_t idx = static_cast<size_t>(row) *
                                   static_cast<size_t>(w) +
                               static_cast<size_t>(col);
            const int64_t c = counts[idx];
            if (c > 0) result.emplace_back(row, col, c);
        }
    }
    // result is already in (row, col) ascending order.
    return result;
}

}  // namespace mal_abm_fast
