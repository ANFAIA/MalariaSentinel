"""Tests for mal_ghana_sim.abm.run (M2 fix — temp_suitability to deg C)."""
from __future__ import annotations

import math
import pathlib

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_bounds

from mal_ghana_sim.abm.run import _load_env_dict


def _write_tiny_env(path: pathlib.Path, temp_suit_arr: np.ndarray) -> None:
    """Write a 4-band env COG with a known temp_suitability band."""
    h, w = temp_suit_arr.shape
    transform = from_bounds(-1.0, 6.0, 1.0, 8.0, w, h)
    profile = {
        "driver": "GTiff", "dtype": "float32", "count": 4, "height": h, "width": w,
        "crs": "EPSG:4326", "transform": transform, "nodata": -9999.0,
        "tiled": False,
    }
    with rasterio.open(str(path), "w", **profile) as dst:
        dst.write(np.full((h, w), 0.5, dtype=np.float32), 1)  # water_frac
        dst.set_band_description(1, "water_frac")
        dst.write(np.full((h, w), 50.0, dtype=np.float32), 2)  # rainfall
        dst.set_band_description(2, "rainfall")
        dst.write(temp_suit_arr.astype(np.float32), 3)  # temp_suitability
        dst.set_band_description(3, "temp_suitability")
        dst.write(np.full((h, w), 0.5, dtype=np.float32), 4)  # ndvi
        dst.set_band_description(4, "ndvi")


def test_water_temp_c_inverts_temp_suitability_to_deg_c(
    tmp_path: pathlib.Path,
) -> None:
    """_load_env_dict must convert the [0, 1] temp_suitability band to deg C.

    Regression test for the 2026-07-14 M2 run that produced suit_max=0
    because temp_suitability (0-1) was passed unchanged to the ABM,
    where it was interpreted as deg C. The EIP formula max(0, T - 16)
    then always returned 0, so the larva -> adult transition never
    fired and the suitability band was empty.
    """
    temp = np.array(
        [[1.0, 0.0],
         [0.5, 0.75]],
        dtype=np.float32,
    )
    env_path = tmp_path / "env.tif"
    _write_tiny_env(env_path, temp)
    env_dict = _load_env_dict(env_path)
    assert "water_temp_c" in env_dict
    from datetime import date
    d = date(2024, 6, 1)
    # Cell (0, 0) -> temp_suitability = 1.0 -> T = 25 - 8*sqrt(0) = 25.0
    t00 = env_dict["water_temp_c"](d, -0.5, 7.5)
    assert abs(t00 - 25.0) < 0.01, f"expected ~25, got {t00}"
    # Cell (0, 1) -> temp_suitability = 0.0 -> T = 25 - 8*sqrt(1) = 17.0
    t01 = env_dict["water_temp_c"](d, 0.5, 7.5)
    assert abs(t01 - 17.0) < 0.01, f"expected ~17, got {t01}"
    # Cell (1, 0) -> temp_suitability = 0.5 -> T = 25 - 8*sqrt(0.5) = 19.34
    t10 = env_dict["water_temp_c"](d, -0.5, 6.5)
    assert abs(t10 - (25.0 - 8.0 * math.sqrt(0.5))) < 0.01, f"expected ~19.34, got {t10}"
    # Cell (1, 1) -> temp_suitability = 0.75 -> T = 25 - 8*sqrt(0.25) = 21.0
    t11 = env_dict["water_temp_c"](d, 0.5, 6.5)
    assert abs(t11 - 21.0) < 0.01, f"expected ~21, got {t11}"


def test_eip_formula_works_with_converted_temp(
    tmp_path: pathlib.Path,
) -> None:
    """The EIP daily GD formula max(0, T - 16) returns positive values
    when the temp_suitability -> deg C conversion is correct.
    """
    temp = np.full((4, 4), 1.0, dtype=np.float32)  # all cells at peak
    env_path = tmp_path / "env.tif"
    _write_tiny_env(env_path, temp)
    env_dict = _load_env_dict(env_path)
    from datetime import date
    t = env_dict["water_temp_c"](date(2024, 6, 1), 0.0, 7.0)
    # EIP_BASE_C = 16, so daily GD = max(0, 25 - 16) = 9.0
    assert abs(t - 25.0) < 0.01
    assert max(0.0, t - 16.0) == 9.0
