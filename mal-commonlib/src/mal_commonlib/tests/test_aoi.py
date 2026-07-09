"""Tests for mal_commonlib.aoi (M1.2a). Deterministic, no network."""
from __future__ import annotations

import math
from pathlib import Path

import pytest
from pydantic import ValidationError

from mal_commonlib.aoi import AOI, Scale


GHANA_W, GHANA_S, GHANA_E, GHANA_N = -3.5, 4.5, 1.5, 11.5


def test_from_bbox_ghana() -> None:
    a = AOI.from_bbox(GHANA_W, GHANA_S, GHANA_E, GHANA_N, "EPSG:4326", "ghana", 1000)
    assert isinstance(a, AOI)
    assert a.slug == "ghana"
    assert a.crs == "EPSG:4326"
    assert a.scale == Scale.REGIONAL
    assert a.gadm_id is None
    assert a.bbox == (GHANA_W, GHANA_S, GHANA_E, GHANA_N)
    # Ghana AOI at 1 km: width ~5°, height ~7°; at ~8° lat, 1° lon ~ 110 km.
    h, w = a.cells_per_side()
    assert isinstance(h, int) and isinstance(w, int)
    assert h > 0 and w > 0


def test_slug_format_rejects_uppercase() -> None:
    with pytest.raises(ValidationError):
        AOI.from_bbox(GHANA_W, GHANA_S, GHANA_E, GHANA_N, "EPSG:4326", "Ghana", 1000)


def test_slug_format_rejects_consecutive_hyphens() -> None:
    with pytest.raises(ValidationError):
        AOI.from_bbox(GHANA_W, GHANA_S, GHANA_E, GHANA_N, "EPSG:4326", "ghana--test", 1000)


def test_slug_format_rejects_leading_hyphen() -> None:
    with pytest.raises(ValidationError):
        AOI.from_bbox(GHANA_W, GHANA_S, GHANA_E, GHANA_N, "EPSG:4326", "-ghana", 1000)


def test_slug_format_accepts_typical_names() -> None:
    a = AOI.from_bbox(GHANA_W, GHANA_S, GHANA_E, GHANA_N, "EPSG:4326", "mozambique-province", 1000)
    assert a.slug == "mozambique-province"


def test_bbox_order_rejects_inverted() -> None:
    with pytest.raises(ValidationError):
        # west > east
        AOI.from_bbox(1.5, 4.5, -3.5, 11.5, "EPSG:4326", "ghana", 1000)


def test_bbox_order_rejects_equal_edges() -> None:
    with pytest.raises(ValidationError):
        # south == north
        AOI.from_bbox(-3.5, 5.0, 1.5, 5.0, "EPSG:4326", "ghana", 1000)


def test_crs_unparseable_rejects() -> None:
    with pytest.raises(ValidationError):
        AOI.from_bbox(GHANA_W, GHANA_S, GHANA_E, GHANA_N, "not-a-crs", "ghana", 1000)


def test_crs_accepts_wkt() -> None:
    wkt = 'PROJCS["WGS 84 / UTM zone 30N",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]],PROJECTION["Transverse_Mercator"],PARAMETER["latitude_of_origin",0],PARAMETER["central_meridian",-3],PARAMETER["scale_factor",0.9996],PARAMETER["false_easting",500000],PARAMETER["false_northing",0],UNIT["metre",1]]'
    a = AOI.from_bbox(500000.0, 0.0, 500100.0, 100.0, wkt, "ghana", 1000)
    assert a.crs_obj.is_projected


def test_to_from_file_roundtrip(tmp_path: Path) -> None:
    a = AOI.from_bbox(GHANA_W, GHANA_S, GHANA_E, GHANA_N, "EPSG:4326", "ghana", 1000,
                      name="Ghana AOI", scale=Scale.NATIONAL)
    p = a.to_file(tmp_path / "aoi.json")
    assert p.exists()
    a2 = AOI.from_file(p)
    assert a2 == a


def test_to_file_creates_parent_dir(tmp_path: Path) -> None:
    a = AOI.from_bbox(GHANA_W, GHANA_S, GHANA_E, GHANA_N, "EPSG:4326", "ghana", 1000)
    p = a.to_file(tmp_path / "nested" / "deep" / "aoi.json")
    assert p.exists()
    assert a == AOI.from_file(p)


def test_cells_per_side_for_ghana() -> None:
    a = AOI.from_bbox(GHANA_W, GHANA_S, GHANA_E, GHANA_N, "EPSG:4326", "ghana", 1000)
    h, w = a.cells_per_side()
    assert isinstance(h, int) and isinstance(w, int)
    # Ghana bbox is ~5° wide × ~7° tall. At ~8° lat, 1° lon ≈ 110 km → 5*110/1 = 550 cells.
    # Use a generous floor: 1 km grid over Ghana must be > 100 in both dimensions.
    assert h > 100
    assert w > 100


