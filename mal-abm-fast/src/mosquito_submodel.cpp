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
#include "mal_abm_fast/dispersal.hpp"
#include "mal_abm_fast/seeding.hpp"
#include "mal_abm_fast/aquatic_cohort_bank.hpp"
#include "mal_abm_fast/gonotrophic_cycle.hpp"
#include "mal_abm_fast/bite_ledger.hpp"
#include "mal_abm_fast/multirate_scheduler.hpp"

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
    std::swap(soa.sex[i],          soa.sex[n - 1]);
    std::swap(soa.lon[i],          soa.lon[n - 1]);
    std::swap(soa.lat[i],          soa.lat[n - 1]);
    std::swap(soa.development_progress[i], soa.development_progress[n - 1]);
    std::swap(soa.parasite_eip_progress[i], soa.parasite_eip_progress[n - 1]);
    std::swap(soa.aquatic_stage[i], soa.aquatic_stage[n - 1]);
    std::swap(soa.larval_instar[i], soa.larval_instar[n - 1]);
    std::swap(soa.stage_age[i],    soa.stage_age[n - 1]);
    std::swap(soa.days_since_active[i], soa.days_since_active[n - 1]);
    std::swap(soa.gonotrophic_state[i], soa.gonotrophic_state[n - 1]);
    std::swap(soa.gonotrophic_timer[i], soa.gonotrophic_timer[n - 1]);
    std::swap(soa.feeding_success[i],   soa.feeding_success[n - 1]);
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
    soa.sex.resize(new_size);
    soa.lon.resize(new_size);
    soa.lat.resize(new_size);
    soa.development_progress.resize(new_size);
    soa.parasite_eip_progress.resize(new_size);
    soa.aquatic_stage.resize(new_size);
    soa.larval_instar.resize(new_size);
    soa.stage_age.resize(new_size);
    soa.days_since_active.resize(new_size);
    soa.gonotrophic_state.resize(new_size);
    soa.gonotrophic_timer.resize(new_size);
    soa.feeding_success.resize(new_size);
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

    // G3 lifecycle: seed 10% adults directly in SoA, 90% eggs in
    // the aquatic cohort bank. Adults start with stage=1 so they
    // disperse on day 1. Eggs develop through the cohort bank's
    // thermal lifecycle and emerge as adults over time.
    //
    // NOTE: the legacy constructor does NOT have AOI context, so
    // adults are placed at (lon=0, lat=0). The first adult_dispersal
    // pass will snap them to the nearest cell. This is the same
    // behaviour as the old detection-based constructor.
    constexpr float UNIFORM_ADULT_FRAC = 0.10f;
    int64_t total_adults = 0;
    int64_t total_eggs = 0;
    for (int64_t p = 0; p < np; ++p) {
        const int64_t k = per_patch[static_cast<size_t>(p)];
        const int64_t n_adults = static_cast<int64_t>(std::llround(
            static_cast<double>(k) * UNIFORM_ADULT_FRAC));
        const int64_t n_eggs = k - n_adults;
        // Adults: stage=1, ready to disperse
        for (int64_t j = 0; j < n_adults; ++j) {
            soa_.uid.push_back(static_cast<int64_t>(soa_.uid.size()));
            soa_.patch_id.push_back(p);
            soa_.row.push_back(0);
            soa_.col.push_back(0);
            soa_.stage.push_back(1);  // adult
            soa_.sex.push_back((rng_.uniform_double() < 0.5) ? 0 : 1);
            soa_.lon.push_back(0.0f);
            soa_.lat.push_back(0.0f);
            soa_.development_progress.push_back(0.0f);
            soa_.parasite_eip_progress.push_back(0.0f);
            soa_.aquatic_stage.push_back(0);
            soa_.larval_instar.push_back(0);
            soa_.stage_age.push_back(0);
            soa_.days_since_active.push_back(0);
            soa_.gonotrophic_state.push_back(
                static_cast<uint8_t>(GonotrophicState::TENERAL));
            soa_.gonotrophic_timer.push_back(0);
            soa_.feeding_success.push_back(0.0f);
        }
        // Eggs in cohort bank
        if (n_eggs > 0) {
            cohort_bank_.add_eggs(p, n_eggs);
        }
        total_adults += n_adults;
        total_eggs += n_eggs;
    }
    soa_.n_alive  = total_adults;
    soa_.next_uid = total_adults;
}

