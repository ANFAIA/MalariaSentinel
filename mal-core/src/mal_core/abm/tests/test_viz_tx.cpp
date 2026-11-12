// SPDX-License-Identifier: MIT
// test_viz_tx.cpp — GoogleTest for transmission-GIF diagnostics and
// a light smoke test of the GifVizTx lifecycle.
#include <gtest/gtest.h>

#include <cmath>
#include <filesystem>
#include <vector>

#include "mobility_schedule.hpp"
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
using mal_abm_fast::tx_diag::extract_top_flows;
using mal_abm_fast::tx_diag::TxFlow;

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
// Top-OD flow extraction (plan 05 §9.4): expected E[F] = P·H_res.
// ---------------------------------------------------------------------------

namespace {

// 2x2 grid (W=2 → 4 cells). Rows 0 and 2 have residents.
//   cell0 (r0,c0): 10 ppl, 50% stay / 50% -> cell1
//   cell2 (r1,c0): 5 ppl, 20% stay / 80% -> cell3
// Off-diagonal expected flows: cell0->cell1 = 5, cell2->cell3 = 4.
mal_abm_fast::SparseOD make_tiny_od() {
    std::vector<int32_t> rp = {0, 2, 2, 4, 4};
    std::vector<int32_t> ci = {0, 1, 2, 3};
    std::vector<float>   vl = {0.5f, 0.5f, 0.2f, 0.8f};
    return mal_abm_fast::SparseOD(std::move(rp), std::move(ci),
                                  std::move(vl), 4, 4);
}

}  // namespace

TEST(VizTxFlows, ExtractsTopFlowsAndMovedTotal) {
    const auto od = make_tiny_od();
    const std::vector<float> res = {10.0f, 0.0f, 5.0f, 0.0f};
    double moved = 0.0;
    const auto flows = extract_top_flows(od, res, /*W=*/2, /*K=*/10, moved);

    EXPECT_NEAR(moved, 9.0, 1e-6);  // 5 + 4
    ASSERT_EQ(flows.size(), 2u);
    // Sorted by volume descending.
    EXPECT_NEAR(flows[0].vol, 5.0f, 1e-6);
    EXPECT_EQ(flows[0].fr, 0); EXPECT_EQ(flows[0].fc, 0);
    EXPECT_EQ(flows[0].tr, 0); EXPECT_EQ(flows[0].tc, 1);
    EXPECT_NEAR(flows[1].vol, 4.0f, 1e-6);
    EXPECT_EQ(flows[1].fr, 1); EXPECT_EQ(flows[1].fc, 0);
    EXPECT_EQ(flows[1].tr, 1); EXPECT_EQ(flows[1].tc, 1);
}

TEST(VizTxFlows, RespectsTopKLimit) {
    const auto od = make_tiny_od();
    const std::vector<float> res = {10.0f, 0.0f, 5.0f, 0.0f};
    double moved = 0.0;
    const auto flows = extract_top_flows(od, res, /*W=*/2, /*K=*/1, moved);
    ASSERT_EQ(flows.size(), 1u);
    EXPECT_NEAR(flows[0].vol, 5.0f, 1e-6);  // the largest only
    EXPECT_NEAR(moved, 9.0, 1e-6);          // moved total is independent of K
}

TEST(VizTxFlows, IdentityOnlyYieldsNoMovement) {
    // Everyone stays home: all flows are diagonal → nothing moves.
    const auto od = mal_abm_fast::SparseOD::identity(4);
    const std::vector<float> res = {10.0f, 1.0f, 5.0f, 2.0f};
    double moved = 0.0;
    const auto flows = extract_top_flows(od, res, /*W=*/2, /*K=*/10, moved);
    EXPECT_TRUE(flows.empty());
    EXPECT_NEAR(moved, 0.0, 1e-9);
}

TEST(VizTxFlows, ZeroPopulationYieldsNoFlows) {
    const auto od = make_tiny_od();
    const std::vector<float> res = {0.0f, 0.0f, 0.0f, 0.0f};
    double moved = 0.0;
    const auto flows = extract_top_flows(od, res, /*W=*/2, /*K=*/10, moved);
    EXPECT_TRUE(flows.empty());
    EXPECT_NEAR(moved, 0.0, 1e-9);
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
