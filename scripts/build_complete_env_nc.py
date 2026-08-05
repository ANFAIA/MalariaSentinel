"""build_complete_env_nc: Create complete daily env NC from real data sources.

Combines:
  - CHIRPS daily rainfall (ghana_rainfall_daily_2024_2025_daily.nc)
  - JRC GSW water occurrence (ghana_water_occurrence.tif) for water_frac
  - ERA5 water temperature (ghana_water_temp_2024.tif) for water_temp_c
  - MODIS NDVI (ghana_ndvi_2024.tif) for ndvi

All static layers are broadcast to all days (same value every day).

Usage:
    uv run python scripts/build_complete_env_nc.py
"""
import numpy as np
import rasterio
import xarray as xr
import pathlib

DATA_DIR = pathlib.Path(__file__).resolve().parent.parent / "data" / "ghana"
RAIN_FILE = DATA_DIR / "ghana_rainfall_daily_2024_2025_daily.nc"
WATER_FRAC_FILE = DATA_DIR / "ghana_water_occurrence.tif"  # JRC GSW (static)
WATER_TEMP_FILE = DATA_DIR / "ghana_water_temp_2024.tif"   # ERA5 (annual)
NDVI_FILE = DATA_DIR / "ghana_ndvi_2024.tif"               # MODIS (annual)
OUTPUT_FILE = DATA_DIR / "ghana_regional_2024_2025_env.nc"

NODATA_SENTINEL = -9999.0


def read_static_tif(path: pathlib.Path, target_shape: tuple[int, int]) -> np.ndarray:
    """Read a single-band TIF and return (H, W) float32 array.

    Resamples to target_shape if needed and replaces nodata with NaN.
    """
    with rasterio.open(path) as src:
        nodata = src.nodata
        data = src.read(1).astype(np.float32)  # (H, W)

        # Replace nodata with NaN
        if nodata is not None:
            mask = np.isclose(data, nodata, atol=1.0) | (data == NODATA_SENTINEL)
            data[mask] = np.nan

        # Resample if shape mismatch
        if data.shape != target_shape:
            from rasterio.enums import Resampling
            data = src.read(
                1,
                out_shape=target_shape,
                resampling=Resampling.bilinear,
            ).astype(np.float32)
            if nodata is not None:
                mask = np.isclose(data, nodata, atol=1.0) | (data == NODATA_SENTINEL)
                data[mask] = np.nan

        return data


