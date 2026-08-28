"""AOI — region-agnostic Area of Interest schema (M1.2a).

The AOI is a typed parameter consumed by the data layer (M1.3a) and the ABM
(M1.4). It carries a slug, name, bbox, CRS, ground resolution, scale level
and an optional GADM id. There is no domain (malaria) logic here.

Multi-scale levels (``Scale``) are defined per the design doc:
    REGIONAL    — 1 km grid, no aggregation, raw raster
    NATIONAL    — GADM-2 mean-pool
    CONTINENTAL — 5 km grid + GADM-0 mean-pool, U-Net only
"""
from __future__ import annotations

import json
import math
import os
import re
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

import geopandas as gpd
import pyproj
import shapely.geometry
import yaml
from pydantic import BaseModel, Field, field_validator

if TYPE_CHECKING:
    pass


class Scale(str, Enum):
    """Multi-scale levels per the design doc."""

    REGIONAL = "regional"        # 1 km grid, no aggregation, raw raster
    NATIONAL = "national"        # GADM-2 mean-pool
    CONTINENTAL = "continental"  # 5 km grid + GADM-0 mean-pool, U-Net only


# Mean Earth radius in metres (WGS-84 authalic sphere approximation).
_EARTH_R = 6_371_008.8

# --- YAML registry -----------------------------------------------------------

_AOIS_YAML_PATH = Path(__file__).parent / "aois.yaml"
_registry_cache: dict | None = None


def _load_aois_yaml() -> dict:
    """Load aois.yaml once, cache for the process lifetime."""
    global _registry_cache
    if _registry_cache is None:
        with open(_AOIS_YAML_PATH) as f:
            _registry_cache = yaml.safe_load(f)
    return _registry_cache


def clear_aoi_cache() -> None:
    """Reset the cached YAML registry (useful for testing)."""
    global _registry_cache
    _registry_cache = None