def test_area_km2_sanity_for_ghana() -> None:
    a = AOI.from_bbox(GHANA_W, GHANA_S, GHANA_E, GHANA_N, "EPSG:4326", "ghana", 1000)
    area = a.area_km2
    # Ghana bbox ~5° × 7°. At ~8° lat, area ≈ 5*110 km × 7*111 km ≈ 428,000 km². Real Ghana ≈ 239k.
    # Use a wide band: 200k–600k km². We're testing a bounding box, not the country's outline.
    assert 200_000.0 < area < 600_000.0


def test_width_height_consistent() -> None:
    a = AOI.from_bbox(GHANA_W, GHANA_S, GHANA_E, GHANA_N, "EPSG:4326", "ghana", 1000)
    assert a.width_m > 0
    assert a.height_m > 0
    assert math.isclose(a.area_km2, (a.width_m * a.height_m) / 1_000_000.0, rel_tol=1e-9)


def test_geom_is_polygon_in_self_crs() -> None:
    a = AOI.from_bbox(GHANA_W, GHANA_S, GHANA_E, GHANA_N, "EPSG:4326", "ghana", 1000)
    g = a.geom
    assert g.bounds == (GHANA_W, GHANA_S, GHANA_E, GHANA_N)
    assert g.area > 0


def test_to_geoseries_returns_geoseries() -> None:
    import geopandas as gpd
    a = AOI.from_bbox(GHANA_W, GHANA_S, GHANA_E, GHANA_N, "EPSG:4326", "ghana", 1000)
    gs = a.to_geoseries()
    assert isinstance(gs, gpd.GeoSeries)
    assert len(gs) == 1
    assert str(gs.crs) == a.crs_obj.to_string() or str(gs.crs).upper() == a.crs.upper() or gs.crs.to_epsg() == a.crs_obj.to_epsg()


def test_immutability() -> None:
    a = AOI.from_bbox(GHANA_W, GHANA_S, GHANA_E, GHANA_N, "EPSG:4326", "ghana", 1000)
    with pytest.raises(ValidationError):
        a.bbox = (0.0, 0.0, 1.0, 1.0)  # type: ignore[misc]


def test_resolution_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        AOI.from_bbox(GHANA_W, GHANA_S, GHANA_E, GHANA_N, "EPSG:4326", "ghana", 0)


def test_resolution_must_be_int_compatible() -> None:
    with pytest.raises(ValidationError):
        AOI.from_bbox(GHANA_W, GHANA_S, GHANA_E, GHANA_N, "EPSG:4326", "ghana", 1.5)


def test_from_gadm_missing_path_raises() -> None:
    import os
    old = os.environ.pop("MAL_GADM_PATH", None)
    try:
        with pytest.raises(FileNotFoundError):
            AOI.from_gadm("GHA", "EPSG:4326", "ghana", 1000)
    finally:
        if old is not None:
            os.environ["MAL_GADM_PATH"] = old


def test_from_gadm_env_path_but_no_file_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Set MAL_GADM_PATH to a path that does not exist; read_file should raise (geopandas side).
    monkeypatch.setenv("MAL_GADM_PATH", str(tmp_path / "does-not-exist.shp"))
    with pytest.raises(Exception):  # geopandas raises a FIONA/DataIO error
        AOI.from_gadm("GHA", "EPSG:4326", "ghana", 1000)


def test_scale_default_is_regional() -> None:
    a = AOI.from_bbox(GHANA_W, GHANA_S, GHANA_E, GHANA_N, "EPSG:4326", "ghana", 1000)
    assert a.scale is Scale.REGIONAL


def test_all_scales_constructable() -> None:
    for s in Scale:
        a = AOI.from_bbox(GHANA_W, GHANA_S, GHANA_E, GHANA_N, "EPSG:4326", "ghana", 1000, scale=s)
        assert a.scale is s


def test_equality() -> None:
    a1 = AOI.from_bbox(GHANA_W, GHANA_S, GHANA_E, GHANA_N, "EPSG:4326", "ghana", 1000)
    a2 = AOI.from_bbox(GHANA_W, GHANA_S, GHANA_E, GHANA_N, "EPSG:4326", "ghana", 1000)
    assert a1 == a2
    a3 = AOI.from_bbox(GHANA_W, GHANA_S, GHANA_E, GHANA_N, "EPSG:4326", "ghana", 2000)
    assert a1 != a3
