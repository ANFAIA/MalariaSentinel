// SPDX-License-Identifier: MIT
// debug_parquet_writer.hpp — the four Parquet files of `--debug`
// (plan §11, §15.1, Paso 2b), written with Apache Arrow C++:
//
//   <stem>_agents.parquet   one row per adult per day (position, state, cascade stage)
//   <stem>_humans.parquet   one row per person per day, ONLY people in E, I or R
//   <stem>_bites.parquet    one row per blood meal (who bit whom, new_infection)
//   <stem>_mating.parquet   mating events (empty until the male layer, Paso 8)
//
// `--debug` is independent of `--scenario` and of the GIF: it only adds these
// files. Rows are buffered per day and written by finish().
#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace mal_abm_fast {

class Engine;

class DebugParquetWriter {
public:
    explicit DebugParquetWriter(std::string stem);
    ~DebugParquetWriter();

    /// Collect the state of simulated day `day` (1-based). Call after
    /// Engine::step(), before the next step resets the bite ledger.
    void record_day(const Engine& engine, int day);

    /// Write the four files; returns their paths. Throws std::runtime_error
    /// on a write failure.
    std::vector<std::string> finish();

    int64_t n_agent_rows() const;
    int64_t n_human_rows() const;
    int64_t n_bite_rows() const;

private:
    struct Impl;
    Impl* impl_;
};

}  // namespace mal_abm_fast
