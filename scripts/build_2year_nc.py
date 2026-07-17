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
OUTPUT_DIR = pathlib.Path("data/runs/ghana/two_year")
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
    """Generate 2-year daily NetCDF from monthly COGs."""
    print(f"Generating 2-year daily NetCDF: {START_YEAR}-{START_MONTH:02d} to "
          f"{START_YEAR + (START_MONTH + N_MONTHS - 2) // 12}_"
          f"{((START_MONTH - 1 + N_MONTHS - 1) % 12) + 1:02d}")
    print(f"Output: {OUTPUT_FILE}")
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Collect all monthly data
    all_daily_data = []
    all_times = []
    h, w = None, None
    meta = None
    
    for i in range(N_MONTHS):
        month_offset = START_MONTH - 1 + i
        year = START_YEAR + month_offset // 12
        month = (month_offset % 12) + 1
        
        print(f"  Reading {year}-{month:02d}...", end=" ")
        daily_data, n_days, meta = build_monthly_arrays(year, month)
        all_daily_data.append(daily_data)
        
        # Generate time coordinates
        for day in range(1, n_days + 1):
            all_times.append(np.datetime64(f"{year:04d}-{month:02d}-{day:02d}"))
        
        if h is None:
            h, w = daily_data.shape[2], daily_data.shape[3]
        
        print(f"({n_days} days, shape={daily_data.shape[1:]})")
    
    # Concatenate all months: (total_days, 4, H, W)
    rainfall = np.concatenate([d[:, 0, :, :] for d in all_daily_data], axis=0)
    temp_suit = np.concatenate([d[:, 1, :, :] for d in all_daily_data], axis=0)
    water_frac = np.concatenate([d[:, 2, :, :] for d in all_daily_data], axis=0)
    ndvi = np.concatenate([d[:, 3, :, :] for d in all_daily_data], axis=0)
    
    total_days = len(all_times)
    print(f"\nTotal: {total_days} days, grid={h}x{w}")
    print(f"  rainfall:     shape={rainfall.shape}, range=[{rainfall.min():.2f}, {rainfall.max():.2f}]")
    print(f"  temp_suit:    shape={temp_suit.shape}, range=[{temp_suit.min():.2f}, {temp_suit.max():.2f}]")
    print(f"  water_frac:   shape={water_frac.shape}, range=[{water_frac.min():.2f}, {water_frac.max():.2f}]")
    print(f"  ndvi:         shape={ndvi.shape}, range=[{ndvi.min():.2f}, {ndvi.max():.2f}]")
    
    # Convert temp_suitability to temperature (deg C)
    # The Mordecai inverse: T = 25 - 8 * sqrt(1 - s)
    # where s is temp_suitability in [0, 1]
    temp_suit_clipped = np.clip(temp_suit, 0.0, 1.0)
    water_temp_c = 25.0 - 8.0 * np.sqrt(1.0 - temp_suit_clipped)
    water_temp_c = water_temp_c.astype(np.float32)
    
    print(f"  water_temp_c: shape={water_temp_c.shape}, range=[{water_temp_c.min():.2f}, {water_temp_c.max():.2f}]")
    
    # Create xarray Dataset
    ds = xr.Dataset(
        {
            "rainfall": (["time", "y", "x"], rainfall,
                         {"long_name": "CHIRPS v2.0 daily precipitation",
                          "units": "mm/day", "_FillValue": np.float32(NODATA_SENTINEL)}),
            "water_temp_c": (["time", "y", "x"], water_temp_c,
                             {"long_name": "ERA5-Land 2m temperature (daily mean)",
                              "units": "degC", "_FillValue": np.float32(NODATA_SENTINEL)}),
            "water_frac": (["time", "y", "x"], water_frac,
                           {"long_name": "JRC GSW open water fraction",
                            "units": "1", "_FillValue": np.float32(NODATA_SENTINEL)}),
            "ndvi": (["time", "y", "x"], ndvi,
                     {"long_name": "MODIS NDVI",
                      "units": "1", "_FillValue": np.float32(NODATA_SENTINEL)}),
        },
        coords={
            "time": all_times,
            "y": np.linspace(meta["transform"][5], meta["transform"][5] + meta["transform"][4] * h, h),
            "x": np.linspace(meta["transform"][2], meta["transform"][2] + meta["transform"][0] * w, w),
        },
        attrs={
            "Conventions": "CF-1.8",
            "title": "MalariaSentinel daily env tensor — ghana 2024-2025",
            "aoi_slug": "ghana",
            "scale": "regional",
            "contract_version": "2.0",
            "generator_version": "m2-daily-0.1.0",
            "crs": str(meta["crs"]),
            "source_url": "https://github.com/davidflorezmazuera/MalariaSentinel",
        },
    )
    
    # CF grid mapping
    ds["latitude"] = xr.DataArray(
        np.linspace(meta["transform"][5], meta["transform"][5] + meta["transform"][4] * h, h),
        dims="y",
        attrs={"units": "degrees_north", "axis": "Y"}
    )
    ds["longitude"] = xr.DataArray(
        np.linspace(meta["transform"][2], meta["transform"][2] + meta["transform"][0] * w, w),
        dims="x",
        attrs={"units": "degrees_east", "axis": "X"}
    )
    ds["time"].attrs.update({
        "axis": "T",
        "long_name": "time",
        "standard_name": "time",
    })
    
    # Write NetCDF with compression
    encoding = {
        "rainfall": {"dtype": "float32", "zlib": True, "complevel": 4},
        "water_temp_c": {"dtype": "float32", "zlib": True, "complevel": 4},
        "water_frac": {"dtype": "float32", "zlib": True, "complevel": 4},
        "ndvi": {"dtype": "float32", "zlib": True, "complevel": 4},
    }
    
    print(f"\nWriting NetCDF to {OUTPUT_FILE}...")
    ds.to_netcdf(OUTPUT_FILE, encoding=encoding)
    
    file_size_mb = OUTPUT_FILE.stat().st_size / (1024 * 1024)
    print(f"Done: {OUTPUT_FILE} ({file_size_mb:.1f} MB)")
    print(f"  Variables: rainfall, water_temp_c, water_frac, ndvi")
    print(f"  Shape: ({total_days}, {h}, {w})")
    print(f"  Time range: {all_times[0]} to {all_times[-1]}")


if __name__ == "__main__":
    main()
