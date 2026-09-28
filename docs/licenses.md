# Upstream Data Licenses — Audit & Decision Log

> Single source of truth for *third-party data licensing* in MalariaSentinel.
> Machine-readable side: every loader `DOWNLOADER` dict carries `license`
> (id from `mal_commonlib.data.licenses.KNOWN_LICENSES`) and `attribution`
> (the literal credit line) — stamped into `data/<aoi>/manifest.json` by
> `malariasim download` / ingest and enforced by
> `mal-commonlib/tests/test_licenses.py`. Pipeline stages emit one
> aggregated warning listing the usage limits (see §6).
>
> Project code license: **Apache-2.0** (`LICENSE`, root + package
> `pyproject.toml`s). This page governs the *data*, which inherits the
> upstream terms it derives from.
>
> Last full audit: 2026-09-27 · Owner: David Flórez-Mazuera

## 1. Decision log

| Decision | Date | Choice | Rationale |
|---|---|---|---|
| MERIT DEM dual-license election (CC BY-NC 4.0 vs ODbL 1.0) | 2026-09-27 | **ODbL 1.0** | Project code is Apache-2.0 (commercial-compatible); all MERIT tiles stay gitignored and are never redistributed, so the share-alike only reaches published vs-DEM-derived products |
| Overture Buildings (building_fraction, wildlife remoteness) | 2026-09-27 | **Keep** | Best available building-coverage source for Ghana; ODbL implications accepted: `host_static.nc` + `mobility_*.csr` + `wildlife_host_proxy` are ODbL share-alike *if redistributed* |
| CC BY-NC occurrence datasets (`guf/`, `colombia_vl/`) | 2026-09-27 | **Isolate to mal-data-explorer** | Non-commercial license conflicts with unrestricted redistribution of model outputs; never import into `mal-commonlib` / `mal-core` pipelines (enforced by test) |
| DEM fallback | — | NASADEM automatic | NASA/USGS public domain — removes licensing risk if MERIT upstream ever becomes unusable |

## 2. Pipeline datasets (`data/<aoi>/`)

