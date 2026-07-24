// SPDX-License-Identifier: MIT
// mobility_schedule.hpp — Sparse OD matrices + time-phase mobility schedule.
//
// G6 adds population mobility: humans and livestock move between
// residential cells and destination cells according to sparse
// origin-destination (OD) matrices.  At each time phase the effective
// host density at cell j is:
//
//   H_eff(j, phase) = Σ_i  P(i→j, phase) × H_residential(i)
//
// where P(i→j, phase) is the OD fraction from cell i to cell j at
// the given phase and H_residential(i) is the residential population.
//
// The OD matrix is stored in Compressed Sparse Row (CSR) format.
// Each row is stochastic (sums to 1.0).  A daytime matrix shifts
// population toward work / urban centres; the night matrix is the
// identity (everyone at home).
//
// This header is header-only (inline definitions) following the
// same convention as grid_spec.hpp.
#pragma once

#include <cmath>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include "aoi.hpp"

namespace mal_abm_fast {

// ---------------------------------------------------------------------------
// TimePhase — the four phases of the daily mobility cycle.
// ---------------------------------------------------------------------------

enum class TimePhase : uint8_t {
    DAY    = 0,  // 06:00–18:00 (work / school)
    EVENING = 1, // 18:00–21:00 (transition)
    NIGHT  = 2,  // 21:00–05:00 (sleeping at home)
    DAWN   = 3,  // 05:00–06:00 (transition)
};

inline constexpr int kNumTimePhases = 4;

// ---------------------------------------------------------------------------
// SparseOD — row-stochastic sparse matrix in CSR format.
// ---------------------------------------------------------------------------

struct SparseOD {
    std::vector<int32_t> row_ptr;   // (n_rows + 1) entries
    std::vector<int32_t> col_idx;   // nnz entries
    std::vector<float>   values;    // nnz entries, each row sums to ~1.0
    int32_t n_rows = 0;
    int32_t n_cols = 0;

    /// Construct an empty (zero-row) OD matrix.
    SparseOD() = default;

    /// Construct from raw CSR arrays.  Validates that each row sums to ~1.0.
    SparseOD(std::vector<int32_t> row_ptr_,
             std::vector<int32_t> col_idx_,
             std::vector<float>   values_,
             int32_t n_rows_,
             int32_t n_cols_)
        : row_ptr(std::move(row_ptr_)),
          col_idx(std::move(col_idx_)),
          values(std::move(values_)),
          n_rows(n_rows_),
          n_cols(n_cols_)
    {
        validate();
    }

    /// Load from a binary CSR file.
    ///
    /// File format (all little-endian):
    ///   [4 bytes] n_rows   (int32)
    ///   [4 bytes] n_cols   (int32)
    ///   [4 bytes] nnz      (int32)
    ///   [4 * (n_rows+1) bytes] row_ptr  (int32 array)
    ///   [4 * nnz bytes]         col_idx  (int32 array)
    ///   [4 * nnz bytes]         values   (float array)
    static SparseOD load_from_csr(const std::string& path) {
        std::ifstream f(path, std::ios::binary);
        if (!f.is_open()) {
            throw std::runtime_error(
                "SparseOD::load_from_csr: cannot open " + path);
        }

        auto read_i32 = [&]() -> int32_t {
            int32_t v = 0;
            f.read(reinterpret_cast<char*>(&v), 4);
            return v;
        };

        const int32_t nr    = read_i32();
        const int32_t nc    = read_i32();
        const int32_t nnz   = read_i32();

        if (nr < 0 || nc < 0 || nnz < 0) {
            throw std::runtime_error(
                "SparseOD::load_from_csr: negative dimension in " + path);
        }

        std::vector<int32_t> rp(static_cast<size_t>(nr + 1));
        std::vector<int32_t> ci(static_cast<size_t>(nnz));
        std::vector<float>   vl(static_cast<size_t>(nnz));

        f.read(reinterpret_cast<char*>(rp.data()),
               static_cast<std::streamsize>(4) * (nr + 1));
        f.read(reinterpret_cast<char*>(ci.data()),
               static_cast<std::streamsize>(4) * nnz);
        f.read(reinterpret_cast<char*>(vl.data()),
               static_cast<std::streamsize>(4) * nnz);

        if (!f.good()) {
            throw std::runtime_error(
                "SparseOD::load_from_csr: read failed for " + path);
        }

        return SparseOD(std::move(rp), std::move(ci), std::move(vl), nr, nc);
    }

