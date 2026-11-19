// SPDX-License-Identifier: MIT
// test_viz_tx.cpp — GoogleTest for transmission-GIF diagnostics and
// a light smoke test of the GifVizTx lifecycle.
#include <gtest/gtest.h>

#include <cmath>
#include <filesystem>
#include <vector>

#include "transmission.hpp"
#include "viz_tx.hpp"

// Test seam for the pure series builder. Its production definition is in
// viz_tx.cpp; keep this declaration local because viz_tx.hpp is out of scope.
namespace mal_abm_fast::tx_diag {
std::vector<int64_t> build_vector_i_series(
    int64_t initial_vector_i,
    const std::vector<mal_abm_fast::TransmissionDailyStats>& daily_history);
}  // namespace mal_abm_fast::tx_diag

using mal_abm_fast::tx_diag::classify_biteable;
using mal_abm_fast::tx_diag::format_cell_length;

// ---------------------------------------------------------------------------
// Biteable-cell classification (plan 05 §4.1): human / animal-only / empty.
// ---------------------------------------------------------------------------

TEST(VizTxCells, ClassifyBiteableThreeClasses) {
    EXPECT_EQ(classify_biteable(10.0, 0.0), 2);   // humans win
    EXPECT_EQ(classify_biteable(0.0, 5.0), 1);    // animal-only
    EXPECT_EQ(classify_biteable(0.0, 0.0), 0);    // empty (incl. sea)
    EXPECT_EQ(classify_biteable(3.0, 2.0), 2);    // humans present dominate
    EXPECT_EQ(classify_biteable(0.0, 0.4), 1);    // any livestock counts
}

// The scale rule is one cell long, whatever the resolution (plan §15.1.2 V3).
TEST(VizTxScale, RuleLabelIsTheCellLength) {
    EXPECT_EQ(format_cell_length(1000.0), "1 km");
    EXPECT_EQ(format_cell_length(2000.0), "2 km");
    EXPECT_EQ(format_cell_length(1500.0), "1.5 km");
    EXPECT_EQ(format_cell_length(500.0), "500 m");
    EXPECT_EQ(format_cell_length(100.0), "100 m");
}

TEST(VizTxTransmission, VectorISeriesStartsWithSeededDayZeroThenDailyHistory) {
    std::vector<mal_abm_fast::TransmissionDailyStats> history(3);
    history[0].day = 0;
    history[0].vector_i = 8;
    history[1].day = 1;
    history[1].vector_i = 6;
    history[2].day = 2;
    history[2].vector_i = 11;

    const auto series = mal_abm_fast::tx_diag::build_vector_i_series(5, history);
    ASSERT_EQ(series.size(), 4u);
    EXPECT_EQ(series[0], 5);   // real pre-step seeded baseline at day 0
    EXPECT_EQ(series[1], 8);   // daily history follows, in order
    EXPECT_EQ(series[2], 6);
    EXPECT_EQ(series[3], 11);
}

// ---------------------------------------------------------------------------
// Renderer lifecycle smoke (no engine required): the object constructs,
// reports ok, writes zero frames, and finish() is safe/idempotent.
// ---------------------------------------------------------------------------

TEST(VizTxLifecycle, ConstructsAndFinishesCleanly) {
    const auto path = (std::filesystem::temp_directory_path() /
                       "viz_tx_smoke.gif").string();
    std::error_code ec;
    std::filesystem::remove(path, ec);

    mal_abm_fast::GifVizTxConfig cfg;
    cfg.path = path;
    cfg.width = 640;
    cfg.fps = 4;
    cfg.every = 1;
    mal_abm_fast::GifVizTx viz(cfg);
    EXPECT_TRUE(viz.ok());
    EXPECT_EQ(viz.frame_count(), 0);
    viz.finish();
    viz.finish();  // idempotent
    EXPECT_TRUE(std::filesystem::exists(path));
    std::filesystem::remove(path, ec);
}

TEST(VizTxLifecycle, EmptyPathFailsGracefully) {
    mal_abm_fast::GifVizTxConfig cfg;
    cfg.path = "";
    mal_abm_fast::GifVizTx viz(cfg);
    EXPECT_FALSE(viz.ok());
    EXPECT_EQ(viz.frame_count(), 0);
    viz.finish();  // no crash on a failed renderer
}
