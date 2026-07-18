"""build_2year_nc: Generate a 2-year daily NetCDF from 24 monthly COGs.

Reads monthly COG files from data/runs/ghana/m2/ and creates a single
daily NetCDF-4 file suitable for the mal_abm_fast engine.

Usage:
    uv run python scripts/build_2year_nc.py
"""
from __future__ import annotations

import calendar
import pathlib

import numpy as np
import rasterio
import xarray as xr

# Configuration
DATA_DIR = pathlib.Path("data/runs/ghana/m2")
OUTPUT_DIR = pathlib.Path("data/ghana")
OUTPUT_FILE = OUTPUT_DIR / "ghana_regional_2024_2025_env.nc"

# Band names (must match the COG order)
BAND_NAMES = ["water_frac", "rainfall", "temp_suitability", "ndvi"]

# Time range: 2024-01 to 2025-12 (24 months)
START_YEAR = 2024
START_MONTH = 1
N_MONTHS = 24

# NoData sentinel
NODATA_SENTINEL = -9999.0


def read_monthly_cog(path: pathlib.Path) -> tuple[np.ndarray, dict]:
    """Read a monthly COG and return (bands, metadata)."""
    with rasterio.open(path) as src:
        data = src.read()  # (4, H, W)
        meta = {
            "crs": src.crs,
            "transform": src.transform,
            "height": src.height,
            "width": src.width,
        }
    return data, meta


def build_monthly_arrays(year: int, month: int) -> tuple[np.ndarray, int]:
    """Read a single month's COG and return (daily_data, n_days).
    
    daily_data shape: (n_days, 4, H, W) - repeats monthly values for each day.
    """
    cog_path = DATA_DIR / f"ghana_regional_{year}_{month:02d}_env.tif"
    if not cog_path.exists():
        raise FileNotFoundError(f"COG not found: {cog_path}")
    
    data, meta = read_monthly_cog(cog_path)
    n_days = calendar.monthrange(year, month)[1]
    
    # Broadcast monthly data to daily: (4, H, W) -> (n_days, 4, H, W)
    daily_data = np.broadcast_to(data, (n_days, *data.shape)).copy()
    
    return daily_data, n_days, meta


