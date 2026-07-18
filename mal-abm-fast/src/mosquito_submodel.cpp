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
#include <utility>
#include <vector>

#include "mal_abm_fast/aoi.hpp"
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
                                   float init_frac, uint64_t seed)
    : rng_(seed), k_per_patch_(k_per_patch) {
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

    for (int64_t p = 0; p < np; ++p) {
        const int64_t k = per_patch[static_cast<size_t>(p)];
        for (int64_t j = 0; j < k; ++j) {
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
                                   uint64_t seed)
    : rng_(seed), k_per_patch_(k_per_patch) {
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

void MosquitoSubmodel::advance_day(const AOI& aoi,
                                   const std::vector<PatchState>& patch_states) {
    larva_mortality_inactive(patch_states);   // Op 1
    larva_mortality_density(patch_states);    // Op 2.5 (Beverton-Holt)
    larva_growth(patch_states);               // Op 2
    larva_to_adult(aoi, patch_states);        // Op 3
    adult_dispersal(aoi);                     // Op 4
    adult_mortality(patch_states);            // Op 6 (Lardeux)
    birth(aoi, patch_states);                 // Op 5
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
                (K + static_cast<double>(LARVA_BH_ALPHA) * static_cast<double>(N));
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
        if (u < static_cast<double>(ADULT_DISPERSE_PROB)) {
            const DispOffset off = offset_m(
                rng_,
                static_cast<double>(soa_.lon[si]),
                static_cast<double>(soa_.lat[si]),
                static_cast<double>(ADULT_DISPERSE_SIGMA_M),
                static_cast<double>(ADULT_DISPERSE_MAX_M));
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

    const double opt_c = static_cast<double>(ADULT_OPT_C);
    const double sigma = static_cast<double>(ADULT_SIGMA);
    const double two_sigma_sq = 2.0 * sigma * sigma;

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
                p_d = std::exp(-((T - opt_c) * (T - opt_c)) / two_sigma_sq);
            } else {
                p_d = static_cast<double>(ADULT_DAILY_MORT_BASE);
            }
            if (p_d < 0.80) p_d = 0.80;
            if (p_d > 1.0)  p_d = 1.0;
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

    struct PatchDraw {
        int64_t patch_id;
        int32_t row;
        int32_t col;
        int64_t n_birth;
    };
    std::vector<PatchDraw> draws;
    draws.reserve(patch_states.size());

    int64_t total_birth = 0;
    for (const auto& ps : patch_states) {
        if (!ps.activated) continue;
        const int n = rng_.binomial(static_cast<int>(k_per_patch_),
                                    static_cast<double>(BIRTH_RATE));
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
