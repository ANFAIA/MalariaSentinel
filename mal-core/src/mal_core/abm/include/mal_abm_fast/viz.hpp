// SPDX-License-Identifier: MIT
// viz.hpp — native in-process GIF renderer for the ABM (plan 04).
//
// The renderer draws one frame per simulated day from the LIVE engine state
// (no state COGs are read back) and encodes them with the vendored public
// domain gif-h. It is a diagnostic view, never a model input: a rendering
// failure must not abort the simulation (observe()/finish() never throw).
//
// Shape encodes scale (plan 04 §2.2): square = patch/cohort aggregate,
// circle = individual adult agent.
#pragma once

#include <memory>
#include <string>
#include <vector>

#include "mosquito_submodel.hpp"  // DailyStats

namespace mal_abm_fast {

class Engine;

struct GifVizConfig {
    std::string path;              // output .gif file
    int  width     = 1280;         // clamped to [640, 2048]
    int  fps       = 6;            // delay = round(100 / fps) centiseconds
    int  every     = 1;            // emit one frame every N simulated days
    bool transmission = false;     // draw the human-prevalence tint + I_H/R_eff
};

class GifViz {
public:
    explicit GifViz(const GifVizConfig& cfg);
    ~GifViz();

    GifViz(GifViz&&) noexcept;
    GifViz& operator=(GifViz&&) noexcept;
    GifViz(const GifViz&) = delete;
    GifViz& operator=(const GifViz&) = delete;

    /// False when the canvas/encoder/file could not be set up. The caller
    /// only logs; a failed renderer never fails the run.
    bool ok() const;

    /// Draw (and emit, when the day matches `every`) one frame from the
    /// current engine state. `history` is the daily stats collected so far,
    /// including the day that just stepped.
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
