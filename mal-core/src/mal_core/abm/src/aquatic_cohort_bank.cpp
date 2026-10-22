// SPDX-License-Identifier: MIT
// aquatic_cohort_bank.cpp — Cohort-based aquatic lifecycle implementation.
//
// Lifecycle stages: Egg → Larva L1 → L2 → L3 → L4 → Pupa → Adult
//
// Daily update order within advance_day():
//   1. Desiccation (eggs + early instars at inactive patches)
//   2. Stage mortality (egg ~8%/day, pupa ~5%/day, density-dependent for larvae)
//   3. Development (thermal curves from thermal_responses.hpp)
//   4. Promotion (Egg→L1 when dev>=1, L1→L2, L2→L3, L3→L4, L4→Pupa)
//
// Emergence is collected AFTER advance_day() via collect_emergence().
#include "mal_abm_fast/aquatic_cohort_bank.hpp"

#include "mal_abm_fast/config.hpp"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <numeric>
#include <random>
#include <stdexcept>
#include <unordered_map>
#include <unordered_set>
#include <utility>

#include "mal_abm_fast/aquatic_stress.hpp"
#include "mal_abm_fast/thermal_responses.hpp"

namespace mal_abm_fast {

// Review-a3 P1-1: egg/pupa daily mortality live in model_constants.yaml
// (aquatic_stages.egg_daily_mort / pupa_daily_mort); accessors below read
// the load_config() singleton — no compiled defaults.
inline float EGG_DAILY_MORT() {
    return static_cast<float>(load_config().aquatic_stages.egg_daily_mort);
}
inline float PUPA_DAILY_MORT() {
    return static_cast<float>(load_config().aquatic_stages.pupa_daily_mort);
}

// Instar duration fraction: each instar is ~25% of total larval duration.
// When a larva's development reaches 1.0 within an instar, it
// advances to the next instar (L1→L2→L3→L4) with development reset to 0.
// When L4 reaches 1.0, it pupates.

// ---------------------------------------------------------------------------
// Rebuild index after structural changes (compact, etc.)
// ---------------------------------------------------------------------------
void AquaticCohortBank::rebuild_index() {
    index_.clear();
    for (size_t i = 0; i < cohorts_.size(); ++i) {
        const auto& c = cohorts_[i];
        const uint8_t s = static_cast<uint8_t>(c.stage);
        index_[{c.patch_id, {s, c.larval_instar}}] = i;
    }
}

// ---------------------------------------------------------------------------
// find_or_create
// ---------------------------------------------------------------------------
AquaticCohort& AquaticCohortBank::find_or_create(
    int64_t patch_id, AquaticStage stage, uint8_t instar) {
    const uint8_t s = static_cast<uint8_t>(stage);
    const CohortKey key{patch_id, {s, instar}};
    auto it = index_.find(key);
    if (it != index_.end()) {
        return cohorts_[it->second];
    }
    // Create new cohort
    AquaticCohort c;
    c.patch_id      = patch_id;
    c.stage         = stage;
    c.larval_instar = instar;
    c.development   = 0.0f;
    c.count         = 0;
    c.mean_age_days = 0.0f;
    const size_t idx = cohorts_.size();
    cohorts_.push_back(c);
    index_[key] = idx;
    return cohorts_[idx];
}

// ---------------------------------------------------------------------------
// compact — remove cohorts with count <= 0
// ---------------------------------------------------------------------------
void AquaticCohortBank::compact() {
    size_t write = 0;
    for (size_t read = 0; read < cohorts_.size(); ++read) {
        if (cohorts_[read].count > 0) {
            if (write != read) {
                cohorts_[write] = std::move(cohorts_[read]);
            }
            ++write;
        }
    }
    cohorts_.resize(write);
    rebuild_index();
}

// ---------------------------------------------------------------------------
// add_eggs
// ---------------------------------------------------------------------------
void AquaticCohortBank::add_eggs(int64_t patch_id, int64_t count) {
    if (count <= 0) return;
    auto& c = find_or_create(patch_id, AquaticStage::EGG, 0);
    c.count += count;
}

// ---------------------------------------------------------------------------
// seed_stage — age-structured seeding for detection-based constructor
// ---------------------------------------------------------------------------
void AquaticCohortBank::seed_stage(
    int64_t patch_id, AquaticStage stage,
    uint8_t instar, int64_t count, float development) {
    if (count <= 0) return;
    auto& c = find_or_create(patch_id, stage, instar);
    c.count += count;
    // Set development progress (weighted average if cohort already exists).
    if (c.count > 0) {
        const float old_count = static_cast<float>(c.count - count);
        c.development = (c.development * old_count +
                         development * static_cast<float>(count)) /
                        static_cast<float>(c.count);
    }
}

// ---------------------------------------------------------------------------
// patch_to_cell helper
// ---------------------------------------------------------------------------
bool AquaticCohortBank::patch_to_cell(
    int64_t patch_id, const std::vector<PatchState>& ps,
    int32_t& row, int32_t& col) const {
    for (const auto& s : ps) {
        if (s.patch_id == patch_id) {
            row = s.row;
            col = s.col;
            return true;
        }
    }
    return false;
}

// ---------------------------------------------------------------------------
// desiccation — kill eggs and early instars at dry patches (preserved
// from the M14 pool module; plan 01 §7).
//
// Driven by the proxy-habitat dry-day streak carried in
// PatchState.habitat_dry_days: consecutive days with S <= ACTIVATION_MIN.
// The desiccation_rate() function from aquatic_stress.hpp handles the
// grace period and ramp.
// ---------------------------------------------------------------------------
void AquaticCohortBank::desiccation(
    const std::vector<PatchState>& patch_states) {
    // Build lookup: patch_id → (dry_days, activated).
    std::unordered_map<int64_t, int> dry_by_patch;
    for (const auto& ps : patch_states) {
        dry_by_patch[ps.patch_id] = ps.habitat_dry_days;
    }

    for (auto& c : cohorts_) {
        if (c.count <= 0) continue;
        // Only eggs and early instars (L1, L2) are vulnerable to desiccation
        bool vulnerable = false;
        if (c.stage == AquaticStage::EGG) {
            vulnerable = true;
        } else if (c.stage == AquaticStage::LARVA &&
                   c.larval_instar <=
                       load_config().aquatic_stress.vulnerable_instar_max) {
            vulnerable = true;
        }
        if (!vulnerable) continue;

        auto it = dry_by_patch.find(c.patch_id);
        if (it == dry_by_patch.end()) continue;  // patch not tracked
        const float rate = desiccation_rate(it->second);
        if (rate <= 0.0f) continue;

        const int64_t deaths = static_cast<int64_t>(
            std::llround(static_cast<double>(c.count) * rate));
        c.count -= std::min(deaths, c.count);
    }
}

// ---------------------------------------------------------------------------
// washout — flush aquatic cohorts during heavy rain (M14)
//
// Heavy rain (>= POOL_RAIN_WASH_MM) washes larvae out of pools.
// Applies to eggs, larvae, and pupae. Adult washout is NOT modelled
// (mosquitoes are not aquatic; they can shelter).
// ---------------------------------------------------------------------------
void AquaticCohortBank::washout(
    const std::vector<PatchState>& patch_states) {
    // Build lookup: patch_id → rain_d
    std::unordered_map<int64_t, float> rain_by_patch;
    for (const auto& ps : patch_states) {
        rain_by_patch[ps.patch_id] = ps.rain_d;
    }

    std::mt19937_64 rng(load_config().rng.aquatic_seed_washout);
    for (auto& c : cohorts_) {
        if (c.count <= 0) continue;
        auto it = rain_by_patch.find(c.patch_id);
        if (it == rain_by_patch.end()) continue;
        const float frac = washout_fraction(it->second);
        if (frac <= 0.0f) continue;

        const double p = static_cast<double>(frac);
        std::binomial_distribution<int64_t> dist(c.count, p);
        const int64_t flushed = dist(rng);
        c.count -= std::min(flushed, c.count);
    }
}

// ---------------------------------------------------------------------------
// stage_mortality — egg and pupa background mortality
// ---------------------------------------------------------------------------
void AquaticCohortBank::stage_mortality(
    const std::vector<PatchState>& /*patch_states*/) {
    // Use a simple deterministic kill fraction per stage.
    // For eggs and pupa: kill a fraction of the cohort each day.
    // Larva mortality is handled separately by larva_mortality_density.
    std::mt19937_64 rng(load_config().rng.aquatic_seed_stage_mortality);
    for (auto& c : cohorts_) {
        if (c.count <= 0) continue;
        float mort_rate = 0.0f;
        if (c.stage == AquaticStage::EGG) {
            mort_rate = EGG_DAILY_MORT();
        } else if (c.stage == AquaticStage::PUPA) {
            mort_rate = PUPA_DAILY_MORT();
        } else {
            continue;  // larvae handled elsewhere
        }
        // Binomial draw for stochastic mortality
        std::binomial_distribution<int64_t> dist(c.count, mort_rate);
        const int64_t deaths = dist(rng);
        c.count -= std::min(deaths, c.count);
    }
}

// ---------------------------------------------------------------------------
// larva_mortality_density — Beverton-Holt density-dependent mortality
// plus the species salinity factor (Fase 6).
//
// Density-dependent survival is multiplied by the species' salinity
// suitability s_hat = salinity_suitability(species_, patch.salinity_ppt)
// as an INDEPENDENT factor: salinity only gates species compatibility of
// the water, not its presence. With the default coluzzii params and
// freshwater patches (salinity 0 psu) s_hat == 1.0.
//
// Contract v3.0/4.0: the per-patch capacity is the ABSOLUTE K[i, s, t]
// (K_ref × cell_area_km2 × S, configured in the PatchState.k_habitat
// field by the coordinator). Capacity contract (plan 03-retirada-k-max):
//   K > 0    → Beverton-Holt survival p = S0 × K / (K + α × N)
//   K == 0   → explicit zero capacity: p = 0 (all larvae of the patch
//              die this day; pupae/eggs are NOT touched by this op)
//   K < 0, NaN, +inf or missing patch state → hard error; no fallback
//              capacity is ever invented. The retired K_eff view and
//              the K_MAX fallback are gone.
// ---------------------------------------------------------------------------
void AquaticCohortBank::larva_mortality_density(
    const std::vector<PatchState>& patch_states,
    const RuntimeOverrides& overrides) {
    // Validate α once: finite and non-negative (0/0 guard lives in the
    // K==0 branch, which fires before the α division matters).
    if (!std::isfinite(overrides.larva_bh_alpha) ||
        overrides.larva_bh_alpha < 0.0f) {
        throw std::runtime_error(
            "larva_mortality_density: larva_bh_alpha must be finite and "
            "non-negative (got " +
            std::to_string(overrides.larva_bh_alpha) + ")");
    }

    // Aggregate larva count per patch across all instars
    std::unordered_map<int64_t, int64_t> larva_per_patch;
    for (const auto& c : cohorts_) {
        if (c.stage == AquaticStage::LARVA && c.count > 0) {
            larva_per_patch[c.patch_id] += c.count;
        }
    }

    // Patch salinity lookup (missing patch => aquatic_stages.
    // salinity_missing_psu => s_hat = 1.0 for the default 0.0 anchor)
    std::unordered_map<int64_t, float> salinity_by_patch;
    // Patch daily capacity lookup (plan §5.4: absolute K per cell).
    std::unordered_map<int64_t, float> capacity_by_patch;
    std::unordered_set<int64_t> known_patches;
    for (const auto& ps : patch_states) {
        salinity_by_patch[ps.patch_id] = ps.salinity_ppt;
        capacity_by_patch[ps.patch_id] = ps.k_habitat;
        known_patches.insert(ps.patch_id);
    }

    std::mt19937_64 rng(load_config().rng.aquatic_seed_larva_mortality);
    for (auto& c : cohorts_) {
        if (c.count <= 0 || c.stage != AquaticStage::LARVA) continue;
        const int64_t N = larva_per_patch[c.patch_id];

        double K_patch;
        if (known_patches.find(c.patch_id) == known_patches.end()) {
            throw std::runtime_error(
                "larva_mortality_density: cohort patch " +
                std::to_string(c.patch_id) +
                " has no PatchState for today — cannot resolve capacity");
        }
        const float k_raw = capacity_by_patch.at(c.patch_id);
        if (!std::isfinite(k_raw) || k_raw < 0.0f) {
            throw std::runtime_error(
                "larva_mortality_density: patch " +
                std::to_string(c.patch_id) +
                " has invalid k_habitat " + std::to_string(k_raw) +
                " (negative, NaN or +inf) — no fallback capacity");
        }
        K_patch = static_cast<double>(k_raw);

        double p;
        if (K_patch <= 0.0) {
            // Explicit zero capacity: no water, no larval survival.
            p = 0.0;
        } else {
            p = static_cast<double>(LARVA_BH_S0()) * K_patch /
                (K_patch + static_cast<double>(overrides.larva_bh_alpha) *
                               static_cast<double>(N));
        }
        // Independent salinity suitability multiplier (Fase 6).
        auto it = salinity_by_patch.find(c.patch_id);
        const float psu = (it == salinity_by_patch.end())
            ? static_cast<float>(load_config()
                                     .aquatic_stages.salinity_missing_psu)
            : it->second;
        const float s_hat = salinity_suitability(species_, psu);
        if (s_hat < 1.0f) p *= static_cast<double>(s_hat);
        // Binomial survival
        std::binomial_distribution<int64_t> dist(c.count, p);
        c.count = dist(rng);
    }
}

// ---------------------------------------------------------------------------
// promote_stages — advance development, transition instars/stages
// ---------------------------------------------------------------------------
void AquaticCohortBank::promote_stages(
    const std::vector<PatchState>& patch_states) {
    std::unordered_map<int64_t, float> temp_by_patch;
    for (const auto& ps : patch_states) {
        if (ps.activated) {
            temp_by_patch[ps.patch_id] = ps.temp_d;
        }
    }

    struct Promotion {
        int64_t patch_id;
        AquaticStage from_stage;
        uint8_t from_instar;
    };
    std::vector<Promotion> promotions;

    for (auto& c : cohorts_) {
        if (c.count <= 0) continue;
        auto it = temp_by_patch.find(c.patch_id);
        if (it == temp_by_patch.end()) continue;
        const float temp_c = it->second;
        c.mean_age_days += 1.0f;
        float rate = 0.0f;
        switch (c.stage) {
            case AquaticStage::EGG:   rate = egg_development_rate(temp_c); break;
            case AquaticStage::LARVA: rate = larva_development_rate(temp_c); break;
            case AquaticStage::PUPA:  rate = pupa_development_rate(temp_c); break;
        }
        c.development += rate;
        if (c.development >= 1.0f) {
            promotions.push_back({c.patch_id, c.stage, c.larval_instar});
        }
    }

    for (const auto& p : promotions) {
        const uint8_t src_s = static_cast<uint8_t>(p.from_stage);
        const CohortKey src_key{p.patch_id, {src_s, p.from_instar}};
        auto src_it = index_.find(src_key);
        if (src_it == index_.end()) continue;
        const size_t src_idx = src_it->second;
        if (cohorts_[src_idx].count <= 0) continue;

        if (p.from_stage == AquaticStage::PUPA) continue;

        AquaticStage next_stage;
        uint8_t next_instar;
        if (p.from_stage == AquaticStage::EGG) {
            next_stage = AquaticStage::LARVA;
            next_instar = 1;
        } else if (p.from_instar < static_cast<uint8_t>(
                       load_config().aquatic_stages.last_larval_instar)) {
            next_stage = AquaticStage::LARVA;
            next_instar = static_cast<uint8_t>(p.from_instar + 1);
        } else {
            next_stage = AquaticStage::PUPA;
            next_instar = 0;
        }

        const int64_t transferred = cohorts_[src_idx].count;
        auto& dst = find_or_create(p.patch_id, next_stage, next_instar);
        dst.count += transferred;
        dst.development = 0.0f;
        dst.mean_age_days = 0.0f;
        // Re-lookup src after find_or_create (vector may have grown)
        auto src_it2 = index_.find(src_key);
        if (src_it2 != index_.end()) {
            cohorts_[src_it2->second].count = 0;
        }
    }
}

// ---------------------------------------------------------------------------
// advance_day — the daily update entry point
// ---------------------------------------------------------------------------
void AquaticCohortBank::advance_day(
    const std::vector<PatchState>& patch_states,
    const RuntimeOverrides& overrides) {
    if (cohorts_.empty()) return;

    // -- DEBUG (env-gated, permanent): per-day aquatic summary for days 0-49
    // of the run — enabled ONLY with MAL_ABM_AQUATIC_DEBUG=1. Prints
    // DBGADV lines to stderr (counts, activated patches, and on days
    // 25/36/37 the first 7 cohorts with their patch thermodynamics).
    // Used to prove the 2026-10-20 whole-year aquatic freeze (nodata
    // sentinel -9999 deg C in the env NC reached the thermal curves);
    // kept behind the flag because it is the only in-engine trace of
    // cohort hygiene.
    static int64_t dbg_day = 0;
    {
        static const bool dbg_enabled =
            std::getenv("MAL_ABM_AQUATIC_DEBUG") != nullptr;
        const bool dbg = dbg_enabled && dbg_day < 50;
        int64_t n_act = 0;
        std::unordered_set<int64_t> known;
        for (const auto& ps : patch_states) {
            if (ps.activated) ++n_act;
            known.insert(ps.patch_id);
        }
        if (dbg) {
            int64_t n_known_c = 0, total = 0;
            for (const auto& c : cohorts_) {
                total += c.count;
                if (known.count(c.patch_id)) ++n_known_c;
            }
            std::fprintf(stderr,
                "DBGADV day=%lld cohorts=%zu total=%lld known=%lld "
                "act_patches=%lld/%zu\n",
                static_cast<long long>(dbg_day), cohorts_.size(),
                static_cast<long long>(total),
                static_cast<long long>(n_known_c),
                static_cast<long long>(n_act), patch_states.size());
            if (dbg_day == 25 || dbg_day == 36 || dbg_day == 37) {
                int shown = 0;
                for (const auto& c : cohorts_) {
                    if (c.count <= 0) continue;
                    if (shown++ > 6) break;
                    std::fprintf(stderr,
                        "DBGADV c pid=%lld r=%d c=%d stage=%u instar=%u count=%lld dev=%.3f act=%d dry=%d k=%.2f temp=%.1f\n",
                        static_cast<long long>(c.patch_id),
                        [] (const std::vector<PatchState>& s, int64_t p) {
                            for (const auto& x : s) if (x.patch_id == p) return x.row;
                            return -1; } (patch_states, c.patch_id),
                        [] (const std::vector<PatchState>& s, int64_t p) {
                            for (const auto& x : s) if (x.patch_id == p) return x.col;
                            return -1; } (patch_states, c.patch_id),
                        static_cast<unsigned>(c.stage),
                        static_cast<unsigned>(c.larval_instar),
                        static_cast<long long>(c.count),
                        c.development,
                        known.count(c.patch_id)
                            ? ([](const std::vector<PatchState>& s, int64_t p)
                               { int a=-1;
                                 for (const auto& x : s)
                                   if (x.patch_id == p) { a=(int)x.activated; }
                                 return a; })(patch_states, c.patch_id)
                            : -1,
                        known.count(c.patch_id)
                            ? ([](const std::vector<PatchState>& s, int64_t p)
                               { for (const auto& x : s)
                                   if (x.patch_id == p)
                                     return (int)x.habitat_dry_days;
                                 return -1; })(patch_states, c.patch_id)
                            : -1,
                        known.count(c.patch_id)
                            ? ([](const std::vector<PatchState>& s, int64_t p)
                               { for (const auto& x : s)
                                   if (x.patch_id == p)
                                     return x.k_habitat;
                                 return -1.0f; })(patch_states, c.patch_id)
                            : -1.0f,
                        known.count(c.patch_id)
                            ? ([](const std::vector<PatchState>& s, int64_t p)
                               { for (const auto& x : s)
                                   if (x.patch_id == p)
                                     return x.temp_d;
                                 return -999.0f; })(patch_states, c.patch_id)
                            : -999.0f);
                }
            }
        }
        ++dbg_day;
    }

    // 1. Desiccation (eggs + early instars at dry patches)
    desiccation(patch_states);

    // 2. Washout (heavy rain flushes aquatic cohorts)
    washout(patch_states);

    // 3. Stage mortality (egg/pupa background, larva density + salinity)
    stage_mortality(patch_states);
    larva_mortality_density(patch_states, overrides);

    // 3. Development + promotion
    promote_stages(patch_states);

    // 4. Compact empty cohorts
    compact();
}

// ---------------------------------------------------------------------------
// collect_emergence — extract adults from pupae with dev >= 1.0
// ---------------------------------------------------------------------------
std::vector<EmergenceEvent> AquaticCohortBank::collect_emergence(
    const std::vector<PatchState>& patch_states) {
    std::vector<EmergenceEvent> events;

    for (auto& c : cohorts_) {
        if (c.count <= 0) continue;
        if (c.stage != AquaticStage::PUPA) continue;
        if (c.development < 1.0f) continue;

        // This pupa cohort has completed development → emerge as adults
        int32_t row = 0, col = 0;
        patch_to_cell(c.patch_id, patch_states, row, col);

        events.push_back({c.patch_id, row, col, c.count});
        c.count = 0;
    }

    compact();
    return events;
}

// ---------------------------------------------------------------------------
// Queries
// ---------------------------------------------------------------------------
int64_t AquaticCohortBank::total_aquatic() const {
    int64_t total = 0;
    for (const auto& c : cohorts_) {
        total += c.count;
    }
    return total;
}

int64_t AquaticCohortBank::count_by_stage(AquaticStage stage) const {
    int64_t total = 0;
    for (const auto& c : cohorts_) {
        if (c.stage == stage) total += c.count;
    }
    return total;
}

int64_t AquaticCohortBank::count_by_stage_instar(
    AquaticStage stage, uint8_t instar) const {
    int64_t total = 0;
    for (const auto& c : cohorts_) {
        if (c.stage == stage && c.larval_instar == instar) total += c.count;
    }
    return total;
}

void AquaticCohortBank::write_diagnostics(const std::string& path,
                                          int32_t day) const {
    // Build a simple JSON diagnostic without nlohmann (header-only).
    std::ofstream f(path);
    if (!f.is_open()) return;

    f << "{\n";
    f << "  \"day\": " << day << ",\n";
    f << "  \"total_aquatic\": " << total_aquatic() << ",\n";

    // Per-stage counts
    f << "  \"by_stage\": {\n";
    f << "    \"egg\": " << count_by_stage(AquaticStage::EGG) << ",\n";
    f << "    \"larva\": " << count_by_stage(AquaticStage::LARVA) << ",\n";
    f << "    \"pupa\": " << count_by_stage(AquaticStage::PUPA) << "\n";
    f << "  },\n";

    // Per-instar counts (larvae only)
    f << "  \"by_instar\": {\n";
    for (uint8_t i = 1; i <= 4; ++i) {
        f << "    \"L" << static_cast<int>(i) << "\": "
          << count_by_stage_instar(AquaticStage::LARVA, i);
        if (i < 4) f << ",";
        f << "\n";
    }
    f << "  },\n";

    // Per-patch summary (top 10 by count)
    std::unordered_map<int64_t, int64_t> patch_counts;
    for (const auto& c : cohorts_) {
        patch_counts[c.patch_id] += c.count;
    }
    std::vector<std::pair<int64_t, int64_t>> sorted_patches(
        patch_counts.begin(), patch_counts.end());
    std::sort(sorted_patches.begin(), sorted_patches.end(),
              [](const auto& a, const auto& b) { return a.second > b.second; });

    f << "  \"top_patches\": [\n";
    const size_t n = std::min(sorted_patches.size(), static_cast<size_t>(10));
    for (size_t i = 0; i < n; ++i) {
        f << "    {\"patch_id\": " << sorted_patches[i].first
          << ", \"count\": " << sorted_patches[i].second << "}";
        if (i + 1 < n) f << ",";
        f << "\n";
    }
    f << "  ],\n";

    // Mean development per stage
    f << "  \"mean_development\": {\n";
    for (auto stage : {AquaticStage::EGG, AquaticStage::LARVA, AquaticStage::PUPA}) {
        float sum_dev = 0.0f;
        int64_t count = 0;
        for (const auto& c : cohorts_) {
            if (c.stage == stage) {
                sum_dev += c.development * static_cast<float>(c.count);
                count += c.count;
            }
        }
        const char* name = (stage == AquaticStage::EGG) ? "egg"
                         : (stage == AquaticStage::LARVA) ? "larva" : "pupa";
        f << "    \"" << name << "\": ";
        if (count > 0) {
            f << std::fixed << std::setprecision(4) << (sum_dev / static_cast<float>(count));
        } else {
            f << "0.0";
        }
        if (stage != AquaticStage::PUPA) f << ",";
        f << "\n";
    }
    f << "  }\n";
    f << "}\n";
}

}  // namespace mal_abm_fast