// ---------------------------------------------------------------------------
// Detection-based constructor
// ---------------------------------------------------------------------------
//
// For each `SeedInstruction`:
//   * `n_adults` agents are added with `stage = 1` (adult) and
//     `development_progress = EIP_THRESHOLD_GD` so the first
//     `larva_to_adult` pass does NOT re-promote them — they are
//     already adult, ready to disperse on day 1.
//   * `n_larvae` agents are added with `stage = 0` (larva) and
//     `development_progress = 0`. They must accumulate
//     growing-degree-days before promotion (matches the legacy
//     "seed K*init_frac larvae" path).
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
    soa_.sex.reserve(cap);
    soa_.lon.reserve(cap);
    soa_.lat.reserve(cap);
    soa_.development_progress.reserve(cap);
    soa_.parasite_eip_progress.reserve(cap);
    soa_.aquatic_stage.reserve(cap);
    soa_.larval_instar.reserve(cap);
    soa_.stage_age.reserve(cap);
    soa_.days_since_active.reserve(cap);
    soa_.gonotrophic_state.reserve(cap);
    soa_.gonotrophic_timer.reserve(cap);
    soa_.feeding_success.reserve(cap);

    for (const auto& inst : instructions) {
        // Adults: ready to disperse immediately.
        for (int32_t j = 0; j < inst.n_adults; ++j) {
            soa_.uid.push_back(static_cast<int64_t>(soa_.uid.size()));
            soa_.patch_id.push_back(inst.patch_id);
            soa_.row.push_back(inst.row);
            soa_.col.push_back(inst.col);
            soa_.stage.push_back(1);  // adult
            soa_.sex.push_back((rng_.uniform_double() < 0.5) ? 0 : 1);
            soa_.lon.push_back(static_cast<float>(inst.lon));
            soa_.lat.push_back(static_cast<float>(inst.lat));
            soa_.development_progress.push_back(0.0f);
            soa_.parasite_eip_progress.push_back(0.0f);
            soa_.aquatic_stage.push_back(0);
            soa_.larval_instar.push_back(0);
            soa_.stage_age.push_back(0);
            soa_.days_since_active.push_back(0);
            soa_.gonotrophic_state.push_back(
                static_cast<uint8_t>(GonotrophicState::TENERAL));
            soa_.gonotrophic_timer.push_back(0);
            soa_.feeding_success.push_back(0.0f);
        }
        // Larvae: seed as eggs in the aquatic cohort bank.
        // The cohort bank will develop them through Egg→L1→L2→L3→L4→Pupa→Adult.
        if (inst.n_larvae > 0) {
            cohort_bank_.add_eggs(inst.patch_id, static_cast<int64_t>(inst.n_larvae));
        }
    }
    soa_.n_alive  = static_cast<int64_t>(soa_.uid.size());
    soa_.next_uid = static_cast<int64_t>(soa_.uid.size());
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
    // -- debug snapshot: pre-day counts
    const int64_t day_idx = day_counter_++;
    int64_t pre_n_alive  = 0;
    int64_t pre_n_adults = 0;
    bool    want_log    = false;
    if (debug_population_) {
        pre_n_alive  = soa_.n_alive;
        pre_n_adults = count_stage(soa_, 1);
        want_log = (day_idx < 10) || (day_idx % 5 == 0);
    }

    // -- G3 lifecycle: aquatic cohort bank handles egg/larva/pupa --
    // 1. Advance aquatic development, mortality, promotions
    cohort_bank_.advance_day(patch_states, overrides_);
    // 2. Collect emerged adults from completed pupae
    const auto emergence = cohort_bank_.collect_emergence(patch_states);
    // 3. Add emerged adults to MosquitoSoA
    int64_t n_emerged = 0;
    for (const auto& ev : emergence) {
        for (int64_t k = 0; k < ev.n_adults; ++k) {
            soa_.uid.push_back(soa_.next_uid++);
            soa_.patch_id.push_back(ev.patch_id);
            soa_.row.push_back(ev.row);
            soa_.col.push_back(ev.col);
            soa_.stage.push_back(1);  // adult
            soa_.sex.push_back((rng_.uniform_double() < 0.5) ? 0 : 1);
            // Snap lon/lat to cell centre
            const int32_t w = aoi.cells_per_side();
            const int32_t h = cells_per_side_h(aoi);
            const double cellW = (aoi.east - aoi.west) / static_cast<double>(w);
            const double cellH = (aoi.north - aoi.south) / static_cast<double>(h);
            soa_.lon.push_back(static_cast<float>(
                aoi.west + (static_cast<double>(ev.col) + 0.5) * cellW));
            soa_.lat.push_back(static_cast<float>(
                aoi.north - (static_cast<double>(ev.row) + 0.5) * cellH));
            soa_.development_progress.push_back(0.0f);
            soa_.parasite_eip_progress.push_back(0.0f);
            soa_.aquatic_stage.push_back(0);
            soa_.larval_instar.push_back(0);
            soa_.stage_age.push_back(0);
            soa_.days_since_active.push_back(0);
            soa_.gonotrophic_state.push_back(
                static_cast<uint8_t>(GonotrophicState::TENERAL));
            soa_.gonotrophic_timer.push_back(0);
            soa_.feeding_success.push_back(0.0f);
        }
        n_emerged += ev.n_adults;
    }
    soa_.n_alive = static_cast<int64_t>(soa_.uid.size());

    // -- G4: gonotrophic cycle (females only) --
    bite_ledger_.reset_day();
    int64_t n_feeding_attempts = 0;
    int64_t n_successful_feeds = 0;
    int64_t n_ovipositions = 0;

    for (int64_t i = 0; i < soa_.n_alive; ++i) {
        const size_t si = static_cast<size_t>(i);
        if (soa_.stage[si] != 1) continue;
        if (soa_.sex[si] != 1) continue;  // females only

        auto g_state = static_cast<GonotrophicState>(soa_.gonotrophic_state[si]);
        auto& g_timer = soa_.gonotrophic_timer[si];
        soa_.feeding_success[si] = 0.0f;

        // Daily state transition
        const bool wants_oviposit = advance_gonotrophic_one_day(
            g_state, g_timer, gonotrophic_params_);
        soa_.gonotrophic_state[si] = static_cast<uint8_t>(g_state);

        if (wants_oviposit) {
            // Egg batch: use mean value (binomial(105, 0.5) ≈ 52).
            // Stochastic version will use Prng in a later gate.
            int32_t eggs = gonotrophic_params_.egg_batch_mean;
            if (eggs < gonotrophic_params_.egg_batch_min)
                eggs = gonotrophic_params_.egg_batch_min;
            if (eggs > gonotrophic_params_.egg_batch_max)
                eggs = gonotrophic_params_.egg_batch_max;
            // Deposit eggs in the aquatic cohort bank.
            cohort_bank_.add_eggs(soa_.patch_id[si],
                                  static_cast<int64_t>(eggs));
            g_state = GonotrophicState::HOST_SEEKING;
            g_timer = 0;
            soa_.gonotrophic_state[si] = static_cast<uint8_t>(g_state);
            soa_.gonotrophic_timer[si] = g_timer;
            n_ovipositions += eggs;
        }

        // Nightly host-seeking: attempt feeding if HOST_SEEKING
        if (g_state == GonotrophicState::HOST_SEEKING) {
            n_feeding_attempts++;
            if (host_landscape_ && host_seeking_) {
                // Use spatial host-seeking model with real host landscape.
                auto attractions = host_seeking_->compute_attraction(
                    soa_.row[si], soa_.col[si], *host_landscape_, aoi);
                const HostType host = host_seeking_->select_host(attractions, rng_);
                bite_ledger_.record_attempt(
                    soa_.row[si], soa_.col[si], host);
                // Check if any hosts are present (attraction field non-empty).
                if (!attractions.empty()) {
                    g_state = GonotrophicState::BLOOD_FED;
                    g_timer = 0;
                    soa_.gonotrophic_state[si] = static_cast<uint8_t>(g_state);
                    soa_.gonotrophic_timer[si] = g_timer;
                    soa_.feeding_success[si] = 1.0f;
                    n_successful_feeds++;
                    bite_ledger_.record_success(
                        soa_.row[si], soa_.col[si], host);
                }
            } else {
                // Fallback: deterministic feeding with default host (HUMAN).
                bite_ledger_.record_attempt(
                    soa_.row[si], soa_.col[si], HostType::HUMAN);
                g_state = GonotrophicState::BLOOD_FED;
                g_timer = 0;
                soa_.gonotrophic_state[si] = static_cast<uint8_t>(g_state);
                soa_.gonotrophic_timer[si] = g_timer;
                soa_.feeding_success[si] = 1.0f;
                n_successful_feeds++;
                bite_ledger_.record_success(
                    soa_.row[si], soa_.col[si], HostType::HUMAN);
            }
        }
    }

    // 4. Adult dispersal
    adult_dispersal(aoi);
    const int64_t pre_mort_n_alive = soa_.n_alive;
    // 5. Adult mortality (Lardeux)
    adult_mortality(patch_states);
    const int64_t post_mort_n_alive = soa_.n_alive;

    // Compute stats
    const int64_t post_n_adults = count_stage(soa_, 1);
    const int64_t n_deaths      = pre_mort_n_alive - post_mort_n_alive;

    last_day_stats_.day          = day_idx;
    last_day_stats_.n_alive      = post_mort_n_alive;
    last_day_stats_.n_adults     = post_n_adults;
    last_day_stats_.n_larvae     = 0;  // larvae are in cohort bank now
    last_day_stats_.n_births     = n_emerged;  // emergence is the only "birth"
    last_day_stats_.n_deaths     = n_deaths;
    last_day_stats_.n_maturation = 0;
    last_day_stats_.n_eggs       = cohort_bank_.count_by_stage(AquaticStage::EGG);
    last_day_stats_.n_pupae      = cohort_bank_.count_by_stage(AquaticStage::PUPA);
    last_day_stats_.n_emerged    = n_emerged;
    last_day_stats_.eip_frac = (post_mort_n_alive > 0)
        ? static_cast<float>(post_n_adults) / static_cast<float>(post_mort_n_alive)
        : 0.0f;
    // G4: gonotrophic stats
    last_day_stats_.n_feeding_attempts = n_feeding_attempts;
    last_day_stats_.n_successful_feeds = n_successful_feeds;
    last_day_stats_.n_ovipositions     = n_ovipositions;

    if (debug_population_ && want_log) {
        const float   temp_d        = seeding_temp_d(
            patch_states, debug_seeding_row_, debug_seeding_col_);
        const float   p_d           = lardeux_p_d(temp_d);
        const bool    in_states     = !std::isnan(static_cast<double>(temp_d));
        std::fprintf(stderr,
            "abm_debug: day=%lld n_alive=%lld n_adults=%lld "
            "n_eggs=%lld n_pupae=%lld n_emerged=%lld "
            "n_feed_att=%lld n_feed_ok=%lld n_ovi=%lld "
            "seeding_in_states=%s seeding_temp_d=%.2f "
            "p_d=%.4f n_deaths=%lld\n",
            static_cast<long long>(day_idx),
            static_cast<long long>(post_mort_n_alive),
            static_cast<long long>(post_n_adults),
            static_cast<long long>(last_day_stats_.n_eggs),
            static_cast<long long>(last_day_stats_.n_pupae),
            static_cast<long long>(n_emerged),
            static_cast<long long>(n_feeding_attempts),
            static_cast<long long>(n_successful_feeds),
            static_cast<long long>(n_ovipositions),
            in_states ? "yes" : "no",
            static_cast<double>(temp_d),
            static_cast<double>(p_d),
            static_cast<long long>(n_deaths));
    }
}

// ---------------------------------------------------------------------------
// Adult dispersal (Op 4 — unchanged from F1.b)
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
