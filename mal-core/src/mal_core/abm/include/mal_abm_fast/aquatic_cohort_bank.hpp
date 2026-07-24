// SPDX-License-Identifier: MIT
// aquatic_cohort_bank.hpp — Cohort-based aquatic mosquito lifecycle.
//
// Eggs, larvae, and pupas are NOT individual agents. They are
// aggregated cohorts per (patch_id, stage, instar) stored here.
// Only adults remain as individual agents in MosquitoSoA.
//
// Lifecycle: Egg → Larva L1 → L2 → L3 → L4 → Pupa → Adult
//
// The bank handles:
//   - egg deposition (from oviposition, M7.2)
//   - daily development (thermal curves from thermal_responses.hpp)
//   - daily mortality (stage-specific + density-dependent for larvae)
//   - instar transitions (L1→L2→L3→L4)
//   - pupation (L4 → Pupa)
//   - emergence (Pupa → Adult, returned as EmergenceEvents)
#pragma once

#include <cstdint>
#include <functional>
#include <string>
#include <unordered_map>
#include <vector>

#include "wire.hpp"
#include "aquatic_stages.hpp"

namespace mal_abm_fast {

// ---------------------------------------------------------------------------
// AquaticCohort — a single cohort at a specific (patch, stage, instar)
// ---------------------------------------------------------------------------
struct AquaticCohort {
    int64_t   patch_id;        // which patch this cohort belongs to
    AquaticStage stage;        // EGG, LARVA, or PUPA
    uint8_t   larval_instar;   // 1-4 for LARVA, 0 otherwise
    float     development;     // [0, 1] fraction of current stage complete
    int64_t   count;           // number of individuals in this cohort
    float     mean_age_days;   // average age in the current stage
};

// ---------------------------------------------------------------------------
// EmergenceEvent — a batch of adults emerging from pupae
// ---------------------------------------------------------------------------
struct EmergenceEvent {
    int64_t  patch_id;
    int32_t  row;
    int32_t  col;
    int64_t  n_adults;
};

// ---------------------------------------------------------------------------
// AquaticCohortBank — the lifecycle engine for immature mosquitoes
// ---------------------------------------------------------------------------
class AquaticCohortBank {
public:
    AquaticCohortBank() = default;

    // Add egg cohorts from oviposition. Eggs are deposited at
    // (patch_id, stage=EGG, instar=0) with development=0.
    void add_eggs(int64_t patch_id, int64_t count);

    // Daily update: advance development, apply mortality, promote
    // through lifecycle stages. Call once per day before
    // collect_emergence().
    void advance_day(const std::vector<PatchState>& patch_states,
                     const RuntimeOverrides& overrides);

    // Collect emerged adults. Returns a list of EmergenceEvents
    // (one per patch with emergences). Removes emerged pupae
    // from the bank. Call AFTER advance_day().
    // patch_states is needed to resolve patch_id → (row, col).
    std::vector<EmergenceEvent> collect_emergence(
        const std::vector<PatchState>& patch_states);

    // --- queries ---
    int64_t total_aquatic() const;
    int64_t count_by_stage(AquaticStage stage) const;
    int64_t count_by_stage_instar(AquaticStage stage, uint8_t instar) const;

    // Write aquatic cohort state to a JSON diagnostic file.
    // The file contains per-stage counts, per-patch breakdown,
    // and development statistics. Called by the engine at snapshot time.
    void write_diagnostics(const std::string& path, int32_t day) const;

    // Read-only access to cohorts (for testing / debug).
    const std::vector<AquaticCohort>& cohorts() const { return cohorts_; }

private:
    std::vector<AquaticCohort> cohorts_;

    // Index: (patch_id, stage, instar) -> index into cohorts_
    using CohortKey = std::pair<int64_t, std::pair<uint8_t, uint8_t>>;
    struct CohortKeyHash {
        std::size_t operator()(const CohortKey& k) const noexcept {
            std::size_t h = std::hash<int64_t>{}(k.first);
            h ^= std::hash<uint8_t>{}(k.second.first) << 1;
            h ^= std::hash<uint8_t>{}(k.second.second) << 2;
            return h;
        }
    };
    std::unordered_map<CohortKey, size_t, CohortKeyHash> index_;

    // Helper: find or create a cohort at (patch_id, stage, instar).
    AquaticCohort& find_or_create(int64_t patch_id, AquaticStage stage,
                                  uint8_t instar);

    // Helper: remove cohorts with count == 0 and rebuild index.
    void compact();

    // Helper: rebuild the key→index map after structural changes.
    void rebuild_index();

    // Helper: promote eggs to L1, L1→L2, L2→L3, L3→L4, L4→Pupa.
    void promote_stages(const std::vector<PatchState>& patch_states);

    // Helper: apply density-dependent mortality to larvae.
    void larva_mortality_density(const RuntimeOverrides& overrides);

    // Helper: apply stage-specific mortality (eggs, pupae).
    void stage_mortality(const std::vector<PatchState>& patch_states);

    // Helper: desiccation for eggs and early instars at inactive patches.
    void desiccation(const std::vector<PatchState>& patch_states);

    // Helper: compute cell (row, col) for a patch_id from patch_states.
    bool patch_to_cell(int64_t patch_id, const std::vector<PatchState>& ps,
                       int32_t& row, int32_t& col) const;
};

}  // namespace mal_abm_fast
