// SPDX-License-Identifier: MIT
// test_transmission_chain.cpp — BUG-3 regression: the SEIR-SEI chain must
// actually complete (S_V -> E_V -> I_V -> infectious bite -> E_H) when a
// human infectious focus sits next to a vector population.
//
// Root cause pinned here: `TransmissionModel::check_and_trigger_outbreak`
// used to require adult vectors in the SAME grid cell as the human focus,
// while the host-seeking kernel detects and bites hosts up to
// host_seeking_radius_m (~1.5 km, i.e. the 8-neighbourhood at 1 km cells)
// away. The outbreak therefore waited for a random dispersal event to drop
// a single mosquito into the settlement and the human infectious window
// closed before the vector cohort could complete an EIP.
#include <gtest/gtest.h>

#include <cmath>
#include <cstdint>
#include <vector>

#include "mal_abm_fast/aoi.hpp"
#include "mal_abm_fast/climate.hpp"
#include "mal_abm_fast/host_landscape.hpp"
#include "mal_abm_fast/host_seeking.hpp"
#include "mal_abm_fast/mosquito_submodel.hpp"
#include "mal_abm_fast/seeding.hpp"
#include "mal_abm_fast/transmission.hpp"
#include "mal_abm_fast/wire.hpp"

namespace mal_abm_fast {
namespace {

AOI make_aoi() {
    AOI aoi;
    aoi.west         = 0.0;
    aoi.south        = 0.0;
    aoi.east         = 0.027;   // 3 cells at 1 km
    aoi.north        = 0.026;   // 3 cells (ceil)
    aoi.resolution_m = 1000;
    aoi.crs          = "EPSG:4326";
    aoi.slug         = "chain_test";
    aoi.scale        = "regional";
    return aoi;
}

std::vector<PatchState> make_patch_states(int32_t h, int32_t w) {
    std::vector<PatchState> ps(static_cast<size_t>(h) * static_cast<size_t>(w));
    for (int32_t r = 0; r < h; ++r) {
        for (int32_t c = 0; c < w; ++c) {
            const size_t idx = static_cast<size_t>(r) * static_cast<size_t>(w) +
                               static_cast<size_t>(c);
            ps[idx].patch_id  = static_cast<int64_t>(idx);
            ps[idx].row       = r;
            ps[idx].col       = c;
            ps[idx].activated = true;
            ps[idx].rain_d    = 20.0f;
            ps[idx].temp_d    = 25.0f;
            ps[idx].k_habitat = 1000.0f;
        }
    }
    return ps;
}

// A focus cell with humans but NO same-cell vectors; the only vectors sit
// in the neighbouring cell, one host-seeking radius away.
TEST(TransmissionChain, SeedsHumanFocusAdjacentToVectors) {
    const int32_t h = 3;
    const int32_t w = 3;
    std::vector<float> human_pop(static_cast<size_t>(h * w), 0.0f);
    human_pop[1 * w + 1] = 500.0f;

    std::vector<float> density(static_cast<size_t>(h * w), 0.0f);
    density[1 * w + 2] = 100.0f;

    TransmissionModel tm;
    TransmissionParams params;
    params.enabled = true;
    params.human_seeding_mode = "random-viable";
    params.human_outbreak_cases = 200.0;
    params.human_min_cell_pop = 50.0;
    tm.init(h, w, human_pop, params, 42);

    tm.check_and_trigger_outbreak(0, density);

    EXPECT_TRUE(tm.outbreak_triggered());
    EXPECT_GT(tm.human_grid().i_at(1, 1), 0.0)
        << "focus must be seeded in the human cell reachable from the "
           "vectors in the neighbouring cell";
}

TEST(TransmissionChain, CompletesHumanVectorHumanCycle) {
    const AOI aoi = make_aoi();
    const int32_t w = aoi.cells_per_side();
    const int32_t h = cells_per_side_h(aoi);
    ASSERT_GE(h, 2);
    ASSERT_GE(w, 3);

    const size_t n_cells = static_cast<size_t>(h) * static_cast<size_t>(w);
    const int32_t focus_r = 1;
    const int32_t focus_c = 1;
    const int32_t vector_r = 1;
    const int32_t vector_c = 2;

    std::vector<float> human_pop(n_cells, 0.0f);
    human_pop[static_cast<size_t>(focus_r) * w + focus_c] = 500.0f;

    std::vector<float> density(n_cells, 0.0f);
    density[static_cast<size_t>(vector_r) * w + vector_c] = 100.0f;

    TransmissionModel tm;
    TransmissionParams params;
    params.enabled = true;
    params.human_seeding_mode = "random-viable";
    params.human_outbreak_cases = 200.0;
    params.human_min_cell_pop = 50.0;
    params.human_outbreak_foci = 1;
    tm.init(h, w, human_pop, params, 7);
    tm.check_and_trigger_outbreak(0, density);
    ASSERT_GT(tm.human_grid().i_at(focus_r, focus_c), 0.0);

    // Humans live only in the focus cell; vectors rest one cell away and
    // must detect the focus through the host-seeking kernel.
    HostLandscape residential;
    residential.load_from_nc("/nonexistent/hosts_chain_test.nc", aoi);
    std::vector<float> h_eff(n_cells, 0.0f);
    h_eff[static_cast<size_t>(focus_r) * w + focus_c] = 500.0f;
    HostLandscape hosts = HostLandscape::make_effective(
        residential, h_eff, h, w);

    HostSeekingModel host_seeking;

    SeedInstruction inst;
    inst.patch_id = static_cast<int32_t>(
        static_cast<size_t>(vector_r) * w + vector_c);
    inst.row = vector_r;
    inst.col = vector_c;
    const double cell_w = (aoi.east - aoi.west) / static_cast<double>(w);
    const double cell_h = (aoi.north - aoi.south) / static_cast<double>(h);
    inst.lon = aoi.west + (vector_c + 0.5) * cell_w;
    inst.lat = aoi.north - (vector_r + 0.5) * cell_h;
    inst.n_adults = 400;
    inst.n_larvae = 0;
    std::vector<SeedInstruction> instructions{inst};

    MosquitoSubmodel sub(1, instructions, 11);
    sub.set_host_landscape(&hosts);
    sub.set_host_seeking_model(&host_seeking);
    sub.set_human_compartment_grid(&tm.human_grid());
    sub.set_transmission_params(&params);

    const std::vector<PatchState> patch_states = make_patch_states(h, w);
    ClimateEngine climate;

    bool saw_e_v = false;
    bool saw_i_v = false;
    bool saw_infectious_bites = false;
    bool saw_e_h = false;
    bool saw_bites_on_humans = false;

    for (int32_t day = 0; day < 45; ++day) {
        sub.advance_day(aoi, patch_states);
        tm.advance_vector_eip(sub.soa_mutable(), climate, patch_states, aoi);
        tm.advance_human_transmission(sub.bite_ledger(), aoi);
        tm.record_daily_stats(day, sub.soa(), sub.bite_ledger());

        const auto& stats = tm.last_day_stats();
        saw_bites_on_humans |= stats.total_bites_on_humans > 0;
        saw_e_v |= stats.vector_e > 0;
        saw_i_v |= stats.vector_i > 0;
        saw_infectious_bites |= stats.infectious_bites > 0;
        saw_e_h |= stats.human_e > 0;
    }

    EXPECT_TRUE(saw_bites_on_humans)
        << "vectors never bit humans: the contact process is broken";
    EXPECT_TRUE(saw_e_v) << "human -> vector leg never produced an E_V";
    EXPECT_TRUE(saw_i_v) << "EIP never completed (no I_V)";
    EXPECT_TRUE(saw_infectious_bites) << "no infectious bite was recorded";
    EXPECT_TRUE(saw_e_h) << "vector -> human leg never produced an E_H";
}

}  // namespace
}  // namespace mal_abm_fast