def main():
    """Generate 2-year daily NetCDF from monthly COGs.
    
    COG band order: water_frac=0, rainfall=1, temp_suitability=2, ndvi=3
    NC output vars: water_frac, rainfall, water_temp_c (°C), ndvi
    """
    print(f"Generating 2-year daily NetCDF: {START_YEAR}-{START_MONTH:02d} to "
          f"{START_YEAR + (START_MONTH + N_MONTHS - 2) // 12}_"
          f"{((START_MONTH - 1 + N_MONTHS - 1) % 12) + 1:02d}")
    print(f"Output: {OUTPUT_FILE}")
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # COG band order: water_frac=0, rainfall=1, temp_suitability=2, ndvi=3
    COG_WATER_FRAC = 0
    COG_RAINFALL = 1
    COG_TEMP_SUIT = 2
    COG_NDVI = 3
    
    # Collect all months
    all_wf, all_rain, all_temp, all_ndvi = [], [], [], []
    all_times = []
    h, w = None, None
    meta = None
    
    for i in range(N_MONTHS):
        month_offset = START_MONTH - 1 + i
        year = START_YEAR + month_offset // 12
        month = (month_offset % 12) + 1
        
        cog_path = DATA_DIR / f"ghana_regional_{year}_{month:02d}_env.tif"
        if not cog_path.exists():
            raise FileNotFoundError(f"COG not found: {cog_path}")
        
        print(f"  Reading {year}-{month:02d}...", end=" ")
        with rasterio.open(cog_path) as src:
            data = src.read().astype(np.float32)  # (4, H, W)
            meta = {
                "crs": src.crs, "transform": src.transform,
                "height": src.height, "width": src.width,
            }
        
        # Replace nodata sentinel with NaN
        for b in range(data.shape[0]):
            data[b][data[b] == NODATA_SENTINEL] = np.nan
        
        n_days = calendar.monthrange(year, month)[1]
        
        # Expand monthly → daily: (4, H, W) → (n_days, 4, H, W)
        wf_daily = np.broadcast_to(data[COG_WATER_FRAC], (n_days, *data[COG_WATER_FRAC].shape)).copy()
        rain_daily = np.broadcast_to(data[COG_RAINFALL], (n_days, *data[COG_RAINFALL].shape)).copy()
        temp_daily = np.broadcast_to(data[COG_TEMP_SUIT], (n_days, *data[COG_TEMP_SUIT].shape)).copy()
        ndvi_daily = np.broadcast_to(data[COG_NDVI], (n_days, *data[COG_NDVI].shape)).copy()
        
        all_wf.append(wf_daily)
        all_rain.append(rain_daily)
        all_temp.append(temp_daily)
        all_ndvi.append(ndvi_daily)
        
        for day in range(1, n_days + 1):
            all_times.append(np.datetime64(f"{year:04d}-{month:02d}-{day:02d}"))
        
        if h is None:
            h, w = meta["height"], meta["width"]
        
        # Stats (ignoring NaN)
        with np.errstate(invalid="ignore"):
            print(f"({n_days} days, rain=[{np.nanmin(data[COG_RAINFALL]):.1f}-{np.nanmax(data[COG_RAINFALL]):.1f}], "
                  f"wf=[{np.nanmin(data[COG_WATER_FRAC]):.2f}-{np.nanmax(data[COG_WATER_FRAC]):.2f}])")
    
    # Concatenate
    water_frac = np.concatenate(all_wf, axis=0)
    rainfall = np.concatenate(all_rain, axis=0)
    temp_suit = np.concatenate(all_temp, axis=0)
    ndvi = np.concatenate(all_ndvi, axis=0)
    
    # Mordecai inverse: T = 25 - 8 * sqrt(1 - s)
    temp_clipped = np.clip(temp_suit, 0.0, 1.0)
    water_temp_c = (25.0 - 8.0 * np.sqrt(1.0 - temp_clipped)).astype(np.float32)
    
    total_days = len(all_times)
    with np.errstate(invalid="ignore"):
        print(f"\nTotal: {total_days} days, grid={h}x{w}")
        print(f"  water_frac:   NaN%={np.isnan(water_frac).mean()*100:.1f}%, range=[{np.nanmin(water_frac):.2f}, {np.nanmax(water_frac):.2f}]")
        print(f"  rainfall:     NaN%={np.isnan(rainfall).mean()*100:.1f}%, range=[{np.nanmin(rainfall):.2f}, {np.nanmax(rainfall):.2f}]")
        print(f"  water_temp_c: NaN%={np.isnan(water_temp_c).mean()*100:.1f}%, range=[{np.nanmin(water_temp_c):.2f}, {np.nanmax(water_temp_c):.2f}]")
        print(f"  ndvi:         NaN%={np.isnan(ndvi).mean()*100:.1f}%, range=[{np.nanmin(ndvi):.2f}, {np.nanmax(ndvi):.2f}]")
    
    # Build y/x coords from GeoTransform
    gt = meta["transform"]
    y_coords = np.linspace(gt[5], gt[5] + gt[4] * h, h)  # top to bottom
    x_coords = np.linspace(gt[2], gt[2] + gt[0] * w, w)  # left to right
    
    # Create xarray Dataset
    ds = xr.Dataset(
        {
            "water_frac": (["time", "y", "x"], water_frac,
                           {"long_name": "JRC GSW open water fraction",
                            "units": "1"}),
            "rainfall": (["time", "y", "x"], rainfall,
                         {"long_name": "CHIRPS v2.0 daily precipitation",
                          "units": "mm/day"}),
            "water_temp_c": (["time", "y", "x"], water_temp_c,
                             {"long_name": "ERA5-Land 2m temperature (daily mean)",
                              "units": "degC"}),
            "ndvi": (["time", "y", "x"], ndvi,
                     {"long_name": "MODIS NDVI",
                      "units": "1"}),
        },
        coords={
            "time": all_times,
            "y": y_coords,
            "x": x_coords,
        },
        attrs={
            "Conventions": "CF-1.8",
            "title": "MalariaSentinel daily env tensor — ghana 2024-2025",
            "aoi_slug": "ghana",
            "scale": "regional",
            "contract_version": "2.0",
            "generator_version": "m2-daily-0.2.0",
            "crs": str(meta["crs"]),
        },
    )
    
    # CF axis attributes for y/x
    ds["y"].attrs.update({
        "axis": "Y", "long_name": "latitude",
        "standard_name": "latitude", "units": "degrees_north",
    })
    ds["x"].attrs.update({
        "axis": "X", "long_name": "longitude",
        "standard_name": "longitude", "units": "degrees_east",
    })
    ds["time"].attrs.update({
        "axis": "T", "long_name": "time", "standard_name": "time",
    })
    
    # Write with compression
    encoding = {v: {"dtype": "float32", "zlib": True, "complevel": 4}
                for v in ["water_frac", "rainfall", "water_temp_c", "ndvi"]}
    
    print(f"\nWriting NetCDF to {OUTPUT_FILE}...")
    ds.to_netcdf(OUTPUT_FILE, encoding=encoding)
    
    file_size_mb = OUTPUT_FILE.stat().st_size / (1024 * 1024)
    print(f"Done: {OUTPUT_FILE} ({file_size_mb:.1f} MB)")
    print(f"  Variables: water_frac, rainfall, water_temp_c, ndvi")
    print(f"  Shape: ({total_days}, {h}, {w})")
    print(f"  Time range: {all_times[0]} → {all_times[-1]}")


if __name__ == "__main__":
    main()
