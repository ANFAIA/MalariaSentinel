// SPDX-License-Identifier: MIT
// viz_tx.hpp — native in-process GIF renderer for malaria TRANSMISSION
// (plan 05, "mapa 2"). Complementary to the habitat/expansion GIF
// (viz.hpp, "mapa 1"): map 1 answers "dónde cría y cómo se expande el
// vector"; map 2 answers "dónde pica, a quién y cómo viaja la
// infección". No habitat information is rendered here (no S, no K, no
// aquatic cohorts, no pluvial z, no patch markers): the strict
// complementarity with map 1 is a hard rule (plan 05 §6).
//
// The renderer draws one frame per simulated day from LIVE engine state
// and encodes it with the vendored gif-h. It is a diagnostic view, never
// a model input: a rendering failure must not abort the simulation
// (observe()/finish() never throw) and it consumes no engine RNG.
//
// Shape encodes scale (plan 04 §2.2): square = aggregate / event, circle
// = individual adult agent — identical symbology to map 1.
#pragma once

#include <memory>
#include <string>
#include <vector>

#include "mosquito_submodel.hpp"  // DailyStats

namespace mal_abm_fast {

class Engine;
struct SparseOD;  // forward decl (defined in mobility_schedule.hpp)

/// Pure, unit-testable diagnostics for the transmission GIF.
namespace tx_diag {

struct TxFlow {
    int32_t fr = 0, fc = 0, tr = 0, tc = 0;
    float vol = 0.0f;
};

/// Biteable-cell class: 0 = no host, 1 = animal-only, 2 = has humans.
int classify_biteable(double humans, double livestock);

/// Top-K non-diagonal OD flows weighted by residential population
/// (expected flow E[F] = P(i→j)·H_res(i); deterministic, no RNG).
/// `moved_out` receives the total population moved off its home cell.
std::vector<TxFlow> extract_top_flows(const SparseOD& od,
                                      const std::vector<float>& residential,
                                      int32_t W, int K, double& moved_out);

}  // namespace tx_diag

struct GifVizTxConfig {
    std::string path;   // output .gif file
    int  width = 1280;  // clamped to [640, 2048]
    int  fps   = 6;     // delay = round(100 / fps) centiseconds
    int  every = 1;     // emit one frame every N simulated days
    // No `transmission` flag: this renderer only makes sense on a run with
    // --enable-transmission, and main.cpp only constructs it then.
};

class GifVizTx {
public:
    explicit GifVizTx(const GifVizTxConfig& cfg);
    ~GifVizTx();

    GifVizTx(GifVizTx&&) noexcept;
    GifVizTx& operator=(GifVizTx&&) noexcept;
    GifVizTx(const GifVizTx&) = delete;
    GifVizTx& operator=(const GifVizTx&) = delete;

    /// False when the canvas/encoder/file could not be set up. The caller
    /// only logs; a failed renderer never fails the run.
    bool ok() const;

    /// Draw (and emit, when the day matches `every`) one frame from the
    /// current engine state. `history` is the mosquito DailyStats collected
    /// so far (used for the movement panel's day axis context); the SEIR /
    /// bite series are read from the TransmissionModel's own history and
    /// the bite ledger. Consumes no engine RNG.
    void observe(const Engine& engine,
                 const std::vector<DailyStats>& history,
                 int day_index,
                 int total_days);

    /// Flush the GIF trailer and close the file. Idempotent.
    void finish();

    /// Number of frames actually written (for the CLI summary line).
    int frame_count() const;

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

}  // namespace mal_abm_fast
