# M7.6 Wind Dispersal — Implementation Plan

## Status

Phase 1 COMPLETE (commit 75cc9ad). Phases 2-3 TBD.

## Phase 1 (DONE): ERA5 Monthly Mean Wind — Simple Advection

What was done:
- WindField C++ class: loads 24-band GeoTIFF (u100/v100 monthly mean ERA5 0.25° at 100m)
- Integration in mosquito_submodel.cpp: GRAVID/OVIPOSITION_SEEKING females migrate during season
- Constants: WIND_MIGRATION_PROB=0.05, WIND_FLIGHT_HOURS=4, WIND_SURVIVAL=0.85, WIND_FLIGHT_SPEED_MS=1.0
- CLI flag: --wind-field (GeoTIFF path)
- Data: ERA5 CDS API, Ghana AOI 2024, 12 monthly means. Total disk ~1.6 MB.
- Displacements: 62-82 km/night (Jul-Sep monsoon), 23-40 km (Dec-Feb Harmattan)
- Consistent with Huestis et al. 2019 (Nature Comms): 30km (2h) / 120km (9h) mean nightly displacement
- 185/185 ctest pass

Known limitation: population dynamics (adult mortality vs larval development gap) causes point-source collapse before migration has observable effect. Separate issue from wind feature itself.

## Phase 2 (~2 sessions): Hourly ERA5 Wind + Night-time-only Migration

Objective: Replace monthly mean with hourly wind data for realistic nightly variation.

Data: ERA5 hourly u100/v100 for Jul-Oct + Dec-Mar (migration season months only). ~50 GB total but can be lazy-loaded per month.
Alternative: Use 6-hourly (00/06/12/18) instead of hourly → ~12 GB, sufficient granularity.

Implementation:
1. New loader: WindField::load_from_nc() — reads time-resolved NetCDF
2. Night window (18:00-06:00): interpolate wind at current hour, advect per hour
3. Mosquito picks random start hour (18-21), flies 4-9 hours (uniform draw)
4. Gradient: wind varies across space too (already handled by nearest-neighbor grid)
5. Add D16 scorer: "spatial spread" — number of cells occupied at >1 adult beyond initial seed set, measured at day 180

Validation: compare trajectory distances against Huestis 2019 Table 2 (mean 30km/2h, 120km/9h) to verify the hourly model produces the right distribution.

Data download: ERA5 CDS API, same area [11.5, -3.5, 4.5, 1.5], 4 time slots per day. Script in `mal-core/src/mal_core/abm/scripts/download_era5_hourly.py`.

## Phase 3 (~4 sessions, optional): Species-specific Migration + Multi-receptor

Objective: Different Anopheles species have different migration behaviors.

Literature:
- An. coluzzii: most common migrant (6M/year crossing 100km line in Sahel)
- An. gambiae s.s.: rare migrant (~81k/year), recolonizes Sahel each wet season
- An. funestus: perennial, less migratory, prefers permanent water

Implementation (requires M7.3 multi-species):
1. Per-species WIND_MIGRATION_PROB, WIND_FLIGHT_HOURS (in SpeciesParams struct)
2. Seasonal schedule per species (gambiae only Jul-Aug, coluzzii Jul-Nov)
3. Reproductive status filter: only blood-fed (post-first-cycle) females migrate
4. Destination habitat selection: migrants that land in non-viable cells (dry, no water) die

## Unresolved: Point-Source Population Collapse

Separate from M7.6. Current parameters:
- ADULT_DAILY_MORT_BASAL=0.93 → mean adult life ~14 days at 27.5°C
- LARVA_A=0.001 → larval development 17.8 days at 25°C
- Gap: adults die before first generation matures

Options (requires user decision):
A. Density-dependent adult mortality (Allee effect): lower mortality when pop < threshold
B. Increase BIRTH_FECUNDITY (0.25→0.50): more eggs per cycle
C. Reduce first_cycle_days (4.0→2.0): faster first oviposition
D. Accept that point-sources need multi-point seeding (10+ points minimum)

## Key Files

| File | Role |
|---|---|
| `mal-core/.../include/mal_abm_fast/wind_field.hpp` | WindField class declaration |
| `mal-core/.../src/wind_field.cpp` | GDAL-based GeoTIFF reader |
| `mal-core/.../include/mal_abm_fast/wire.hpp` | WIND_* constants |
| `mal-core/.../src/mosquito_submodel.cpp` | Migration logic in adult_dispersal() |
| `mal-core/.../src/engine.cpp` | WindField loading + month setting |
| `mal-core/.../src/main.cpp` | --wind-field CLI flag |
| `data/ghana/wind_era5_monthly_mean_2024.tif` | 24-band ERA5 GeoTIFF |
| `data/ghana/wind_era5_monthly_mean_2024.nc` | NetCDF source |
| `papers/anopheles-dynamics/` | References: Huestis 2019, Faiman 2020, North & Godfray 2018, Hammond 2022 |

## References

1. Huestis DL et al. (2019). Windborne long-distance migration of malaria mosquitoes in the Sahel. Nature Communications.
2. Faiman R et al. (2020). The effects of high-altitude windborne migration on survival, oviposition, and blood-feeding of An. gambiae s.l. J Med Entomol.
3. North A, Godfray HCJ (2018). Modelling the persistence of mosquito vectors of malaria in Burkina Faso. Malaria Journal.
4. Hammond AM et al. (2022). Spatial modelling for population replacement of mosquito vectors at continental scale. PLOS Comp Biol.
