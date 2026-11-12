// SPDX-License-Identifier: MIT
// viz_common.hpp — shared raster primitives for the native GIF renderers.
//
// Extracted from viz.cpp (plan 04 / plan 05 §7) so the habitat GIF
// (map 1) and the transmission GIF (map 2, viz_tx) compose pixels with
// the SAME Canvas, text, and panel primitives. No model logic lives
// here: this is a pure software rasterizer over an RGBA buffer, encoded
// by the caller with the vendored gif-h.
//
// Shape encodes scale (plan 04 §2.2): square = aggregate, circle =
// individual agent. The Canvas is never a model input.
#pragma once

#include <chrono>
#include <cstdint>
#include <memory>
#include <string>
#include <utility>
#include <vector>

namespace mal_abm_fast {

/// RGBA colour. `a` = 255 is opaque; the Canvas alpha-blends anything lower.
struct Color {
    uint8_t r = 0, g = 0, b = 0, a = 255;
};

/// Linear interpolation between two colours (alpha forced opaque).
Color lerp(Color a, Color b, double t);

/// Software rasterizer over a row-major RGBA buffer.
class Canvas {
public:
    Canvas(int w, int h);

    int width() const { return w_; }
    int height() const { return h_; }
    uint8_t* data() { return px_.data(); }
    const uint8_t* data() const { return px_.data(); }
    bool valid() const;

    void fill(Color c);
    void blend(int x, int y, Color c);
    void fill_rect(int x, int y, int w, int h, Color c);
    void stroke_rect(int x, int y, int w, int h, Color c);
    void disc(int cx, int cy, int r, Color c);
    void ring(int cx, int cy, int r, Color c);
    void line(int x0, int y0, int x1, int y1, Color c);
    void text(int x, int y, const std::string& s, Color c, int scale = 2);

private:
    int w_ = 0;
    int h_ = 0;
    std::vector<uint8_t> px_;
};

// --- text metrics -------------------------------------------------------

int text_w(const std::string& s, int scale = 2);
int text_scale_fit(const std::string& s, int avail_px);

// --- formatting ---------------------------------------------------------

/// Compact integer formatting ("1.23M" / "45.6k" / "1234") for info blocks.
std::string fmt_count(int64_t v);
/// ISO calendar date "YYYY-MM-DD" for a sys_days.
std::string date_iso(std::chrono::sys_days d);

// --- plotting helpers ---------------------------------------------------

/// Log/linear value → pixel row inside a plot rect (y0 = top).
int plot_y(double v, double vmin, double vmax, int y0, int h, bool log_scale);
/// Exact power of ten for decade bounds.
double dec_pow10(int d);

// --- shared panel chrome ------------------------------------------------

/// Draw a filled panel with a border and a dim title; used by every
/// right-column chart in both maps.
void draw_panel_frame(Canvas& cv, int x, int y, int w, int h,
                      const std::string& title);
/// Draw a title-titled list of (text, colour) metric rows, shrinking the
/// row pitch (never the list) so every line fits even on the 640px canvas.
void draw_info(Canvas& cv, int x, int y, int w, int h,
               const std::vector<std::pair<std::string, Color>>& lines);

// --- shared palette -----------------------------------------------------
// Background / chrome, mosquito gonotrophic state colours (identical
// symbology across map 1 and map 2 — plan 05 §9.7), and the human
// prevalence / infection red. Map-specific colours stay in each renderer.

extern const Color kBackground;
extern const Color kPanel;
extern const Color kPanelBorder;
extern const Color kText;
extern const Color kTextDim;
extern const Color kHostSeek;    // host-seeking / teneral mosquito
extern const Color kBloodFed;    // blood-fed / resting mosquito
extern const Color kGravid;      // gravid mosquito
extern const Color kInfectious;  // I_V ring / infectious marker
extern const Color kPrev;        // human prevalence / infection red

// --- GIF encoding ------------------------------------------------------
// The vendored gif-h defines non-inline functions, so it must be compiled
// in exactly ONE translation unit. Both renderers (map 1 and map 2) encode
// through this thin RAII wrapper, whose implementation (viz_common.cpp) is
// the sole includer of gif.h (plan 05 §7).
class GifSink {
public:
    GifSink();
    ~GifSink();
    GifSink(GifSink&&) noexcept;
    GifSink& operator=(GifSink&&) noexcept;
    GifSink(const GifSink&) = delete;
    GifSink& operator=(const GifSink&) = delete;

    /// Open `path` for a width×height GIF; `delay_cs` is the per-frame
    /// delay in centiseconds. Returns false on failure (bad path/IO).
    bool open(const std::string& path, int width, int height,
              uint32_t delay_cs);
    /// Append one RGBA8 frame (width*height*4 bytes). False if not open.
    bool write_frame(const uint8_t* rgba, int width, int height,
                     uint32_t delay_cs);
    /// Close the file and free the encoder. Idempotent.
    void close();
    bool is_open() const;

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

}  // namespace mal_abm_fast