    /// Get destination cells and fractions for a given origin row.
    std::vector<std::pair<int32_t, float>> destinations(int32_t origin) const {
        std::vector<std::pair<int32_t, float>> result;
        if (origin < 0 || origin >= n_rows) return result;

        const int32_t start = row_ptr[origin];
        const int32_t end   = row_ptr[origin + 1];
        result.reserve(static_cast<size_t>(end - start));
        for (int32_t k = start; k < end; ++k) {
            result.emplace_back(col_idx[k], values[k]);
        }
        return result;
    }

    /// Number of non-zero entries.
    int32_t nnz() const {
        return row_ptr.empty() ? 0 : row_ptr.back();
    }

    /// Build an identity matrix (everyone stays home).
    static SparseOD identity(int32_t n) {
        std::vector<int32_t> rp(static_cast<size_t>(n + 1));
        std::vector<int32_t> ci(static_cast<size_t>(n));
        std::vector<float>   vl(static_cast<size_t>(n), 1.0f);
        for (int32_t i = 0; i <= n; ++i) rp[i] = i;
        for (int32_t i = 0; i < n;  ++i) ci[i] = i;
        return SparseOD(std::move(rp), std::move(ci), std::move(vl), n, n);
    }

private:
    /// Validate row sums (each row ≈ 1.0).
    void validate() const {
        if (row_ptr.size() != static_cast<size_t>(n_rows + 1)) {
            throw std::runtime_error(
                "SparseOD::validate: row_ptr size mismatch");
        }
        for (int32_t r = 0; r < n_rows; ++r) {
            const int32_t start = row_ptr[r];
            const int32_t end   = row_ptr[r + 1];
            float sum = 0.0f;
            for (int32_t k = start; k < end; ++k) {
                sum += values[static_cast<size_t>(k)];
                if (col_idx[k] < 0 || col_idx[k] >= n_cols) {
                    throw std::runtime_error(
                        "SparseOD::validate: col_idx out of bounds at row " +
                        std::to_string(r));
                }
            }
            if (std::abs(sum - 1.0f) > 0.01f && end > start) {
                throw std::runtime_error(
                    "SparseOD::validate: row " + std::to_string(r) +
                    " sums to " + std::to_string(sum) + " (expected ~1.0)");
            }
        }
    }
};

// ---------------------------------------------------------------------------
// MobilitySchedule — loads OD matrices for human and livestock mobility.
// ---------------------------------------------------------------------------

class MobilitySchedule {
public:
    MobilitySchedule() = default;

    /// Load human OD matrices for day and night phases.
    void load_human_od(const std::string& day_path,
                       const std::string& night_path)
    {
        human_day_   = SparseOD::load_from_csr(day_path);
        human_night_ = SparseOD::load_from_csr(night_path);

        if (human_day_.n_rows != human_night_.n_rows ||
            human_day_.n_cols != human_night_.n_cols) {
            throw std::runtime_error(
                "MobilitySchedule::load_human_od: dimension mismatch");
        }
        human_loaded_ = true;
    }

    /// Load livestock OD matrix (seasonal, same matrix for all phases).
    void load_livestock_od(const std::string& seasonal_path) {
        livestock_day_   = SparseOD::load_from_csr(seasonal_path);
        livestock_night_ = SparseOD::identity(livestock_day_.n_rows);
        livestock_loaded_ = true;
    }

