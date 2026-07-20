---
name: data-explorer
description: Explore and visualize malaria vector datasets. Covers Ghana, Colombia, REACT, and French Guiana datasets with mapping, comparison, and bias analysis scripts. Use when exploring datasets, creating maps, or analyzing data quality.
---

## Overview

`mal-data-explorer/` contains standalone visualization and analysis scripts for malaria vector datasets. All scripts are independent — they read from `../data/` and write figures to `../data/maps/`. No inter-dependencies between scripts.

### Datasets

| ID | Location | Records | Source | License |
|----|----------|---------|--------|---------|
| `ghana_idit` | Ghana (multi-ecozona) | 1,008 larvae | Univ. Ghana Medical School | CC0 1.0 |
| `colombia_vl` | Pacífico colombiano | 229,394 mosquitoes | PMI VectorLink | CC BY-NC 4.0 |
| `react` | Burkina Faso + Côte d'Ivoire | 60,705 mosquitoes | IRD (IRD) | CC BY 4.0 |
| `guf` | French Guiana + Amapá, Brazil | 3,917 specimens | Institut Pasteur Guyane | CC BY-NC 4.0 |

### Dependencies

```
pandas>=2.0, matplotlib>=3.8, geopandas>=1.0, shapely>=2.0,
cartopy>=0.24, contextily>=1.6, scipy>=1.17.1
```

## Available Scripts

| # | Script | Purpose |
|---|--------|---------|
| 01 | `01_dataset_metadata.py` | Metadata audit of the GUF Anopheles GBIF dataset (basisOfRecord, samplingProtocol, institutionCode, etc.) |
| 02 | `02_map_anopheles_guf.py` | Map French Guiana + Amapá Anopheles occurrences by species |
| 03 | `03_map_ghana.py` | Map Ghana IDIT larval sites with top-10 localities and year distribution |
| 04 | `04_map_colombia.py` | Map Colombia VectorLink (PMI) sites by dominant species |
| 05 | `05_map_react.py` | Map REACT Burkina Faso + Côte d'Ivoire biting rates, indoor/outdoor distribution, monthly captures |
| 06 | `06_compare_three_maps.py` | Side-by-side map comparison of REACT, Ghana, and Colombia datasets |
| 07 | `07_compare_datasets.py` | Quantitative comparison of 6 datasets with quality scoring table |
| 08 | `08_explore_react.py` | Deep dive into REACT data structure (events, occurrences, measurements, molecular data) |
| 09 | `09_two_focus_analysis.py` | Statistical analysis of REACT's two-focus geographic pattern |
| 10 | `10_two_focus_plot.py` | Regional and zoomed visualization of the two REACT focus areas |
| 11 | `11_bias_analysis.py` | Quantitative bias analysis of GUF dataset (temporal, geographic, institutional, species) |
| 12 | `12_bias_plot.py` | Bias visualization: records by year, distance to Cayenne, institution × decade, species × decade |

## Running Scripts

All scripts must be run from `mal-data-explorer/`:

```bash
cd mal-data-explorer

# Dataset metadata
uv run python 01_dataset_metadata.py

# Individual maps
uv run python 02_map_anopheles_guf.py
uv run python 03_map_ghana.py
uv run python 04_map_colombia.py
uv run python 05_map_react.py

# Comparisons
uv run python 06_compare_three_maps.py
uv run python 07_compare_datasets.py

# REACT deep dive
uv run python 08_explore_react.py
uv run python 09_two_focus_analysis.py
uv run python 10_two_focus_plot.py

# Bias analysis
uv run python 11_bias_analysis.py
uv run python 12_bias_plot.py
```

## Dataset Details

### ghana_idit — Ghana IDIT

- **Source**: Univ. Ghana Medical School (anopheles_phenotypic, cloud.gbif.org)
- **Records**: 1,008 larvae across 20-24 localities
- **Years**: 2023–2025
- **Key columns**: `scientificName`, `locality`, `decimalLatitude`, `decimalLongitude`, `year`, `basisOfRecord`
- **Method**: Larval sampling
- **Identification**: kdr genotyping
- **Coverage**: Multi-ecological zone Ghana (Savana Sudanian, humid forest, coastal forest)
- **Known issues**: Clean dataset, few missing fields

