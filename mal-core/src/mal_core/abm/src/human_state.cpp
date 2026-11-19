// SPDX-License-Identifier: MIT
// human_state.cpp — Individual human population (SoA) with SEIR timers.
// See human_state.hpp for the design (plan Paso 2a).
#include "mal_abm_fast/human_state.hpp"

#include <algorithm>
#include <cmath>
#include <numeric>
#include <stdexcept>
#include <string>

namespace mal_abm_fast {

namespace {

double* bucket_of(HumanState s,
                  std::vector<double>& sus, std::vector<double>& exp,
                  std::vector<double>& inf, std::vector<double>& rec,
                  size_t cell) {
    switch (s) {
        case HumanState::SUSCEPTIBLE: return &sus[cell];
        case HumanState::EXPOSED:     return &exp[cell];
        case HumanState::INFECTIOUS:  return &inf[cell];
        case HumanState::RECOVERED:   return &rec[cell];
    }
    return &sus[cell];
}

// Uniform position of person `id` inside its cell: a pure function of
// (seed, id), so the position never depends on insertion order.
void uniform_in_cell(uint64_t seed, int64_t id, double& u, double& v) {
    uint64_t st = seed ^ (static_cast<uint64_t>(id) * 0x9E3779B97F4A7C15ULL);
    const uint64_t a = splitmix64(st);
    const uint64_t b = splitmix64(st);
    u = static_cast<double>(a >> 11) * (1.0 / 9007199254740992.0);
    v = static_cast<double>(b >> 11) * (1.0 / 9007199254740992.0);
}

// Float rounding must not push a position onto the cell's upper edge.
float below(double value, double upper) {
    float f = static_cast<float>(value);
    const float up = static_cast<float>(upper);
    if (f >= up) f = std::nextafter(up, 0.0f);
    return f;
}

}  // namespace

HumanState parse_human_state(const std::string& s) {
    if (s == "SUSCEPTIBLE") return HumanState::SUSCEPTIBLE;
    if (s == "EXPOSED")     return HumanState::EXPOSED;
    if (s == "INFECTIOUS")  return HumanState::INFECTIOUS;
    if (s == "RECOVERED")   return HumanState::RECOVERED;
    throw std::invalid_argument("unknown human state '" + s + "'");
}

void HumanSoA::clear() {
    human_id.clear(); cell_id.clear();
    home_x.clear(); home_y.clear(); cur_x.clear(); cur_y.clear();
    state.clear(); timer.clear(); susceptible.clear();
}

void HumanSoA::reserve(size_t n) {
    human_id.reserve(n); cell_id.reserve(n);
    home_x.reserve(n); home_y.reserve(n); cur_x.reserve(n); cur_y.reserve(n);
    state.reserve(n); timer.reserve(n); susceptible.reserve(n);
}

void HumanCompartmentGrid::init(
    int32_t h, int32_t w,
    const std::vector<float>& human_density,
    int32_t incubation_days,
    int32_t infectious_days,
    int32_t immunity_days,
    bool immunity_enabled,
    double initial_prevalence,
    double cell_m,
    uint64_t seed)
{
    if (h <= 0 || w <= 0) {
        throw std::invalid_argument("HumanCompartmentGrid: invalid grid dimensions");
    }
    if (!(cell_m > 0.0)) {
        throw std::invalid_argument("HumanCompartmentGrid: cell_m must be > 0");
    }
    h_ = h;
    w_ = w;
    cell_m_ = cell_m;
    const int64_t n_cells = static_cast<int64_t>(h_) * static_cast<int64_t>(w_);
    if (static_cast<int64_t>(human_density.size()) != n_cells) {
        throw std::invalid_argument(
            "HumanCompartmentGrid: human_density size (" +
            std::to_string(human_density.size()) + ") does not match h*w (" +
            std::to_string(n_cells) + ")");
    }

    incubation_days_ = std::max(1, incubation_days);
    infectious_days_ = std::max(1, infectious_days);
    immunity_days_   = std::max(1, immunity_days);
    immunity_enabled_ = immunity_enabled;

    const double init_prev = std::clamp(initial_prevalence, 0.0, 1.0);

    int64_t total = 0;
    std::vector<int64_t> count(static_cast<size_t>(n_cells), 0);
    for (int64_t c = 0; c < n_cells; ++c) {
        const double d = static_cast<double>(human_density[static_cast<size_t>(c)]);
        const int64_t n = (d > 0.0) ? static_cast<int64_t>(std::llround(d)) : 0;
        count[static_cast<size_t>(c)] = n;
        total += n;
    }

    soa_.clear();
    soa_.reserve(static_cast<size_t>(total));
    for (int64_t c = 0; c < n_cells; ++c) {
        const int64_t n = count[static_cast<size_t>(c)];
        const int32_t row = static_cast<int32_t>(c / w_);
        const int32_t col = static_cast<int32_t>(c % w_);
        // Row 0 is the northernmost row; y grows north from the SW corner.
        const double x0 = static_cast<double>(col) * cell_m_;
        const double y0 = static_cast<double>(h_ - 1 - row) * cell_m_;
        const int64_t n_inf = static_cast<int64_t>(
            std::llround(static_cast<double>(n) * init_prev));
        for (int64_t slot = 0; slot < n; ++slot) {
            const int64_t id = (c << 32) | slot;
            double u, v;
            uniform_in_cell(seed, id, u, v);
            const float px = below(x0 + u * cell_m_, x0 + cell_m_);
            const float py = below(y0 + v * cell_m_, y0 + cell_m_);
            soa_.human_id.push_back(id);
            soa_.cell_id.push_back(static_cast<int32_t>(c));
            soa_.home_x.push_back(px);
            soa_.home_y.push_back(py);
            soa_.cur_x.push_back(px);
            soa_.cur_y.push_back(py);
            soa_.susceptible.push_back(1);
            if (slot < n_inf) {
                soa_.state.push_back(static_cast<uint8_t>(HumanState::INFECTIOUS));
                // Timers spread evenly over the infectious period.
                soa_.timer.push_back(1 + static_cast<int32_t>(slot % infectious_days_));
            } else {
                soa_.state.push_back(static_cast<uint8_t>(HumanState::SUSCEPTIBLE));
                soa_.timer.push_back(0);
            }
        }
    }
    rebuild_cell_index_();
}

void HumanCompartmentGrid::set_individuals(const std::vector<HumanSeed>& people) {
    if (h_ <= 0 || w_ <= 0) {
        throw std::runtime_error("HumanCompartmentGrid::set_individuals: init() first");
    }
    const double width_m  = static_cast<double>(w_) * cell_m_;
    const double height_m = static_cast<double>(h_) * cell_m_;

    struct Placed { int64_t cell; size_t order; };
    std::vector<Placed> placed;
    placed.reserve(people.size());
    for (size_t k = 0; k < people.size(); ++k) {
        const HumanSeed& p = people[k];
        if (!(p.x >= 0.0 && p.x < width_m && p.y >= 0.0 && p.y < height_m)) {
            throw std::runtime_error(
                "human at (" + std::to_string(p.x) + " m, " + std::to_string(p.y) +
                " m) lies outside the " + std::to_string(w_) + "x" +
                std::to_string(h_) + " grid");
        }
        const int32_t col = static_cast<int32_t>(p.x / cell_m_);
        const int32_t row = h_ - 1 - static_cast<int32_t>(p.y / cell_m_);
        placed.push_back({static_cast<int64_t>(row) * w_ + col, k});
    }
    // Cell-major, declaration order inside a cell.
    std::stable_sort(placed.begin(), placed.end(),
                     [](const Placed& a, const Placed& b) { return a.cell < b.cell; });

    soa_.clear();
    soa_.reserve(people.size());
    int64_t prev_cell = -1;
    int64_t slot = 0;
    for (const Placed& pl : placed) {
        slot = (pl.cell == prev_cell) ? slot + 1 : 0;
        prev_cell = pl.cell;
        const HumanSeed& p = people[pl.order];
        soa_.human_id.push_back((pl.cell << 32) | slot);
        soa_.cell_id.push_back(static_cast<int32_t>(pl.cell));
        soa_.home_x.push_back(static_cast<float>(p.x));
        soa_.home_y.push_back(static_cast<float>(p.y));
        soa_.cur_x.push_back(static_cast<float>(p.x));
        soa_.cur_y.push_back(static_cast<float>(p.y));
        soa_.susceptible.push_back(1);
        soa_.state.push_back(static_cast<uint8_t>(p.state));
        int32_t t = 0;
        if (p.state != HumanState::SUSCEPTIBLE) {
            const int32_t full =
                (p.state == HumanState::EXPOSED)    ? incubation_days_
              : (p.state == HumanState::INFECTIOUS) ? infectious_days_
                                                    : immunity_days_;
            t = (p.timer_days > 0.0)
                    ? std::min(full, std::max(1, static_cast<int32_t>(std::lround(p.timer_days))))
                    : full;
        }
        soa_.timer.push_back(t);
    }
    rebuild_cell_index_();
}

void HumanCompartmentGrid::build_spatial_index(double target_bin_m) {
    if (h_ <= 0 || w_ <= 0) return;
    const double width_m  = static_cast<double>(w_) * cell_m_;
    const double height_m = static_cast<double>(h_) * cell_m_;
    // Cap the number of bins (~3e7) so a country-sized AOI stays cheap.
    constexpr double kMaxBins = 3.0e7;
    bin_m_ = std::max(target_bin_m, std::sqrt(width_m * height_m / kMaxBins));
    nbx_ = static_cast<int32_t>(std::ceil(width_m / bin_m_));
    nby_ = static_cast<int32_t>(std::ceil(height_m / bin_m_));
    const size_t nb = static_cast<size_t>(nbx_) * static_cast<size_t>(nby_);
    bin_begin_.assign(nb + 1, 0);
    auto key = [&](size_t i) {
        const int32_t bx = std::min(nbx_ - 1, static_cast<int32_t>(soa_.cur_x[i] / bin_m_));
        const int32_t by = std::min(nby_ - 1, static_cast<int32_t>(soa_.cur_y[i] / bin_m_));
        return static_cast<size_t>(by) * static_cast<size_t>(nbx_) + static_cast<size_t>(bx);
    };
    const size_t n = soa_.size();
    for (size_t i = 0; i < n; ++i) ++bin_begin_[key(i) + 1];
    for (size_t b = 0; b < nb; ++b) bin_begin_[b + 1] += bin_begin_[b];
    bin_people_.assign(n, 0);
    std::vector<int64_t> fill(bin_begin_.begin(), bin_begin_.end() - 1);
    for (size_t i = 0; i < n; ++i) bin_people_[static_cast<size_t>(fill[key(i)]++)] = static_cast<uint32_t>(i);
}

bool HumanCompartmentGrid::nearest_to_segment(
    double x0, double y0, double x1, double y1, double radius,
    SegmentHit& hit) const
{
    if (bin_begin_.empty() || radius <= 0.0) return false;
    const double xmin = std::min(x0, x1) - radius, xmax = std::max(x0, x1) + radius;
    const double ymin = std::min(y0, y1) - radius, ymax = std::max(y0, y1) + radius;
    const int32_t bx0 = std::max(0, static_cast<int32_t>(std::floor(xmin / bin_m_)));
    const int32_t bx1 = std::min(nbx_ - 1, static_cast<int32_t>(std::floor(xmax / bin_m_)));
    const int32_t by0 = std::max(0, static_cast<int32_t>(std::floor(ymin / bin_m_)));
    const int32_t by1 = std::min(nby_ - 1, static_cast<int32_t>(std::floor(ymax / bin_m_)));
    const double dx = x1 - x0, dy = y1 - y0;
    const double len2 = dx * dx + dy * dy;
    double best_d2 = radius * radius;
    int64_t best = -1;
    for (int32_t by = by0; by <= by1; ++by) {
        for (int32_t bx = bx0; bx <= bx1; ++bx) {
            const size_t b = static_cast<size_t>(by) * static_cast<size_t>(nbx_) + static_cast<size_t>(bx);
            for (int64_t k = bin_begin_[b]; k < bin_begin_[b + 1]; ++k) {
                const uint32_t i = bin_people_[static_cast<size_t>(k)];
                const double px = static_cast<double>(soa_.cur_x[i]) - x0;
                const double py = static_cast<double>(soa_.cur_y[i]) - y0;
                double t = (len2 > 0.0) ? (px * dx + py * dy) / len2 : 0.0;
                t = std::clamp(t, 0.0, 1.0);
                const double ex = px - t * dx, ey = py - t * dy;
                const double d2 = ex * ex + ey * ey;
                if (d2 <= best_d2) { best_d2 = d2; best = static_cast<int64_t>(i); }
            }
        }
    }
    if (best < 0) return false;
    hit.person = best;
    hit.d_min = std::sqrt(best_d2);
    // First point of the segment within `radius` of the person.
    const double px = static_cast<double>(soa_.cur_x[static_cast<size_t>(best)]) - x0;
    const double py = static_cast<double>(soa_.cur_y[static_cast<size_t>(best)]) - y0;
    if (len2 <= 0.0 || px * px + py * py <= radius * radius) {
        hit.t_entry = 0.0;
    } else {
        // |t*d - p|^2 = r^2  =>  len2 t^2 - 2 (p.d) t + (|p|^2 - r^2) = 0, smaller root
        const double b = px * dx + py * dy;
        const double c = px * px + py * py - radius * radius;
        const double disc = std::max(0.0, b * b - len2 * c);
        hit.t_entry = std::clamp((b - std::sqrt(disc)) / len2, 0.0, 1.0);
    }
    return true;
}

void HumanCompartmentGrid::rebuild_cell_index_() {
    bin_begin_.clear();
    bin_people_.clear();
    const size_t n_cells = static_cast<size_t>(total_cells());
    cell_begin_.assign(n_cells + 1, 0);
    for (size_t i = 0; i < soa_.size(); ++i) {
        ++cell_begin_[static_cast<size_t>(soa_.cell_id[i]) + 1];
    }
    for (size_t c = 0; c < n_cells; ++c) cell_begin_[c + 1] += cell_begin_[c];

    susceptible_.assign(n_cells, 0.0);
    exposed_.assign(n_cells, 0.0);
    infectious_.assign(n_cells, 0.0);
    recovered_.assign(n_cells, 0.0);
    population_.assign(n_cells, 0.0);
    daily_incidence_.assign(n_cells, 0.0);
    daily_prevalence_.assign(n_cells, 0.0);

    for (size_t i = 0; i < soa_.size(); ++i) {
        const size_t c = static_cast<size_t>(soa_.cell_id[i]);
        population_[c] += 1.0;
        *bucket_of(static_cast<HumanState>(soa_.state[i]),
                   susceptible_, exposed_, infectious_, recovered_, c) += 1.0;
    }
    for (size_t c = 0; c < n_cells; ++c) refresh_prevalence_(c);
}

void HumanCompartmentGrid::refresh_prevalence_(size_t cell) {
    daily_prevalence_[cell] =
        (population_[cell] > 0.0) ? infectious_[cell] / population_[cell] : 0.0;
}

void HumanCompartmentGrid::set_state_(size_t i, HumanState to, int32_t timer) {
    const size_t c = static_cast<size_t>(soa_.cell_id[i]);
    *bucket_of(static_cast<HumanState>(soa_.state[i]),
               susceptible_, exposed_, infectious_, recovered_, c) -= 1.0;
    *bucket_of(to, susceptible_, exposed_, infectious_, recovered_, c) += 1.0;
    soa_.state[i] = static_cast<uint8_t>(to);
    soa_.timer[i] = timer;
    refresh_prevalence_(c);
}

int64_t HumanCompartmentGrid::infect_first_susceptibles_(size_t cell, int64_t n) {
    int64_t done = 0;
    const size_t b = static_cast<size_t>(cell_begin_[cell]);
    const size_t e = static_cast<size_t>(cell_begin_[cell + 1]);
    for (size_t i = b; i < e && done < n; ++i) {
        if (soa_.state[i] != static_cast<uint8_t>(HumanState::SUSCEPTIBLE)) continue;
        // Imported cases enter at infectious age zero (full infectious period).
        set_state_(i, HumanState::INFECTIOUS, infectious_days_);
        ++done;
    }
    return done;
}

void HumanCompartmentGrid::seed_infections(int32_t row, int32_t col, double count) {
    if (row < 0 || row >= h_ || col < 0 || col >= w_) return;
    if (count <= 0.0) return;
    const size_t c = static_cast<size_t>(row) * static_cast<size_t>(w_) +
                     static_cast<size_t>(col);
    if (population_[c] <= 0.0) return;
    infect_first_susceptibles_(c, static_cast<int64_t>(std::llround(count)));
}

std::vector<std::pair<int32_t, int32_t>> HumanCompartmentGrid::seed_random_viable_foci(
    int32_t n_foci,
    double cases_per_focus,
    double min_pop,
    const std::vector<float>& mosquito_density,
    Prng& rng)
{
    std::vector<std::pair<int32_t, int32_t>> seeded;
    if (n_foci <= 0 || cases_per_focus <= 0.0) return seeded;

    const int64_t n_cells = total_cells();
    std::vector<int64_t> with_mosquitoes;

    for (int64_t c = 0; c < n_cells; ++c) {
        const size_t idx = static_cast<size_t>(c);
        if (population_[idx] >= min_pop && susceptible_[idx] > 0.0) {
            if (!mosquito_density.empty() && idx < mosquito_density.size() &&
                mosquito_density[idx] > 0.0f)
            {
                with_mosquitoes.push_back(c);
            }
        }
    }

    // A viable outbreak focus needs local vectors; human-only fallback would
    // falsely report transmission establishment.
    if (with_mosquitoes.empty()) return seeded;
    std::vector<int64_t>& pool = with_mosquitoes;

    // Shuffle pool using Fisher-Yates
    for (size_t i = pool.size() - 1; i > 0; --i) {
        size_t j = static_cast<size_t>(rng.uniform_double() * static_cast<double>(i + 1));
        if (j > i) j = i;
        std::swap(pool[i], pool[j]);
    }

    const size_t count = std::min(static_cast<size_t>(n_foci), pool.size());
    for (size_t i = 0; i < count; ++i) {
        const int64_t c = pool[i];
        const int32_t r = static_cast<int32_t>(c / w_);
        const int32_t col = static_cast<int32_t>(c % w_);
        seed_infections(r, col, cases_per_focus);
        seeded.push_back({r, col});
    }

    return seeded;
}

void HumanCompartmentGrid::seed_explicit_foci(
    const std::vector<std::tuple<int32_t, int32_t, double>>& foci)
{
    for (const auto& [r, c, cases] : foci) {
        seed_infections(r, c, cases);
    }
}

std::vector<std::pair<int32_t, int32_t>> HumanCompartmentGrid::seed_outbreak_cluster(
    int32_t core_row,
    int32_t core_col,
    double total_cases,
    int32_t radius_cells,
    double min_pop,
    const std::vector<float>& mosquito_density,
    Prng& rng)
{
    std::vector<std::pair<int32_t, int32_t>> seeded;
    if (total_cases <= 0.0 || radius_cells < 0) return seeded;
    if (core_row < 0 || core_row >= h_ || core_col < 0 || core_col >= w_) {
        return seeded;
    }

    // 1. Candidate cluster cells: Chebyshev window around the core,
    //    human pop >= min_pop. Core always included (min(pop, cases)).
    struct Candidate { int32_t r, c; double pop; };
    std::vector<Candidate> cands;
    const int32_t r0 = std::max(0, core_row - radius_cells);
    const int32_t r1 = std::min(h_ - 1, core_row + radius_cells);
    const int32_t c0 = std::max(0, core_col - radius_cells);
    const int32_t c1 = std::min(w_ - 1, core_col + radius_cells);
    for (int32_t r = r0; r <= r1; ++r) {
        for (int32_t c = c0; c <= c1; ++c) {
            const size_t idx = static_cast<size_t>(r) * static_cast<size_t>(w_) +
                               static_cast<size_t>(c);
            if (population_[idx] >= min_pop) {
                cands.push_back({r, c, population_[idx]});
            }
        }
    }
    if (cands.empty()) return seeded;

    // 2. Share per cell ∝ pop × (floor + mosquito density): cases
    //    concentrate where humans AND vectors coexist — the imported
    //    cases land in the transmission-receptive part of the cluster,
    //    not in the densest (most diluting) cell. The floor keeps
    //    temporarily vector-free cells in the pool. Cells can receive
    //    at most their susceptible count (seed_infections truncates);
    //    redistribute the remainder over the next-largest cells so a
    //    small-core cluster still concentrates the cases.
    //    The floor is a local scenario constant (not a YAML model key).
    std::vector<double> shares(cands.size());
    double w_total = 0.0;
    for (size_t i = 0; i < cands.size(); ++i) {
        const size_t idx = static_cast<size_t>(cands[i].r) *
            static_cast<size_t>(w_) + static_cast<size_t>(cands[i].c);
        const float dens = (idx < mosquito_density.size())
            ? mosquito_density[idx] : 0.0f;
        const double wt = static_cast<double>(cands[i].pop) *
            (0.05 + static_cast<double>(dens));
        shares[i] = wt;
        w_total += wt;
    }
    if (w_total <= 0.0) return seeded;
    for (double& s : shares) s = total_cases * (s / w_total);
    // Largest-share-first seeding: receptive cells take their full
    // share, then leftovers flow to the rest (two-pass greedy).
    std::vector<size_t> order(cands.size());
    for (size_t i = 0; i < order.size(); ++i) order[i] = i;
    std::sort(order.begin(), order.end(), [&](size_t a, size_t b) {
        return shares[a] > shares[b];
    });
    double remaining = total_cases;
    for (size_t k = 0; k < order.size() && remaining > 1e-9; ++k) {
        const size_t i = order[k];
        const size_t idx = static_cast<size_t>(cands[i].r) *
            static_cast<size_t>(w_) + static_cast<size_t>(cands[i].c);
        const double want = std::min(shares[i], remaining);
        const double before = infectious_[idx];
        seed_infections(cands[i].r, cands[i].c, want);
        remaining -= (infectious_[idx] - before);
        seeded.push_back({cands[i].r, cands[i].c});
    }
    (void)rng;  // deterministic distribution; rng kept for API symmetry
    return seeded;
}

void HumanCompartmentGrid::advance_day() {
    std::fill(daily_incidence_.begin(), daily_incidence_.end(), 0.0);

    const uint8_t S = static_cast<uint8_t>(HumanState::SUSCEPTIBLE);
    const size_t n = soa_.size();
    for (size_t i = 0; i < n; ++i) {
        const uint8_t st = soa_.state[i];
        if (st == S) continue;
        if (--soa_.timer[i] > 0) continue;
        switch (static_cast<HumanState>(st)) {
            case HumanState::EXPOSED:
                set_state_(i, HumanState::INFECTIOUS, infectious_days_);
                break;
            case HumanState::INFECTIOUS:
                if (immunity_enabled_) {
                    set_state_(i, HumanState::RECOVERED, immunity_days_);
                } else {
                    set_state_(i, HumanState::SUSCEPTIBLE, 0);   // I -> S, no immunity
                }
                break;
            case HumanState::RECOVERED:
                set_state_(i, HumanState::SUSCEPTIBLE, 0);       // immunity waned
                break;
            case HumanState::SUSCEPTIBLE:
                break;
        }
    }
}

int64_t HumanCompartmentGrid::pick_person(int32_t row, int32_t col, Prng& rng) const {
    if (row < 0 || row >= h_ || col < 0 || col >= w_) return -1;
    const size_t c = static_cast<size_t>(row) * static_cast<size_t>(w_) +
                     static_cast<size_t>(col);
    const int64_t b = cell_begin_[c];
    const int64_t n = cell_begin_[c + 1] - b;
    if (n <= 0) return -1;
    int64_t k = static_cast<int64_t>(rng.uniform_double() * static_cast<double>(n));
    if (k >= n) k = n - 1;
    return b + k;
}

bool HumanCompartmentGrid::expose(int64_t index) {
    if (index < 0 || index >= n_people()) return false;
    const size_t i = static_cast<size_t>(index);
    if (soa_.state[i] != static_cast<uint8_t>(HumanState::SUSCEPTIBLE) ||
        soa_.susceptible[i] == 0) {
        return false;
    }
    // The timer starts at the full incubation period and is only decremented
    // by the following days, so the person turns infectious after exactly
    // `incubation_days_` further advance_day() calls.
    set_state_(i, HumanState::EXPOSED, incubation_days_);
    daily_incidence_[static_cast<size_t>(soa_.cell_id[i])] += 1.0;
    return true;
}

HumanCompartmentStats HumanCompartmentGrid::compute_stats() const {
    HumanCompartmentStats stats;
    const int64_t n = total_cells();
    for (int64_t i = 0; i < n; ++i) {
        const size_t idx = static_cast<size_t>(i);
        stats.total_susceptible += susceptible_[idx];
        stats.total_exposed     += exposed_[idx];
        stats.total_infectious  += infectious_[idx];
        stats.total_recovered   += recovered_[idx];
        stats.total_population  += population_[idx];
        stats.total_incidence   += daily_incidence_[idx];
    }
    if (stats.total_population > 0.0) {
        stats.mean_prevalence = stats.total_infectious / stats.total_population;
    }
    return stats;
}

bool HumanCompartmentGrid::validate_invariants(bool strict) const {
    auto fail = [&](const std::string& msg) {
        if (strict) throw std::runtime_error("HumanCompartmentGrid invariant violation: " + msg);
        return false;
    };

    const size_t n_cells = static_cast<size_t>(total_cells());
    if (cell_begin_.size() != n_cells + 1 ||
        cell_begin_.back() != static_cast<int64_t>(soa_.size())) {
        return fail("cell index does not cover the population");
    }

    std::vector<double> s(n_cells, 0.0), e(n_cells, 0.0), in(n_cells, 0.0), r(n_cells, 0.0);
    const double width_m  = static_cast<double>(w_) * cell_m_;
    const double height_m = static_cast<double>(h_) * cell_m_;
    for (size_t i = 0; i < soa_.size(); ++i) {
        const int32_t cell = soa_.cell_id[i];
        if (cell < 0 || static_cast<size_t>(cell) >= n_cells) {
            return fail("person " + std::to_string(i) + " has cell_id out of range");
        }
        const size_t c = static_cast<size_t>(cell);
        if (static_cast<int64_t>(i) < cell_begin_[c] || static_cast<int64_t>(i) >= cell_begin_[c + 1]) {
            return fail("person " + std::to_string(i) + " is outside its cell's range");
        }
        if (i > 0 && soa_.human_id[i] <= soa_.human_id[i - 1]) {
            return fail("human_id not strictly increasing at person " + std::to_string(i));
        }
        if ((soa_.human_id[i] >> 32) != cell) {
            return fail("human_id of person " + std::to_string(i) + " does not encode its cell");
        }
        // The cell of a position: column from x, row from y (row 0 = north).
        const int32_t pcol = static_cast<int32_t>(soa_.home_x[i] / cell_m_);
        const int32_t prow = h_ - 1 - static_cast<int32_t>(soa_.home_y[i] / cell_m_);
        if (!(soa_.home_x[i] >= 0.0f && soa_.home_x[i] < width_m &&
              soa_.home_y[i] >= 0.0f && soa_.home_y[i] < height_m) ||
            static_cast<int64_t>(prow) * w_ + pcol != cell) {
            return fail("person " + std::to_string(i) + " is not inside its home cell");
        }
        const auto st = static_cast<HumanState>(soa_.state[i]);
        if (st == HumanState::SUSCEPTIBLE) {
            s[c] += 1.0;
        } else {
            if (soa_.timer[i] <= 0) {
                return fail("person " + std::to_string(i) + " has a non-positive timer");
            }
            (st == HumanState::EXPOSED ? e : st == HumanState::INFECTIOUS ? in : r)[c] += 1.0;
        }
    }
    for (size_t c = 0; c < n_cells; ++c) {
        if (s[c] != susceptible_[c] || e[c] != exposed_[c] ||
            in[c] != infectious_[c] || r[c] != recovered_[c] ||
            s[c] + e[c] + in[c] + r[c] != population_[c]) {
            return fail("derived statistics of cell " + std::to_string(c) +
                        " disagree with the individuals");
        }
    }
    return true;
}

}  // namespace mal_abm_fast
