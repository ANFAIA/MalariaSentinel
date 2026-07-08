# mal-data-explorer

Anopheles dataset visualization, mapping, and bias analysis scripts.

## Scripts

| # | Script | Description |
|---|--------|-------------|
| 01 | `01_dataset_metadata.py` | Metadata audit of Anopheles GBIF dataset (GUF) |
| 02 | `02_map_anopheles_guf.py` | Map of Anopheles occurrences in French Guiana + Amapá |
| 03 | `03_map_ghana.py` | Map of Ghana IDIT larval sites |
| 04 | `04_map_colombia.py` | Map of Colombia VectorLink (PMI) sites |
| 05 | `05_map_react.py` | Map of REACT (IRD) Burkina Faso + Côte d'Ivoire |
| 06 | `06_compare_three_maps.py` | Side-by-side map comparison of 3 datasets |
| 07 | `07_compare_datasets.py` | Quantitative comparison of 6 datasets |
| 08 | `08_explore_react.py` | REACT dataset structure exploration |
| 09 | `09_two_focus_analysis.py` | Two-foci pattern analysis of REACT |
| 10 | `10_two_focus_plot.py` | Visualization of REACT two-foci pattern |
| 11 | `11_bias_analysis.py` | Quantitative bias analysis of GUF Anopheles dataset |
| 12 | `12_bias_plot.py` | Bias analysis visualizations |

## Usage

```bash
cd mal-data-explorer
uv run python 03_map_ghana.py
uv run python 12_bias_plot.py
```

Scripts read from `../data/` and write figures to `../data/maps/`.