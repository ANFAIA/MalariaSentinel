"""build_complete_env_nc: Create complete daily env NC from rainfall + synthetic vars.

Combines CHIRPS daily rainfall with synthetic water_temp_c, water_frac, ndvi
to produce a complete env NC consumable by the C++ ABM's read_env_nc().
"""
import numpy as np
import xarray as xr
import pathlib

DATA_DIR = pathlib.Path(__file__).resolve().parent.parent / "data" / "ghana"
RAIN_FILE = DATA_DIR / "ghana_rainfall_daily_2024_2025_daily.nc"
OUTPUT_FILE = DATA_DIR / "ghana_regional_2024_2025_env.nc"


def main():
    print(f"Reading rainfall: {RAIN_FILE}")
    rain_ds = xr.open_dataset(RAIN_FILE)
    rainfall = rain_ds.rainfall.values  # (731, 779, 551)
    times = rain_ds.time.values
    y = rain_ds.y.values
    x = rain_ds.x.values
    n_days, h, w = rainfall.shape

    print(f"  Shape: ({n_days}, {h}, {w})")
    print(f"  Time: {times[0]} → {times[-1]}")

    # Synthetic water_temp_c: 25°C ± 3°C (tropical)
    np.random.seed(42)
    water_temp_c = (25.0 + 3.0 * np.random.randn(n_days, h, w)).astype(np.float32)
    water_temp_c = np.clip(water_temp_c, 15.0, 35.0)

    # Synthetic water_frac: static 0.01 (mostly land)
    water_frac = np.full((n_days, h, w), 0.01, dtype=np.float32)

    # Synthetic ndvi: 0.5 ± 0.1 (vegetated)
    ndvi = (0.5 + 0.1 * np.random.randn(n_days, h, w)).astype(np.float32)
    ndvi = np.clip(ndvi, 0.0, 1.0)

    print(f"  water_temp_c: [{water_temp_c.min():.1f}, {water_temp_c.max():.1f}]")
    print(f"  water_frac: [{water_frac.min():.2f}, {water_frac.max():.2f}]")
    print(f"  ndvi: [{ndvi.min():.2f}, {ndvi.max():.2f}]")

    # Build Dataset
    ds = xr.Dataset(
        {
            "water_frac": (["time", "y", "x"], water_frac,
                           {"long_name": "JRC GSW open water fraction", "units": "1"}),
            "rainfall": (["time", "y", "x"], rainfall,
                         {"long_name": "CHIRPS v2.0 daily precipitation", "units": "mm/day"}),
            "water_temp_c": (["time", "y", "x"], water_temp_c,
                             {"long_name": "ERA5-Land 2m temperature (daily mean)", "units": "degC"}),
            "ndvi": (["time", "y", "x"], ndvi,
                     {"long_name": "MODIS NDVI", "units": "1"}),
        },
        coords={"time": times, "y": y, "x": x},
        attrs={
            "Conventions": "CF-1.8",
            "title": "MalariaSentinel daily env tensor — ghana 2024-2025",
            "aoi_slug": "ghana",
            "scale": "regional",
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


if __name__ == "__main__":
    main()