### colombia_vl — Colombia VectorLink (PMI)

- **Source**: PMI VectorLink via ipt.biodiversidad.co/sib
- **Records**: 229,394 mosquitoes across 25 localities
- **Years**: 2021–2023
- **Key columns**: `scientificName`, `locality`, `municipality`, `individualCount`, `eventDate`, `samplingProtocol`
- **Municipalities**: Timbiquí, Guapi, Santa Bárbara
- **Method**: HLC indoor + outdoor
- **Species**: *Anopheles neivai* (dominant), *An. albimanus*, *An. apicimacula*
- **Known issues**: Requires `eventDate` parsing with `utc=True`

### react — REACT (IRD)

- **Source**: IRD via ipt.gbif.fr (anopheles_collections_react_project)
- **Records**: 60,705 mosquitoes across 421 villages (59 unique)
- **Years**: 2016–2018
- **Files**: `event.txt`, `occurrence.txt`, `measurementorfacts.txt`, `extendedmeasurementorfact.txt`
- **Key columns**: `eventID`, `locationID`, `locality`, `country`, `decimalLatitude`, `decimalLongitude`, `scientificName`, `individualCount`
- **Method**: HLC indoor + outdoor
- **Molecular data**: PCR for *Plasmodium falciparum* infection, kdr mutation, ace-1 mutation, parity
- **Coverage**: Diébougou area (Burkina Faso) + Korhogo area (Côte d'Ivoire), ~300 km apart
- **Known issues**: Multi-file format; `locationID` parsed with regex `^(\d+[A-Z]+)` for village grouping

### guf — Institut Pasteur Guyane (French Guiana)

- **Source**: Institut Pasteur de la Guyane via ipt.gbif.fr
- **Records**: 3,917 specimens
- **Years**: 1902–2014 (113 years of data)
- **Key columns**: `scientificName`, `decimalLatitude`, `decimalLongitude`, `year`, `basisOfRecord`, `institutionCode`, `samplingProtocol`, `lifeStage`
- **Method**: Mixed (HLC, light traps, larval collection, mosquito magnet)
- **Known issues**:
  - Many columns are 100% NaN: `sex`, `month`, `day`, `habitat`, `eventRemarks`, `waterBody`, `country`, `coordinatePrecision`, `typeStatus`
  - Pre-2000 records have approximate coordinates (town-level)
  - Post-2000 records have precise GPS coordinates
  - Species bias: *A. darlingi* (primary vector) dominates collections

## Output

Scripts generate PNG figures in `data/maps/`. Pre-existing outputs:

| File | Script | Description |
|------|--------|-------------|
| `ghana_idit_map.png` | 03 | Ghana larval sites map |
| `colombia_vl_map.png` | 04 | Colombia VectorLink map |
| `react_map.png` | 05 | REACT biting rate map |
| `tres_mapas.png` | 06 | Three-dataset comparison |
| `datasets_comparacion.png` | 07 | Six-dataset quantitative comparison |
| `dos_focos.png` | 10 | Two-focus pattern visualization |
| `sesgos_anopheles.png` | 12 | GUF bias analysis plots |
| `guf/mapa_anopheles.png` | 02 | French Guiana species map |

View outputs:

```bash
open data/maps/ghana_idit_map.png
open data/maps/react_map.png
```

## Key Functions and Patterns

All scripts follow the same pattern:

1. **Load data** with `pd.read_csv(path, sep="\t", low_memory=False)`
2. **Filter** coordinates: `df[(df["decimalLatitude"].between(-90, 90)) & (df["decimalLongitude"].between(-180, 180))]`
3. **Aggregate** by village/locality using `groupby().agg()`
4. **Plot** with cartopy projections (`ccrs.PlateCarree()`) and `cfeature` (LAND, OCEAN, COASTLINE, BORDERS, RIVERS)
5. **Save** with `plt.savefig("../data/maps/<name>.png", dpi=150, bbox_inches="tight", facecolor="white")`

### Common cartopy setup

```python
import cartopy.crs as ccrs
import cartopy.feature as cfeature

ax = plt.axes(projection=ccrs.PlateCarree())
ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())
ax.add_feature(cfeature.LAND, facecolor="#f0ece2")
ax.add_feature(cfeature.OCEAN, facecolor="#a8c8e0")
ax.add_feature(cfeature.COASTLINE, linewidth=0.6, color="#333")
ax.add_feature(cfeature.BORDERS, linewidth=0.7, color="#555", linestyle=":")
ax.add_feature(cfeature.RIVERS, linewidth=0.3, color="#3a78a8")
```

### REACT data loading (multi-file)

```python
REACT = "../data/react"
events = pd.read_csv(f"{REACT}/event.txt", sep="\t", low_memory=False)
occ = pd.read_csv(f"{REACT}/occurrence.txt", sep="\t", low_memory=False)
emof = pd.read_csv(f"{REACT}/extendedmeasurementorfact.txt", sep="\t", low_memory=False)
mof = pd.read_csv(f"{REACT}/measurementorfacts.txt", sep="\t", low_memory=False)

# Group events by village
events["village_id"] = events["locationID"].str.extract(r"^(\d+[A-Z]+)")
mosq_per_event = occ.groupby("eventID").size().rename("n_mosq")
events = events.merge(mosq_per_event, on="eventID", how="left")
```

### Distance calculation

```python
import numpy as np
cayenne_lat, cayenne_lon = 4.937, -52.326
df["dist_cayenne_km"] = np.sqrt(
    ((df["decimalLatitude"] - cayenne_lat) * 111) ** 2
    + ((df["decimalLongitude"] - cayenne_lon) * 111 * np.cos(np.radians(cayenne_lat))) ** 2
)
```

## Customization

### Changing extent / bounding box

Modify the `ax.set_extent()` call. Common regions:

```python
# Ghana
ax.set_extent([-3.5, 1.0, 4.5, 11.5])

# REACT (Burkina Faso + Côte d'Ivoire)
ax.set_extent([-6.5, -2.8, 8.5, 11.5])

# Colombia Pacific
ax.set_extent([-78.2, -77.4, 2.3, 3.0])

# French Guiana (auto from data)
lat_min, lat_max = df["decimalLatitude"].min() - 0.5, df["decimalLatitude"].max() + 0.5
lon_min, lon_max = df["decimalLongitude"].min() - 0.5, df["decimalLongitude"].max() + 0.5
```

### Adding new datasets

Copy any existing script, update the path constant and aggregation logic:

```python
NEW_DATASET = "../data/new_dataset"
df = pd.read_csv(f"{NEW_DATASET}/occurrence.txt", sep="\t", low_memory=False)
```

### Modifying color schemes

Scripts use these palettes:

- **YlOrRd**: biting rate / intensity (REACT)
- **YlGnBu**: larval counts (Ghana)
- **tab10**: species color-coding (GUF)
- **Named dict**: species-specific colors (Colombia)

## Troubleshooting

### Missing data files

Scripts read from `../data/`. If you get `FileNotFoundError`, restore the data:

```bash
uv run --with requests --with rasterio --with matplotlib --with numpy \
    python scripts/restore_data.py
```

Or restore a single dataset: `uv run python scripts/restore_data.py react`

### Import errors (cartopy, geopandas)

Ensure dependencies are installed:

```bash
uv sync --all-packages
```

Cartopy requires system libraries on macOS:

```bash
brew install proj geos
```

### Empty plots or NaN warnings

GUF dataset has many NaN columns (sex, month, day, habitat, etc.) — this is upstream, not a bug. Scripts are defensive against empty fields.

### REACT multi-file merge issues

REACT uses 4 separate TSV files. If `eventID` or `occurrenceID` merge fails, check for trailing whitespace or encoding issues:

```python
events = pd.read_csv(f"{REACT}/event.txt", sep="\t", low_memory=False)
events["eventID"] = events["eventID"].str.strip()
```

### matplotlib grid warnings

Scripts set `matplotlib.rcParams["axes.grid"] = False` to suppress grid artifacts on cartopy projections.