| Loader | Upstream product | License | Attribution (literal) | Notes |
|---|---|---|---|---|
| `era5.py` | ERA5-Land daily stats + ERA5 single-levels (Copernicus CDS) | Copernicus licence → **CC BY 4.0** (unified 2025-07-02) | "Contains modified Copernicus Climate Change Service information [Year]. Neither the European Commission nor ECMWF is responsible…" | Our 2024–2025 downloads straddle both licence regimes; the attribution wording is the same in practice |
| `chirps.py` | CHIRPS v2.0, UCSB CHC | Free, no formal licence; citation required | Funk, C.C., et al., 2014, USGS Data Series 832, 4 p. | v2 production stops 2026 — migrating to CHIRPS v3.0 keeps the same terms |
| `modis.py` | MODIS MOD13A3 v061 (NASA LP DAAC) | Free (NASA EOSDIS) | Citation: DOI 10.5067/MODIS/MOD13A3.061 | |
| `smap.py` | SMAP RSS L3 SSS V6.0 (PO.DAAC) | Free (NASA EOSDIS) | Citation: DOI 10.5067/SMP60-3SMCS | |
| `jrc_gsw.py` / `hydrorivers.py` | JRC Global Surface Water v1.4 (via Planetary Computer STAC) | CC BY 4.0 (EC reuse, Decision 2011/833/EU) | Pekel, J.-F., et al., 2016, Nature 540, 418–422 + © EU/JRC | ⚠️ PC's own STAC metadata lists the collection as "proprietary" — known inconsistency in the PC catalog TSV; the underlying JRC product is CC BY JRC open data. If legal certainty is ever needed, switch the fetch to the JRC FTP (`jeodpp.jrc.ec.europa.eu/.../GSWE/`) |
| `worldcover.py` (legacy) + `wildlife.py` input | ESA WorldCover 2020/2021 (via Planetary Computer) | **CC BY 4.0** with a **literal line** | "© ESA WorldCover project [2021] / Contains modified Copernicus Sentinel data (2021) processed by ESA WorldCover consortium" | The year in brackets must match the map (2020 or 2021) |
| `worldpop.py` | WorldPop Global 2000–2020 Constrained (GHA 2019) | **CC BY 4.0** + responsible-use disclaimer | WorldPop (www.worldpop.org), Lloyd et al. 2019 | Upstream disclaimer: data not for uses that discriminate/exploit/harm individuals; user assesses combination risks |
| `glw.py` | FAO GLW4 2020 D-DA (5 species) | **CC BY 4.0** (FAO catalog) | GLW4-2020 © FAO | Density layers; no country mask (bbox totals include neighbouring strips — see memory #57) |
| `ghsl.py` | GHS-SMOD E2030 R2023A (EC JRC) | CC BY 4.0 (EC reuse policy) | "Source: © European Union, Joint Research Centre" | |
| `buildings.py` | Overture Maps Buildings (from OSM + Microsoft) | **ODbL 1.0** | "© OpenStreetMap contributors, Overture Maps Foundation" | ODbL = *share-alike of derived databases*; see §4 |
| `dem.py` | MERIT DEM 90 m (Yamazaki Lab) / NASADEM fallback | Dual CC BY-NC 4.0 / ODbL 1.0 → **elected ODbL** | Yamazaki, D., et al., 2017, GRL 44, 5844–5853 | Redistribution of the full raw dataset requires written permission (we never do — tiles gitignored). NASADEM is public domain |
| `coastline.py` | GSHHG shapefiles (Wessel & Smith) | **LGPL v3** (data) + copyright notice | Wessel, P., & Smith, W. H. F. 1996, JGR 101, 8741–8743 | Authors ask to be *notified* if the raw data is modified for commercial use |

## 3. Derived (ingest) products and their license inheritance

| Product | From what | Compound license |
|---|---|---|
| `env` (regional NC) | CHIRPS + JRC GSW + ERA5 + MODIS | `CC-BY-4.0+Copernicus-Cite+CHIRPS-Cite+NASA-Cite` — attribution-only across the board |
| `habitat` (gpkg) | MERIT DEM (TWI) + JRC GSW | `ODbL-1.0+CC-BY-4.0` |
| `host_static` (nc) | WorldPop + GLW4 + GHS-SMOD + Overture buildings + wildlife proxy | `CC-BY-4.0+ODbL-1.0+NASA-Cite` |
| `mobility_*` (csr) | host_static-derived | `CC-BY-4.0+ODbL-1.0+NASA-Cite` |
| `host_manifest` / `mobility_manifest` (json) | metadata of the above | inherit parent |

## 4. The one hot spot: the MalariaSentinel ODbL surface

Overture buildings is **ODbL** (a Derivative Database of OSM + Microsoft footprints).
Everything that ingests `building_fraction` inherits ODbL for *derived-database* purposes:

- `building_fraction` term in `host_static.nc`
- `wildlife_host_proxy`'s remoteness term
- the urban-persistent patch union (M7.4.1) computed from `urban_class==30 + building_fraction`
- the mobility CSR graphs built on host_static

**Redistribution rule**: if any of those files is ever published/shared, it must be
under ODbL 1.0 with the OSM attribution line. Internal use, publication of
papers, and code distribution are unaffected. Raw tiles stay gitignored.

## 5. Reference (occurrence) datasets — `data/`

GBIF-mediated occurrence archives; licenses verified against each IPT `eml.xml`:

| Dataset | Records | License | Restriction |
|---|---|---|---|
| `ghana_idit/` | 1,008 | **CC0 1.0** | none (cite the dataset) |
| `react/` (IRD) | 60,705 | **CC BY 4.0** | attribution |
| `guf/` (Institut Pasteur) | 3,917 | **CC BY-NC 4.0** | **non-commercial only** — explorer-only |
| `colombia_vl/` (PMI VectorLink) | 1,502 | **CC BY-NC 4.0** | **non-commercial only** — explorer-only |

Plus `data/moua_2016.pdf` (Moua et al. 2016, open access via HAL) — reference copy.
`terrain/` SRTM tiles are delivered via the **OpenTopography** API (a
not-for-profit research service); the underlying SRTM is NASA public domain but the
OpenTopography portal service terms should be honoured when re-deriving tiles.

## 6. Warnings in the pipeline

Stages that register/read manifests call
`mal_commonlib.data.licenses.warn_manifest_limits(aoi)` (download runner,
`ingest/env.py`, `ingest/hosts.py`) and emit a **single aggregated**
UserWarning listing every limit that applies, e.g.:

```
UserWarning: Upstream dataset licenses limit some uses:
  - LGPL v3 (data): notify Wessel/Smith...
  - Literal 'Contains modified Copernicus Climate Change Service...'
  - ODbL share-alike: any DERIVED DATABASE (host_static.nc, ...) requires ODbL ...
```

Adding a new loader: set `license` + `attribution` in the `DOWNLOADER` dict
(and, if a new license id is needed, extend `KNOWN_LICENSES` there plus the
table in §2). `test_licenses.py` enforces both.

## 7. Known gaps / future work

- Verify live via Planetary Computer's STAC `/collections/jrc-gsw` what
  license field it currently serves, and consider switching to the JRC FTP
  mirror to avoid the "proprietary" PC listing ambiguity.
- CHIRPS v2 → v3.0 migration before 2026 cutoff (same terms, wider extent).
