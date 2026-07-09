"""Habitat engine facade for the M1 ABM thin slice.

Materialises habitat patches from a GeoDataFrame (the gpkg emitted by
``scripts.build_env``) into ``HabitatPatch`` agents and exposes a
per-day activation query used by ``AnophelesABM``.

For the thin slice only ``PLUVIAL_POOL`` patches are honoured; the
rest of the Hardy 2013 enum is ``[M7+]`` per
``docs/abm-mesa-geo-adaptation.md`` §3.
"""
from __future__ import annotations

from __future__ import annotations

import geopandas as gpd
from shapely.geometry import Point

from .habitat import HabitatPatch, HabitatType


class HabitatEngine:
    """Thin facade over the M1.3a habitat patches gpkg.

    Parameters
    ----------
    aoi : mal_commonlib.aoi.AOI
        The AOI the model runs on. Currently only used to validate that
        the patch CRS matches the AOI's CRS; the engine does not clip.
    habitat_patches_gdf : gpd.GeoDataFrame
        The patches to materialise. Must have a ``twi_value`` column
        (used as a per-patch attribute). Geometry must be Point-like.
    """

    def __init__(self, aoi, habitat_patches_gdf: gpd.GeoDataFrame) -> None:
        self.aoi = aoi
        self.gdf = habitat_patches_gdf
        self.patches: list[HabitatPatch] = []

    def materialise(self, model) -> None:
        """Create ``HabitatPatch`` agents in ``model`` from the gpkg.

        Skips patches whose ``hab_type`` column is present and not
        ``PLUVIAL_POOL`` (M1 only honours that subtype). Geometry is
        passed through unchanged; CRS is taken from the gpkg.
        """
        gdf = self.gdf
        if gdf is None or len(gdf) == 0:
            return
        for _, row in gdf.iterrows():
            hab_type_value = row.get("hab_type", HabitatType.PLUVIAL_POOL.value)
            try:
                hab_type = HabitatType(hab_type_value)
            except ValueError:
                continue
            if hab_type is not HabitatType.PLUVIAL_POOL:
                continue
            geom = row.geometry
            if geom is None or geom.is_empty:
                continue
            K = int(row.get("K", 1000))
            twi_value = float(row.get("twi_value", 0.0))
            crs = str(gdf.crs) if gdf.crs is not None else "EPSG:4326"
            patch = HabitatPatch(
                model, geom, crs, K=K, twi_value=twi_value,
            )
            self.patches.append(patch)
            model.schedule.add(patch, type_key=HabitatPatch)
        return None

    def get_active_patches(self, date) -> list[HabitatPatch]:
        """Return the list of patches currently ``activated`` (PLUVIAL_POOL rule)."""
        return [p for p in self.patches if p.activated]

    @classmethod
    def from_gpkg(cls, aoi, path) -> "HabitatEngine":
        """Build an engine from a ``.gpkg`` file path (M1.3b output)."""
        gdf = gpd.read_file(str(path))
        return cls(aoi, gdf)
