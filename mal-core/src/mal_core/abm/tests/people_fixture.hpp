// SPDX-License-Identifier: MIT
// people_fixture.hpp — test helper: the mosquito submodel has no host-search
// path other than the perception cascade, which needs individual people. This
// attaches a few people next to every adult so a unit test of the gonotrophic
// cycle or the lifecycle still sees blood meals.
#pragma once

#include <cmath>
#include <map>
#include <memory>
#include <utility>
#include <vector>

#include "mal_abm_fast/aoi.hpp"
#include "mal_abm_fast/host_cascade.hpp"
#include "mal_abm_fast/human_state.hpp"
#include "mal_abm_fast/mosquito_submodel.hpp"

namespace mal_abm_fast::testing {

/// People are placed within 5 m of every distinct (10 m rounded) adult site.
/// The returned grid must outlive `sub`.
inline std::unique_ptr<HumanCompartmentGrid> attach_people_near_adults(
    MosquitoSubmodel& sub, const AOI& aoi, int per_site = 20)
{
    const int32_t W = aoi.cells_per_side();
    const int32_t H = cells_per_side_h(aoi);
    const double wm = static_cast<double>(W) * aoi.resolution_m;
    const double hm = static_cast<double>(H) * aoi.resolution_m;
    std::map<std::pair<long, long>, std::pair<double, double>> sites;
    const MosquitoSoA& soa = sub.soa();
    for (int64_t i = 0; i < soa.n_alive; ++i) {
        const size_t si = static_cast<size_t>(i);
        if (soa.stage[si] != 1) continue;
        const XY xy = lonlat_to_xy(aoi, soa.lon[si], soa.lat[si]);
        const double x = std::min(std::max(xy.x, 10.0), wm - 10.0);
        const double y = std::min(std::max(xy.y, 10.0), hm - 10.0);
        sites[{std::lround(x / 10.0), std::lround(y / 10.0)}] = {x, y};
    }
    auto grid = std::make_unique<HumanCompartmentGrid>();
    grid->init(H, W, std::vector<float>(static_cast<size_t>(H) * W, 0.0f), 12, 20, 180,
               false, 0.0, static_cast<double>(aoi.resolution_m), 1);
    std::vector<HumanSeed> people;
    for (const auto& [key, xy] : sites) {
        for (int k = 0; k < per_site; ++k) {
            HumanSeed p;
            p.x = xy.first + 5.0 * std::cos(k);
            p.y = xy.second + 5.0 * std::sin(k);
            people.push_back(p);
        }
    }
    grid->set_individuals(people);
    grid->build_spatial_index(25.0);
    sub.set_human_compartment_grid(grid.get());
    sub.set_cascade(CascadeParams::for_species(MosquitoSpeciesId::ANOPHELES_COLUZZII), 123);
    return grid;
}

}  // namespace mal_abm_fast::testing
