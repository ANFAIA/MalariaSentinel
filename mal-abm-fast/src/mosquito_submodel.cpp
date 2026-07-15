// SPDX-License-Identifier: MIT
// mosquito_submodel.cpp — F1.b: Polars-style vectorised mosquito half
// of the ABM, ported to a C++20 SoA.
//
// Per-day order (mirrors `mal_ghana_sim.abm.mosquito_submodel.
// MosquitoSubmodel.advance_day` exactly):
//   1. larva_mortality_inactive(patch_states)
//   2. larva_growth(patch_states)
//   3. larva_to_adult()
//   4. adult_dispersal()
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
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

#include "mal_abm_fast/aoi.hpp"
#include "mal_abm_fast/dispersal.hpp"
#include "mal_abm_fast/eip.hpp"

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
}

}  // namespace

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
        }
    }
    soa_.n_alive  = n;
    soa_.next_uid = n;
}

// ---------------------------------------------------------------------------
// Per-day orchestrator
// ---------------------------------------------------------------------------

void MosquitoSubmodel::advance_day(const AOI& aoi,
                                   const std::vector<PatchState>& patch_states) {
    larva_mortality_inactive(patch_states);
    larva_growth(patch_states);
    larva_to_adult(aoi, patch_states);
    adult_dispersal();
    birth(aoi, patch_states);
}

// ---------------------------------------------------------------------------
// Op 1: larva mortality at inactive patches
// ---------------------------------------------------------------------------

void MosquitoSubmodel::larva_mortality_inactive(
    const std::vector<PatchState>& patch_states) {
    if (soa_.n_alive <= 0) return;

    std::unordered_set<int64_t> inactive;
    inactive.reserve(patch_states.size());
    for (const auto& ps : patch_states) {
        if (!ps.activated) inactive.insert(ps.patch_id);
    }
    if (inactive.empty()) return;

    // Reverse swap-with-last: walk the live range from the tail down
    // to 0; for each larva at an inactive patch, swap with the
    // current last and decrement n_alive. The swapped-in element was
    // already processed in a previous (higher-i) iteration, so it
    // never needs to be re-checked.
    int64_t i = soa_.n_alive - 1;
    while (i >= 0) {
        const size_t si = static_cast<size_t>(i);
        if (soa_.stage[si] == 0 &&
            inactive.find(soa_.patch_id[si]) != inactive.end()) {
            swap_with_last(soa_, i, soa_.n_alive);
            --soa_.n_alive;
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

    std::unordered_map<int64_t, float> active_temp;
    active_temp.reserve(patch_states.size());
    for (const auto& ps : patch_states) {
        if (ps.activated) active_temp[ps.patch_id] = ps.temp_d;
    }
    if (active_temp.empty()) return;

    for (int64_t i = 0; i < soa_.n_alive; ++i) {
        const size_t si = static_cast<size_t>(i);
        if (soa_.stage[si] != 0) continue;
        const auto it = active_temp.find(soa_.patch_id[si]);
        if (it == active_temp.end()) continue;
        ++soa_.stage_age[si];
        soa_.eip_progress[si] = accumulate_eip(soa_.eip_progress[si], it->second);
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
    // Build a patch_id -> (row, col) lookup from the per-day patch state.
    std::unordered_map<int64_t, std::pair<int32_t, int32_t>> patch_cell;
    patch_cell.reserve(patch_states.size());
    for (const auto& ps : patch_states) {
        patch_cell[ps.patch_id] = {ps.row, ps.col};
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
            // from the per-day patch state cache.
            auto it = patch_cell.find(soa_.patch_id[si]);
            if (it != patch_cell.end()) {
                const int32_t r = it->second.first;
                const int32_t c = it->second.second;
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

void MosquitoSubmodel::adult_dispersal() {
    for (int64_t i = 0; i < soa_.n_alive; ++i) {
        const size_t si = static_cast<size_t>(i);
        if (soa_.stage[si] != 1) continue;
        const double u = rng_.uniform_double();
        if (!(u < static_cast<double>(ADULT_DISPERSE_PROB))) continue;
        const DispOffset off = offset_m(
            rng_,
            static_cast<double>(soa_.lon[si]),
            static_cast<double>(soa_.lat[si]),
            static_cast<double>(ADULT_DISPERSE_SIGMA_M),
            static_cast<double>(ADULT_DISPERSE_MAX_M));
        soa_.lon[si] = static_cast<float>(static_cast<double>(soa_.lon[si]) + off.dlon);
        soa_.lat[si] = static_cast<float>(static_cast<double>(soa_.lat[si]) + off.dlat);
    }
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
    std::unordered_map<int64_t, int64_t> counts;
    counts.reserve(static_cast<size_t>(soa_.n_alive));
    for (int64_t i = 0; i < soa_.n_alive; ++i) {
        const size_t si = static_cast<size_t>(i);
        ++counts[soa_.patch_id[si]];
    }
    std::vector<std::pair<int64_t, int64_t>> result;
    result.reserve(counts.size());
    for (const auto& kv : counts) result.emplace_back(kv.first, kv.second);
    std::sort(result.begin(), result.end(),
              [](const std::pair<int64_t, int64_t>& a,
                 const std::pair<int64_t, int64_t>& b) {
                  return a.first < b.first;
              });
    return result;
}

std::vector<std::tuple<int32_t, int32_t, int64_t>>
MosquitoSubmodel::adult_density_by_cell(const AOI& aoi) const {
    const int32_t w = aoi.cells_per_side();
    const int32_t h = cells_per_side_h(aoi);
    if (w <= 0 || h <= 0) return {};

    const double cellW = (aoi.east - aoi.west) / static_cast<double>(w);
    const double cellH = (aoi.north - aoi.south) / static_cast<double>(h);

    // Composite key (row, col) -> int64: row in the high 32 bits,
    // col in the low 32 bits (both unsigned, so the sign bit never
    // interferes with the shift).
    auto pack = [](int32_t r, int32_t c) -> int64_t {
        return (static_cast<int64_t>(static_cast<uint32_t>(r)) << 32) |
               static_cast<int64_t>(static_cast<uint32_t>(c));
    };
    auto unpack_r = [](int64_t k) -> int32_t {
        return static_cast<int32_t>(static_cast<uint32_t>(
            static_cast<int64_t>(k) >> 32));
    };
    auto unpack_c = [](int64_t k) -> int32_t {
        return static_cast<int32_t>(static_cast<uint32_t>(k & 0xFFFFFFFFLL));
    };

    std::unordered_map<int64_t, int64_t> counts;
    counts.reserve(static_cast<size_t>(soa_.n_alive));

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
        ++counts[pack(row, col)];
    }

    std::vector<std::tuple<int32_t, int32_t, int64_t>> result;
    result.reserve(counts.size());
    for (const auto& kv : counts) {
        result.emplace_back(unpack_r(kv.first), unpack_c(kv.first), kv.second);
    }
    std::sort(result.begin(), result.end(),
              [](const std::tuple<int32_t, int32_t, int64_t>& a,
                 const std::tuple<int32_t, int32_t, int64_t>& b) {
                  if (std::get<0>(a) != std::get<0>(b)) return std::get<0>(a) < std::get<0>(b);
                  return std::get<1>(a) < std::get<1>(b);
              });
    return result;
}

}  // namespace mal_abm_fast
