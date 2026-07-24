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

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <fstream>
#include <iomanip>
#include <numeric>
#include <random>
#include <unordered_map>
#include <utility>

#include "mal_abm_fast/thermal_responses.hpp"

namespace mal_abm_fast {

// ---------------------------------------------------------------------------
// Egg & pupa mortality constants (daily rates)
// ---------------------------------------------------------------------------
// Egg: ~8% daily mortality (Giglioli 1965, Depinay 2004)
//   At 25°C egg duration ~1.1 days → survival ~0.92
inline constexpr float EGG_DAILY_MORT     = 0.08f;
// Pupa: ~5% daily mortality (pupae are robust, Depinay 2004)
inline constexpr float PUPA_DAILY_MORT    = 0.05f;
// Desiccation rate for eggs and early instars at inactive patches
inline constexpr float AQUATIC_DESICCATION_DAILY_RATE = 0.10f;

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
// desiccation — kill eggs and early instars at inactive patches
// ---------------------------------------------------------------------------
void AquaticCohortBank::desiccation(
    const std::vector<PatchState>& patch_states) {
    // Build active set
    std::unordered_map<int64_t, bool> active;
    for (const auto& ps : patch_states) {
        active[ps.patch_id] = ps.activated;
    }

    for (auto& c : cohorts_) {
        if (c.count <= 0) continue;
        // Only eggs and early instars (L1, L2) are vulnerable to desiccation
        bool vulnerable = false;
        if (c.stage == AquaticStage::EGG) {
            vulnerable = true;
        } else if (c.stage == AquaticStage::LARVA && c.larval_instar <= 2) {
            vulnerable = true;
        }
        if (!vulnerable) continue;

        auto it = active.find(c.patch_id);
        if (it == active.end() || !it->second) {
            // Inactive patch — apply desiccation
            const int64_t deaths = static_cast<int64_t>(
                std::llround(static_cast<double>(c.count) * AQUATIC_DESICCATION_DAILY_RATE));
            c.count -= std::min(deaths, c.count);
        }
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
    std::mt19937_64 rng(42);  // deterministic for reproducibility
    for (auto& c : cohorts_) {
        if (c.count <= 0) continue;
        float mort_rate = 0.0f;
        if (c.stage == AquaticStage::EGG) {
            mort_rate = EGG_DAILY_MORT;
        } else if (c.stage == AquaticStage::PUPA) {
            mort_rate = PUPA_DAILY_MORT;
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
// ---------------------------------------------------------------------------
void AquaticCohortBank::larva_mortality_density(
    const RuntimeOverrides& overrides) {
    // Aggregate larva count per patch across all instars
    std::unordered_map<int64_t, int64_t> larva_per_patch;
    for (const auto& c : cohorts_) {
        if (c.stage == AquaticStage::LARVA && c.count > 0) {
            larva_per_patch[c.patch_id] += c.count;
        }
    }

    const double K = static_cast<double>(K_MAX);
    std::mt19937_64 rng(123);  // deterministic
    for (auto& c : cohorts_) {
        if (c.count <= 0 || c.stage != AquaticStage::LARVA) continue;
        const int64_t N = larva_per_patch[c.patch_id];
        const double p = static_cast<double>(LARVA_BH_S0) * K /
            (K + static_cast<double>(overrides.larva_bh_alpha) * static_cast<double>(N));
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
        } else if (p.from_instar < 4) {
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

    // 1. Desiccation (eggs + early instars at inactive patches)
    desiccation(patch_states);

    // 2. Stage mortality (egg/pupa background, larva density-dependent)
    stage_mortality(patch_states);
    larva_mortality_density(overrides);

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
