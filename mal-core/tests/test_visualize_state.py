"""Tests for abm/scripts/visualize_state.py (data contract 4.0: raw counts)."""
from __future__ import annotations

import json

import numpy as np
import pytest
import rasterio
from mal_core.abm.scripts.visualize_state import (
    cohort_row_for_day,
    find_state_files,
    main,
    moving_average,
)
from PIL import Image
from rasterio.transform import from_origin


def _write_state_tif(path, counts: np.ndarray) -> None:
    """Write a 2-band raw-count state GeoTIFF (adult_patch_count, adult_cell_count)."""
    height, width = counts.shape
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=2,
        dtype="float32",
        crs="EPSG:4326",
        transform=from_origin(0.0, 1.0, 0.01, 0.01),
    ) as dst:
        dst.write(counts.astype("float32"), 1)
        dst.write(counts.astype("float32"), 2)
        dst.set_band_description(1, "adult_patch_count")
        dst.set_band_description(2, "adult_cell_count")


def test_moving_average_is_trailing_without_zero_padding():
    out = moving_average([10, 20, 30, 40], window=2)
    assert out.tolist() == pytest.approx([10.0, 15.0, 25.0, 35.0])


def test_cohort_row_is_one_based_snapshot_day():
    cohort = {"daily": [{"day": 0, "n_adults": 113}, {"day": 1, "n_adults": 90}]}
    assert cohort_row_for_day(cohort, 1)["n_adults"] == 113
    assert cohort_row_for_day(cohort, 2)["n_adults"] == 90
    assert cohort_row_for_day(cohort, 3) is None
    assert cohort_row_for_day(None, 1) is None


def test_find_state_files_skips_transmission_and_falls_back_to_subdir(tmp_path):
    (tmp_path / "run_day001.tif").write_bytes(b"")
    (tmp_path / "run_transmission_day001.tif").write_bytes(b"")
    files = find_state_files(tmp_path)
    assert [day for _, day in files] == [1]

    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "run_day007.tif").write_bytes(b"")
    empty = tmp_path / "empty"
    empty.mkdir()
    (empty / "nested").mkdir()
    (empty / "nested" / "run_day009.tif").write_bytes(b"")
    assert [day for _, day in find_state_files(empty)] == [9]


def test_main_renders_gif_from_raw_counts(tmp_path):
    counts = np.zeros((12, 16), dtype="float32")
    counts[3, 4] = 1.0     # sparse cell must stay visible on the log scale
    counts[8, 11] = 46.0   # focus peak
    _write_state_tif(tmp_path / "aoi_abm_seed0001_day001.tif", counts)
    _write_state_tif(tmp_path / "aoi_abm_seed0001_day002.tif", counts * 0.5)
    cohort = {
        "n_days": 2,
        "daily": [
            {"day": 0, "n_adults": 47, "n_larvae": 10, "n_eggs": 2, "n_pupae": 1},
            {"day": 1, "n_adults": 23, "n_larvae": 5, "n_eggs": 1, "n_pupae": 1},
        ],
    }
    (tmp_path / "aoi_abm_seed0001_cohort.json").write_text(json.dumps(cohort))

    out = tmp_path / "anim.gif"
    main(
        [
            "--run-dir", str(tmp_path),
            "--output", str(out),
            "--fps", "2",
            "--max-width", "480",
        ]
    )

    assert out.exists()
    with Image.open(out) as im:
        assert im.n_frames == 2
        assert im.size[0] == 480
        assert im.info["duration"] == 500