def main():
    print(f"Reading rainfall: {RAIN_FILE}")
    rain_ds = xr.open_dataset(RAIN_FILE)
    rainfall_raw = rain_ds.rainfall.values  # (731, 779, 551)
    times = rain_ds.time.values
    y = rain_ds.y.values
    x = rain_ds.x.values
    n_days, h, w = rainfall_raw.shape
    target_shape = (h, w)

    print(f"  Shape: ({n_days}, {h}, {w})")
    print(f"  Time: {times[0]} → {times[-1]}")

    # Mask rainfall nodata (-9999) → 0.0 (no rain)
    # Must replace with 0, NOT NaN: NaN rainfall propagates through the
    # C++ climate engine and causes NaN in aquatic dynamics, producing
    # population crashes. The C++ code does NOT check isfinite() for rain.
    rainfall = rainfall_raw.astype(np.float32)
    nodata_mask = rainfall_raw == NODATA_SENTINEL
    nodata_count = int(np.sum(nodata_mask))
    rainfall[nodata_mask] = 0.0
    # Also clamp negative rainfall (artifact of nodata corruption)
    rainfall[rainfall < 0] = 0.0
    print(f"  rainfall nodata (-9999) count: {nodata_count} → replaced with 0.0")

    # JRC GSW water occurrence -> water_frac (static, repeat for all days)
    print(f"\nReading water_frac from: {WATER_FRAC_FILE}")
    water_frac_static = read_static_tif(WATER_FRAC_FILE, target_shape)
    # JRC GSW values are 0-100 (percentage); normalize to 0-1
    if np.nanmax(water_frac_static) > 1.0:
        water_frac_static = water_frac_static / 100.0
        print("  Normalized from percentage to [0,1]")
    # Replace NaN with 0.0 (no water). NaN water_frac causes the C++
    # viability filter (water_frac > 0.05) to reject patches, which is
    # correct but we make it explicit for clarity.
    water_frac_static = np.nan_to_num(water_frac_static, nan=0.0)
    water_frac = np.broadcast_to(water_frac_static, (n_days, h, w)).copy()
    n_viable = int(np.sum(water_frac_static > 0.05))
    print(f"  water_frac: [{water_frac.min():.4f}, {water_frac.max():.4f}], "
          f"mean={water_frac.mean():.4f}")
    print(f"  cells with water_frac > 0.05: {n_viable} / {h * w}")
    if n_viable == 0:
        raise RuntimeError(
            "CRITICAL: 0 viable habitat patches! Check water_occurrence.tif "
            "contains real JRC GSW data, not a fill value."
        )

    # ERA5 water temperature -> water_temp_c (static annual, repeat for all days)
    print(f"\nReading water_temp_c from: {WATER_TEMP_FILE}")
    water_temp_static = read_static_tif(WATER_TEMP_FILE, target_shape)
    # Replace NaN with 25°C (safe tropical default — matches the C++ fallback)
    water_temp_static = np.nan_to_num(water_temp_static, nan=25.0)
    water_temp_c = np.broadcast_to(water_temp_static, (n_days, h, w)).copy()
    print(f"  water_temp_c: [{water_temp_c.min():.1f}, {water_temp_c.max():.1f}], "
          f"mean={water_temp_c.mean():.1f}")

    # MODIS NDVI -> ndvi (static annual, repeat for all days)
    print(f"\nReading ndvi from: {NDVI_FILE}")
    ndvi_static = read_static_tif(NDVI_FILE, target_shape)
    # Replace NaN with 0.5 (moderate vegetation — safe default)
    ndvi_static = np.nan_to_num(ndvi_static, nan=0.5)
    ndvi_static = np.clip(ndvi_static, 0.0, 1.0)
    ndvi = np.broadcast_to(ndvi_static, (n_days, h, w)).copy()
    print(f"  ndvi: [{ndvi.min():.2f}, {ndvi.max():.2f}], "
          f"mean={ndvi.mean():.2f}")

    # Build Dataset
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
        coords={"time": times, "y": y, "x": x},
        attrs={
            "Conventions": "CF-1.8",
            "title": "MalariaSentinel daily env tensor — ghana 2024-2025",
            "aoi_slug": "ghana",
            "scale": "regional",
            "contract_version": "2.0",
            "generator_version": "m2-daily-0.3.0",
        },
    )

    encoding = {v: {"dtype": "float32", "zlib": True, "complevel": 4}
                for v in ["water_frac", "rainfall", "water_temp_c", "ndvi"]}

    print(f"\nWriting: {OUTPUT_FILE}")
    ds.to_netcdf(OUTPUT_FILE, encoding=encoding)
    size_mb = OUTPUT_FILE.stat().st_size / (1024 * 1024)
    print(f"Done: {size_mb:.1f} MB")
    print(f"  Variables: {list(ds.data_vars)}")
    print(f"  Shape: ({n_days}, {h}, {w})")

    # Final summary — critical for debugging
    print(f"\n=== SUMMARY ===")
    print(f"  water_frac:  [{water_frac.min():.4f}, {water_frac.max():.4f}], "
          f"viable cells (>0.05): {int(np.sum(water_frac[0] > 0.05))}")
    print(f"  rainfall:    [{rainfall.min():.1f}, {rainfall.max():.1f}], "
          f"mean={rainfall.mean():.1f}")
    print(f"  water_temp:  [{water_temp_c.min():.1f}, {water_temp_c.max():.1f}], "
          f"mean={water_temp_c.mean():.1f}")
    print(f"  ndvi:        [{ndvi.min():.2f}, {ndvi.max():.2f}], "
          f"mean={ndvi.mean():.2f}")
    print(f"  Any NaN in rainfall? {np.any(np.isnan(rainfall))}")
    print(f"  Any NaN in water_frac? {np.any(np.isnan(water_frac))}")
    print(f"  Any NaN in water_temp? {np.any(np.isnan(water_temp_c))}")
    print(f"  Any NaN in ndvi? {np.any(np.isnan(ndvi))}")


if __name__ == "__main__":
    main()