    /// Construct in-memory OD matrices directly (for testing).
    void set_human_od(SparseOD day, SparseOD night) {
        if (day.n_rows != night.n_rows || day.n_cols != night.n_cols) {
            throw std::runtime_error(
                "MobilitySchedule::set_human_od: dimension mismatch");
        }
        human_day_   = std::move(day);
        human_night_ = std::move(night);
        human_loaded_ = true;
    }

    void set_livestock_od(SparseOD day) {
        livestock_day_   = std::move(day);
        livestock_night_ = SparseOD::identity(livestock_day_.n_rows);
        livestock_loaded_ = true;
    }

    /// Get the presence distribution for a given origin cell at a given phase.
    std::vector<std::pair<int32_t, float>> get_presence(
        int32_t origin_cell,
        TimePhase phase,
        bool is_livestock = false) const
    {
        const SparseOD& od = select_od(phase, is_livestock);
        return od.destinations(origin_cell);
    }

    /// Compute the effective host density at a target cell.
    /// H_eff(j, phase) = Σ_i P(i→j, phase) × H_residential(i)
    float effective_hosts_at(
        int32_t target_cell,
        TimePhase phase,
        const std::vector<float>& residential_population,
        bool is_livestock = false) const
    {
        const SparseOD& od = select_od(phase, is_livestock);
        if (od.n_rows == 0 || od.n_cols == 0) return 0.0f;
        if (target_cell < 0 || target_cell >= od.n_cols) return 0.0f;

        float total = 0.0f;
        for (int32_t i = 0; i < od.n_rows; ++i) {
            const int32_t start = od.row_ptr[i];
            const int32_t end   = od.row_ptr[i + 1];
            const float pop_i = (static_cast<size_t>(i) < residential_population.size())
                                ? residential_population[static_cast<size_t>(i)]
                                : 0.0f;
            for (int32_t k = start; k < end; ++k) {
                if (od.col_idx[k] == target_cell) {
                    total += od.values[static_cast<size_t>(k)] * pop_i;
                    break;
                }
            }
        }
        return total;
    }

    int32_t n_cells() const {
        if (human_loaded_) return human_day_.n_rows;
        if (livestock_loaded_) return livestock_day_.n_rows;
        return 0;
    }

    bool has_human() const { return human_loaded_; }
    bool has_livestock() const { return livestock_loaded_; }
    bool has_data() const { return human_loaded_ || livestock_loaded_; }
    int32_t n_matrices() const {
        return (human_loaded_ ? 2 : 0) + (livestock_loaded_ ? 1 : 0);
    }

    /// Load from a directory containing expected CSR files.
    void load_from_directory(const std::string& dir, const AOI& /*aoi*/) {
        namespace fs = std::filesystem;
        const fs::path base(dir);
        if (!fs::exists(base)) return;

        const auto day_p   = base / "human_mobility_day.csr";
        const auto night_p = base / "human_mobility_night.csr";
        const auto live_p  = base / "livestock_mobility_season.csr";

        if (fs::exists(day_p) && fs::exists(night_p)) {
            load_human_od(day_p.string(), night_p.string());
        }
        if (fs::exists(live_p)) {
            load_livestock_od(live_p.string());
        }
    }

private:
    SparseOD human_day_;
    SparseOD human_night_;
    SparseOD livestock_day_;
    SparseOD livestock_night_;
    bool human_loaded_    = false;
    bool livestock_loaded_ = false;

    const SparseOD& select_od(TimePhase phase, bool is_livestock) const {
        if (is_livestock) {
            if (!livestock_loaded_) {
                throw std::runtime_error(
                    "MobilitySchedule: livestock OD not loaded");
            }
            return (phase == TimePhase::NIGHT) ? livestock_night_ : livestock_day_;
        }
        if (!human_loaded_) {
            throw std::runtime_error(
                "MobilitySchedule: human OD not loaded");
        }
        switch (phase) {
            case TimePhase::NIGHT:  return human_night_;
            case TimePhase::DAY:
            case TimePhase::EVENING:
            case TimePhase::DAWN:   return human_day_;
        }
        return human_day_;  // fallback
    }
};

}  // namespace mal_abm_fast
