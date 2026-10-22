"""Regression tests for the wildlife host proxy loader.

The critical case: the habitat-suitability table must stay keyed to the
SOURCE's label codes. When the source swapped ESA WorldCover (codes
10..100) for Dynamic World (codes 0..8) on 2026-10-17, the table kept the
WC keys and every DW label silently mapped to suitability 0.0 — the
wildlife proxy degenerated to {0.15, 0.35} over all of Ghana (water +
remoteness components only). These tests pin the alignment so the failure
mode is a loud table/source mismatch, never a silent 0.
"""
from __future__ import annotations

import numpy as np
import pytest

from mal_commonlib.aoi import AOI
from mal_commonlib.data.loaders import dynamic_world as dw
from mal_commonlib.data.loaders import wildlife as wl


def test_suitability_table_covers_all_dw_codes() -> None:
    """Every DW label code 0-8 must have an explicit, in-range entry."""
    assert set(wl.HABITAT_SUITABILITY) == set(range(9))
    for code, score in wl.HABITAT_SUITABILITY.items():
        assert 0.0 <= score <= 1.0, f"DW code {code} out of range: {score}"


def test_suitability_values_conserve_wc_anchor() -> None:
    """Per-class anchor values carried over from the WC-era table."""
    assert wl.HABITAT_SUITABILITY[1] == pytest.approx(0.9)    # trees
    assert wl.HABITAT_SUITABILITY[5] == pytest.approx(0.7)    # shrub_and_scrub
    assert wl.HABITAT_SUITABILITY[2] == pytest.approx(0.6)    # grass
    assert wl.HABITAT_SUITABILITY[4] == pytest.approx(0.3)    # crops
    assert wl.HABITAT_SUITABILITY[6] == pytest.approx(0.05)   # built
    assert wl.HABITAT_SUITABILITY[7] == pytest.approx(0.2)    # bare
    assert wl.HABITAT_SUITABILITY[0] == pytest.approx(0.0)    # water
    # flooded_vegetation inherits the WC wetland(0.4)/mangrove(0.5) range.
    assert 0.4 <= wl.HABITAT_SUITABILITY[3] <= 0.5


def test_label_mapping_keeps_nodata_and_maps_all_codes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A real (H,W) label plane maps through the table exactly, and NoData
    pixels keep NoData instead of silently becoming 0 suitability."""
    H, W = 4, 5
    labels = np.array(
        [
            [0, 1, 2, 3, 4],
            [5, 6, 7, 8, -9999],
            [-9999, 0, 1, 2, 3],
            [4, 5, 6, 7, 8],
        ],
        dtype=np.int32,
    )
    da = dw.xr.DataArray(
        labels, dims=("y", "x"),
        coords={"y": np.arange(H, dtype=float), "x": np.arange(W, dtype=float)},
        name="label",
    )
    monkeypatch.setattr(wl, "load_dw_label_mode", lambda aoi, **_: da)

    aoi = AOI.from_slug("ghana")
    habitat = wl._load_dw_habitat_pc(aoi, year=2024)

    assert habitat.shape == (H, W)
    # Every in-range code got its table value.
    for r, c in [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4),
                 (1, 0), (1, 1), (1, 2), (1, 3),
                 (2, 1), (2, 2), (2, 3), (2, 4),
                 (3, 0), (3, 1), (3, 2), (3, 3), (3, 4)]:
        want = wl.HABITAT_SUITABILITY[labels[r, c]]
        assert habitat[r, c] == pytest.approx(want), (r, c)
    # NoData pixels keep NoData (not the WC-era silent 0.0).
    assert habitat[1, 4] == wl._NODATA_OUT_SCALAR
    assert habitat[2, 0] == wl._NODATA_OUT_SCALAR


def test_composite_no_longer_degenerates(monkeypatch: pytest.MonkeyPatch) -> None:
    """The 2026-10-18 regression: forest-only AOI must score well above the
    {0.15, 0.35} degenerate values the WC-keyed table produced."""
    H, W = 3, 3
    da = dw.xr.DataArray(
        np.full((H, W), 1, dtype=np.int32),  # all trees (0.9)
        dims=("y", "x"),
        coords={"y": np.arange(H, dtype=float), "x": np.arange(W, dtype=float)},
        name="label",
    )
    monkeypatch.setattr(wl, "load_dw_label_mode", lambda aoi, **_: da)

    # Neutral water (NoData → 0.5) + zero buildings → 0.5*0.9 + 0.3*0.5 + 0.2*1.0
    fake_water = np.full((H, W), wl._NODATA_OUT_SCALAR, dtype=np.float32)
    fake_bld = np.zeros((H, W), dtype=np.float32)

    import mal_commonlib.data.loaders.jrc_gsw as jrc_mod
    import mal_commonlib.data.loaders.buildings as bld_mod

    monkeypatch.setattr(
        jrc_mod, "load_jrc_gsw_habitat_features",
        lambda aoi, **_: _fake_ds({"jrc_persistent": fake_water}),
    )
    monkeypatch.setattr(
        bld_mod, "load_buildings_fraction",
        lambda aoi, cache_dir=None: _fake_da(fake_bld),
    )

    aoi = AOI.from_slug("ghana")
    proxy = wl.load_wildlife_host_proxy(aoi, year=2024)
    vals = np.unique(proxy.values)
    # 0.5*0.9 + 0.3*0.5(water nodata-neutral) + 0.2*1.0(remote) = 0.60
    assert vals.size == 1
    assert float(vals[0]) == pytest.approx(0.5 * 0.9 + 0.3 * 0.5 + 0.2 * 1.0)


def _fake_da(arr: np.ndarray):
    h, w = arr.shape
    return dw.xr.DataArray(
        arr,
        dims=("y", "x"),
        coords={"y": np.arange(h, dtype=float), "x": np.arange(w, dtype=float)},
        name="proxy_component",
    )


def _fake_ds(planes: dict[str, np.ndarray]):
    return dw.xr.Dataset(
        {name: dw.xr.DataArray(arr, dims=("y", "x"))
         for name, arr in planes.items()}
    )