class AOI(BaseModel):
    """Area of Interest — region-agnostic from M1.

    The AOI is a typed parameter; the data layer and the ABM consume
    bbox + CRS + scale + slug. No hardcoded Ghana logic.

    Attributes:
        slug: stable identifier used in file naming (e.g. "ghana", "mozambique").
              Lowercase, [a-z0-9-], no leading/trailing hyphens, no consecutive hyphens.
        name: human-readable name (e.g. "Ghana NMCP AOI").
        bbox: (west, south, east, north) in CRS units. For EPSG:4326, west<east and south<north.
        crs: EPSG code or WKT. Must be parseable by pyproj.CRS.from_user_input.
        resolution_m: cell size in metres on the ground. For EPSG:4326, used to
                      derive degree-per-cell via the AOI centroid latitude.
        scale: REGIONAL/NATIONAL/CONTINENTAL — see ``Scale`` enum.
        gadm_id: optional GADM identifier (e.g. "GHA" for Ghana, "GHA.1_1" for region).
                 When set, ``from_gadm()`` can be used to populate bbox from GADM boundaries.
        iso3: ISO 3166-1 alpha-3 country code (e.g. "GHA"). Required for country-scoped
              data loaders (WorldPop, GADM, livestock); raises ValueError if absent when
              needed. Always lowercase, exactly 3 letters.
    """

    slug: str = Field(..., min_length=1, max_length=64)
    name: str
    bbox: tuple[float, float, float, float]
    crs: str
    resolution_m: int = Field(..., gt=0)
    scale: Scale = Scale.REGIONAL
    gadm_id: str | None = None
    iso3: str | None = None

    model_config = {"frozen": True}

    # -- validators -----------------------------------------------------------

    @field_validator("slug")
    @classmethod
    def _slug_format(cls, v: str) -> str:
        if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", v):
            raise ValueError(
                f"slug must be lowercase [a-z0-9-], no leading/trailing/consecutive hyphens; got {v!r}"
            )
        return v

    @field_validator("iso3")
    @classmethod
    def _iso3_format(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip().upper()
        if not re.fullmatch(r"[A-Z]{3}", v):
            raise ValueError(
                f"iso3 must be 3 letters (ISO 3166-1 alpha-3); got {v!r}"
            )
        return v

    @field_validator("bbox")
    @classmethod
    def _bbox_order(cls, v: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
        w, s, e, n = v
        if not (w < e and s < n):
            raise ValueError(f"bbox must satisfy west<east and south<north; got {v!r}")
        return v

    @field_validator("crs")
    @classmethod
    def _crs_parseable(cls, v: str) -> str:
        try:
            pyproj.CRS.from_user_input(v)
        except Exception as e:
            raise ValueError(f"crs not parseable by pyproj: {v!r} ({e})") from e
        return v

    # -- geometry helpers ----------------------------------------------------

    @property
    def crs_obj(self) -> pyproj.CRS:
        """Parsed CRS as a ``pyproj.CRS`` object."""
        return pyproj.CRS.from_user_input(self.crs)

    @property
    def _is_geographic(self) -> bool:
        return self.crs_obj.is_geographic

    @property
    def _centroid_lat(self) -> float:
        """Centroid latitude in degrees (geographic CRS) or None for projected."""
        _, s, _, n = self.bbox
        return 0.5 * (s + n)

    def _m_per_unit(self) -> tuple[float, float]:
        """Approximate (m_per_unit_x, m_per_unit_y) at the AOI centroid.

        Geographic CRS → great-circle metres per degree. Projected CRS → CRS linear units.
        """
        if self._is_geographic:
            lat_rad = math.radians(self._centroid_lat)
            m_per_deg_lat = (math.pi * _EARTH_R) / 180.0
            m_per_deg_lon = m_per_deg_lat * math.cos(lat_rad)
            return m_per_deg_lon, m_per_deg_lat
        # Projected: assume linear units are metres (UTM, etc.). The CRS conversion factor
        # is reported by pyproj; fall back to 1.0 if unknown.
        cf = self.crs_obj.coordinate_system
        try:
            unit_m = float(cf.unit_conversion_factor) if cf is not None and cf.unit_conversion_factor else 1.0
        except (AttributeError, TypeError):
            unit_m = 1.0
        return unit_m, unit_m

    @property
    def width_m(self) -> float:
        w, _, e, _ = self.bbox
        m_per_x, _ = self._m_per_unit()
        return abs(e - w) * m_per_x

    @property
    def height_m(self) -> float:
        _, s, _, n = self.bbox
        _, m_per_y = self._m_per_unit()
        return abs(n - s) * m_per_y

    @property
    def area_km2(self) -> float:
        return (self.width_m * self.height_m) / 1_000_000.0

    @property
    def geom(self) -> shapely.geometry.Polygon:
        """Bounding box as a shapely Polygon in ``self.crs``."""
        w, s, e, n = self.bbox
        return shapely.geometry.box(w, s, e, n)

    def cells_per_side(self) -> tuple[int, int]:
        """(H, W) cells needed to cover the bbox at ``resolution_m`` (rounded up)."""
        h = int(math.ceil(self.height_m / self.resolution_m))
        w = int(math.ceil(self.width_m / self.resolution_m))
        return h, w

    def to_geoseries(self, crs: str | None = None) -> gpd.GeoSeries:
        """Bounding box as a ``GeoSeries``. ``crs`` defaults to ``self.crs``."""
        return gpd.GeoSeries([self.geom], crs=crs if crs is not None else self.crs)

    # -- I/O -----------------------------------------------------------------

    def to_file(self, path: Path | str) -> Path:
        """Serialize to JSON. Returns the written path."""
        p = Path(path)
        payload = {
            "slug": self.slug,
            "name": self.name,
            "bbox": list(self.bbox),
            "crs": self.crs,
            "resolution_m": self.resolution_m,
            "scale": self.scale.value,
            "gadm_id": self.gadm_id,
            "iso3": self.iso3,
        }
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(payload, indent=2))
        return p

    @classmethod
    def from_file(cls, path: Path | str) -> "AOI":
        """Inverse of ``to_file``."""
        p = Path(path)
        payload = json.loads(p.read_text())
        return cls(
            slug=payload["slug"],
            name=payload["name"],
            bbox=tuple(payload["bbox"]),
            crs=payload["crs"],
            resolution_m=int(payload["resolution_m"]),
            scale=Scale(payload["scale"]),
            gadm_id=payload.get("gadm_id"),
            iso3=payload.get("iso3"),
        )

    # -- constructors --------------------------------------------------------

    @classmethod
    def from_bbox(
        cls,
        west: float, south: float, east: float, north: float,
        crs: str, slug: str, resolution_m: int,
        *,
        name: str | None = None,
        scale: Scale = Scale.REGIONAL,
        iso3: str | None = None,
        gadm_id: str | None = None,
    ) -> "AOI":
        """Build an AOI from an explicit bbox.

        Args:
            iso3: ISO 3166-1 alpha-3 country code (e.g. "GHA"). Required to use
                country-scoped loaders (WorldPop, GADM, livestock); can be set
                later via ``with_iso3()``.
            gadm_id: optional GADM identifier for subnational AOIs.
        """
        return cls(
            slug=slug,
            name=name if name is not None else slug,
            bbox=(float(west), float(south), float(east), float(north)),
            crs=crs,
            resolution_m=resolution_m,
            scale=scale,
            gadm_id=gadm_id,
            iso3=iso3,
        )

    # -- slug registry (reads from aois.yaml) --------------------------------

    @classmethod
    def from_slug(cls, slug: str) -> "AOI":
        """Build an AOI from a slug key (e.g. ``'ghana'``).

        Reads ``aois.yaml`` bundled alongside this module.  Raises
        ``ValueError`` if the slug is not in the registry.
        """
        registry = _load_aois_yaml()
        if slug not in registry:
            raise ValueError(
                f"Unknown AOI slug {slug!r}; available: {sorted(registry)}"
            )
        cfg = registry[slug]
        return cls(
            slug=slug,
            name=cfg.get("name", slug),
            bbox=tuple(cfg["bbox"]),
            crs=cfg["crs"],
            resolution_m=cfg["resolution_m"],
            scale=Scale(cfg.get("scale", "regional")),
            gadm_id=cfg.get("gadm_id"),
            iso3=cfg.get("iso3"),
        )

    @classmethod
    def from_gadm(
        cls,
        gadm_id: str, crs: str, slug: str, resolution_m: int,
        *,
        gadm_path: Path | str | None = None,
        name: str | None = None,
        scale: Scale = Scale.REGIONAL,
        iso3: str | None = None,
    ) -> "AOI":
        """Load an AOI from a GADM file.

        Looks up ``gadm_id`` in the GADM shapefile and computes the bbox from the
        matching geometry. The GADM path resolves in this order:
            1. explicit ``gadm_path`` argument
            2. ``MAL_GADM_PATH`` environment variable
            3. otherwise: ``FileNotFoundError`` with a clear message.

        The id is matched against any ``GID_<n>`` column (GADM-0..GADM-5).
        For country-level ids (e.g. "GHA"), pass ``iso3="GHA"`` so country-scoped
        data loaders work; if omitted, it is inferred from the first three chars
        of the GADM id (uppercased).
        """
        if gadm_path is None:
            env = os.environ.get("MAL_GADM_PATH")
            if not env:
                raise FileNotFoundError(
                    "GADM path not provided: pass gadm_path=... or set MAL_GADM_PATH"
                )
            gadm_path = env

        gdf = gpd.read_file(str(gadm_path))
        gid_col = None
        for col in gdf.columns:
            if col.startswith("GID_") and col[4:].isdigit():
                if gid_col is None or int(col[4:]) > int(gid_col[4:]):
                    gid_col = col
        if gid_col is None:
            raise ValueError(
                f"No GID_<n> column found in {gadm_path}; columns={list(gdf.columns)}"
            )

        match = gdf[gdf[gid_col] == gadm_id]
        if match.empty:
            raise KeyError(
                f"gadm_id {gadm_id!r} not found in {gadm_path} (column {gid_col})"
            )

        geom = match.geometry
        # Reproject if needed so the bbox is in the requested CRS.
        if str(gdf.crs) != str(pyproj.CRS.from_user_input(crs)):
            geom = geom.to_crs(crs)
        minx, miny, maxx, maxy = geom.total_bounds

        # Infer ISO-3 from the first three chars of the GADM id when not given.
        if iso3 is None and re.fullmatch(r"[A-Z]{3}", gadm_id[:3]):
            iso3 = gadm_id[:3]

        return cls(
            slug=slug,
            name=name if name is not None else f"{slug} ({gadm_id})",
            bbox=(float(minx), float(miny), float(maxx), float(maxy)),
            crs=crs,
            resolution_m=resolution_m,
            scale=scale,
            gadm_id=gadm_id,
            iso3=iso3,
        )

    def require_iso3(self) -> str:
        """Return ``iso3`` or raise ``ValueError`` if missing.

        Country-scoped data loaders (WorldPop, GADM, livestock) need the ISO-3
        country code to build download URLs. Call this at the top of any
        loader that requires a country-level identifier.
        """
        if not self.iso3:
            raise ValueError(
                f"AOI {self.slug!r} has no iso3; pass iso3='XXX' to "
                f"from_bbox/from_slug/from_gadm or set it in aois.yaml"
            )
        return self.iso3


__all__ = ["AOI", "Scale", "clear_aoi_cache"]
